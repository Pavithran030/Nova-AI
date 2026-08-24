from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.webhook import PaymentEvent, InvoiceEvent
from app.models.transaction import Transaction
from app.models.invoice import Invoice

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/payment-event")
def handle_payment_event(event: PaymentEvent, db: Session = Depends(get_db)):
    tx = Transaction(
        id=event.transaction_id,
        merchant_id=event.merchant_id,
        customer_id=event.customer_id,
        amount=event.amount,
        currency=event.currency,
        status=event.status,
        error_code=event.error_code,
        error_description=event.error_description,
        mandate_id=event.mandate_id
    )
    db.add(tx)
    db.commit()
    return {"status": "success", "id": tx.id}

@router.post("/invoice-overdue")
def handle_invoice_overdue(event: InvoiceEvent, db: Session = Depends(get_db)):
    inv = Invoice(
        id=event.invoice_id,
        merchant_id=event.merchant_id,
        customer_id=event.customer_id,
        amount=event.amount,
        due_date=event.due_date,
        status=event.status
    )
    db.add(inv)
    db.commit()
    return {"status": "success", "id": inv.id}
