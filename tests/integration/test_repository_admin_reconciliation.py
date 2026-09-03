from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select

from gitdock.db.base import Base
from gitdock.db.models import AuditLog, GitHubAccount, GitHubInstallation, RepositoryCache, User
from gitdock.db.session import create_engine, create_session_factory
from gitdock.github.auth import InstallationAccessToken, UserAccessToken
from gitdock.github.errors import (
    GitHubErrorKind,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubTransientError,
)
from gitdock.github.models import GitHubPaginationLinks, GitHubRateLimit, GitHubResponse
from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.repository_admin import RepositoryCreateRequest, RepositoryUpdateRequest
from gitdock.github.token_provider import InstallationTokenProvider
from gitdock.services.confirmations import ConfirmationService
from gitdock.services.repository_admin import RepositoryAdminService, RepositoryAdminState


class MutableClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 9, 4, 0, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


class FakeUserAuthorization:
    async def get_valid_token(self, *, user_id: int) -> UserAccessToken:
        assert user_id > 0
        return UserAccessToken(SecretStr("ghu_test"), None, None, None)


class FakeTokenSource:
    async def create_installation_token(
        self,
        installation_id: int,
        *,
        permissions=None,
        repository_ids=None,
    ) -> InstallationAccessToken:
        assert installation_id == 99
        assert permissions == {"administration": "write"}
        assert tuple(repository_ids or ()) == (1351822221,)
        return InstallationAccessToken(
            SecretStr("ghs_admin"),
            datetime.now(UTC) + timedelta(hours=1),
            dict(permissions or {}),
        )


class ReconciliationReadGateway:
    def __init__(self, current: RepositorySnapshot | None) -> None:
        self.current = current
        self.calls: list[tuple[str, str]] = []

    async def get_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ) -> RepositorySnapshot:
        assert token.get_secret_value() in {"ghs_admin", "ghu_test"}
        self.calls.append((owner_login, name))
        if self.current is None or (
            self.current.owner_login != owner_login or self.current.name != name
        ):
            raise GitHubNotFoundError(
                GitHubErrorKind.NOT_FOUND,
                "repository missing during reconciliation",
                status_code=404,
            )
        return self.current


class ReconciliationAdminGateway:
    def __init__(self, read_gateway: ReconciliationReadGateway) -> None:
        self.read_gateway = read_gateway
        self.create_mode = "success"
        self.update_mode = "success"
        self.delete_mode = "success"
        self.create_calls = 0
        self.update_calls = 0
        self.delete_calls = 0

    async def create_personal_repository(
        self,
        token: SecretStr,
        request: RepositoryCreateRequest,
    ) -> GitHubResponse[RepositorySnapshot]:
        assert token.get_secret_value() == "ghu_test"
        self.create_calls += 1
        created = snapshot(
            1351822222,
            request.name,
            private=request.private,
            description=request.description,
        )
        if self.create_mode == "transient_applied":
            self.read_gateway.current = created
            raise transient_error()
        if self.create_mode == "transient_unresolved":
            raise transient_error()
        if self.create_mode == "permission":
            raise permission_error()
        return response(created, request_id="create-ok")

    async def create_organization_repository(
        self,
        token: SecretStr,
        *,
        organization: str,
        request: RepositoryCreateRequest,
    ) -> GitHubResponse[RepositorySnapshot]:
        assert token.get_secret_value() == "ghu_test"
        self.create_calls += 1
        created = snapshot(
            1351822222,
            request.name,
            owner=organization,
            private=request.private,
            description=request.description,
        )
        if self.create_mode == "transient_applied":
            self.read_gateway.current = created
            raise transient_error()
        return response(created, request_id="org-create-ok")

    async def update_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        request: RepositoryUpdateRequest,
    ) -> GitHubResponse[RepositorySnapshot]:
        assert token.get_secret_value() == "ghs_admin"
        self.update_calls += 1
        current = self.read_gateway.current
        assert current is not None
        updated = snapshot(
            current.github_repository_id,
            request.name or name,
            owner=owner_login,
            private=current.private if request.private is None else request.private,
            archived=current.archived if request.archived is None else request.archived,
            description=current.description if request.description is None else request.description,
            default_branch=(
                current.default_branch if request.default_branch is None else request.default_branch
            ),
        )
        if self.update_mode == "transient_applied":
            self.read_gateway.current = updated
            raise transient_error()
        if self.update_mode == "transient_unresolved":
            raise transient_error()
        if self.update_mode == "permission":
            raise permission_error()
        self.read_gateway.current = updated
        return response(updated, request_id="update-ok")

    async def delete_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ) -> GitHubResponse[None]:
        assert token.get_secret_value() == "ghs_admin"
        self.delete_calls += 1
        if self.delete_mode == "transient_applied":
            self.read_gateway.current = None
            raise transient_error()
        if self.delete_mode == "transient_unresolved":
            raise transient_error()
        if self.delete_mode == "permission":
            raise permission_error()
        self.read_gateway.current = None
        return response(None, status_code=204, request_id="delete-ok")


def snapshot(
    repository_id: int,
    name: str = "GitDock",
    *,
    owner: str = "ahmed9461",
    private: bool = True,
    archived: bool = False,
    description: str | None = "repo",
    default_branch: str = "main",
) -> RepositorySnapshot:
    now = datetime(2026, 9, 4, 0, 0, tzinfo=UTC)
    return RepositorySnapshot(
        github_repository_id=repository_id,
        owner_login=owner,
        name=name,
        full_name=f"{owner}/{name}",
        html_url=f"https://github.com/{owner}/{name}",
        private=private,
        archived=archived,
        fork=False,
        default_branch=default_branch,
        language="Python",
        description=description,
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


def transient_error() -> GitHubTransientError:
    return GitHubTransientError(
        GitHubErrorKind.TRANSIENT,
        "write response was lost",
        request_id="uncertain-write",
    )


def permission_error() -> GitHubPermissionError:
    return GitHubPermissionError(
        GitHubErrorKind.PERMISSION,
        "write permission missing",
        status_code=403,
        request_id="denied-write",
    )


async def build_service(*, confirmations: ConfirmationService | None = None):
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

    read_gateway = ReconciliationReadGateway(current)
    admin_gateway = ReconciliationAdminGateway(read_gateway)
    service = RepositoryAdminService(
        sessions,
        FakeUserAuthorization(),  # type: ignore[arg-type]
        InstallationTokenProvider(FakeTokenSource()),
        read_gateway,
        admin_gateway,
        confirmations or ConfirmationService(),
    )
    return engine, sessions, service, read_gateway, admin_gateway, user_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_uncertain_create_reconciles_remote_success() -> None:
    engine, sessions, service, _, admin, user_id = await build_service()
    admin.create_mode = "transient_applied"
    plan = await service.begin_create(
        user_id=user_id,
        request=RepositoryCreateRequest("Recovered", "desc", True),
    )

    result = await service.confirm_create(user_id=user_id, token=plan.token)

    assert result.state is RepositoryAdminState.APPLIED
    assert result.repository is not None and result.repository.name == "Recovered"
    async with sessions() as session:
        audit = await session.scalar(
            select(AuditLog).where(AuditLog.operation == "repository.create")
        )
        assert audit is not None and audit.status == "success"
        assert audit.details_json is not None and audit.details_json["reconciled"] is True
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_uncertain_update_reconciles_remote_success_and_cache() -> None:
    engine, sessions, service, _, admin, user_id = await build_service()
    admin.update_mode = "transient_applied"
    plan = await service.begin_update(
        user_id=user_id,
        github_repository_id=1351822221,
        request=RepositoryUpdateRequest(archived=True),
    )

    result = await service.confirm_update(user_id=user_id, token=plan.token)

    assert result.state is RepositoryAdminState.APPLIED
    async with sessions() as session:
        cached = await session.scalar(
            select(RepositoryCache).where(RepositoryCache.github_repository_id == 1351822221)
        )
        assert cached is not None and cached.archived is True
        audit = await session.scalar(
            select(AuditLog).where(AuditLog.operation == "repository.update")
        )
        assert audit is not None and audit.status == "success"
        assert audit.details_json is not None and audit.details_json["reconciled"] is True
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_uncertain_delete_reconciles_not_found_as_success() -> None:
    engine, sessions, service, _, admin, user_id = await build_service()
    admin.delete_mode = "transient_applied"
    plan = await service.begin_delete(
        user_id=user_id,
        github_repository_id=1351822221,
        typed_full_name="ahmed9461/GitDock",
    )
    assert plan is not None

    result = await service.confirm_delete(user_id=user_id, token=plan.token)

    assert result.state is RepositoryAdminState.APPLIED
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(RepositoryCache)) == 0
        audit = await session.scalar(
            select(AuditLog).where(AuditLog.operation == "repository.delete")
        )
        assert audit is not None and audit.status == "success"
        assert audit.details_json is not None and audit.details_json["reconciled"] is True
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unresolved_write_remains_uncertain_not_failure() -> None:
    engine, sessions, service, _, admin, user_id = await build_service()
    admin.create_mode = "transient_unresolved"
    plan = await service.begin_create(
        user_id=user_id,
        request=RepositoryCreateRequest("UnknownOutcome", None, True),
    )

    result = await service.confirm_create(user_id=user_id, token=plan.token)

    assert result.state is RepositoryAdminState.UNCERTAIN
    async with sessions() as session:
        audit = await session.scalar(
            select(AuditLog).where(AuditLog.operation == "repository.create")
        )
        assert audit is not None and audit.status == "uncertain"
        assert audit.details_json is not None and audit.details_json["reconciled"] is False
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_expired_delete_confirmation_never_executes_write() -> None:
    clock = MutableClock()
    confirmations = ConfirmationService(ttl=timedelta(seconds=5), clock=clock)
    engine, _, service, _, admin, user_id = await build_service(confirmations=confirmations)
    plan = await service.begin_delete(
        user_id=user_id,
        github_repository_id=1351822221,
        typed_full_name="ahmed9461/GitDock",
    )
    assert plan is not None
    clock.now += timedelta(seconds=6)

    result = await service.confirm_delete(user_id=user_id, token=plan.token)

    assert result.state is RepositoryAdminState.INVALID
    assert admin.delete_calls == 0
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_permission_failure_is_audited_as_failure_and_raised() -> None:
    engine, sessions, service, _, admin, user_id = await build_service()
    admin.delete_mode = "permission"
    plan = await service.begin_delete(
        user_id=user_id,
        github_repository_id=1351822221,
        typed_full_name="ahmed9461/GitDock",
    )
    assert plan is not None

    with pytest.raises(GitHubPermissionError):
        await service.confirm_delete(user_id=user_id, token=plan.token)

    async with sessions() as session:
        audit = await session.scalar(
            select(AuditLog).where(AuditLog.operation == "repository.delete")
        )
        assert audit is not None and audit.status == "failure"
        assert audit.details_json is not None
        assert audit.details_json["error_kind"] == GitHubErrorKind.PERMISSION.value
    await engine.dispose()
