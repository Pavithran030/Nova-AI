from sqlalchemy.orm import Session
from app.models.policy_config import PolicyConfig
from app.models.recovery_action import RecoveryAction
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.services.classifier import classify_root_cause, classify_transaction

def decide_action(db: Session, entity_type: str, entity_id: str) -> RecoveryAction:
    below_threshold = False

    if entity_type == 'transaction':
        tx = db.query(Transaction).filter(Transaction.id == entity_id).first()
        if not tx:
            raise ValueError(f"Transaction {entity_id} not found")
        root_cause, conf, reason, below_threshold = classify_transaction(db, tx)
    elif entity_type == 'invoice':
        inv = db.query(Invoice).filter(Invoice.id == entity_id).first()
        if not inv:
            raise ValueError(f"Invoice {entity_id} not found")
        root_cause, conf, reason = classify_root_cause(None, inv.status)
    else:
        raise ValueError(f"Unknown entity_type {entity_type}")

    if below_threshold:
        # Below the classifier's empirically-derived confidence threshold —
        # don't trust the automated action, hand off to a human instead.
        action_type = "ESCALATE_TO_HUMAN"
        stop_reason = "low_confidence"
    else:
        policy = db.query(PolicyConfig).filter(PolicyConfig.root_cause == root_cause).first()
        action_type = policy.action_type if policy else "DEFAULT_RETRY"
        stop_reason = None

    action = RecoveryAction(
        entity_type=entity_type,
        entity_id=entity_id,
        root_cause=root_cause,
        root_cause_confidence=conf,
        action_type=action_type,
        stop_reason=stop_reason
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action
