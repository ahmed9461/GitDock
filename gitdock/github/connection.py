"""Restart-safe GitHub App installation and OAuth connection orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.db.models.identity import GitHubInstallation
from gitdock.github.auth import GitHubAuthClient, GitHubAuthUrlBuilder
from gitdock.github.auth_state import AuthorizationFlow, GitHubAuthorizationStateService
from gitdock.github.binding import InstallationBindingService


class GitHubConnectionError(RuntimeError):
    """Raised when a GitHub connection flow cannot be completed safely."""


@dataclass(frozen=True, slots=True)
class ConnectionRedirect:
    url: str


class GitHubConnectionService:
    """Two-stage install -> user verification -> installation binding flow."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        state_service: GitHubAuthorizationStateService,
        url_builder: GitHubAuthUrlBuilder,
        auth_client: GitHubAuthClient,
        binding_service: InstallationBindingService,
    ) -> None:
        self._session_factory = session_factory
        self._state_service = state_service
        self._url_builder = url_builder
        self._auth_client = auth_client
        self._binding_service = binding_service

    async def begin_installation(self, *, user_id: int) -> ConnectionRedirect:
        async with self._session_factory() as session:
            async with session.begin():
                request = await self._state_service.create(
                    session,
                    user_id=user_id,
                    flow=AuthorizationFlow.INSTALLATION_BINDING,
                )
        return ConnectionRedirect(url=self._url_builder.installation_url(request.state))

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
    ) -> GitHubInstallation:
        """Consume OAuth state before exchange, then verify/bind the candidate installation."""

        async with self._session_factory() as session:
            async with session.begin():
                consumed = await self._state_service.consume(
                    session,
                    state=state,
                    expected_flow=AuthorizationFlow.USER_AUTHORIZATION,
                )

        installation_id = consumed.candidate_installation_id
        if installation_id is None:
            raise GitHubConnectionError("authorization state is missing installation context")

        user_token = await self._auth_client.exchange_user_code(
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=consumed.code_verifier,
        )

        async with self._session_factory() as session:
            async with session.begin():
                bound_installation = await self._binding_service.bind(
                    session,
                    user_id=consumed.user_id,
                    user_access_token=user_token.token,
                    installation_id=installation_id,
                )
                await session.flush()
                installation_database_id = bound_installation.id

        async with self._session_factory() as session:
            reloaded_installation = await session.get(
                GitHubInstallation, installation_database_id
            )
            if reloaded_installation is None:
                raise GitHubConnectionError("verified GitHub installation could not be reloaded")
            session.expunge(reloaded_installation)
            return reloaded_installation
