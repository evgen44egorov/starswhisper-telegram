from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: SecretStr = Field(alias="BOT_TOKEN", min_length=20)
    bot_env: str = Field(default="dev", alias="BOT_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./astrobot.db",
        alias="DATABASE_URL",
    )
    ai_provider: str = Field(default="demo", alias="AI_PROVIDER")
    ai_api_key: SecretStr | None = Field(default=None, alias="AI_API_KEY")
    ai_model: str = Field(default="gpt-4.1-mini", alias="AI_MODEL")
    ai_timeout_seconds: int = Field(
        default=90,
        alias="AI_TIMEOUT_SECONDS",
        ge=10,
        le=180,
    )
    ai_max_output_tokens: int = Field(
        default=900,
        alias="AI_MAX_OUTPUT_TOKENS",
        ge=200,
        le=2000,
    )
    payments_mode: str = Field(default="demo", alias="PAYMENTS_MODE")
    support_username: str | None = Field(default=None, alias="SUPPORT_USERNAME")
    admin_telegram_id: int | None = Field(
        default=None,
        alias="ADMIN_TELEGRAM_ID",
        gt=0,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
