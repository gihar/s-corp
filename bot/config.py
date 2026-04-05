from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/protocol_bot"
    anthropic_api_key: str = ""
    openai_api_key: str = ""  # Used for Whisper STT (optional)
    debug: bool = False

    # YooKassa payment settings
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""

    # Webhook server (receives YooKassa payment notifications)
    webhook_port: int = 8080


settings = Settings()
