from sqlalchemy import Column, String, Integer, Float, DateTime, func, JSON
from app.database import Base
from app.models.merchant import generate_uuid

class RecoveryAction(Base):
    __tablename__ = "recovery_actions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    entity_type = Column(String(50), nullable=False) # 'transaction' or 'invoice'
    entity_id = Column(String(36), nullable=False, index=True)
    root_cause = Column(String(100), nullable=True)
    root_cause_confidence = Column(Float, nullable=True)
    action_type = Column(String(100), nullable=False)
    actor = Column(String(20), default="agent")  # 'agent' or 'baseline' -- lets daily-cap
    # counting and reporting scope correctly per actor, since two shadow runs
    # (agent vs baseline) over the same customer/day must not share one budget.
    channel = Column(String(50), nullable=True)
    content_sent = Column(String, nullable=True)
    decided_at = Column(DateTime, default=func.now())
    executed_at = Column(DateTime, nullable=True)
    scheduled_for = Column(DateTime, nullable=True)
    outcome = Column(String(50), nullable=True)
    stop_reason = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now())
