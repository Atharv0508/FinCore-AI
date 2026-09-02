from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.common import MongoDocument, utc_now


class Match(MongoDocument):
    user_id: str = Field(min_length=1)
    invoice_id: str
    payment_ids: list[str] = Field(default_factory=list)
    settlement_ids: list[str] = Field(default_factory=list)
    classification: Literal["Paid", "Partial", "Unpaid", "Exception"]
    match_tier: int = Field(ge=1, le=4)
    confidence: float = Field(ge=0, le=1)
    evidence: list[dict] = Field(default_factory=list)
    settlement_delta: int | None = None
    explanation: str | None = None
    reconciled_at: datetime = Field(default_factory=utc_now)

