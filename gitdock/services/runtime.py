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
from gitdock.github.repositories import GitHubRepositoryGateway
from gitdock.github.token_provider import InstallationTokenProvider
from gitdock.security.crypto import CredentialCipher
from gitdock.services.identity import OwnerIdentityService
from gitdock.services.repositories import RepositoryReadService


@dataclass(slots=True)
class RuntimeServices:
    identity: OwnerIdentityService
    repository_read: RepositoryReadService | None
    github_connection: GitHubConnectionService | None
    http_client: httpx.AsyncClient | None

    async def close(self) -> None:
        if self.http_client is not None:
            await self.http_client.aclose()


def create_runtime_services(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> RuntimeServices:
    identity = OwnerIdentityService(session_factory)
    if not settings.github_auth_configured:
        return RuntimeServices(identity, None, None, None)

    jwt_issuer = GitHubAppJwtIssuer.from_settings(settings)
    assert settings.credential_encryption_key is not None
    cipher = CredentialCipher(
        {
            settings.credential_encryption_key_version: settings.credential_encryption_key.get_secret_value()
        },
        settings.credential_encryption_key_version,
    )
    http_client = httpx.AsyncClient()
    auth_client = GitHubAuthClient(http_client, settings, jwt_issuer)
    token_provider = InstallationTokenProvider(auth_client)
    repository_gateway = GitHubRepositoryGateway(GitHubRestClient(http_client))
    repository_read = RepositoryReadService(
        session_factory,
        token_provider,
        repository_gateway,
    )
    state_service = GitHubAuthorizationStateService(cipher)
    connection = GitHubConnectionService(
        session_factory,
        state_service,
        GitHubAuthUrlBuilder(settings),
        auth_client,
        InstallationBindingService(auth_client),
    )
    return RuntimeServices(identity, repository_read, connection, http_client)
