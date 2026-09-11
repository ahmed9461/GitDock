"""Current installed-repository resolution for file operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.db.models import GitHubInstallation, RepositoryCache
from gitdock.github.permissions import GitHubCapability, combine_installation_permissions
from gitdock.github.token_provider import InstallationTokenProvider
from gitdock.services.file_types import (
    CurrentRepository,
    FileSelectionError,
    InstalledRepositoryContext,
    RepositoryReadGateway,
)


class FileRepositoryContextResolver:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        token_provider: InstallationTokenProvider,
        repository_gateway: RepositoryReadGateway,
    ) -> None:
        self._session_factory = session_factory
        self._token_provider = token_provider
        self._repository_gateway = repository_gateway
        levels = combine_installation_permissions(
            {GitHubCapability.REPOSITORY_METADATA_READ, GitHubCapability.CONTENTS_READ}
        )
        self._read_permissions = {name: level.value for name, level in levels.items()}

    async def resolve(self, *, user_id: int, github_repository_id: int) -> CurrentRepository:
        if user_id <= 0 or github_repository_id <= 0:
            raise FileSelectionError("repository selection is invalid")
        async with self._session_factory() as session:
            row = await session.scalar(
                select(RepositoryCache).where(
                    RepositoryCache.user_id == user_id,
                    RepositoryCache.github_repository_id == github_repository_id,
                )
            )
            if row is None:
                raise FileSelectionError("repository selection is stale")
            installation = await session.get(GitHubInstallation, row.installation_db_id)
            if installation is None or installation.user_id != user_id or installation.suspended:
                raise FileSelectionError("repository installation is unavailable")
            context = InstalledRepositoryContext(
                installation_id=installation.installation_id,
                github_repository_id=github_repository_id,
                owner_login=row.owner_login,
                repository_name=row.name,
            )
        token = await self._token_provider.get_token(
            context.installation_id,
            permissions=self._read_permissions,
            repository_ids=[github_repository_id],
        )
        repository = await self._repository_gateway.get_repository(
            token.token,
            owner_login=context.owner_login,
            name=context.repository_name,
        )
        if repository.github_repository_id != github_repository_id:
            raise FileSelectionError("repository identity changed unexpectedly")
        return CurrentRepository(context=context, repository=repository, read_token=token.token)
