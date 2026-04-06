from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/protocol_bot"

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_db_url_scheme(cls, v: str) -> str:
        """Railway injects DATABASE_URL with postgres:// or postgresql:// scheme.
        SQLAlchemy asyncpg driver requires postgresql+asyncpg://."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    anthropic_api_key: str = ""
    openai_api_key: str = ""  # Used for Whisper STT (optional)
    debug: bool = False

    # YooKassa payment settings
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""

    # Webhook server port. Railway injects PORT automatically; falls back to 8080.
    webhook_port: int = 8080
    port: int = 8080  # Railway's injected PORT env var (used as alias)

    # Comma-separated Telegram user IDs allowed to use /admin
    # e.g. ADMIN_USER_IDS=123456789,987654321
    admin_user_ids: List[int] = []


settings = Settings()
