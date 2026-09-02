from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.common import MongoDocument, utc_now


class ExceptionRecord(MongoDocument):
    user_id: str = Field(min_length=1)
    invoice_id: str | None = None
    payment_id: str | None = None
    settlement_id: str | None = None
    match_id: str | None = None
    category: str
    status: Literal["open", "resolved", "ignored"] = "open"
    severity: Literal["low", "medium", "high"] = "medium"
    details: dict = Field(default_factory=dict)
    ai_reasoning: dict | None = None
    resolved_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)

