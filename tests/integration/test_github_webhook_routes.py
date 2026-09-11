from __future__ import annotations

import asyncio
import hashlib
import hmac
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from gitdock.app import create_app
from gitdock.core.config import Settings
from gitdock.core.constants import GITHUB_WEBHOOK_MAX_BODY_BYTES
from gitdock.db.base import Base
from gitdock.db.session import create_engine


def _settings(db_path: Path, *, webhook_secret: str | None = "route-webhook-key") -> Settings:
    return Settings(
        env="test",
        database_url=f"sqlite+aiosqlite:///{db_path}",
        telegram_bot_token="123456:abcdefghijklmnopqrstuvwxyzABCDEFGH",
        telegram_owner_id=123,
        telegram_webhook_secret="telegram-test-key",
        github_webhook_secret=webhook_secret,
    )


async def _create_schema(database_url: str) -> None:
    engine = create_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()


def _signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _headers(
    *,
    secret: str,
    body: bytes,
    delivery_id: str = "route-delivery-1",
    event_name: str = "push",
) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": _signature(secret, body),
        "X-GitHub-Delivery": delivery_id,
        "X-GitHub-Event": event_name,
    }


def _delivery_count(db_path: Path) -> int:
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute("SELECT COUNT(*) FROM github_webhook_deliveries").fetchone()
        assert row is not None
        return int(row[0])
    finally:
        connection.close()


@pytest.mark.integration
def test_github_webhook_accepts_valid_raw_body_and_deduplicates(tmp_path: Path) -> None:
    db_path = tmp_path / "webhooks.db"
    settings = _settings(db_path)
    asyncio.run(_create_schema(settings.database_url))
    body = b'{"ref":"refs/heads/main","after":"abc"}'
    headers = _headers(secret="route-webhook-key", body=body)

    app = create_app(settings)
    with TestClient(app) as client:
        accepted = client.post("/github/webhook", headers=headers, content=body)
        duplicate = client.post("/github/webhook", headers=headers, content=body)

    assert accepted.status_code == 202
    assert accepted.json() == {"status": "accepted"}
    assert duplicate.status_code == 202
    assert duplicate.json() == {"status": "duplicate"}
    assert _delivery_count(db_path) == 1
    assert "route-webhook-key" not in accepted.text
    assert "refs/heads/main" not in accepted.text


@pytest.mark.integration
def test_github_webhook_rejects_forged_signature_before_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "forged.db"
    settings = _settings(db_path)
    asyncio.run(_create_schema(settings.database_url))
    body = b'{"action":"opened"}'
    headers = _headers(secret="wrong-key", body=body)

    app = create_app(settings)
    with TestClient(app) as client:
        forged = client.post("/github/webhook", headers=headers, content=body)
        missing = client.post(
            "/github/webhook",
            headers={
                "X-GitHub-Delivery": "route-delivery-2",
                "X-GitHub-Event": "issues",
            },
            content=body,
        )

    assert forged.status_code == 403
    assert missing.status_code == 403
    assert _delivery_count(db_path) == 0


@pytest.mark.integration
def test_github_webhook_validates_metadata_only_after_authentication(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    settings = _settings(db_path)
    asyncio.run(_create_schema(settings.database_url))
    body = b"{}"

    app = create_app(settings)
    with TestClient(app) as client:
        invalid_metadata = client.post(
            "/github/webhook",
            headers={
                "X-Hub-Signature-256": _signature("route-webhook-key", body),
                "X-GitHub-Event": "push",
            },
            content=body,
        )
        unauthenticated_bad_metadata = client.post(
            "/github/webhook",
            headers={"X-GitHub-Event": "bad event"},
            content=body,
        )

    assert invalid_metadata.status_code == 400
    assert unauthenticated_bad_metadata.status_code == 403
    assert _delivery_count(db_path) == 0


@pytest.mark.integration
def test_github_webhook_rejects_delivery_id_reuse_for_different_content(tmp_path: Path) -> None:
    db_path = tmp_path / "conflict.db"
    settings = _settings(db_path)
    asyncio.run(_create_schema(settings.database_url))
    first_body = b'{"action":"opened"}'
    second_body = b'{"action":"closed"}'

    app = create_app(settings)
    with TestClient(app) as client:
        first = client.post(
            "/github/webhook",
            headers=_headers(secret="route-webhook-key", body=first_body),
            content=first_body,
        )
        conflict = client.post(
            "/github/webhook",
            headers=_headers(secret="route-webhook-key", body=second_body),
            content=second_body,
        )

    assert first.status_code == 202
    assert conflict.status_code == 409
    assert _delivery_count(db_path) == 1


@pytest.mark.integration
def test_github_webhook_rejects_oversized_body_without_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "oversized.db"
    settings = _settings(db_path)
    asyncio.run(_create_schema(settings.database_url))
    body = b"x" * (GITHUB_WEBHOOK_MAX_BODY_BYTES + 1)

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.post("/github/webhook", content=body)

    assert response.status_code == 413
    assert _delivery_count(db_path) == 0


@pytest.mark.integration
def test_github_webhook_returns_unavailable_when_secret_is_not_configured(tmp_path: Path) -> None:
    settings = _settings(tmp_path / "disabled.db", webhook_secret=None)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post("/github/webhook", content=b"{}")

    assert response.status_code == 503
