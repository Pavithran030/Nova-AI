"""
Nova — full historical dataset generator, for end-to-end testing.

Unlike synthetic_data.py (a small, unprocessed batch used by the
/simulate/generate-batch demo endpoint), this script:
  1. Builds a larger customer base with mandates spread realistically over
     the past two years (so mandate_age_days is real, not ~0 for everyone).
  2. Generates transactions/invoices/abandonments spread over `days_back`
     days, with every one of the 6 ML root-cause buckets explicitly
     represented via realistic error codes (not left to random chance).
  3. Runs a large fraction of that history through the REAL pipeline
     (classify_transaction -> decide_action -> execute_action, via
     orchestrator.process_item) for both "agent" and a "baseline" shadow
     run, so recovery_actions and audit_log end up with genuine,
     classifier-driven history instead of empty tables.

This exercises the actual wired ML classifier/scorer, the escalation path,
and NPCI logging under real volume — the point is to test the application,
not just decorate the database.

Usage (from the backend/ directory, with the venv active):
    python -m app.utils.generate_history
"""

import random
from datetime import datetime, timedelta

from app.database import SessionLocal, engine, Base
from app.models.merchant import Merchant
from app.models.customer_feature import CustomerFeature
from app.models.mandate import Mandate
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from app.utils.synthetic_data import seed_policy_config
from app.services.orchestrator import process_item
from app.services.scorer import calculate_payment_probability_ml, expected_recovery_value

# Explicit templates so every root cause the classifier was trained on is
# guaranteed real, meaningful volume — not left to a random error-code pick.
ERROR_CODE_TEMPLATES = {
    "INSUFFICIENT_FUNDS": ["INSUFF_BALANCE", "NSF_ERROR", "LOW_BAL_DECLINE"],
    "BANK_TIMEOUT": ["BANK_TIMEOUT_ERROR", "UPI_TIMEOUT", "GATEWAY_TIMEOUT"],
    "CARD_EXPIRED": ["CARD_EXPIRED_001", "EXP_CARD_DECLINE"],
    "MANDATE_REVOKED": ["MANDATE_REVOKED", "MANDATE_EXPIRED"],
    "RISK_DECLINE": ["RISK_FLAGGED", "FRAUD_SUSPECTED_DECLINE"],
    "NETWORK_ERROR": ["NETWORK_CONN_FAIL", "CONN_RESET"],
}
ROOT_CAUSES = list(ERROR_CODE_TEMPLATES.keys())


def _random_amount(mean_log=8.0, sigma=1.0, lo=300, hi=80000):
    return min(max(random.lognormvariate(mean_log, sigma), lo), hi)


def generate_history(
    db,
    num_customers=120,
    days_back=45,
    txns_per_day_range=(4, 10),
    invoices_total=40,
    abandoned_total=25,
    process_fraction=0.85,
    baseline_fraction=0.4,
):
    seed_policy_config(db)

    merchant = Merchant(name="Test Merchant", tenant_id="tenant_history_001")
    db.add(merchant)
    db.commit()
    db.refresh(merchant)

    # --- Customers, customer features, and mandates with realistic ages ---
    customers = []
    for i in range(1, num_customers + 1):
        customer_id = f"cust_{i:04d}"
        on_time = random.uniform(0.2, 0.99)
        success_rate = random.uniform(0.3, 0.99)
        total_transactions = random.randint(3, 150)
        feat = CustomerFeature(
            customer_id=customer_id,
            avg_transaction_amount=random.uniform(500, 60000),
            historical_success_rate=success_rate,
            on_time_payment_rate=on_time,
            total_transactions=total_transactions,
        )
        db.add(feat)

        mandate = None
        if random.random() < 0.6:
            # Spread mandate creation over the past 2 years, not "now" for
            # every mandate, so mandate_age_days is a real, varied signal.
            created_at = datetime.now() - timedelta(days=random.uniform(10, 730))
            mandate = Mandate(
                merchant_id=merchant.id,
                customer_id=customer_id,
                status=random.choice(["active", "active", "active", "expired", "revoked"]),
                expiry_date=created_at + timedelta(days=365),
                created_at=created_at,
            )
            db.add(mandate)
        customers.append({
            "customer_id": customer_id,
            "on_time": on_time,
            "history_len": total_transactions,
            "mandate": mandate,
        })

    db.commit()
    for c in customers:
        if c["mandate"] is not None:
            db.refresh(c["mandate"])

    # --- Transactions: every root cause explicit, spread over days_back days ---
    all_transactions = []
    for day_offset in range(days_back):
        day_dt = datetime.now() - timedelta(days=day_offset)
        for _ in range(random.randint(*txns_per_day_range)):
            customer = random.choice(customers)
            root_cause = random.choice(ROOT_CAUSES)
            error_code = random.choice(ERROR_CODE_TEMPLATES[root_cause])
            created_at = day_dt - timedelta(hours=random.uniform(0, 24))

            tx = Transaction(
                merchant_id=merchant.id,
                customer_id=customer["customer_id"],
                amount=_random_amount(),
                status="failed",
                error_code=error_code,
                error_description=f"Simulated {root_cause.lower()} failure",
                mandate_id=customer["mandate"].id if customer["mandate"] else None,
                attempt_count=random.randint(0, 2),
                created_at=created_at,
            )
            db.add(tx)
            all_transactions.append(tx)

    # --- Abandoned checkouts ---
    for _ in range(abandoned_total):
        customer = random.choice(customers)
        tx = Transaction(
            merchant_id=merchant.id,
            customer_id=customer["customer_id"],
            amount=_random_amount(mean_log=7.5, lo=200, hi=40000),
            status="abandoned",
            created_at=datetime.now() - timedelta(days=random.uniform(0, days_back)),
        )
        db.add(tx)
        all_transactions.append(tx)

    # --- Overdue invoices, varying days-overdue / broken-promise history ---
    all_invoices = []
    for _ in range(invoices_total):
        customer = random.choice(customers)
        days_overdue = random.randint(1, 90)
        due_date = datetime.now() - timedelta(days=days_overdue)
        amount = _random_amount(mean_log=9.0, lo=2000, hi=300000)
        broken_promises = random.randint(0, 3)
        followup_count = random.randint(0, 4)

        # Same ML scorer the live app uses — without this, payment_probability
        # and expected_recovery_value stay NULL and /recovery/queue's B2B
        # expected-value ranking silently degrades to date-sort for everyone.
        prob = calculate_payment_probability_ml(
            days_overdue, amount, customer["on_time"], broken_promises,
            customer["history_len"], followup_count,
        )
        expected_val = expected_recovery_value(amount, prob)

        inv = Invoice(
            merchant_id=merchant.id,
            customer_id=customer["customer_id"],
            amount=amount,
            due_date=due_date,
            status="overdue",
            days_overdue=days_overdue,
            broken_promise_count=broken_promises,
            payment_probability=prob,
            expected_recovery_value=expected_val,
            followup_count=followup_count,
            created_at=due_date,
        )
        db.add(inv)
        all_invoices.append(inv)

    db.commit()
    for tx in all_transactions:
        db.refresh(tx)
    for inv in all_invoices:
        db.refresh(inv)

    # --- Run a large fraction through the REAL pipeline ---
    processed = {"agent": 0, "baseline": 0, "skipped": 0}
    for tx in all_transactions:
        if random.random() > process_fraction:
            processed["skipped"] += 1
            continue
        process_item(db, "transaction", tx.id, actor="agent")
        processed["agent"] += 1
        if random.random() < baseline_fraction:
            process_item(db, "transaction", tx.id, actor="baseline")
            processed["baseline"] += 1

    for inv in all_invoices:
        if random.random() > process_fraction:
            processed["skipped"] += 1
            continue
        process_item(db, "invoice", inv.id, actor="agent")
        processed["agent"] += 1
        if random.random() < baseline_fraction:
            process_item(db, "invoice", inv.id, actor="baseline")
            processed["baseline"] += 1

    return {
        "merchant_id": merchant.id,
        "customers": len(customers),
        "transactions": len(all_transactions),
        "invoices": len(all_invoices),
        "processed": processed,
    }


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Wipe existing data first so this is a clean, reproducible test run.
        for model in [AuditLog, RecoveryAction, Invoice, Transaction, Mandate, CustomerFeature, Merchant]:
            db.query(model).delete()
        db.commit()

        summary = generate_history(db)
        print("History generated successfully:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
