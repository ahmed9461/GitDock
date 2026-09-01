from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import select

from gitdock.core.config import Settings
from gitdock.db.base import Base
from gitdock.db.models import GitHubAccount, User
from gitdock.db.session import create_engine, create_session_factory
from gitdock.github.auth import GitHubUserIdentity, UserAccessToken
from gitdock.github.auth_state import GitHubAuthorizationStateService
from gitdock.github.connection import GitHubConnectionService
from gitdock.github.credentials import GitHubUserCredentialStore
from gitdock.security.crypto import CredentialCipher
from gitdock.services.confirmations import ConfirmationService
from gitdock.services.user_authorization import GitHubUserAuthorizationService

FIXED_NOW = datetime(2026, 9, 1, 1, 0, tzinfo=UTC)


class FakeAuthClient:
    async def exchange_user_code(
        self,
        *,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> UserAccessToken:
        assert code == "oauth-code"
        assert redirect_uri == "https://gitdock.example/github/oauth/callback"
        assert len(code_verifier) > 40
        return UserAccessToken(
            token=SecretStr("ghu_user_access"),
            expires_at=FIXED_NOW + timedelta(hours=8),
            refresh_token=SecretStr("ghr_user_refresh"),
            refresh_expires_at=FIXED_NOW + timedelta(days=180),
        )

    async def get_authenticated_user(self, user_token: SecretStr) -> GitHubUserIdentity:
        assert user_token.get_secret_value() == "ghu_user_access"
        return GitHubUserIdentity(github_user_id=55, login="octocat")

    async def refresh_user_access_token(self, refresh_token: SecretStr) -> UserAccessToken:
        raise AssertionError("refresh is not expected during initial authorization")


class FakeUrlBuilder:
    def installation_url(self, state: str) -> str:
        return f"https://github.com/apps/gitdock/installations/new?state={state}"

    def user_authorization_url(self, state: str, code_challenge: str, redirect_uri: str) -> str:
        assert state
        assert code_challenge
        assert redirect_uri == "https://gitdock.example/github/oauth/callback"
        return f"https://github.com/login/oauth/authorize?state={state}&challenge={code_challenge}"


class NoopBindingService:
    async def bind(self, *args, **kwargs):
        raise AssertionError("standalone user authorization must not bind an installation")


def settings() -> Settings:
    return Settings(
        env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        telegram_bot_token="123456:abcdefghijklmnopqrstuvwxyzABCDEFGH",
        telegram_owner_id=123,
        github_app_id=12345,
        github_app_slug="gitdock-test",
        github_client_id="Iv1.test-client-id",
        github_client_secret="test-client-secret",
        github_private_key_path="/tmp/not-used.pem",
        credential_encryption_key=Fernet.generate_key().decode("ascii"),
        public_base_url="https://gitdock.example",
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_standalone_user_authorization_reuses_state_pkce_and_persists_credentials() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    cipher = CredentialCipher({1: Fernet.generate_key()}, active_version=1)
    auth_client = FakeAuthClient()
    user_authorization = GitHubUserAuthorizationService(
        sessions,
        auth_client,
        GitHubUserCredentialStore(cipher),
        ConfirmationService(clock=lambda: FIXED_NOW),
        clock=lambda: FIXED_NOW,
    )
    connection_service = GitHubConnectionService(
        sessions,
        GitHubAuthorizationStateService(cipher, clock=lambda: FIXED_NOW),
        FakeUrlBuilder(),  # type: ignore[arg-type]
        auth_client,  # type: ignore[arg-type]
        NoopBindingService(),  # type: ignore[arg-type]
        user_authorization,
    )

    async with sessions() as session:
        async with session.begin():
            user = User()
            session.add(user)
            await session.flush()
            user_id = user.id

    request = await connection_service.begin_user_authorization(
        user_id=user_id,
        redirect_uri="https://gitdock.example/github/oauth/callback",
    )
    state = request.url.split("state=", 1)[1].split("&", 1)[0]
    completion = await connection_service.complete_user_authorization(
        state=state,
        code="oauth-code",
        redirect_uri="https://gitdock.example/github/oauth/callback",
    )

    assert completion.account_login == "octocat"
    assert completion.installation_account_login is None
    async with sessions() as session:
        account = await session.scalar(
            select(GitHubAccount).where(GitHubAccount.user_id == user_id)
        )
        assert account is not None
        assert account.github_user_id == 55
        assert account.login == "octocat"
        assert account.encrypted_access_token is not None
        assert b"ghu_user_access" not in account.encrypted_access_token
        assert account.encrypted_refresh_token is not None

    await engine.dispose()
