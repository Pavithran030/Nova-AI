from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from app.database import Base
from app.models.merchant import generate_uuid

class Mandate(Base):
    __tablename__ = "mandates"
    
    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    merchant_id = Column(String(36), ForeignKey("merchants.id"), nullable=False)
    customer_id = Column(String(36), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    expiry_date = Column(DateTime, nullable=False)
    max_attempts = Column(Integer, default=4)
    attempts_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
