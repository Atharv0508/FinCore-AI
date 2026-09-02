from datetime import datetime

from pydantic import Field

from app.models.common import MongoDocument, RawPayload, utc_now


class Invoice(MongoDocument):
    user_id: str = Field(min_length=1)
    razorpay_invoice_id: str = Field(min_length=1)
    invoice_number: str | None = None
    status: str | None = None
    customer_email: str | None = None
    customer_name: str | None = None
    currency: str = "INR"
    amount: int = Field(ge=0, description="Amount in the smallest currency unit")
    amount_paid: int = Field(default=0, ge=0)
    issued_at: datetime | None = None
    due_at: datetime | None = None
    paid_at: datetime | None = None
    raw: RawPayload
    synced_at: datetime = Field(default_factory=utc_now)

