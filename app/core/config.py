from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables and a local .env file."""

    app_name: str = "FinCore AI API"
    environment: str = "development"
    mongodb_uri: str
    mongodb_database: str = "bitwise"
    google_client_id: str
    jwt_secret: str
    jwt_expire_minutes: int = 480
    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    fernet_key: str
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
