from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select

from gitdock.db.base import Base
from gitdock.db.models import GitHubInstallation, RepositoryCache, User
from gitdock.db.session import create_engine, create_session_factory
from gitdock.github.auth import InstallationAccessToken
from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.token_provider import InstallationTokenProvider
from gitdock.services.repositories import (
    RepositoryFilter,
    RepositoryReadService,
    RepositorySelectionError,
)


class FakeTokenSource:
    def __init__(self) -> None:
        self.calls: list[tuple[int, dict[str, str] | None, tuple[int, ...] | None]] = []

    async def create_installation_token(
        self,
        installation_id: int,
        *,
        permissions=None,
        repository_ids=None,
    ) -> InstallationAccessToken:
        normalized_ids = tuple(repository_ids) if repository_ids else None
        self.calls.append((installation_id, permissions, normalized_ids))
        return InstallationAccessToken(
            token=SecretStr(f"ghs_{installation_id}"),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            permissions=dict(permissions or {}),
        )


class FakeRepositoryGateway:
    def __init__(self, repositories: tuple[RepositorySnapshot, ...]) -> None:
        self.repositories = repositories
        self.detail_calls: list[tuple[str, str, str]] = []

    async def list_installation_repositories(
        self,
        token: SecretStr,
    ) -> tuple[RepositorySnapshot, ...]:
        assert token.get_secret_value().startswith("ghs_")
        return self.repositories

    async def get_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ) -> RepositorySnapshot:
        self.detail_calls.append((token.get_secret_value(), owner_login, name))
        for repository in self.repositories:
            if repository.owner_login == owner_login and repository.name == name:
                return repository
        raise AssertionError("test repository not found")


def snapshot(
    repository_id: int,
    name: str,
    *,
    private: bool = False,
    archived: bool = False,
    fork: bool = False,
    minutes_ago: int = 0,
) -> RepositorySnapshot:
    now = datetime.now(UTC)
    return RepositorySnapshot(
        github_repository_id=repository_id,
        owner_login="ahmed9461",
        name=name,
        full_name=f"ahmed9461/{name}",
        html_url=f"https://github.com/ahmed9461/{name}",
        private=private,
        archived=archived,
        fork=fork,
        default_branch="main",
        language="Python",
        description=None,
        stars=repository_id,
        forks=0,
        updated_at=now - timedelta(minutes=minutes_ago),
        pushed_at=now - timedelta(minutes=minutes_ago),
    )


async def build_service(repositories: tuple[RepositorySnapshot, ...]):
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    async with sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        installation = GitHubInstallation(
            user_id=user.id,
            installation_id=99,
            account_login="ahmed9461",
            account_type="User",
            suspended=False,
            permissions_json={"metadata": "read"},
        )
        session.add(installation)
        await session.commit()
        user_id = user.id

    token_source = FakeTokenSource()
    gateway = FakeRepositoryGateway(repositories)
    service = RepositoryReadService(
        sessions,
        InstallationTokenProvider(token_source),
        gateway,
    )
    return engine, sessions, service, token_source, gateway, user_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repository_list_is_paginated_filtered_and_cached() -> None:
    repositories = tuple(
        snapshot(index, f"Repo{index}", private=index % 2 == 0, minutes_ago=index)
        for index in range(1, 11)
    )
    engine, sessions, service, token_source, _, user_id = await build_service(repositories)

    first_page = await service.list_repositories(user_id=user_id, page=1)
    second_page = await service.list_repositories(user_id=user_id, page=2)
    private_page = await service.list_repositories(
        user_id=user_id,
        repository_filter=RepositoryFilter.PRIVATE,
    )

    assert len(first_page.items) == 8
    assert len(second_page.items) == 2
    assert first_page.total_pages == 2
    assert private_page.total_items == 5
    assert all(repository.private for repository in private_page.items)
    assert token_source.calls
    assert token_source.calls[0][1] == {"metadata": "read"}

    async with sessions() as session:
        cached_count = await session.scalar(select(func.count()).select_from(RepositoryCache))
        assert cached_count == 10

    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repository_detail_resolves_compact_id_only_inside_same_user_installation() -> None:
    repository = snapshot(1351822221, "GitDock", private=True)
    engine, sessions, service, token_source, gateway, user_id = await build_service((repository,))
    await service.list_repositories(user_id=user_id)

    detail = await service.repository_detail(
        user_id=user_id,
        github_repository_id=repository.github_repository_id,
    )

    assert detail.full_name == "ahmed9461/GitDock"
    assert gateway.detail_calls == [("ghs_99", "ahmed9461", "GitDock")]
    assert token_source.calls[-1][2] == (1351822221,)

    async with sessions() as session:
        other_user = User()
        session.add(other_user)
        await session.commit()
        other_user_id = other_user.id

    with pytest.raises(RepositorySelectionError, match="stale"):
        await service.repository_detail(
            user_id=other_user_id,
            github_repository_id=repository.github_repository_id,
        )

    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_prunes_repositories_removed_from_installation() -> None:
    one = snapshot(1, "One")
    two = snapshot(2, "Two")
    engine, sessions, service, _, gateway, user_id = await build_service((one, two))
    await service.list_repositories(user_id=user_id)

    gateway.repositories = (one,)
    refreshed = await service.list_repositories(user_id=user_id)

    assert [repository.name for repository in refreshed.items] == ["One"]
    async with sessions() as session:
        cached_ids = set(
            (await session.scalars(select(RepositoryCache.github_repository_id))).all()
        )
        assert cached_ids == {1}

    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_home_without_bound_installation_is_disconnected_and_does_not_request_token() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    async with sessions() as session:
        user = User()
        session.add(user)
        await session.commit()
        user_id = user.id

    token_source = FakeTokenSource()
    service = RepositoryReadService(
        sessions,
        InstallationTokenProvider(token_source),
        FakeRepositoryGateway(()),
    )
    status = await service.home(user_id=user_id)

    assert status.connected is False
    assert status.repository_count == 0
    assert token_source.calls == []
    await engine.dispose()
