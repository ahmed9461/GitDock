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
    github_app_slug: str | None = None
    github_client_id: str | None = None
    github_client_secret: SecretStr | None = None
    github_private_key_path: str | None = None
    github_webhook_secret: SecretStr | None = None

    credential_encryption_key: SecretStr | None = None
    credential_encryption_key_version: int = 1

    @field_validator("telegram_owner_id")
    @classmethod
    def owner_id_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("telegram owner id must be positive")
        return value

    @field_validator("credential_encryption_key_version")
    @classmethod
    def encryption_key_version_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("credential encryption key version must be positive")
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
        self._validate_github_auth_group()
        return self

    def _validate_github_auth_group(self) -> None:
        values_present = (
            self.github_app_id is not None,
            bool(self.github_app_slug and self.github_app_slug.strip()),
            bool(self.github_client_id and self.github_client_id.strip()),
            self.github_client_secret is not None,
            bool(self.github_private_key_path and self.github_private_key_path.strip()),
            self.credential_encryption_key is not None,
        )
        if not any(values_present):
            return
        if self.github_app_id is None or self.github_app_id <= 0:
            raise ValueError("GitHub App auth requires a positive GITDOCK_GITHUB_APP_ID")
        if not self.github_app_slug or not self.github_app_slug.strip():
            raise ValueError("GitHub App auth requires GITDOCK_GITHUB_APP_SLUG")
        if not self.github_client_id or not self.github_client_id.strip():
            raise ValueError("GitHub App auth requires GITDOCK_GITHUB_CLIENT_ID")
        if self.github_client_secret is None or not self.github_client_secret.get_secret_value():
            raise ValueError("GitHub App auth requires GITDOCK_GITHUB_CLIENT_SECRET")
        if not self.github_private_key_path or not self.github_private_key_path.strip():
            raise ValueError("GitHub App auth requires GITDOCK_GITHUB_PRIVATE_KEY_PATH")
        if (
            self.credential_encryption_key is None
            or not self.credential_encryption_key.get_secret_value()
        ):
            raise ValueError("GitHub App auth requires GITDOCK_CREDENTIAL_ENCRYPTION_KEY")

    @property
    def github_auth_configured(self) -> bool:
        """Return whether the complete GitHub App authentication group is configured."""

        return self.github_app_id is not None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache process-level settings."""

    return Settings()
