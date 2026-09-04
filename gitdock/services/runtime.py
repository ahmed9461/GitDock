"""Runtime composition root for Telegram/GitHub application services."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.core.config import Settings
from gitdock.github.auth import GitHubAppJwtIssuer, GitHubAuthClient, GitHubAuthUrlBuilder
from gitdock.github.auth_state import GitHubAuthorizationStateService
from gitdock.github.binding import InstallationBindingService
from gitdock.github.client import GitHubRestClient
from gitdock.github.connection import GitHubConnectionService
from gitdock.github.credentials import GitHubUserCredentialStore
from gitdock.github.repositories import GitHubRepositoryGateway
from gitdock.github.repository_admin import GitHubRepositoryAdminGateway
from gitdock.github.search import GitHubRepositorySearchGateway
from gitdock.github.token_provider import InstallationTokenProvider
from gitdock.security.crypto import CredentialCipher
from gitdock.services.confirmations import ConfirmationService
from gitdock.services.identity import OwnerIdentityService
from gitdock.services.repositories import RepositoryReadService
from gitdock.services.repository_admin import RepositoryAdminService
from gitdock.services.search import RepositorySearchService
from gitdock.services.user_authorization import GitHubUserAuthorizationService


@dataclass(slots=True)
class RuntimeServices:
    identity: OwnerIdentityService
    repository_read: RepositoryReadService | None
    repository_search: RepositorySearchService
    github_connection: GitHubConnectionService | None
    user_authorization: GitHubUserAuthorizationService | None
    http_client: httpx.AsyncClient | None
    repository_admin: RepositoryAdminService | None = None

    async def close(self) -> None:
        if self.http_client is not None:
            await self.http_client.aclose()


def create_runtime_services(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> RuntimeServices:
    identity = OwnerIdentityService(session_factory)
    http_client = httpx.AsyncClient()
    rest_client = GitHubRestClient(http_client)
    repository_search = RepositorySearchService(GitHubRepositorySearchGateway(rest_client))

    if not settings.github_auth_configured:
        return RuntimeServices(
            identity=identity,
            repository_read=None,
            repository_search=repository_search,
            github_connection=None,
            user_authorization=None,
            http_client=http_client,
        )

    jwt_issuer = GitHubAppJwtIssuer.from_settings(settings)
    assert settings.credential_encryption_key is not None
    encryption_key_version = settings.credential_encryption_key_version
    encryption_key = settings.credential_encryption_key.get_secret_value()
    cipher = CredentialCipher({encryption_key_version: encryption_key}, encryption_key_version)
    credential_store = GitHubUserCredentialStore(cipher)
    auth_client = GitHubAuthClient(http_client, settings, jwt_issuer)
    confirmations = ConfirmationService()
    user_authorization = GitHubUserAuthorizationService(
        session_factory,
        auth_client,
        credential_store,
        confirmations,
    )
    token_provider = InstallationTokenProvider(auth_client)
    repository_gateway = GitHubRepositoryGateway(rest_client)
    repository_read = RepositoryReadService(
        session_factory,
        token_provider,
        repository_gateway,
    )
    repository_admin = RepositoryAdminService(
        session_factory,
        user_authorization,
        token_provider,
        repository_gateway,
        GitHubRepositoryAdminGateway(rest_client),
        confirmations,
    )
    state_service = GitHubAuthorizationStateService(cipher)
    connection = GitHubConnectionService(
        session_factory,
        state_service,
        GitHubAuthUrlBuilder(settings),
        auth_client,
        InstallationBindingService(auth_client),
        user_authorization,
    )
    return RuntimeServices(
        identity=identity,
        repository_read=repository_read,
        repository_search=repository_search,
        github_connection=connection,
        user_authorization=user_authorization,
        http_client=http_client,
        repository_admin=repository_admin,
    )
