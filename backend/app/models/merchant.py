from sqlalchemy import Column, String, DateTime, func
from app.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Merchant(Base):
    __tablename__ = "merchants"
    
    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    name = Column(String(255), nullable=False)
    tenant_id = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
