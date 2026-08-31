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


def test_valid_test_settings() -> None:
    settings = valid_settings()
    assert settings.telegram_owner_id == 123


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
