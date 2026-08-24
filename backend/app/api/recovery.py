from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.orchestrator import process_item
from app.models.recovery_action import RecoveryAction
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.services.classifier import classify_root_cause

router = APIRouter(prefix="/recovery", tags=["recovery"])

@router.get("/queue")
def get_recovery_queue(db: Session = Depends(get_db)):
    txs = db.query(Transaction).filter(Transaction.status.in_(["failed", "abandoned"])).all()
    invs = db.query(Invoice).filter(Invoice.status == "overdue").all()
    
    items = []
    for tx in txs:
        rc, conf, _ = classify_root_cause(tx.error_code, tx.status)
        items.append({
            "id": tx.id,
            "entity_type": "transaction",
            "entity_id": tx.id,
            "amount": tx.amount,
            "root_cause": rc,
            "confidence": conf,
            "status": tx.status,
            "next_action": "delay_retry" if rc == "INSUFFICIENT_FUNDS" else "immediate_retry",
            "scheduled_for": None,
            "attempt_count": tx.attempt_count,
            "max_attempts": tx.max_attempts,
            "customer_id": tx.customer_id,
            "created_at": tx.created_at
        })
        
    for inv in invs:
        rc, conf, _ = classify_root_cause(None, inv.status)
        items.append({
            "id": inv.id,
            "entity_type": "invoice",
            "entity_id": inv.id,
            "amount": inv.amount,
            "root_cause": rc,
            "confidence": conf,
            "status": inv.status,
            "next_action": "b2b_follow_up",
            "scheduled_for": None,
            "attempt_count": inv.followup_count,
            "max_attempts": 3,
            "customer_id": inv.customer_id,
            "created_at": inv.created_at,
            "expected_recovery_value": inv.expected_recovery_value or 0.0,
            "days_overdue": inv.days_overdue
        })
        
    # Sort invoices by expected_recovery_value DESC, txs just by created_at DESC for now
    items.sort(key=lambda x: (x.get("expected_recovery_value", 0) or 0, x["created_at"]), reverse=True)
        
    return {"items": items, "total": len(items)}

@router.post("/{entity_type}/{id}/execute")
def execute_recovery(entity_type: str, id: str, db: Session = Depends(get_db)):
    try:
        action = process_item(db, entity_type, id)
        return {"status": "success", "action_id": action.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{id}/status")
def get_recovery_status(id: str, db: Session = Depends(get_db)):
    action = db.query(RecoveryAction).filter(RecoveryAction.id == id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action
