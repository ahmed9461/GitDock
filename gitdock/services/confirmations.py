"""Durable one-time confirmation issuance and consumption."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from gitdock.core.constants import CONFIRMATION_TOKEN_BYTES, CONFIRMATION_TTL_SECONDS
from gitdock.db.models.confirmation import PendingConfirmation

Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class IssuedConfirmation:
    token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ConsumedConfirmation:
    target_fingerprint: str
    payload: dict[str, Any]
    risk_tier: int


class ConfirmationService:
    """Persist confirmations without storing their raw callback token."""

    def __init__(
        self,
        *,
        ttl: timedelta | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._ttl = ttl or timedelta(seconds=CONFIRMATION_TTL_SECONDS)
        if self._ttl.total_seconds() <= 0:
            raise ValueError("confirmation TTL must be positive")
        self._clock = clock or (lambda: datetime.now(UTC))

    async def create(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        operation_type: str,
        target_fingerprint: str,
        payload: dict[str, Any],
        risk_tier: int,
    ) -> IssuedConfirmation:
        if user_id <= 0:
            raise ValueError("user ID must be positive")
        if not operation_type or not target_fingerprint:
            raise ValueError("confirmation operation and target are required")
        if risk_tier < 0:
            raise ValueError("risk tier must not be negative")

        now = self._now()
        await session.execute(
            update(PendingConfirmation)
            .where(
                PendingConfirmation.user_id == user_id,
                PendingConfirmation.operation_type == operation_type,
                PendingConfirmation.consumed_at.is_(None),
            )
            .values(consumed_at=now)
            .execution_options(synchronize_session=False)
        )

        token = secrets.token_urlsafe(CONFIRMATION_TOKEN_BYTES)
        expires_at = now + self._ttl
        session.add(
            PendingConfirmation(
                user_id=user_id,
                token_digest=self._digest(token),
                operation_type=operation_type,
                target_fingerprint=target_fingerprint,
                payload_json=dict(payload),
                risk_tier=risk_tier,
                expires_at=expires_at,
            )
        )
        await session.flush()
        return IssuedConfirmation(token=token, expires_at=expires_at)

    async def consume(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        token: str,
        expected_operation: str,
    ) -> ConsumedConfirmation | None:
        if user_id <= 0 or not token or not expected_operation:
            return None
        now = self._now()
        statement = (
            update(PendingConfirmation)
            .where(
                PendingConfirmation.user_id == user_id,
                PendingConfirmation.token_digest == self._digest(token),
                PendingConfirmation.operation_type == expected_operation,
                PendingConfirmation.consumed_at.is_(None),
                PendingConfirmation.expires_at > now,
            )
            .values(consumed_at=now)
            .returning(
                PendingConfirmation.target_fingerprint,
                PendingConfirmation.payload_json,
                PendingConfirmation.risk_tier,
            )
            .execution_options(synchronize_session=False)
        )
        row = (await session.execute(statement)).one_or_none()
        if row is None:
            return None
        target_fingerprint, payload, risk_tier = row
        if not isinstance(target_fingerprint, str) or not isinstance(payload, dict):
            return None
        if not isinstance(risk_tier, int):
            return None
        return ConsumedConfirmation(target_fingerprint, dict(payload), risk_tier)

    async def cancel(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        token: str,
        expected_operation: str,
    ) -> bool:
        return (
            await self.consume(
                session,
                user_id=user_id,
                token=token,
                expected_operation=expected_operation,
            )
            is not None
        )

    def _now(self) -> datetime:
        return self._clock().astimezone(UTC)

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
