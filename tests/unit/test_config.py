from cryptography.fernet import Fernet
import pytest
from pydantic import ValidationError

from gitdock.core.config import Settings


def valid_settings(**overrides):
    values = {
        "env": "test",
        "database_url": "sqlite+aiosqlite:///:memory:",
        "telegram_bot_token": "123456:abcdefghijklmnopqrstuvwxyzABCDEFGH",
        "telegram_owner_id": 123,
    }
    values.update(overrides)
    return Settings(**values)


def valid_github_overrides() -> dict[str, object]:
    return {
        "github_app_id": 12345,
        "github_app_slug": "gitdock-test",
        "github_client_id": "Iv1.test-client-id",
        "github_client_secret": "test-client-secret",
        "github_private_key_path": "/run/secrets/github-app.pem",
        "credential_encryption_key": Fernet.generate_key().decode("ascii"),
        "credential_encryption_key_version": 1,
    }


def test_valid_test_settings() -> None:
    settings = valid_settings()
    assert settings.telegram_owner_id == 123
    assert settings.github_auth_configured is False


def test_complete_github_auth_group_is_accepted() -> None:
    settings = valid_settings(**valid_github_overrides())

    assert settings.github_auth_configured is True
    assert settings.github_app_id == 12345


def test_partial_github_auth_group_fails_closed() -> None:
    with pytest.raises(ValidationError, match="GITDOCK_GITHUB_APP_SLUG"):
        valid_settings(github_app_id=12345)


def test_github_auth_requires_encryption_key() -> None:
    values = valid_github_overrides()
    values.pop("credential_encryption_key")

    with pytest.raises(ValidationError, match="GITDOCK_CREDENTIAL_ENCRYPTION_KEY"):
        valid_settings(**values)


def test_encryption_key_version_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="key version must be positive"):
        valid_settings(credential_encryption_key_version=0)


def test_missing_telegram_token_fails_closed() -> None:
    with pytest.raises(ValidationError):
        Settings(env="test", telegram_owner_id=123)


def test_missing_owner_id_fails_closed() -> None:
    with pytest.raises(ValidationError):
        Settings(env="test", telegram_bot_token="123456:abcdefghijklmnopqrstuvwxyzABCDEFGH")


def test_malformed_database_driver_is_rejected() -> None:
    with pytest.raises(ValidationError):
        valid_settings(database_url="postgresql://user:pass@localhost/db")


def test_production_requires_postgres_and_webhook_settings() -> None:
    with pytest.raises(ValidationError):
        valid_settings(env="production")
