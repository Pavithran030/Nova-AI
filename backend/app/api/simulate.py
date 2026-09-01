from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.synthetic_data import generate_all_synthetic_data
from app.services.orchestrator import process_item
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from datetime import datetime

router = APIRouter(prefix="/simulate", tags=["simulate"])

@router.post("/generate-batch")
def generate_batch(db: Session = Depends(get_db)):
    # Clear existing data
    db.query(RecoveryAction).delete()
    db.query(AuditLog).delete()
    db.query(Transaction).delete()
    db.query(Invoice).delete()
    db.commit()
    
    generate_all_synthetic_data(db)
    return {"status": "success", "message": "Synthetic data generated"}

@router.post("/run-baseline")
def run_baseline(db: Session = Depends(get_db)):
    db.query(RecoveryAction).filter(RecoveryAction.actor == "baseline").delete()
    db.query(AuditLog).filter(AuditLog.actor == "baseline").delete()
    db.commit()
    
    txs = db.query(Transaction).filter(Transaction.status.in_(["failed", "abandoned"])).all()
    invs = db.query(Invoice).filter(Invoice.status == "overdue").all()
    
    count = 0
    for tx in txs:
        process_item(db, "transaction", tx.id, actor="baseline")
        count += 1
    for inv in invs:
        process_item(db, "invoice", inv.id, actor="baseline")
        count += 1
        
    return {"status": "success", "actions_executed": count}

@router.post("/run-agent")
def run_agent(db: Session = Depends(get_db)):
    db.query(RecoveryAction).filter(RecoveryAction.actor == "agent").delete()
    db.query(AuditLog).filter(AuditLog.actor == "agent").delete()
    db.commit()
    
    txs = db.query(Transaction).filter(Transaction.status.in_(["failed", "abandoned"])).all()
    invs = db.query(Invoice).filter(Invoice.status == "overdue").all()
    
    count = 0
    for tx in txs:
        process_item(db, "transaction", tx.id, actor="agent")
        count += 1
    for inv in invs:
        process_item(db, "invoice", inv.id, actor="agent")
        count += 1
        
    return {"status": "success", "actions_executed": count}
