from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.models.recovery_action import RecoveryAction
from datetime import datetime

def run_baseline_policy(db: Session):
    # Naive baseline policy (retry everything, ignore windows)
    transactions = db.query(Transaction).filter(Transaction.status.in_(["failed", "abandoned"])).all()
    invoices = db.query(Invoice).filter(Invoice.status == "overdue").order_by(Invoice.days_overdue.desc()).all()
    
    actions = []
    for tx in transactions:
        action = RecoveryAction(
            entity_type="transaction",
            entity_id=tx.id,
            root_cause="UNKNOWN",
            action_type="IMMEDIATE_RETRY",
            executed_at=datetime.now(),
            outcome="BASELINE_EXECUTED"
        )
        db.add(action)
        actions.append(action)
        
    for inv in invoices:
        action = RecoveryAction(
            entity_type="invoice",
            entity_id=inv.id,
            root_cause="UNKNOWN",
            action_type="FOLLOW_UP",
            executed_at=datetime.now(),
            outcome="BASELINE_EXECUTED"
        )
        db.add(action)
        actions.append(action)
        
    db.commit()
    return len(actions)
