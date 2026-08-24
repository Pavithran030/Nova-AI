from sqlalchemy import Column, String, Integer, DateTime, func, JSON, Boolean
from app.database import Base
from app.models.merchant import generate_uuid

class PolicyConfig(Base):
    __tablename__ = "policy_config"
    
    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    root_cause = Column(String(100), nullable=False, unique=True)
    action_type = Column(String(100), nullable=False)
    action_sequence = Column(JSON, nullable=True)
    max_attempts = Column(Integer, default=3)
    allowed_windows = Column(JSON, nullable=True)
    escalation_threshold = Column(Integer, nullable=True)
    daily_cap = Column(Integer, default=2)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
