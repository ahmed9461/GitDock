"""Typed application configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

Environment = Literal["development", "test", "production"]
SUPPORTED_DATABASE_DRIVERS = {"postgresql+asyncpg", "sqlite+aiosqlite"}


class Settings(BaseSettings):
    """GitDock settings loaded from GITDOCK_* environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="GITDOCK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Environment = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./gitdock.db"

    telegram_bot_token: SecretStr
    telegram_owner_id: int
    public_base_url: HttpUrl | None = None
    telegram_webhook_secret: SecretStr | None = None

    github_app_id: int | None = None
    github_client_id: str | None = None
    github_client_secret: SecretStr | None = None
    github_private_key_path: str | None = None
    github_webhook_secret: SecretStr | None = None

    @field_validator("telegram_owner_id")
    @classmethod
    def owner_id_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("telegram owner id must be positive")
        return value

    @field_validator("database_url")
    @classmethod
    def database_url_must_use_supported_async_driver(cls, value: str) -> str:
        try:
            driver = make_url(value).drivername
        except Exception as exc:
            raise ValueError("database URL is malformed") from exc
        if driver not in SUPPORTED_DATABASE_DRIVERS:
            supported = ", ".join(sorted(SUPPORTED_DATABASE_DRIVERS))
            raise ValueError(f"database driver must be one of: {supported}")
        return value

    @model_validator(mode="after")
    def validate_environment_safety(self) -> Self:
        if self.env == "production":
            if not self.database_url.startswith("postgresql+asyncpg://"):
                raise ValueError("production requires PostgreSQL via postgresql+asyncpg")
            if self.public_base_url is None:
                raise ValueError("production requires GITDOCK_PUBLIC_BASE_URL")
            if self.telegram_webhook_secret is None:
                raise ValueError("production requires GITDOCK_TELEGRAM_WEBHOOK_SECRET")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache process-level settings."""

    return Settings()
