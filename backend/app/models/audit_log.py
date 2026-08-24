from sqlalchemy import Column, String, Integer, DateTime, func, JSON
from app.database import Base
from app.models.merchant import generate_uuid

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False, index=True)
    action_type = Column(String(100), nullable=False)
    reasoning = Column(String, nullable=True)
    actor = Column(String(100), default="system")
    npci_window = Column(String(50), nullable=True)
    attempt_number = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True) # renamed from metadata to avoid conflict
    timestamp = Column(DateTime, default=func.now())
