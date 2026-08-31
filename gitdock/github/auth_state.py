"""Durable one-time GitHub authorization state with PKCE S256 support."""

from __future__ import annotations

import base64
import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from gitdock.core.constants import GITHUB_AUTH_STATE_TTL_SECONDS
from gitdock.db.models.github_auth import GitHubAuthorizationState
from gitdock.security.crypto import CredentialCipher

Clock = Callable[[], datetime]


class AuthorizationFlow(StrEnum):
    INSTALLATION_BINDING = "installation_binding"
    USER_AUTHORIZATION = "user_authorization"


class InvalidAuthorizationState(RuntimeError):
    """Raised for missing, wrong-flow, expired, or already-consumed state."""


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    state: str
    code_challenge: str
    code_challenge_method: str = "S256"


@dataclass(frozen=True, slots=True)
class ConsumedAuthorizationState:
    user_id: int
    flow: AuthorizationFlow
    code_verifier: str
    candidate_installation_id: int | None


class GitHubAuthorizationStateService:
    """Create and atomically consume restart-safe OAuth authorization state."""

    def __init__(
        self,
        cipher: CredentialCipher,
        *,
        ttl: timedelta | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._cipher = cipher
        self._ttl = ttl or timedelta(seconds=GITHUB_AUTH_STATE_TTL_SECONDS)
        if self._ttl.total_seconds() <= 0:
            raise ValueError("authorization state TTL must be positive")
        self._clock = clock or (lambda: datetime.now(UTC))

    async def create(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        flow: AuthorizationFlow,
        candidate_installation_id: int | None = None,
    ) -> AuthorizationRequest:
        if user_id <= 0:
            raise ValueError("user ID must be positive")
        if candidate_installation_id is not None and candidate_installation_id <= 0:
            raise ValueError("candidate installation ID must be positive")

        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        state_digest = self._digest_state(state)
        encrypted = self._cipher.encrypt(code_verifier)
        expires_at = self._clock().astimezone(UTC) + self._ttl

        session.add(
            GitHubAuthorizationState(
                user_id=user_id,
                state_digest=state_digest,
                flow=flow.value,
                candidate_installation_id=candidate_installation_id,
                encrypted_code_verifier=encrypted.ciphertext,
                code_verifier_key_version=encrypted.key_version,
                expires_at=expires_at,
            )
        )
        await session.flush()
        return AuthorizationRequest(
            state=state,
            code_challenge=self._pkce_challenge(code_verifier),
        )

    async def consume(
        self,
        session: AsyncSession,
        *,
        state: str,
        expected_flow: AuthorizationFlow,
    ) -> ConsumedAuthorizationState:
        if not state:
            raise InvalidAuthorizationState("authorization state is invalid or expired")

        now = self._clock().astimezone(UTC)
        statement = (
            update(GitHubAuthorizationState)
            .where(
                GitHubAuthorizationState.state_digest == self._digest_state(state),
                GitHubAuthorizationState.flow == expected_flow.value,
                GitHubAuthorizationState.consumed_at.is_(None),
                GitHubAuthorizationState.expires_at > now,
            )
            .values(consumed_at=now)
            .returning(
                GitHubAuthorizationState.user_id,
                GitHubAuthorizationState.encrypted_code_verifier,
                GitHubAuthorizationState.code_verifier_key_version,
                GitHubAuthorizationState.candidate_installation_id,
            )
        )
        result = await session.execute(statement)
        row = result.one_or_none()
        if row is None:
            raise InvalidAuthorizationState("authorization state is invalid or expired")

        user_id, encrypted_verifier, key_version, candidate_installation_id = row
        if not isinstance(user_id, int) or not isinstance(encrypted_verifier, bytes):
            raise InvalidAuthorizationState("authorization state record is invalid")
        if not isinstance(key_version, int):
            raise InvalidAuthorizationState("authorization state record is invalid")
        if candidate_installation_id is not None and not isinstance(candidate_installation_id, int):
            raise InvalidAuthorizationState("authorization state record is invalid")

        code_verifier = self._cipher.decrypt(encrypted_verifier, key_version)
        return ConsumedAuthorizationState(
            user_id=user_id,
            flow=expected_flow,
            code_verifier=code_verifier,
            candidate_installation_id=candidate_installation_id,
        )

    @staticmethod
    def _digest_state(state: str) -> str:
        return hashlib.sha256(state.encode("utf-8")).hexdigest()

    @staticmethod
    def _pkce_challenge(code_verifier: str) -> str:
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
