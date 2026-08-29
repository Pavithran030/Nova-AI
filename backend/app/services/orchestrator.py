from sqlalchemy.orm import Session
from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.services.classifier import classify_root_cause
from app.services.policy_engine import decide_action
from app.services.executor import execute_action
from app.utils.npci import is_valid_npci_window, get_next_valid_window, check_attempt_budget
from datetime import datetime
import random

def process_item(db: Session, entity_type: str, entity_id: str, actor="agent"):
    # Actor can be 'agent' or 'baseline'
    action = decide_action(db, entity_type, entity_id)
    
    # NPCI check for mandates (only if agent)
    in_window = True
    if actor == "agent" and entity_type == "transaction":
        tx = db.query(Transaction).filter(Transaction.id == entity_id).first()
        if tx and tx.mandate_id:
            in_window = is_valid_npci_window(datetime.now())
            if not in_window:
                # Need to schedule instead
                action.scheduled_for = get_next_valid_window(datetime.now())
    
    # Execute action
    exec_res = execute_action(action.action_type, entity_type, entity_id)
    action.channel = exec_res["channel"]
    action.content_sent = exec_res["content_sent"]
    action.executed_at = datetime.now()
    
    # Simulate outcome (baseline ~30-36%, agent ~65-72%)
    prob = 0.68 if actor == "agent" else 0.33
    if random.random() < prob:
        action.outcome = "SUCCESS" if actor == "agent" else "BASELINE_SUCCESS"
    else:
        action.outcome = "FAILED" if actor == "agent" else "BASELINE_FAILED"

    # Only the real agent run updates live entity state — a baseline run is
    # a shadow comparison for reporting and must never mutate actual data.
    if actor == "agent" and action.outcome == "SUCCESS":
        if entity_type == "transaction" and tx is not None:
            tx.status = "recovered"
        elif entity_type == "invoice":
            inv = db.query(Invoice).filter(Invoice.id == entity_id).first()
            if inv:
                inv.status = "paid"

    db.commit()
    db.refresh(action)
    
    # Audit Log
    log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action_type=action.action_type,
        reasoning=f"{actor} processed item based on root cause {action.root_cause}",
        actor=actor,
        npci_window="valid" if in_window else "invalid",
        timestamp=datetime.now()
    )
    db.add(log)
    db.commit()
    
    return action
