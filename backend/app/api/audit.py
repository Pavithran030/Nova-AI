from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.audit_log import AuditLog
from typing import Optional

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/log")
def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
        
    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    offset = (page - 1) * page_size
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size).all()
    
    return {
        "items": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/{entity_type}/{entity_id}")
def get_entity_audit(entity_type: str, entity_id: str, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).filter(
        AuditLog.entity_type == entity_type,
        AuditLog.entity_id == entity_id
    ).order_by(AuditLog.timestamp.desc()).all()
    return logs
