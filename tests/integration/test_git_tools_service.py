from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr
from sqlalchemy import select

from gitdock.db.base import Base
from gitdock.db.models import AuditLog, GitHubInstallation, RepositoryCache, User
from gitdock.db.session import create_engine, create_session_factory
from gitdock.github.auth import InstallationAccessToken
from gitdock.github.errors import GitHubErrorKind, GitHubNotFoundError, GitHubTransientError
from gitdock.github.git_tools import (
    BranchSnapshot,
    CommitDetail,
    CommitSummary,
    CompareSnapshot,
    CreatedBranch,
)
from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.token_provider import InstallationTokenProvider
from gitdock.services.confirmations import ConfirmationService
from gitdock.services.git_tools import BranchCreateState, GitToolsService

_REPOSITORY_ID = 1351822221


class FakeTokenSource:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def create_installation_token(
        self,
        installation_id: int,
        *,
        permissions=None,
        repository_ids=None,
    ) -> InstallationAccessToken:
        assert installation_id == 99
        assert tuple(repository_ids or ()) == (_REPOSITORY_ID,)
        normalized = dict(permissions or {})
        self.calls.append(normalized)
        label = "write" if normalized.get("contents") == "write" else "read"
        return InstallationAccessToken(
            SecretStr(f"ghs_{label}"),
            datetime.now(UTC) + timedelta(hours=1),
            normalized,
        )


class FakeRepositoryGateway:
    def __init__(self, repository: RepositorySnapshot) -> None:
        self.repository = repository

    async def get_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ) -> RepositorySnapshot:
        assert token.get_secret_value().startswith("ghs_read")
        return self.repository


class FakeGitGateway:
    def __init__(self) -> None:
        self.branches = {"main": "a" * 40, "feature/x": "b" * 40}
        self.create_calls = 0
        self.create_mode = "success"

    async def list_branches(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ) -> tuple[BranchSnapshot, ...]:
        assert token.get_secret_value().startswith("ghs_read")
        return tuple(
            BranchSnapshot(branch, sha, branch == "main")
            for branch, sha in self.branches.items()
        )

    async def get_branch(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        branch: str,
    ) -> BranchSnapshot:
        sha = self.branches.get(branch)
        if sha is None:
            raise GitHubNotFoundError(
                GitHubErrorKind.NOT_FOUND, "missing", status_code=404
            )
        return BranchSnapshot(branch, sha, branch == "main")

    async def recent_commits(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        ref=None,
        limit=30,
    ) -> tuple[CommitSummary, ...]:
        return (
            CommitSummary(
                "c" * 40,
                "feat: one",
                "Ahmed",
                datetime(2026, 9, 11, tzinfo=UTC),
                "https://github.com/ahmed9461/GitDock/commit/" + "c" * 40,
            ),
        )

    async def get_commit(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        ref: str,
    ) -> CommitDetail:
        sha = self.branches.get(ref, ref)
        if len(sha) != 40:
            raise GitHubNotFoundError(
                GitHubErrorKind.NOT_FOUND, "missing", status_code=404
            )
        return CommitDetail(
            sha,
            "commit",
            "Ahmed",
            datetime(2026, 9, 11, tzinfo=UTC),
            f"https://github.com/ahmed9461/GitDock/commit/{sha}",
            (),
            1,
            0,
            1,
        )

    async def compare(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        base: str,
        head: str,
    ) -> CompareSnapshot:
        return CompareSnapshot("ahead", 1, 0, 1, ())

    async def create_branch(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        branch: str,
        sha: str,
    ) -> CreatedBranch:
        assert token.get_secret_value().startswith("ghs_write")
        self.create_calls += 1
        self.branches[branch] = sha
        if self.create_mode == "transient_applied":
            raise GitHubTransientError(
                GitHubErrorKind.TRANSIENT,
                "lost response",
                request_id="lost-request",
            )
        return CreatedBranch(branch, sha, "create-request")


def _snapshot() -> RepositorySnapshot:
    now = datetime.now(UTC)
    return RepositorySnapshot(
        github_repository_id=_REPOSITORY_ID,
        owner_login="ahmed9461",
        name="GitDock",
        full_name="ahmed9461/GitDock",
        html_url="https://github.com/ahmed9461/GitDock",
        private=True,
        archived=False,
        fork=False,
        default_branch="main",
        language="Python",
        description="repo",
        stars=1,
        forks=0,
        updated_at=now,
        pushed_at=now,
    )


async def _build_service():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    repository = _snapshot()
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
            permissions_json={"contents": "write", "metadata": "read"},
        )
        session.add(installation)
        await session.flush()
        session.add(
            RepositoryCache(
                user_id=user.id,
                installation_db_id=installation.id,
                github_repository_id=repository.github_repository_id,
                owner_login=repository.owner_login,
                name=repository.name,
                full_name=repository.full_name,
                html_url=repository.html_url,
                private=repository.private,
                archived=repository.archived,
                fork=repository.fork,
                default_branch=repository.default_branch,
                language=repository.language,
                description=repository.description,
                stars=repository.stars,
                forks=repository.forks,
                github_updated_at=repository.updated_at,
                github_pushed_at=repository.pushed_at,
            )
        )
        await session.commit()
        user_id = user.id

    tokens = FakeTokenSource()
    git = FakeGitGateway()
    service = GitToolsService(
        sessions,
        InstallationTokenProvider(tokens),
        FakeRepositoryGateway(repository),
        git,
        ConfirmationService(),
    )
    return engine, sessions, service, git, tokens, user_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reads_branches_commits_and_compare() -> None:
    engine, _, service, _, _, user_id = await _build_service()
    branches = await service.list_branches(
        user_id=user_id, github_repository_id=_REPOSITORY_ID
    )
    commits = await service.recent_commits(
        user_id=user_id, github_repository_id=_REPOSITORY_ID
    )
    compare = await service.compare(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        base="main",
        head="feature/x",
    )
    assert [branch.name for branch in branches.branches] == ["main", "feature/x"]
    assert commits.commits[0].sha == "c" * 40
    assert compare.comparison.ahead_by == 1
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_branch_create_is_preview_confirm_and_scoped_write() -> None:
    engine, sessions, service, git, tokens, user_id = await _build_service()
    plan = await service.begin_create_branch(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        branch="feature/new",
        base_ref="main",
    )
    assert git.create_calls == 0
    outcome = await service.confirm_create_branch(
        user_id=user_id, token=plan.confirmation_token
    )
    assert outcome.state is BranchCreateState.APPLIED
    assert git.create_calls == 1
    assert {"contents": "write", "metadata": "read"} in tokens.calls
    async with sessions() as session:
        audit = await session.scalar(
            select(AuditLog).where(AuditLog.operation == "git.branch.create")
        )
        assert audit is not None and audit.status == "success"
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_branch_create_rejects_stale_base_without_write() -> None:
    engine, _, service, git, _, user_id = await _build_service()
    plan = await service.begin_create_branch(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        branch="feature/new",
        base_ref="main",
    )
    git.branches["main"] = "e" * 40
    outcome = await service.confirm_create_branch(
        user_id=user_id, token=plan.confirmation_token
    )
    assert outcome.state is BranchCreateState.STALE
    assert git.create_calls == 0
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_uncertain_create_reconciles_existing_target_without_replay() -> None:
    engine, _, service, git, _, user_id = await _build_service()
    git.create_mode = "transient_applied"
    plan = await service.begin_create_branch(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        branch="feature/new",
        base_ref="main",
    )
    outcome = await service.confirm_create_branch(
        user_id=user_id, token=plan.confirmation_token
    )
    assert outcome.state is BranchCreateState.APPLIED
    assert git.create_calls == 1
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancelled_branch_confirmation_is_not_reusable() -> None:
    engine, _, service, git, _, user_id = await _build_service()
    plan = await service.begin_create_branch(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        branch="feature/new",
        base_ref="main",
    )
    assert await service.cancel_create_branch(
        user_id=user_id, token=plan.confirmation_token
    )
    outcome = await service.confirm_create_branch(
        user_id=user_id, token=plan.confirmation_token
    )
    assert outcome.state is BranchCreateState.INVALID
    assert git.create_calls == 0
    await engine.dispose()
