from datetime import datetime

from pydantic import Field

from app.models.common import MongoDocument, RawPayload, utc_now


class Settlement(MongoDocument):
    user_id: str = Field(min_length=1)
    razorpay_settlement_id: str = Field(min_length=1)
    status: str | None = None
    currency: str = "INR"
    amount: int = Field(ge=0)
    fees: int = Field(default=0, ge=0)
    tax: int = Field(default=0, ge=0)
    utr: str | None = None
    settled_at: datetime | None = None
    raw: RawPayload
    synced_at: datetime = Field(default_factory=utc_now)

