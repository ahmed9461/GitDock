from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from gitdock.db.base import Base
from gitdock.db.models.webhook import GitHubWebhookDelivery
from gitdock.db.session import create_engine, create_session_factory
from gitdock.services.webhooks import (
    GitHubWebhookIngestionService,
    WebhookDeliveryConflict,
    WebhookDeliveryState,
    WebhookPayloadTooLarge,
)


async def _runtime(*, max_payload_bytes: int = 1024, clock=None):
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    service = GitHubWebhookIngestionService(
        sessions,
        "integration-webhook-key",
        max_payload_bytes=max_payload_bytes,
        clock=clock,
    )
    return engine, sessions, service


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_ingestion_is_durable_idempotent_and_conflict_safe() -> None:
    engine, sessions, service = await _runtime()
    body = b'{"action":"opened"}'

    first = await service.ingest(delivery_id="delivery-1", event_name="issues", body=body)
    duplicate = await service.ingest(delivery_id="delivery-1", event_name="issues", body=body)

    assert first.duplicate is False
    assert duplicate.duplicate is True
    async with sessions() as session:
        count = await session.scalar(select(func.count()).select_from(GitHubWebhookDelivery))
        assert count == 1

    restarted = GitHubWebhookIngestionService(sessions, "integration-webhook-key")
    snapshot = await restarted.get("delivery-1")
    assert snapshot is not None
    assert snapshot.payload_bytes == body
    assert snapshot.state is WebhookDeliveryState.PENDING

    with pytest.raises(WebhookDeliveryConflict):
        await restarted.ingest(
            delivery_id="delivery-1",
            event_name="issues",
            body=b'{"action":"closed"}',
        )

    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_ingestion_enforces_payload_limit_before_persistence() -> None:
    engine, sessions, service = await _runtime(max_payload_bytes=4)

    with pytest.raises(WebhookPayloadTooLarge):
        await service.ingest(delivery_id="delivery-2", event_name="push", body=b"12345")

    async with sessions() as session:
        count = await session.scalar(select(func.count()).select_from(GitHubWebhookDelivery))
        assert count == 0
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_worker_state_retries_and_recovers_abandoned_claims() -> None:
    now = [datetime(2026, 9, 12, 12, 0, tzinfo=UTC)]

    def clock() -> datetime:
        return now[0]

    engine, sessions, service = await _runtime(clock=clock)
    service = GitHubWebhookIngestionService(
        sessions,
        "integration-webhook-key",
        processing_lease=timedelta(minutes=5),
        retry_delay=timedelta(seconds=30),
        clock=clock,
    )
    await service.ingest(delivery_id="delivery-3", event_name="push", body=b"{}")

    first_claim = await service.claim_next()
    assert first_claim is not None
    assert first_claim.state is WebhookDeliveryState.PROCESSING
    assert first_claim.attempt_count == 1
    assert await service.claim_next() is None

    restarted = GitHubWebhookIngestionService(
        sessions,
        "integration-webhook-key",
        processing_lease=timedelta(minutes=5),
        retry_delay=timedelta(seconds=30),
        clock=clock,
    )
    now[0] += timedelta(minutes=6)
    recovered = await restarted.claim_next()
    assert recovered is not None
    assert recovered.delivery_id == "delivery-3"
    assert recovered.attempt_count == 2

    assert await restarted.mark_failed("delivery-3", error_code="temporary_failure")
    assert await restarted.claim_next() is None
    now[0] += timedelta(seconds=31)
    retry = await restarted.claim_next()
    assert retry is not None
    assert retry.attempt_count == 3
    assert await restarted.mark_processed("delivery-3")

    final = await restarted.get("delivery-3")
    assert final is not None
    assert final.state is WebhookDeliveryState.PROCESSED
    assert final.processed_at == now[0]
    assert final.last_error_code is None

    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_pruning_only_removes_processed_expired_deliveries() -> None:
    now = [datetime(2026, 9, 12, 13, 0, tzinfo=UTC)]

    def clock() -> datetime:
        return now[0]

    engine, sessions, _ = await _runtime(clock=clock)
    service = GitHubWebhookIngestionService(
        sessions,
        "integration-webhook-key",
        retention=timedelta(minutes=1),
        clock=clock,
    )
    await service.ingest(delivery_id="processed-delivery", event_name="push", body=b"{}")
    await service.ingest(delivery_id="pending-delivery", event_name="push", body=b"{}")
    claimed = await service.claim_next()
    assert claimed is not None
    assert claimed.delivery_id == "processed-delivery"
    assert await service.mark_processed("processed-delivery")

    now[0] += timedelta(minutes=2)
    assert await service.prune_processed() == 1
    assert await service.get("processed-delivery") is None
    pending = await service.get("pending-delivery")
    assert pending is not None
    assert pending.state is WebhookDeliveryState.PENDING

    await engine.dispose()
