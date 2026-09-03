from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select

from gitdock.db.base import Base
from gitdock.db.models import AuditLog, GitHubAccount, GitHubInstallation, RepositoryCache, User
from gitdock.db.session import create_engine, create_session_factory
from gitdock.github.auth import InstallationAccessToken, UserAccessToken
from gitdock.github.models import GitHubPaginationLinks, GitHubRateLimit, GitHubResponse
from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.repository_admin import RepositoryCreateRequest, RepositoryUpdateRequest
from gitdock.github.token_provider import InstallationTokenProvider
from gitdock.services.confirmations import ConfirmationService
from gitdock.services.repository_admin import (
    RepositoryAdminService,
    RepositoryAdminState,
)


class FakeUserAuthorization:
    async def get_valid_token(self, *, user_id: int) -> UserAccessToken:
        assert user_id > 0
        return UserAccessToken(SecretStr("ghu_test"), None, None, None)


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
        ids = tuple(repository_ids) if repository_ids else None
        self.calls.append((installation_id, dict(permissions or {}) or None, ids))
        return InstallationAccessToken(
            SecretStr("ghs_admin"),
            datetime.now(UTC) + timedelta(hours=1),
            dict(permissions or {}),
        )


class FakeReadGateway:
    def __init__(self, current: RepositorySnapshot) -> None:
        self.current = current
        self.calls = 0

    async def get_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ) -> RepositorySnapshot:
        assert token.get_secret_value() == "ghs_admin"
        self.calls += 1
        assert owner_login == self.current.owner_login
        assert name == self.current.name
        return self.current


class FakeAdminGateway:
    def __init__(self, current: RepositorySnapshot) -> None:
        self.current = current
        self.create_calls = 0
        self.update_calls = 0
        self.delete_calls = 0

    async def create_personal_repository(self, token: SecretStr, request: RepositoryCreateRequest):
        assert token.get_secret_value() == "ghu_test"
        self.create_calls += 1
        created = snapshot(self.current.github_repository_id + 1, request.name, private=request.private)
        return response(created, request_id="create-1")

    async def create_organization_repository(
        self,
        token: SecretStr,
        *,
        organization: str,
        request: RepositoryCreateRequest,
    ):
        raise AssertionError("organization creation not expected")

    async def update_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        request: RepositoryUpdateRequest,
    ):
        assert token.get_secret_value() == "ghs_admin"
        self.update_calls += 1
        updated = snapshot(
            self.current.github_repository_id,
            request.name or name,
            private=self.current.private if request.private is None else request.private,
            archived=self.current.archived if request.archived is None else request.archived,
        )
        self.current = updated
        return response(updated, request_id="update-1")

    async def delete_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ):
        assert token.get_secret_value() == "ghs_admin"
        self.delete_calls += 1
        return response(None, status_code=204, request_id="delete-1")


def snapshot(
    repository_id: int,
    name: str = "GitDock",
    *,
    private: bool = True,
    archived: bool = False,
) -> RepositorySnapshot:
    now = datetime(2026, 9, 3, 18, 0, tzinfo=UTC)
    return RepositorySnapshot(
        github_repository_id=repository_id,
        owner_login="ahmed9461",
        name=name,
        full_name=f"ahmed9461/{name}",
        html_url=f"https://github.com/ahmed9461/{name}",
        private=private,
        archived=archived,
        fork=False,
        default_branch="main",
        language="Python",
        description="repo",
        stars=1,
        forks=0,
        updated_at=now,
        pushed_at=now,
    )


def response(data, *, status_code: int = 200, request_id: str | None = None):
    return GitHubResponse(
        data=data,
        rate_limit=GitHubRateLimit(None, None, None, None, None, None),
        pagination=GitHubPaginationLinks(),
        request_id=request_id,
        status_code=status_code,
    )


async def build_service():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    current = snapshot(1351822221)
    async with sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        session.add(
            GitHubAccount(
                user_id=user.id,
                github_user_id=128654158,
                login="ahmed9461",
                encrypted_access_token=b"encrypted",
                credential_generation=3,
            )
        )
        installation = GitHubInstallation(
            user_id=user.id,
            installation_id=99,
            account_login="ahmed9461",
            account_type="User",
            suspended=False,
            permissions_json={"administration": "write"},
        )
        session.add(installation)
        await session.flush()
        session.add(
            RepositoryCache(
                user_id=user.id,
                installation_db_id=installation.id,
                github_repository_id=current.github_repository_id,
                owner_login=current.owner_login,
                name=current.name,
                full_name=current.full_name,
                html_url=current.html_url,
                private=current.private,
                archived=current.archived,
                fork=current.fork,
                default_branch=current.default_branch,
                language=current.language,
                description=current.description,
                stars=current.stars,
                forks=current.forks,
                github_updated_at=current.updated_at,
                github_pushed_at=current.pushed_at,
            )
        )
        await session.commit()
        user_id = user.id

    token_source = FakeTokenSource()
    read_gateway = FakeReadGateway(current)
    admin_gateway = FakeAdminGateway(current)
    service = RepositoryAdminService(
        sessions,
        FakeUserAuthorization(),  # type: ignore[arg-type]
        InstallationTokenProvider(token_source),
        read_gateway,
        admin_gateway,
        ConfirmationService(),
    )
    return engine, sessions, service, token_source, read_gateway, admin_gateway, user_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_requires_confirmation_and_reuse_cannot_duplicate_write() -> None:
    engine, sessions, service, _, _, admin, user_id = await build_service()
    plan = await service.begin_create(
        user_id=user_id,
        request=RepositoryCreateRequest("NewRepo", "desc", True),
    )
    assert admin.create_calls == 0

    first = await service.confirm_create(user_id=user_id, token=plan.token)
    second = await service.confirm_create(user_id=user_id, token=plan.token)

    assert first.state is RepositoryAdminState.APPLIED
    assert first.repository is not None and first.repository.name == "NewRepo"
    assert second.state is RepositoryAdminState.INVALID
    assert admin.create_calls == 1
    async with sessions() as session:
        audit = await session.scalar(select(AuditLog).where(AuditLog.operation == "repository.create"))
        assert audit is not None
        assert audit.status == "success"
        assert audit.repository_full_name == "ahmed9461/NewRepo"
        assert "token" not in str(audit.details_json).lower()
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_uses_repository_scoped_admin_token_and_refreshes_cache() -> None:
    engine, sessions, service, token_source, _, admin, user_id = await build_service()
    plan = await service.begin_update(
        user_id=user_id,
        github_repository_id=1351822221,
        request=RepositoryUpdateRequest(archived=True),
    )
    result = await service.confirm_update(user_id=user_id, token=plan.token)

    assert result.state is RepositoryAdminState.APPLIED
    assert admin.update_calls == 1
    assert token_source.calls[-1] == (99, {"administration": "write"}, (1351822221,))
    async with sessions() as session:
        cached = await session.scalar(
            select(RepositoryCache).where(RepositoryCache.github_repository_id == 1351822221)
        )
        assert cached is not None and cached.archived is True
        assert await session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.operation == "repository.update")
        ) == 1
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_stale_snapshot_fails_closed_without_write() -> None:
    engine, _, service, _, read_gateway, admin, user_id = await build_service()
    plan = await service.begin_update(
        user_id=user_id,
        github_repository_id=1351822221,
        request=RepositoryUpdateRequest(archived=True),
    )
    read_gateway.current = snapshot(1351822221, private=False)

    result = await service.confirm_update(user_id=user_id, token=plan.token)

    assert result.state is RepositoryAdminState.STALE
    assert admin.update_calls == 0
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_requires_exact_full_name_and_removes_cache_once() -> None:
    engine, sessions, service, _, _, admin, user_id = await build_service()
    wrong = await service.begin_delete(
        user_id=user_id,
        github_repository_id=1351822221,
        typed_full_name="gitdock",
    )
    assert wrong is None
    assert admin.delete_calls == 0

    plan = await service.begin_delete(
        user_id=user_id,
        github_repository_id=1351822221,
        typed_full_name="ahmed9461/GitDock",
    )
    assert plan is not None
    first = await service.confirm_delete(user_id=user_id, token=plan.token)
    second = await service.confirm_delete(user_id=user_id, token=plan.token)

    assert first.state is RepositoryAdminState.APPLIED
    assert second.state is RepositoryAdminState.INVALID
    assert admin.delete_calls == 1
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(RepositoryCache)) == 0
        audit = await session.scalar(select(AuditLog).where(AuditLog.operation == "repository.delete"))
        assert audit is not None and audit.status == "success"
    await engine.dispose()
