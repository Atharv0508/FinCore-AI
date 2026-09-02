from typing import Literal

from pydantic import BaseModel, Field


class AIExceptionReasoning(BaseModel):
    """Validated conclusion returned by Grok for a Tier-4 exception."""

    likely_cause: str = Field(min_length=1, max_length=500)
    recommended_action: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0, le=1)
    severity: Literal["low", "medium", "high"]
    requires_human_review: bool
    evidence_refs: list[str] = Field(default_factory=list, max_length=10)
