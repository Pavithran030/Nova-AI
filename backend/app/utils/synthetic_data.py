from sqlalchemy.orm import Session
from app.models.merchant import Merchant
from app.models.customer_feature import CustomerFeature
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.models.policy_config import PolicyConfig
from app.models.mandate import Mandate
from app.services.scorer import calculate_payment_probability_ml, expected_recovery_value
from datetime import datetime, timedelta
import random

def seed_policy_config(db: Session):
    policies = [
        {"root_cause": "INSUFFICIENT_FUNDS", "action_type": "delay_retry"},
        {"root_cause": "BANK_TIMEOUT", "action_type": "immediate_retry_with_backoff"},
        {"root_cause": "CARD_EXPIRED", "action_type": "send_update_link"},
        {"root_cause": "MANDATE_REVOKED", "action_type": "trigger_reauth"},
        {"root_cause": "RISK_DECLINE", "action_type": "auto_appeal"},
        {"root_cause": "NETWORK_ERROR", "action_type": "immediate_retry_exponential"},
        {"root_cause": "ABANDONMENT", "action_type": "checkout_nudge"},
        {"root_cause": "OVERDUE", "action_type": "b2b_follow_up"},
    ]
    for p in policies:
        if not db.query(PolicyConfig).filter_by(root_cause=p["root_cause"]).first():
            db.add(PolicyConfig(**p))
    db.commit()

def generate_all_synthetic_data(db: Session):
    seed_policy_config(db)
    
    merchant = Merchant(name="Test Merchant", tenant_id="tenant_123")
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    
    error_codes = ['INSUFF_BALANCE', 'BANK_TIMEOUT_ERROR', 'CARD_EXPIRED_001', 'MANDATE_REVOKED', 'RISK_FLAGGED', 'NETWORK_CONN_FAIL', 'UPI_TIMEOUT']
    
    for i in range(1, 81):
        customer_id = f"cust_{i:03d}"
        on_time = random.uniform(0.3, 0.99)
        feat = CustomerFeature(
            customer_id=customer_id,
            avg_transaction_amount=random.uniform(500, 50000),
            historical_success_rate=random.uniform(0.4, 0.99),
            on_time_payment_rate=on_time,
            total_transactions=random.randint(5, 100)
        )
        db.add(feat)
        db.commit()
        
        has_mandate = random.choice([True, False])
        mandate_id = None
        if has_mandate:
            mandate = Mandate(merchant_id=merchant.id, customer_id=customer_id, status="active", expiry_date=datetime.now() + timedelta(days=365))
            db.add(mandate)
            db.commit()
            db.refresh(mandate)
            mandate_id = mandate.id
        
        created_at = datetime.now() - timedelta(days=random.uniform(0, 7), hours=random.uniform(0, 24))
        amount = random.lognormvariate(8, 1) # Approx 500-50000 range
        amount = min(max(amount, 500), 50000)
        
        if i <= 50:
            tx = Transaction(
                merchant_id=merchant.id,
                customer_id=customer_id,
                amount=amount,
                status="failed",
                error_code=random.choice(error_codes),
                mandate_id=mandate_id,
                created_at=created_at
            )
            db.add(tx)
        elif i <= 70:
            days_overdue = random.randint(1, 30)
            broken_promises = random.randint(0, 3)
            history_len = random.randint(1, 20)
            prob = calculate_payment_probability_ml(
                days_overdue, amount, on_time, broken_promises, history_len, 0
            )
            expected_val = expected_recovery_value(amount, prob)

            inv = Invoice(
                merchant_id=merchant.id,
                customer_id=customer_id,
                amount=amount,
                due_date=created_at,
                status="overdue",
                days_overdue=days_overdue,
                broken_promise_count=broken_promises,
                payment_probability=prob,
                expected_recovery_value=expected_val,
                created_at=created_at
            )
            db.add(inv)
        else:
            tx = Transaction(
                merchant_id=merchant.id,
                customer_id=customer_id,
                amount=amount,
                status="abandoned",
                created_at=created_at
            )
            db.add(tx)
            
    db.commit()
