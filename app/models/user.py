from datetime import datetime

from pydantic import EmailStr, Field

from app.models.common import MongoDocument, utc_now


class User(MongoDocument):
    google_sub: str = Field(min_length=1, description="Stable Google subject identifier")
    email: EmailStr
    display_name: str | None = None
    avatar_url: str | None = None
    last_login_at: datetime | None = None
    razorpay_credentials_encrypted: str | None = None
    credential_updated_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)

