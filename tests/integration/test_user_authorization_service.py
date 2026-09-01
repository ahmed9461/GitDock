from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import func, select

from gitdock.db.base import Base
from gitdock.db.models import GitHubAccount, GitHubInstallation, RepositoryCache, User
from gitdock.db.session import create_engine, create_session_factory
from gitdock.github.auth import GitHubUserIdentity, UserAccessToken
from gitdock.github.credentials import GitHubUserCredentialStore
from gitdock.security.crypto import CredentialCipher
from gitdock.services.confirmations import ConfirmationService
from gitdock.services.user_authorization import (
    DisconnectState,
    GitHubUserAuthorizationService,
)

FIXED_NOW = datetime(2026, 9, 1, 1, 0, tzinfo=UTC)


class FakeUserAuthClient:
    def __init__(self) -> None:
        self.identity = GitHubUserIdentity(github_user_id=55, login="octocat")
        self.refresh_calls = 0

    async def get_authenticated_user(self, user_token: SecretStr) -> GitHubUserIdentity:
        assert user_token.get_secret_value().startswith("ghu_")
        return self.identity

    async def refresh_user_access_token(self, refresh_token: SecretStr) -> UserAccessToken:
        assert refresh_token.get_secret_value() == "ghr_old"
        self.refresh_calls += 1
        return UserAccessToken(
            token=SecretStr("ghu_rotated"),
            expires_at=FIXED_NOW + timedelta(hours=8),
            refresh_token=SecretStr("ghr_rotated"),
            refresh_expires_at=FIXED_NOW + timedelta(days=180),
        )


def token(
    access: str = "ghu_initial",
    refresh: str = "ghr_old",
    *,
    expires_at: datetime | None = None,
) -> UserAccessToken:
    return UserAccessToken(
        token=SecretStr(access),
        expires_at=expires_at or FIXED_NOW + timedelta(hours=8),
        refresh_token=SecretStr(refresh),
        refresh_expires_at=FIXED_NOW + timedelta(days=180),
    )


async def make_service():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    cipher = CredentialCipher({1: Fernet.generate_key()}, active_version=1)
    client = FakeUserAuthClient()
    service = GitHubUserAuthorizationService(
        sessions,
        client,
        GitHubUserCredentialStore(cipher),
        ConfirmationService(clock=lambda: FIXED_NOW),
        clock=lambda: FIXED_NOW,
    )
    async with sessions() as session:
        async with session.begin():
            user = User()
            session.add(user)
            await session.flush()
            user_id = user.id
    return engine, sessions, client, service, user_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_authorization_persists_encrypted_identity_and_refreshes_rotating_token() -> None:
    engine, sessions, client, service, user_id = await make_service()

    async with sessions() as session:
        async with session.begin():
            account = await service.persist_authorization(
                session,
                user_id=user_id,
                token=token(expires_at=FIXED_NOW + timedelta(minutes=1)),
            )
            account_id = account.id
            assert account.credential_generation == 1
            assert account.encrypted_access_token is not None
            assert b"ghu_initial" not in account.encrypted_access_token

    refreshed = await service.get_valid_token(user_id=user_id)
    assert refreshed.token.get_secret_value() == "ghu_rotated"
    assert client.refresh_calls == 1

    async with sessions() as session:
        stored = await session.get(GitHubAccount, account_id)
        assert stored is not None
        assert stored.credential_generation == 2
        loaded = service._credential_store.load(stored)
        assert loaded is not None
        assert loaded.access_token.get_secret_value() == "ghu_rotated"
        assert loaded.refresh_token is not None
        assert loaded.refresh_token.get_secret_value() == "ghr_rotated"

    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_disconnect_clears_credentials_installations_and_repository_cache_once() -> None:
    engine, sessions, _, service, user_id = await make_service()

    async with sessions() as session:
        async with session.begin():
            account = await service.persist_authorization(session, user_id=user_id, token=token())
            account_id = account.id
            installation = GitHubInstallation(
                user_id=user_id,
                installation_id=99,
                account_login="octocat",
                account_type="User",
                suspended=False,
                permissions_json={"metadata": "read"},
            )
            session.add(installation)
            await session.flush()
            session.add(
                RepositoryCache(
                    user_id=user_id,
                    installation_db_id=installation.id,
                    github_repository_id=123,
                    owner_login="octocat",
                    name="demo",
                    full_name="octocat/demo",
                    html_url="https://github.com/octocat/demo",
                    private=False,
                    archived=False,
                    fork=False,
                    default_branch="main",
                    language="Python",
                    description=None,
                    stars=1,
                    forks=0,
                    github_updated_at=FIXED_NOW,
                    github_pushed_at=FIXED_NOW,
                )
            )

    request = await service.begin_disconnect(user_id=user_id)
    assert request is not None
    assert request.installation_count == 1

    result = await service.confirm_disconnect(user_id=user_id, token=request.token)
    assert result.state is DisconnectState.DISCONNECTED
    assert result.installations_removed == 1
    assert (await service.confirm_disconnect(user_id=user_id, token=request.token)).state is DisconnectState.INVALID

    async with sessions() as session:
        stored = await session.get(GitHubAccount, account_id)
        assert stored is not None
        assert stored.encrypted_access_token is None
        assert stored.credential_generation == 2
        assert await session.scalar(select(func.count(GitHubInstallation.id))) == 0
        assert await session.scalar(select(func.count(RepositoryCache.id))) == 0

    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_old_disconnect_confirmation_cannot_remove_newer_reauthorization() -> None:
    engine, sessions, _, service, user_id = await make_service()

    async with sessions() as session:
        async with session.begin():
            await service.persist_authorization(session, user_id=user_id, token=token())

    request = await service.begin_disconnect(user_id=user_id)
    assert request is not None

    async with sessions() as session:
        async with session.begin():
            account = await service.persist_authorization(
                session,
                user_id=user_id,
                token=token(access="ghu_newer"),
            )
            assert account.credential_generation == 2

    result = await service.confirm_disconnect(user_id=user_id, token=request.token)
    assert result.state is DisconnectState.STALE
    status = await service.status(user_id=user_id)
    assert status.authorized is True
    assert status.login == "octocat"

    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_disconnect_cancel_consumes_confirmation_and_blocks_later_confirm() -> None:
    engine, sessions, _, service, user_id = await make_service()

    async with sessions() as session:
        async with session.begin():
            await service.persist_authorization(session, user_id=user_id, token=token())

    request = await service.begin_disconnect(user_id=user_id)
    assert request is not None
    assert await service.cancel_disconnect(user_id=user_id, token=request.token) is True
    result = await service.confirm_disconnect(user_id=user_id, token=request.token)
    assert result.state is DisconnectState.INVALID
    assert (await service.status(user_id=user_id)).authorized is True

    await engine.dispose()
