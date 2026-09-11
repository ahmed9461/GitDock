from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr
from sqlalchemy import select

from gitdock.db.base import Base
from gitdock.db.models import AuditLog, FileWriteSession, GitHubInstallation, RepositoryCache, User
from gitdock.db.session import create_engine, create_session_factory
from gitdock.domain.files import RepositoryPathError, git_blob_sha
from gitdock.github.auth import InstallationAccessToken
from gitdock.github.contents import (
    ContentEntry,
    ContentKind,
    FileContent,
    FileWriteResult,
    RefSnapshot,
)
from gitdock.github.errors import GitHubErrorKind, GitHubNotFoundError, GitHubTransientError
from gitdock.github.models import GitHubPaginationLinks, GitHubRateLimit, GitHubResponse
from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.token_provider import InstallationTokenProvider
from gitdock.services.confirmations import ConfirmationService
from gitdock.services.file_browser import FileBrowserService, FileDisplayKind, FileWriteState

_REPOSITORY_ID = 1351822221


class FakeTokenSource:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, str], tuple[int, ...]]] = []

    async def create_installation_token(
        self,
        installation_id: int,
        *,
        permissions=None,
        repository_ids=None,
    ) -> InstallationAccessToken:
        assert installation_id == 99
        normalized = dict(permissions or {})
        repositories = tuple(repository_ids or ())
        self.calls.append((normalized, repositories))
        assert repositories == (_REPOSITORY_ID,)
        label = "write" if normalized.get("contents") == "write" else "read"
        return InstallationAccessToken(
            SecretStr(f"ghs_{label}_{len(self.calls)}"),
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
        assert owner_login == self.repository.owner_login
        assert name == self.repository.name
        return self.repository


class FakeContentsGateway:
    def __init__(self) -> None:
        self.branch_heads = {"main": "a" * 40, "feature/docs": "b" * 40}
        self.files: dict[tuple[str, str], bytes] = {
            ("main", "docs/README.md"): b"one\ntwo\n",
            ("feature/docs", "docs/README.md"): b"one\ntwo\n",
            ("main", ".github/workflows/ci.yml"): b"name: CI\n",
        }
        self.put_calls = 0
        self.delete_calls = 0
        self.put_mode = "success"
        self.delete_mode = "success"

    async def list_directory(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        ref: str,
    ) -> tuple[ContentEntry, ...]:
        assert token.get_secret_value().startswith("ghs_read")
        assert path == "docs"
        assert ref in self.branch_heads.values()
        return (
            ContentEntry(
                "README.md",
                "docs/README.md",
                git_blob_sha(b"one\ntwo\n"),
                8,
                ContentKind.FILE,
                "https://github.com/ahmed9461/GitDock/blob/main/docs/README.md",
            ),
            ContentEntry(
                "api",
                "docs/api",
                "c" * 40,
                0,
                ContentKind.DIRECTORY,
                "https://github.com/ahmed9461/GitDock/tree/main/docs/api",
            ),
        )

    async def get_file(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        ref: str,
    ) -> FileContent:
        assert token.get_secret_value().startswith("ghs_read")
        branch = self._branch_for_ref(ref)
        content = self.files.get((branch, path))
        if content is None:
            raise _not_found()
        return FileContent(
            name=path.rsplit("/", 1)[-1],
            path=path,
            sha=git_blob_sha(content),
            size=len(content),
            content=content,
            html_url=f"https://github.com/ahmed9461/GitDock/blob/{branch}/{path}",
        )

    async def resolve_ref(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        ref: str,
    ) -> RefSnapshot:
        assert token.get_secret_value().startswith("ghs_read")
        if ref in self.branch_heads:
            return RefSnapshot(ref, self.branch_heads[ref])
        if ref in self.branch_heads.values():
            return RefSnapshot(ref, ref)
        raise _not_found()

    async def get_branch(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        branch: str,
    ) -> RefSnapshot:
        assert token.get_secret_value().startswith("ghs_read")
        if branch not in self.branch_heads:
            raise _not_found()
        return RefSnapshot(branch, self.branch_heads[branch])

    async def put_file(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        branch: str,
        message: str,
        content: bytes,
        expected_sha: str | None = None,
    ) -> GitHubResponse[FileWriteResult]:
        assert token.get_secret_value().startswith("ghs_write")
        self.put_calls += 1
        if expected_sha is not None:
            current = self.files.get((branch, path))
            assert current is not None and git_blob_sha(current) == expected_sha
        self.files[(branch, path)] = content
        self.branch_heads[branch] = _commit_sha(self.put_calls)
        result = _response(
            FileWriteResult(
                git_blob_sha(content),
                self.branch_heads[branch],
                _commit_url(self.branch_heads[branch]),
            ),
            request_id="put-request",
        )
        if self.put_mode == "transient_applied":
            raise _transient()
        return result

    async def delete_file(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        branch: str,
        message: str,
        expected_sha: str,
    ) -> GitHubResponse[FileWriteResult]:
        assert token.get_secret_value().startswith("ghs_write")
        self.delete_calls += 1
        current = self.files.get((branch, path))
        assert current is not None and git_blob_sha(current) == expected_sha
        del self.files[(branch, path)]
        self.branch_heads[branch] = _commit_sha(10 + self.delete_calls)
        result = _response(
            FileWriteResult(
                None, self.branch_heads[branch], _commit_url(self.branch_heads[branch])
            ),
            request_id="delete-request",
        )
        if self.delete_mode == "transient_applied":
            raise _transient()
        return result

    def _branch_for_ref(self, ref: str) -> str:
        if ref in self.branch_heads:
            return ref
        for branch, head in self.branch_heads.items():
            if head == ref:
                return branch
        raise _not_found()


def _snapshot() -> RepositorySnapshot:
    now = datetime(2026, 9, 4, tzinfo=UTC)
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


def _response(data, *, request_id: str | None = None):
    return GitHubResponse(
        data=data,
        rate_limit=GitHubRateLimit(None, None, None, None, None, None),
        pagination=GitHubPaginationLinks(),
        request_id=request_id,
        status_code=200,
    )


def _not_found() -> GitHubNotFoundError:
    return GitHubNotFoundError(GitHubErrorKind.NOT_FOUND, "missing", status_code=404)


def _transient() -> GitHubTransientError:
    return GitHubTransientError(
        GitHubErrorKind.TRANSIENT,
        "response lost",
        request_id="lost-response",
    )


def _commit_sha(seed: int) -> str:
    return f"{seed:x}".rjust(40, "f")[-40:]


def _commit_url(sha: str) -> str:
    return f"https://github.com/ahmed9461/GitDock/commit/{sha}"


async def _build_service(*, confirmations: ConfirmationService | None = None):
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
            permissions_json={"contents": "write", "workflows": "write"},
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

    token_source = FakeTokenSource()
    contents = FakeContentsGateway()
    service = FileBrowserService(
        sessions,
        InstallationTokenProvider(token_source),
        FakeRepositoryGateway(repository),
        contents,
        confirmations or ConfirmationService(),
    )
    return engine, sessions, service, contents, token_source, user_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_browser_lists_directory_and_previews_utf8_text() -> None:
    engine, _, service, _, _, user_id = await _build_service()

    directory = await service.browse_directory(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        path="docs",
        ref="main",
    )
    file = await service.view_file(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        path="docs/README.md",
        ref="main",
    )

    assert [entry.name for entry in directory.entries] == ["api", "README.md"]
    assert file.display_kind is FileDisplayKind.TEXT
    assert file.preview_pages == ("one\ntwo\n",)
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unsafe_path_is_rejected_before_gitHub_access() -> None:
    engine, _, service, _, tokens, user_id = await _build_service()
    with pytest.raises(RepositoryPathError):
        await service.browse_directory(
            user_id=user_id,
            github_repository_id=_REPOSITORY_ID,
            path="../secret",
        )
    assert tokens.calls == []
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_non_default_create_is_tier1_persisted_and_audited() -> None:
    engine, sessions, service, contents, _, user_id = await _build_service()
    plan = await service.begin_create(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        branch="feature/docs",
        path="docs/new.txt",
        content=b"hello\n",
    )
    assert plan.risk_tier == 1

    result = await service.confirm_create(user_id=user_id, token=plan.token)
    assert result.state is FileWriteState.APPLIED
    assert contents.files[("feature/docs", "docs/new.txt")] == b"hello\n"
    async with sessions() as session:
        staged = await session.scalar(
            select(FileWriteSession).where(FileWriteSession.user_id == user_id)
        )
        assert (
            staged is not None and staged.consumed_at is not None and staged.content_bytes is None
        )
        audit = await session.scalar(select(AuditLog).where(AuditLog.operation == "file.create"))
        assert audit is not None and audit.status == "success"
        assert audit.details_json is not None and audit.details_json["path"] == "docs/new.txt"
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_default_branch_update_is_tier2_and_stale_branch_head_blocks_write() -> None:
    engine, _, service, contents, _, user_id = await _build_service()
    plan = await service.begin_update(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        branch="main",
        path="docs/README.md",
        content=b"changed\n",
    )
    assert plan.risk_tier == 2
    contents.branch_heads["main"] = "9" * 40

    result = await service.confirm_update(user_id=user_id, token=plan.token)
    assert result.state is FileWriteState.STALE
    assert contents.put_calls == 0
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_write_requests_contents_and_workflows_permissions() -> None:
    engine, _, service, _, token_source, user_id = await _build_service()
    plan = await service.begin_update(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        branch="main",
        path=".github/workflows/ci.yml",
        content=b"name: Updated CI\n",
    )
    result = await service.confirm_update(user_id=user_id, token=plan.token)

    assert result.state is FileWriteState.APPLIED
    write_permissions = [
        permissions
        for permissions, _ in token_source.calls
        if permissions.get("contents") == "write"
    ]
    assert {"contents": "write", "workflows": "write"} in write_permissions
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancelled_file_write_confirmation_cannot_execute_later() -> None:
    engine, _, service, contents, _, user_id = await _build_service()
    plan = await service.begin_update(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        branch="main",
        path="docs/README.md",
        content=b"cancelled\n",
    )

    assert await service.cancel_update(user_id=user_id, token=plan.token) is True
    assert await service.cancel_update(user_id=user_id, token=plan.token) is False
    result = await service.confirm_update(user_id=user_id, token=plan.token)
    assert result.state is FileWriteState.INVALID
    assert contents.put_calls == 0
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_uncertain_update_reconciles_remote_blob_sha_as_applied() -> None:
    engine, sessions, service, contents, _, user_id = await _build_service()
    contents.put_mode = "transient_applied"
    plan = await service.begin_update(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        branch="main",
        path="docs/README.md",
        content=b"recovered\n",
    )

    result = await service.confirm_update(user_id=user_id, token=plan.token)
    assert result.state is FileWriteState.APPLIED
    assert contents.put_calls == 1
    async with sessions() as session:
        audit = await session.scalar(select(AuditLog).where(AuditLog.operation == "file.update"))
        assert audit is not None and audit.status == "success"
        assert audit.details_json is not None and audit.details_json["reconciled"] is True
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_uncertain_delete_reconciles_missing_file_as_applied() -> None:
    engine, sessions, service, contents, _, user_id = await _build_service()
    contents.delete_mode = "transient_applied"
    plan = await service.begin_delete(
        user_id=user_id,
        github_repository_id=_REPOSITORY_ID,
        branch="main",
        path="docs/README.md",
    )

    result = await service.confirm_delete(user_id=user_id, token=plan.token)
    assert result.state is FileWriteState.APPLIED
    assert contents.delete_calls == 1
    async with sessions() as session:
        audit = await session.scalar(select(AuditLog).where(AuditLog.operation == "file.delete"))
        assert audit is not None and audit.status == "success"
        assert audit.details_json is not None and audit.details_json["reconciled"] is True
    await engine.dispose()
