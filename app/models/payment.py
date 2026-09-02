from datetime import datetime

from pydantic import Field

from app.models.common import MongoDocument, RawPayload, utc_now


class Payment(MongoDocument):
    user_id: str = Field(min_length=1)
    razorpay_payment_id: str = Field(min_length=1)
    invoice_id: str | None = None
    order_id: str | None = None
    settlement_id: str | None = None
    email: str | None = None
    status: str | None = None
    method: str | None = None
    currency: str = "INR"
    amount: int = Field(ge=0)
    fee: int | None = Field(default=None, ge=0)
    tax: int | None = Field(default=None, ge=0)
    captured_at: datetime | None = None
    raw: RawPayload
    synced_at: datetime = Field(default_factory=utc_now)
