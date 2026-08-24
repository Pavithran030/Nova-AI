from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, func
from app.database import Base
from app.models.merchant import generate_uuid

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    merchant_id = Column(String(36), ForeignKey("merchants.id"), nullable=False)
    customer_id = Column(String(36), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False)
    days_overdue = Column(Integer, default=0)
    broken_promise_count = Column(Integer, default=0)
    payment_probability = Column(Float, nullable=True)
    expected_recovery_value = Column(Float, nullable=True)
    followup_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
