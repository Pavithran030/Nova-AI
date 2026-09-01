from datetime import datetime, timedelta

from app.models.merchant import Merchant
from app.models.mandate import Mandate
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.utils.synthetic_data import seed_policy_config
from app.services.orchestrator import process_item

OUTSIDE_WINDOW = datetime(2026, 8, 25, 11, 30, 0)  # 11:30am -- invalid NPCI window
INSIDE_WINDOW = datetime(2026, 8, 25, 14, 0, 0)    # 2:00pm  -- valid NPCI window


def _make_merchant(db):
    m = Merchant(name="Test Merchant", tenant_id="t1")
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _make_mandate(db, merchant, customer_id, attempts_used=0, max_attempts=4):
    m = Mandate(
        merchant_id=merchant.id, customer_id=customer_id, status="active",
        expiry_date=datetime.now() + timedelta(days=365),
        attempts_used=attempts_used, max_attempts=max_attempts,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _make_mandate_tx(db, merchant, mandate, customer_id, error_code="BANK_TIMEOUT_ERROR", attempt_count=0):
    tx = Transaction(
        merchant_id=merchant.id, customer_id=customer_id, amount=1000,
        status="failed", error_code=error_code, mandate_id=mandate.id,
        attempt_count=attempt_count,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def test_attempt_cap_stops_execution_without_incrementing_further(db):
    seed_policy_config(db)
    merchant = _make_merchant(db)
    mandate = _make_mandate(db, merchant, "cust_cap", attempts_used=4, max_attempts=4)
    tx = _make_mandate_tx(db, merchant, mandate, "cust_cap")

    action = process_item(db, "transaction", tx.id, actor="agent", now=INSIDE_WINDOW)

    assert action.outcome == "STOPPED"
    assert action.stop_reason == "max_attempts"
    db.refresh(mandate)
    assert mandate.attempts_used == 4  # unchanged -- no attempt was actually consumed


def test_npci_window_agent_reschedules_baseline_violates(db):
    seed_policy_config(db)
    merchant = _make_merchant(db)

    mandate_a = _make_mandate(db, merchant, "cust_agent")
    tx_a = _make_mandate_tx(db, merchant, mandate_a, "cust_agent")
    action_a = process_item(db, "transaction", tx_a.id, actor="agent", now=OUTSIDE_WINDOW)

    assert action_a.outcome == "SCHEDULED"
    assert action_a.scheduled_for is not None
    db.refresh(mandate_a)
    assert mandate_a.attempts_used == 0  # rescheduled, not consumed

    mandate_b = _make_mandate(db, merchant, "cust_baseline")
    tx_b = _make_mandate_tx(db, merchant, mandate_b, "cust_baseline")
    action_b = process_item(db, "transaction", tx_b.id, actor="baseline", now=OUTSIDE_WINDOW)

    assert action_b.outcome in ("BASELINE_SUCCESS", "BASELINE_FAILED")  # fired anyway
    violation = db.query(AuditLog).filter(
        AuditLog.entity_id == tx_b.id, AuditLog.npci_window == "invalid_violated"
    ).first()
    assert violation is not None


def test_daily_cap_stops_third_action_same_customer_same_day(db):
    seed_policy_config(db)
    merchant = _make_merchant(db)
    customer_id = "cust_daily"

    outcomes = []
    for _ in range(3):
        tx = Transaction(
            merchant_id=merchant.id, customer_id=customer_id, amount=500,
            status="failed", error_code="CARD_EXPIRED_001",
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        outcomes.append(process_item(db, "transaction", tx.id, actor="agent", now=INSIDE_WINDOW))

    assert outcomes[0].outcome in ("SUCCESS", "FAILED")
    assert outcomes[1].outcome in ("SUCCESS", "FAILED")
    assert outcomes[2].outcome == "STOPPED"
    assert outcomes[2].stop_reason == "daily_cap"


def test_single_nudge_cap_for_abandonment(db):
    seed_policy_config(db)
    merchant = _make_merchant(db)
    tx = Transaction(
        merchant_id=merchant.id, customer_id="cust_abandon", amount=750,
        status="abandoned",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    first = process_item(db, "transaction", tx.id, actor="agent", now=INSIDE_WINDOW)
    second = process_item(db, "transaction", tx.id, actor="agent", now=INSIDE_WINDOW + timedelta(hours=1))

    assert first.outcome in ("SUCCESS", "FAILED")
    assert second.outcome == "STOPPED"
    assert second.stop_reason == "single_nudge_cap"


def test_audit_log_written_for_executed_action(db):
    seed_policy_config(db)
    merchant = _make_merchant(db)
    tx = Transaction(
        merchant_id=merchant.id, customer_id="cust_audit", amount=900,
        status="failed", error_code="NETWORK_CONN_FAIL",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    action = process_item(db, "transaction", tx.id, actor="agent", now=INSIDE_WINDOW)

    log = db.query(AuditLog).filter(AuditLog.entity_id == tx.id).first()
    assert log is not None
    assert log.actor == "agent"
    assert action.root_cause in log.reasoning


def test_baseline_run_does_not_mutate_real_attempt_budget(db):
    """Baseline is a read-only counterfactual -- it evaluates against the
    real current budget but must never consume it, since two parallel
    decision systems can't both really retry the same live mandate."""
    seed_policy_config(db)
    merchant = _make_merchant(db)
    mandate = _make_mandate(db, merchant, "cust_shadow", attempts_used=0, max_attempts=4)
    tx = _make_mandate_tx(db, merchant, mandate, "cust_shadow")

    process_item(db, "transaction", tx.id, actor="baseline", now=INSIDE_WINDOW)

    db.refresh(mandate)
    assert mandate.attempts_used == 0
