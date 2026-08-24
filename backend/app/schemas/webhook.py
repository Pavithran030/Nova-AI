from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PaymentEvent(BaseModel):
    transaction_id: str
    merchant_id: str
    customer_id: str
    amount: float
    currency: str = "INR"
    status: str
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    mandate_id: Optional[str] = None
    timestamp: datetime = datetime.now()

class InvoiceEvent(BaseModel):
    invoice_id: str
    merchant_id: str
    customer_id: str
    amount: float
    due_date: datetime
    status: str
    timestamp: datetime = datetime.now()
