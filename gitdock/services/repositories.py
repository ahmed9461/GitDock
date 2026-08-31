"""Read-only repository application service for P2.3."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import ceil
from typing import Protocol

from pydantic import SecretStr
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.core.constants import DEFAULT_PAGE_SIZE
from gitdock.db.models.identity import GitHubInstallation
from gitdock.db.models.repository import RepositoryCache
from gitdock.github.errors import GitHubNotFoundError
from gitdock.github.permissions import GitHubCapability, combine_installation_permissions
from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.token_provider import InstallationTokenProvider


class RepositoryFilter(StrEnum):
    ALL = "all"
    PRIVATE = "private"
    PUBLIC = "public"
    ACTIVE = "active"
    ARCHIVED = "archived"
    SOURCE = "source"
    FORK = "fork"


class RepositorySelectionError(RuntimeError):
    """Raised when a compact repository callback no longer maps to the current user."""


class RepositoryGateway(Protocol):
    async def list_installation_repositories(
        self,
        token: SecretStr,
    ) -> tuple[RepositorySnapshot, ...]: ...

    async def get_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ) -> RepositorySnapshot: ...


@dataclass(frozen=True, slots=True)
class InstallationContext:
    database_id: int
    installation_id: int
    account_login: str


@dataclass(frozen=True, slots=True)
class HomeStatus:
    connected: bool
    account_label: str | None
    installation_count: int
    repository_count: int


@dataclass(frozen=True, slots=True)
class RepositoryListPage:
    items: tuple[RepositorySnapshot, ...]
    page: int
    total_pages: int
    total_items: int
    repository_filter: RepositoryFilter


class RepositoryReadService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        token_provider: InstallationTokenProvider,
        gateway: RepositoryGateway,
    ) -> None:
        self._session_factory = session_factory
        self._token_provider = token_provider
        self._gateway = gateway
        permission_levels = combine_installation_permissions(
            {GitHubCapability.REPOSITORY_METADATA_READ}
        )
        self._metadata_permissions = {
            name: level.value for name, level in permission_levels.items()
        }

    async def home(self, *, user_id: int) -> HomeStatus:
        installations = await self._installations(user_id)
        if not installations:
            return HomeStatus(False, None, 0, 0)
        repositories = await self._refresh_all(user_id, installations)
        account_label = installations[0].account_login
        if len(installations) > 1:
            account_label = f"{account_label} +{len(installations) - 1}"
        return HomeStatus(
            connected=True,
            account_label=account_label,
            installation_count=len(installations),
            repository_count=len(repositories),
        )

    async def list_repositories(
        self,
        *,
        user_id: int,
        page: int = 1,
        repository_filter: RepositoryFilter = RepositoryFilter.ALL,
    ) -> RepositoryListPage:
        if page <= 0:
            raise ValueError("page must be positive")
        installations = await self._installations(user_id)
        if not installations:
            return RepositoryListPage((), 1, 1, 0, repository_filter)

        repositories = self._apply_filter(
            await self._refresh_all(user_id, installations), repository_filter
        )
        total_items = len(repositories)
        total_pages = max(1, ceil(total_items / DEFAULT_PAGE_SIZE))
        effective_page = min(page, total_pages)
        start = (effective_page - 1) * DEFAULT_PAGE_SIZE
        end = start + DEFAULT_PAGE_SIZE
        return RepositoryListPage(
            items=tuple(repositories[start:end]),
            page=effective_page,
            total_pages=total_pages,
            total_items=total_items,
            repository_filter=repository_filter,
        )

    async def repository_detail(
        self,
        *,
        user_id: int,
        github_repository_id: int,
    ) -> RepositorySnapshot:
        if github_repository_id <= 0:
            raise RepositorySelectionError("repository selection is invalid")

        async with self._session_factory() as session:
            row = await session.scalar(
                select(RepositoryCache).where(
                    RepositoryCache.user_id == user_id,
                    RepositoryCache.github_repository_id == github_repository_id,
                )
            )
            if row is None:
                raise RepositorySelectionError("repository selection is stale")
            installation = await session.get(GitHubInstallation, row.installation_db_id)
            if installation is None or installation.user_id != user_id or installation.suspended:
                raise RepositorySelectionError("repository installation is unavailable")
            owner_login = row.owner_login
            name = row.name
            installation_id = installation.installation_id
            installation_db_id = installation.id

        token = await self._token_provider.get_token(
            installation_id,
            permissions=self._metadata_permissions,
            repository_ids=[github_repository_id],
        )
        try:
            snapshot = await self._gateway.get_repository(
                token.token,
                owner_login=owner_login,
                name=name,
            )
        except GitHubNotFoundError:
            await self._remove_cache(user_id, github_repository_id)
            raise

        if snapshot.github_repository_id != github_repository_id:
            raise RepositorySelectionError("repository identity changed unexpectedly")
        await self._upsert_one(user_id, installation_db_id, snapshot)
        return snapshot

    async def _installations(self, user_id: int) -> tuple[InstallationContext, ...]:
        if user_id <= 0:
            raise ValueError("user ID must be positive")
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(GitHubInstallation)
                    .where(
                        GitHubInstallation.user_id == user_id,
                        GitHubInstallation.suspended.is_(False),
                    )
                    .order_by(GitHubInstallation.id)
                )
            ).all()
            return tuple(
                InstallationContext(row.id, row.installation_id, row.account_login) for row in rows
            )

    async def _refresh_all(
        self,
        user_id: int,
        installations: tuple[InstallationContext, ...],
    ) -> list[RepositorySnapshot]:
        merged: dict[int, tuple[int, RepositorySnapshot]] = {}
        for installation in installations:
            token = await self._token_provider.get_token(
                installation.installation_id,
                permissions=self._metadata_permissions,
            )
            repositories = await self._gateway.list_installation_repositories(token.token)
            for repository in repositories:
                merged[repository.github_repository_id] = (
                    installation.database_id,
                    repository,
                )

        async with self._session_factory() as session:
            async with session.begin():
                await self._sync_cache(session, user_id=user_id, repositories=merged)

        return sorted(
            (item[1] for item in merged.values()),
            key=lambda repository: (repository.updated_at, repository.full_name.casefold()),
            reverse=True,
        )

    async def _sync_cache(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        repositories: dict[int, tuple[int, RepositorySnapshot]],
    ) -> None:
        existing_rows = (
            await session.scalars(select(RepositoryCache).where(RepositoryCache.user_id == user_id))
        ).all()
        existing = {row.github_repository_id: row for row in existing_rows}

        for repository_id, (installation_db_id, snapshot) in repositories.items():
            row = existing.get(repository_id)
            if row is None:
                row = RepositoryCache(
                    user_id=user_id,
                    installation_db_id=installation_db_id,
                    github_repository_id=snapshot.github_repository_id,
                    owner_login=snapshot.owner_login,
                    name=snapshot.name,
                    full_name=snapshot.full_name,
                    html_url=snapshot.html_url,
                    private=snapshot.private,
                    archived=snapshot.archived,
                    fork=snapshot.fork,
                    default_branch=snapshot.default_branch,
                    language=snapshot.language,
                    description=snapshot.description,
                    stars=snapshot.stars,
                    forks=snapshot.forks,
                    github_updated_at=snapshot.updated_at,
                    github_pushed_at=snapshot.pushed_at,
                    cached_at=datetime.now(UTC),
                )
                session.add(row)
            else:
                self._apply_snapshot(row, installation_db_id, snapshot)

        stale_ids = set(existing) - set(repositories)
        if stale_ids:
            await session.execute(
                delete(RepositoryCache).where(
                    RepositoryCache.user_id == user_id,
                    RepositoryCache.github_repository_id.in_(stale_ids),
                )
            )

    async def _upsert_one(
        self,
        user_id: int,
        installation_db_id: int,
        snapshot: RepositorySnapshot,
    ) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.scalar(
                    select(RepositoryCache).where(
                        RepositoryCache.user_id == user_id,
                        RepositoryCache.github_repository_id == snapshot.github_repository_id,
                    )
                )
                if row is None:
                    row = RepositoryCache(
                        user_id=user_id,
                        installation_db_id=installation_db_id,
                        github_repository_id=snapshot.github_repository_id,
                        owner_login=snapshot.owner_login,
                        name=snapshot.name,
                        full_name=snapshot.full_name,
                        html_url=snapshot.html_url,
                        private=snapshot.private,
                        archived=snapshot.archived,
                        fork=snapshot.fork,
                        default_branch=snapshot.default_branch,
                        language=snapshot.language,
                        description=snapshot.description,
                        stars=snapshot.stars,
                        forks=snapshot.forks,
                        github_updated_at=snapshot.updated_at,
                        github_pushed_at=snapshot.pushed_at,
                        cached_at=datetime.now(UTC),
                    )
                    session.add(row)
                else:
                    self._apply_snapshot(row, installation_db_id, snapshot)

    async def _remove_cache(self, user_id: int, github_repository_id: int) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(RepositoryCache).where(
                        RepositoryCache.user_id == user_id,
                        RepositoryCache.github_repository_id == github_repository_id,
                    )
                )

    @staticmethod
    def _apply_snapshot(
        row: RepositoryCache,
        installation_db_id: int,
        snapshot: RepositorySnapshot,
    ) -> None:
        row.installation_db_id = installation_db_id
        row.owner_login = snapshot.owner_login
        row.name = snapshot.name
        row.full_name = snapshot.full_name
        row.html_url = snapshot.html_url
        row.private = snapshot.private
        row.archived = snapshot.archived
        row.fork = snapshot.fork
        row.default_branch = snapshot.default_branch
        row.language = snapshot.language
        row.description = snapshot.description
        row.stars = snapshot.stars
        row.forks = snapshot.forks
        row.github_updated_at = snapshot.updated_at
        row.github_pushed_at = snapshot.pushed_at
        row.cached_at = datetime.now(UTC)

    @staticmethod
    def _apply_filter(
        repositories: list[RepositorySnapshot],
        repository_filter: RepositoryFilter,
    ) -> list[RepositorySnapshot]:
        if repository_filter is RepositoryFilter.ALL:
            return repositories
        if repository_filter is RepositoryFilter.PRIVATE:
            return [repository for repository in repositories if repository.private]
        if repository_filter is RepositoryFilter.PUBLIC:
            return [repository for repository in repositories if not repository.private]
        if repository_filter is RepositoryFilter.ACTIVE:
            return [repository for repository in repositories if not repository.archived]
        if repository_filter is RepositoryFilter.ARCHIVED:
            return [repository for repository in repositories if repository.archived]
        if repository_filter is RepositoryFilter.SOURCE:
            return [repository for repository in repositories if not repository.fork]
        if repository_filter is RepositoryFilter.FORK:
            return [repository for repository in repositories if repository.fork]
        raise ValueError("unsupported repository filter")
