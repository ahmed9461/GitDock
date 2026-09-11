"""Durable, idempotent GitHub webhook ingestion and worker-state service."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.core.constants import (
    GITHUB_WEBHOOK_MAX_BODY_BYTES,
    GITHUB_WEBHOOK_PROCESSING_LEASE_SECONDS,
    GITHUB_WEBHOOK_RETENTION_SECONDS,
    GITHUB_WEBHOOK_RETRY_DELAY_SECONDS,
)
from gitdock.db.models.webhook import GitHubWebhookDelivery
from gitdock.github.webhooks import (
    validate_delivery_id,
    validate_event_name,
    verify_webhook_signature,
)

Clock = Callable[[], datetime]
_ERROR_CODE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


class WebhookDeliveryState(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    FAILED = "failed"
    PROCESSED = "processed"


class WebhookPayloadTooLarge(ValueError):
    """Raised when a webhook body exceeds the configured durable-ingestion limit."""


class WebhookDeliveryConflict(RuntimeError):
    """Raised when a delivery id is reused for different event content."""


@dataclass(frozen=True, slots=True)
class WebhookIngestResult:
    delivery_id: str
    duplicate: bool


@dataclass(frozen=True, slots=True)
class WebhookDeliverySnapshot:
    delivery_id: str
    event_name: str
    payload_sha256: str
    payload_size: int
    payload_bytes: bytes
    state: WebhookDeliveryState
    attempt_count: int
    processing_started_at: datetime | None
    next_attempt_at: datetime | None
    processed_at: datetime | None
    last_error_code: str | None
    expires_at: datetime
    created_at: datetime


class GitHubWebhookIngestionService:
    """Authenticate, persist, deduplicate, and expose retryable delivery state."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        secret: str,
        *,
        max_payload_bytes: int = GITHUB_WEBHOOK_MAX_BODY_BYTES,
        retention: timedelta | None = None,
        processing_lease: timedelta | None = None,
        retry_delay: timedelta | None = None,
        clock: Clock | None = None,
    ) -> None:
        if not secret:
            raise ValueError("GitHub webhook secret must not be empty")
        if max_payload_bytes <= 0:
            raise ValueError("webhook payload limit must be positive")
        self._session_factory = session_factory
        self._secret = secret
        self._max_payload_bytes = max_payload_bytes
        self._retention = retention or timedelta(seconds=GITHUB_WEBHOOK_RETENTION_SECONDS)
        self._processing_lease = processing_lease or timedelta(
            seconds=GITHUB_WEBHOOK_PROCESSING_LEASE_SECONDS
        )
        self._retry_delay = retry_delay or timedelta(seconds=GITHUB_WEBHOOK_RETRY_DELAY_SECONDS)
        if self._retention.total_seconds() <= 0:
            raise ValueError("webhook retention must be positive")
        if self._processing_lease.total_seconds() <= 0:
            raise ValueError("webhook processing lease must be positive")
        if self._retry_delay.total_seconds() < 0:
            raise ValueError("webhook retry delay must not be negative")
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def max_payload_bytes(self) -> int:
        return self._max_payload_bytes

    def verify_signature(self, *, body: bytes, signature: str | None) -> bool:
        return verify_webhook_signature(secret=self._secret, body=body, signature=signature)

    async def ingest(
        self,
        *,
        delivery_id: str,
        event_name: str,
        body: bytes,
    ) -> WebhookIngestResult:
        delivery_id = validate_delivery_id(delivery_id)
        event_name = validate_event_name(event_name)
        if len(body) > self._max_payload_bytes:
            raise WebhookPayloadTooLarge("GitHub webhook payload exceeds configured limit")

        payload_sha256 = hashlib.sha256(body).hexdigest()
        now = self._now()
        async with self._session_factory() as session:
            existing = await self._get_model(session, delivery_id)
            if existing is not None:
                return self._duplicate_or_conflict(existing, event_name, body, payload_sha256)

            session.add(
                GitHubWebhookDelivery(
                    delivery_id=delivery_id,
                    event_name=event_name,
                    payload_sha256=payload_sha256,
                    payload_size=len(body),
                    payload_bytes=body,
                    status=WebhookDeliveryState.PENDING.value,
                    expires_at=now + self._retention,
                    updated_at=now,
                )
            )
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                existing = await self._get_model(session, delivery_id)
                if existing is None:
                    raise
                return self._duplicate_or_conflict(existing, event_name, body, payload_sha256)
        return WebhookIngestResult(delivery_id=delivery_id, duplicate=False)

    async def get(self, delivery_id: str) -> WebhookDeliverySnapshot | None:
        delivery_id = validate_delivery_id(delivery_id)
        async with self._session_factory() as session:
            model = await self._get_model(session, delivery_id)
            return None if model is None else self._snapshot(model)

    async def claim_next(self) -> WebhookDeliverySnapshot | None:
        """Claim the oldest eligible delivery, including abandoned processing leases."""

        now = self._now()
        stale_before = now - self._processing_lease
        eligible = or_(
            GitHubWebhookDelivery.status == WebhookDeliveryState.PENDING.value,
            and_(
                GitHubWebhookDelivery.status == WebhookDeliveryState.FAILED.value,
                or_(
                    GitHubWebhookDelivery.next_attempt_at.is_(None),
                    GitHubWebhookDelivery.next_attempt_at <= now,
                ),
            ),
            and_(
                GitHubWebhookDelivery.status == WebhookDeliveryState.PROCESSING.value,
                GitHubWebhookDelivery.processing_started_at.is_not(None),
                GitHubWebhookDelivery.processing_started_at <= stale_before,
            ),
        )
        async with self._session_factory() as session:
            statement = (
                select(GitHubWebhookDelivery)
                .where(eligible)
                .order_by(GitHubWebhookDelivery.created_at, GitHubWebhookDelivery.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            model = await session.scalar(statement)
            if model is None:
                return None
            model.status = WebhookDeliveryState.PROCESSING.value
            model.attempt_count += 1
            model.processing_started_at = now
            model.next_attempt_at = None
            model.last_error_code = None
            model.updated_at = now
            await session.commit()
            return self._snapshot(model)

    async def mark_failed(
        self,
        delivery_id: str,
        *,
        error_code: str,
        retry_after: timedelta | None = None,
    ) -> bool:
        delivery_id = validate_delivery_id(delivery_id)
        if _ERROR_CODE_RE.fullmatch(error_code) is None:
            raise ValueError("webhook error code must be a bounded safe identifier")
        delay = self._retry_delay if retry_after is None else retry_after
        if delay.total_seconds() < 0:
            raise ValueError("webhook retry delay must not be negative")
        now = self._now()
        async with self._session_factory() as session:
            model = await self._get_for_update(session, delivery_id)
            if model is None or model.status != WebhookDeliveryState.PROCESSING.value:
                return False
            model.status = WebhookDeliveryState.FAILED.value
            model.processing_started_at = None
            model.next_attempt_at = now + delay
            model.last_error_code = error_code
            model.updated_at = now
            await session.commit()
            return True

    async def mark_processed(self, delivery_id: str) -> bool:
        delivery_id = validate_delivery_id(delivery_id)
        now = self._now()
        async with self._session_factory() as session:
            model = await self._get_for_update(session, delivery_id)
            if model is None or model.status != WebhookDeliveryState.PROCESSING.value:
                return False
            model.status = WebhookDeliveryState.PROCESSED.value
            model.processing_started_at = None
            model.next_attempt_at = None
            model.last_error_code = None
            model.processed_at = now
            model.updated_at = now
            await session.commit()
            return True

    async def prune_processed(self) -> int:
        """Delete only processed deliveries whose raw-payload retention window elapsed."""

        now = self._now()
        async with self._session_factory() as session:
            result = await session.execute(
                delete(GitHubWebhookDelivery).where(
                    GitHubWebhookDelivery.status == WebhookDeliveryState.PROCESSED.value,
                    GitHubWebhookDelivery.expires_at <= now,
                )
            )
            await session.commit()
            return int(result.rowcount or 0)

    async def _get_for_update(
        self,
        session: AsyncSession,
        delivery_id: str,
    ) -> GitHubWebhookDelivery | None:
        return await session.scalar(
            select(GitHubWebhookDelivery)
            .where(GitHubWebhookDelivery.delivery_id == delivery_id)
            .with_for_update()
        )

    @staticmethod
    async def _get_model(
        session: AsyncSession,
        delivery_id: str,
    ) -> GitHubWebhookDelivery | None:
        return await session.scalar(
            select(GitHubWebhookDelivery).where(GitHubWebhookDelivery.delivery_id == delivery_id)
        )

    @staticmethod
    def _duplicate_or_conflict(
        existing: GitHubWebhookDelivery,
        event_name: str,
        body: bytes,
        payload_sha256: str,
    ) -> WebhookIngestResult:
        if (
            existing.event_name == event_name
            and existing.payload_sha256 == payload_sha256
            and existing.payload_size == len(body)
            and existing.payload_bytes == body
        ):
            return WebhookIngestResult(delivery_id=existing.delivery_id, duplicate=True)
        raise WebhookDeliveryConflict("GitHub delivery id was reused for different content")

    @staticmethod
    def _snapshot(model: GitHubWebhookDelivery) -> WebhookDeliverySnapshot:
        return WebhookDeliverySnapshot(
            delivery_id=model.delivery_id,
            event_name=model.event_name,
            payload_sha256=model.payload_sha256,
            payload_size=model.payload_size,
            payload_bytes=bytes(model.payload_bytes),
            state=WebhookDeliveryState(model.status),
            attempt_count=model.attempt_count,
            processing_started_at=model.processing_started_at,
            next_attempt_at=model.next_attempt_at,
            processed_at=model.processed_at,
            last_error_code=model.last_error_code,
            expires_at=model.expires_at,
            created_at=model.created_at,
        )

    def _now(self) -> datetime:
        return self._clock().astimezone(UTC)
