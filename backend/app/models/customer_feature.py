from sqlalchemy import Column, String, Integer, Float, DateTime, func
from app.database import Base

class CustomerFeature(Base):
    __tablename__ = "customer_features"
    
    customer_id = Column(String(36), primary_key=True, index=True)
    avg_transaction_amount = Column(Float, default=0.0)
    historical_success_rate = Column(Float, default=0.0)
    payment_frequency = Column(String(50), nullable=True)
    typical_payment_day = Column(Integer, nullable=True)
    on_time_payment_rate = Column(Float, default=0.0)
    total_transactions = Column(Integer, default=0)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
