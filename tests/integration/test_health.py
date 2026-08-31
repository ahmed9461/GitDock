import pytest
from fastapi.testclient import TestClient

from gitdock.app import create_app
from gitdock.core.config import Settings


def settings() -> Settings:
    return Settings(
        env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        telegram_bot_token="123456:abcdefghijklmnopqrstuvwxyzABCDEFGH",
        telegram_owner_id=123,
        telegram_webhook_secret="test-webhook-secret",
    )


@pytest.mark.integration
def test_health_and_readiness_do_not_expose_secrets() -> None:
    app = create_app(settings())
    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "GitDock"}
    assert ready.status_code == 200
    rendered = ready.text
    assert "test-webhook-secret" not in rendered
    assert "abcdefghijklmnopqrstuvwxyz" not in rendered


@pytest.mark.integration
def test_telegram_webhook_rejects_wrong_secret_before_processing() -> None:
    app = create_app(settings())
    with TestClient(app) as client:
        response = client.post(
            "/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
            json={"update_id": 1},
        )
    assert response.status_code == 401
