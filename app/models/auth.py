from pydantic import BaseModel, Field


class GoogleTokenRequest(BaseModel):
    credential: str = Field(min_length=20, description="Google ID token returned by Google Sign-In")


class SessionUser(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
