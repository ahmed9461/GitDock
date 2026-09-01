"""Durable GitHub user-authorization lifecycle service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

from pydantic import SecretStr
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.core.constants import USER_ACCESS_TOKEN_REFRESH_MARGIN_SECONDS
from gitdock.db.models.confirmation import PendingConfirmation
from gitdock.db.models.github_auth import GitHubAuthorizationState
from gitdock.db.models.identity import GitHubAccount, GitHubInstallation
from gitdock.db.models.repository import RepositoryCache
from gitdock.github.auth import GitHubUserIdentity, UserAccessToken
from gitdock.github.credentials import GitHubUserCredentialStore
from gitdock.services.confirmations import ConfirmationService

Clock = Callable[[], datetime]
DISCONNECT_OPERATION = "github.disconnect"


class UserAuthorizationClient(Protocol):
    async def get_authenticated_user(self, user_token: SecretStr) -> GitHubUserIdentity: ...

    async def refresh_user_access_token(self, refresh_token: SecretStr) -> UserAccessToken: ...


class UserAuthorizationError(RuntimeError):
    """Safe local user-authorization lifecycle failure."""


class ReauthorizationRequired(UserAuthorizationError):
    """Raised when durable user context must be authorized again."""


class UserAuthorizationChanged(UserAuthorizationError):
    """Raised when local credential state changed during a refresh operation."""


class DisconnectState(StrEnum):
    DISCONNECTED = "disconnected"
    STALE = "stale"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class UserAuthorizationStatus:
    authorized: bool
    login: str | None
    github_user_id: int | None
    access_expires_at: datetime | None
    refresh_expires_at: datetime | None
    refresh_available: bool
    installation_count: int


@dataclass(frozen=True, slots=True)
class DisconnectRequest:
    token: str
    account_login: str
    installation_count: int
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class DisconnectResult:
    state: DisconnectState
    account_login: str | None = None
    installations_removed: int = 0


class GitHubUserAuthorizationService:
    """Persist, refresh, inspect, and locally disconnect GitHub user context."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        auth_client: UserAuthorizationClient,
        credential_store: GitHubUserCredentialStore,
        confirmations: ConfirmationService,
        *,
        refresh_margin: timedelta | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._auth_client = auth_client
        self._credential_store = credential_store
        self._confirmations = confirmations
        self._refresh_margin = refresh_margin or timedelta(
            seconds=USER_ACCESS_TOKEN_REFRESH_MARGIN_SECONDS
        )
        if self._refresh_margin.total_seconds() < 0:
            raise ValueError("user token refresh margin must not be negative")
        self._clock = clock or (lambda: datetime.now(UTC))

    async def persist_authorization(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        token: UserAccessToken,
    ) -> GitHubAccount:
        if user_id <= 0:
            raise ValueError("user ID must be positive")
        identity = await self._auth_client.get_authenticated_user(token.token)

        by_identity = await session.scalar(
            select(GitHubAccount).where(GitHubAccount.github_user_id == identity.github_user_id)
        )
        if by_identity is not None and by_identity.user_id != user_id:
            raise UserAuthorizationError("GitHub user identity is already bound to another user")

        user_accounts = (
            await session.scalars(
                select(GitHubAccount).where(GitHubAccount.user_id == user_id).order_by(GitHubAccount.id)
            )
        ).all()
        for account in user_accounts:
            if account.github_user_id != identity.github_user_id and account.encrypted_access_token:
                self._credential_store.clear(account)

        account = by_identity
        if account is None:
            account = GitHubAccount(
                user_id=user_id,
                github_user_id=identity.github_user_id,
                login=identity.login,
                credential_generation=0,
            )
            session.add(account)
        else:
            account.login = identity.login

        self._credential_store.persist(account, token)
        await session.flush()
        return account

    async def status(self, *, user_id: int) -> UserAuthorizationStatus:
        if user_id <= 0:
            raise ValueError("user ID must be positive")
        async with self._session_factory() as session:
            account = await self._active_account(session, user_id)
            installation_count = int(
                await session.scalar(
                    select(func.count(GitHubInstallation.id)).where(
                        GitHubInstallation.user_id == user_id
                    )
                )
                or 0
            )
            if account is None:
                return UserAuthorizationStatus(
                    False,
                    None,
                    None,
                    None,
                    None,
                    False,
                    installation_count,
                )
            return UserAuthorizationStatus(
                True,
                account.login,
                account.github_user_id,
                account.token_expires_at,
                account.refresh_token_expires_at,
                account.encrypted_refresh_token is not None,
                installation_count,
            )

    async def get_valid_token(self, *, user_id: int) -> UserAccessToken:
        if user_id <= 0:
            raise ValueError("user ID must be positive")
        async with self._session_factory() as session:
            account = await self._active_account(session, user_id)
            if account is None:
                raise ReauthorizationRequired("GitHub user authorization is not available")
            credentials = self._credential_store.load(account)
            if credentials is None:
                raise ReauthorizationRequired("GitHub user authorization is not available")
            account_id = account.id
            generation = account.credential_generation

        now = self._now()
        if credentials.expires_at is None or self._as_utc(credentials.expires_at) > now + self._refresh_margin:
            return UserAccessToken(
                credentials.access_token,
                credentials.expires_at,
                credentials.refresh_token,
                credentials.refresh_expires_at,
            )

        if credentials.refresh_token is None:
            raise ReauthorizationRequired("GitHub user authorization must be renewed")
        if (
            credentials.refresh_expires_at is not None
            and self._as_utc(credentials.refresh_expires_at) <= now
        ):
            raise ReauthorizationRequired("GitHub refresh authorization has expired")

        refreshed = await self._auth_client.refresh_user_access_token(credentials.refresh_token)

        async with self._session_factory() as session:
            async with session.begin():
                current = await session.get(GitHubAccount, account_id)
                if (
                    current is None
                    or current.user_id != user_id
                    or current.credential_generation != generation
                    or current.encrypted_access_token is None
                ):
                    raise UserAuthorizationChanged(
                        "GitHub user authorization changed while the token was refreshing"
                    )
                self._credential_store.persist(current, refreshed)
                await session.flush()
        return refreshed

    async def refresh_if_needed(self, *, user_id: int) -> UserAuthorizationStatus:
        await self.get_valid_token(user_id=user_id)
        return await self.status(user_id=user_id)

    async def begin_disconnect(self, *, user_id: int) -> DisconnectRequest | None:
        if user_id <= 0:
            raise ValueError("user ID must be positive")
        async with self._session_factory() as session:
            async with session.begin():
                account = await self._active_account(session, user_id)
                if account is None:
                    return None
                installation_count = int(
                    await session.scalar(
                        select(func.count(GitHubInstallation.id)).where(
                            GitHubInstallation.user_id == user_id
                        )
                    )
                    or 0
                )
                target = self._fingerprint(account)
                issued = await self._confirmations.create(
                    session,
                    user_id=user_id,
                    operation_type=DISCONNECT_OPERATION,
                    target_fingerprint=target,
                    payload={
                        "account_id": account.id,
                        "github_user_id": account.github_user_id,
                        "credential_generation": account.credential_generation,
                    },
                    risk_tier=1,
                )
                return DisconnectRequest(
                    issued.token,
                    account.login,
                    installation_count,
                    issued.expires_at,
                )

    async def cancel_disconnect(self, *, user_id: int, token: str) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                return await self._confirmations.cancel(
                    session,
                    user_id=user_id,
                    token=token,
                    expected_operation=DISCONNECT_OPERATION,
                )

    async def confirm_disconnect(self, *, user_id: int, token: str) -> DisconnectResult:
        if user_id <= 0 or not token:
            return DisconnectResult(DisconnectState.INVALID)
        async with self._session_factory() as session:
            async with session.begin():
                consumed = await self._confirmations.consume(
                    session,
                    user_id=user_id,
                    token=token,
                    expected_operation=DISCONNECT_OPERATION,
                )
                if consumed is None:
                    return DisconnectResult(DisconnectState.INVALID)

                account_id = consumed.payload.get("account_id")
                github_user_id = consumed.payload.get("github_user_id")
                credential_generation = consumed.payload.get("credential_generation")
                if not all(
                    isinstance(value, int) and not isinstance(value, bool)
                    for value in (account_id, github_user_id, credential_generation)
                ):
                    return DisconnectResult(DisconnectState.STALE)

                account = await session.get(GitHubAccount, account_id)
                if (
                    account is None
                    or account.user_id != user_id
                    or account.github_user_id != github_user_id
                    or account.credential_generation != credential_generation
                    or account.encrypted_access_token is None
                    or consumed.target_fingerprint != self._fingerprint(account)
                ):
                    return DisconnectResult(DisconnectState.STALE)

                account_login = account.login
                installations_removed = int(
                    await session.scalar(
                        select(func.count(GitHubInstallation.id)).where(
                            GitHubInstallation.user_id == user_id
                        )
                    )
                    or 0
                )

                accounts = (
                    await session.scalars(
                        select(GitHubAccount).where(GitHubAccount.user_id == user_id)
                    )
                ).all()
                for stored_account in accounts:
                    if stored_account.encrypted_access_token is not None:
                        self._credential_store.clear(stored_account)

                await session.execute(delete(RepositoryCache).where(RepositoryCache.user_id == user_id))
                await session.execute(
                    delete(GitHubInstallation).where(GitHubInstallation.user_id == user_id)
                )
                await session.execute(
                    delete(GitHubAuthorizationState).where(
                        GitHubAuthorizationState.user_id == user_id,
                        GitHubAuthorizationState.consumed_at.is_(None),
                    )
                )
                await session.execute(
                    update(PendingConfirmation)
                    .where(
                        PendingConfirmation.user_id == user_id,
                        PendingConfirmation.consumed_at.is_(None),
                    )
                    .values(consumed_at=self._now())
                    .execution_options(synchronize_session=False)
                )
                return DisconnectResult(
                    DisconnectState.DISCONNECTED,
                    account_login=account_login,
                    installations_removed=installations_removed,
                )

    async def _active_account(self, session: AsyncSession, user_id: int) -> GitHubAccount | None:
        rows = (
            await session.scalars(
                select(GitHubAccount)
                .where(
                    GitHubAccount.user_id == user_id,
                    GitHubAccount.encrypted_access_token.is_not(None),
                )
                .order_by(GitHubAccount.id)
            )
        ).all()
        if len(rows) > 1:
            raise UserAuthorizationError("multiple active GitHub user authorizations are invalid")
        return rows[0] if rows else None

    @staticmethod
    def _fingerprint(account: GitHubAccount) -> str:
        return (
            f"github-account:{account.id}:user:{account.github_user_id}:"
            f"generation:{account.credential_generation}"
        )

    def _now(self) -> datetime:
        return self._clock().astimezone(UTC)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
