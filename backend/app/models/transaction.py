from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, func
from app.database import Base
from app.models.merchant import generate_uuid

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    merchant_id = Column(String(36), ForeignKey("merchants.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="INR")
    status = Column(String(50), nullable=False)
    error_code = Column(String(100), nullable=True)
    error_description = Column(String(255), nullable=True)
    mandate_id = Column(String(36), ForeignKey("mandates.id"), nullable=True)
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=4)
    last_attempt_at = Column(DateTime, nullable=True)
    customer_id = Column(String(36), nullable=False, index=True)
    device_fingerprint = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
