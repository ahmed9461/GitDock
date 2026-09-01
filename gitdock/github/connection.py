"""Restart-safe GitHub App installation and OAuth connection orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.db.models.identity import GitHubAccount
from gitdock.github.auth import GitHubAuthClient, GitHubAuthUrlBuilder, UserAccessToken
from gitdock.github.auth_state import AuthorizationFlow, GitHubAuthorizationStateService
from gitdock.github.binding import InstallationBindingService


class GitHubConnectionError(RuntimeError):
    """Raised when a GitHub connection flow cannot be completed safely."""


class UserAuthorizationPersister(Protocol):
    async def persist_authorization(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        token: UserAccessToken,
    ) -> GitHubAccount: ...


@dataclass(frozen=True, slots=True)
class ConnectionRedirect:
    url: str


@dataclass(frozen=True, slots=True)
class ConnectionCompletion:
    account_login: str
    installation_account_login: str | None


class GitHubConnectionService:
    """Installation binding plus reusable durable GitHub user-authorization flow."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        state_service: GitHubAuthorizationStateService,
        url_builder: GitHubAuthUrlBuilder,
        auth_client: GitHubAuthClient,
        binding_service: InstallationBindingService,
        user_authorization: UserAuthorizationPersister,
    ) -> None:
        self._session_factory = session_factory
        self._state_service = state_service
        self._url_builder = url_builder
        self._auth_client = auth_client
        self._binding_service = binding_service
        self._user_authorization = user_authorization

    async def begin_installation(self, *, user_id: int) -> ConnectionRedirect:
        async with self._session_factory() as session:
            async with session.begin():
                request = await self._state_service.create(
                    session,
                    user_id=user_id,
                    flow=AuthorizationFlow.INSTALLATION_BINDING,
                )
        return ConnectionRedirect(url=self._url_builder.installation_url(request.state))

    async def begin_user_authorization(
        self,
        *,
        user_id: int,
        redirect_uri: str,
    ) -> ConnectionRedirect:
        if not redirect_uri:
            raise ValueError("redirect URI is required")
        async with self._session_factory() as session:
            async with session.begin():
                request = await self._state_service.create(
                    session,
                    user_id=user_id,
                    flow=AuthorizationFlow.USER_AUTHORIZATION,
                )
        return ConnectionRedirect(
            url=self._url_builder.user_authorization_url(
                request.state,
                request.code_challenge,
                redirect_uri,
            )
        )

    async def continue_after_installation(
        self,
        *,
        state: str,
        candidate_installation_id: int,
        redirect_uri: str,
    ) -> ConnectionRedirect:
        """Consume install state, but treat GitHub's installation_id as untrusted candidate data."""

        if candidate_installation_id <= 0:
            raise GitHubConnectionError("candidate installation ID is invalid")
        async with self._session_factory() as session:
            async with session.begin():
                consumed = await self._state_service.consume(
                    session,
                    state=state,
                    expected_flow=AuthorizationFlow.INSTALLATION_BINDING,
                )
                oauth_request = await self._state_service.create(
                    session,
                    user_id=consumed.user_id,
                    flow=AuthorizationFlow.USER_AUTHORIZATION,
                    candidate_installation_id=candidate_installation_id,
                )
        return ConnectionRedirect(
            url=self._url_builder.user_authorization_url(
                oauth_request.state,
                oauth_request.code_challenge,
                redirect_uri,
            )
        )

    async def complete_user_authorization(
        self,
        *,
        state: str,
        code: str,
        redirect_uri: str,
    ) -> ConnectionCompletion:
        """Consume OAuth state, persist durable user context, and bind an installation if present."""

        async with self._session_factory() as session:
            async with session.begin():
                consumed = await self._state_service.consume(
                    session,
                    state=state,
                    expected_flow=AuthorizationFlow.USER_AUTHORIZATION,
                )

        user_token = await self._auth_client.exchange_user_code(
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=consumed.code_verifier,
        )

        installation_account_login: str | None = None
        async with self._session_factory() as session:
            async with session.begin():
                if consumed.candidate_installation_id is not None:
                    bound_installation = await self._binding_service.bind(
                        session,
                        user_id=consumed.user_id,
                        user_access_token=user_token.token,
                        installation_id=consumed.candidate_installation_id,
                    )
                    installation_account_login = bound_installation.account_login

                account = await self._user_authorization.persist_authorization(
                    session,
                    user_id=consumed.user_id,
                    token=user_token,
                )
                await session.flush()
                account_login = account.login

        return ConnectionCompletion(
            account_login=account_login,
            installation_account_login=installation_account_login,
        )
