"""Safe repository file browsing and one-file write use cases for P4.1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from pydantic import SecretStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.core.constants import (
    FILE_COMMIT_MESSAGE_MAX_CHARS,
    FILE_SINGLE_UPLOAD_MAX_BYTES,
    FILE_TEXT_PREVIEW_MAX_BYTES,
    FILE_WRITE_SESSION_TTL_SECONDS,
)
from gitdock.db.models import AuditLog, FileWriteSession, GitHubInstallation, RepositoryCache
from gitdock.domain.files import (
    TextDiffPreview,
    build_text_diff,
    content_sha256,
    decode_utf8_text,
    git_blob_sha,
    is_workflow_path,
    normalize_repository_path,
    normalize_repository_ref,
    paginate_text,
    parent_repository_path,
)
from gitdock.github.contents import ContentEntry, ContentKind, FileContent, FileWriteResult, RefSnapshot
from gitdock.github.errors import GitHubGatewayError, GitHubNotFoundError
from gitdock.github.models import GitHubResponse
from gitdock.github.permissions import GitHubCapability, combine_installation_permissions
from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.token_provider import InstallationTokenProvider
from gitdock.services.confirmations import ConfirmationService, ConsumedConfirmation
from gitdock.services.repository_reconciliation import should_reconcile_write_error

FILE_CREATE_OPERATION = "file.create"
FILE_UPDATE_OPERATION = "file.update"
FILE_DELETE_OPERATION = "file.delete"


class FileDisplayKind(StrEnum):
    TEXT = "text"
    BINARY = "binary"
    LARGE = "large"
    UNAVAILABLE = "unavailable"


class FileWriteState(StrEnum):
    APPLIED = "applied"
    STALE = "stale"
    INVALID = "invalid"
    UNCERTAIN = "uncertain"


class FileBrowserError(RuntimeError):
    """Safe local file-browser failure."""


class FileSelectionError(FileBrowserError):
    """Raised when repository callback context is no longer current."""


class FileWriteValidationError(FileBrowserError, ValueError):
    """Raised when a requested file write is not safe to stage."""


class ContentsGateway(Protocol):
    async def list_directory(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        ref: str,
    ) -> tuple[ContentEntry, ...]: ...

    async def get_file(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        ref: str,
    ) -> FileContent: ...

    async def resolve_ref(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        ref: str,
    ) -> RefSnapshot: ...

    async def get_branch(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        branch: str,
    ) -> RefSnapshot: ...

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
    ) -> GitHubResponse[FileWriteResult]: ...

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
    ) -> GitHubResponse[FileWriteResult]: ...


class RepositoryReadGateway(Protocol):
    async def get_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ) -> RepositorySnapshot: ...


@dataclass(frozen=True, slots=True)
class DirectoryView:
    repository: RepositorySnapshot
    ref: str
    ref_commit_sha: str
    path: str
    entries: tuple[ContentEntry, ...]


@dataclass(frozen=True, slots=True)
class FileView:
    repository: RepositorySnapshot
    ref: str
    ref_commit_sha: str
    file: FileContent
    display_kind: FileDisplayKind
    preview_pages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FileWritePlan:
    token: str
    operation: str
    repository: RepositorySnapshot
    branch: str
    path: str
    risk_tier: int
    diff: TextDiffPreview | None


@dataclass(frozen=True, slots=True)
class FileWriteOutcome:
    state: FileWriteState
    operation: str
    repository: RepositorySnapshot | None
    branch: str | None
    path: str | None
    commit_sha: str | None = None


@dataclass(frozen=True, slots=True)
class _InstalledRepositoryContext:
    installation_id: int
    github_repository_id: int
    owner_login: str
    repository_name: str


@dataclass(frozen=True, slots=True)
class _StagedWrite:
    session_id: int
    user_id: int
    operation: str
    github_repository_id: int
    installation_id: int
    repository_full_name: str
    repository_default_branch: str
    branch: str
    path: str
    branch_head_sha: str
    expected_file_sha: str | None
    desired_blob_sha: str | None
    content_digest: str | None
    content: bytes | None
    commit_message: str
    risk_tier: int


class FileBrowserService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        token_provider: InstallationTokenProvider,
        repository_gateway: RepositoryReadGateway,
        contents_gateway: ContentsGateway,
        confirmations: ConfirmationService,
    ) -> None:
        self._session_factory = session_factory
        self._token_provider = token_provider
        self._repository_gateway = repository_gateway
        self._contents_gateway = contents_gateway
        self._confirmations = confirmations
        read_levels = combine_installation_permissions(
            {GitHubCapability.REPOSITORY_METADATA_READ, GitHubCapability.CONTENTS_READ}
        )
        self._read_permissions = {name: level.value for name, level in read_levels.items()}

    async def browse_directory(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        path: str = "",
        ref: str | None = None,
    ) -> DirectoryView:
        normalized_path = normalize_repository_path(path, allow_root=True)
        _, repository, token = await self._current_repository(user_id, github_repository_id)
        normalized_ref = normalize_repository_ref(ref or repository.default_branch)
        resolved = await self._contents_gateway.resolve_ref(
            token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            ref=normalized_ref,
        )
        entries = await self._contents_gateway.list_directory(
            token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            path=normalized_path,
            ref=resolved.commit_sha,
        )
        for entry in entries:
            try:
                entry_path = normalize_repository_path(entry.path, allow_root=False)
            except ValueError as exc:
                raise FileBrowserError("GitHub returned an unsafe repository path") from exc
            if parent_repository_path(entry_path) != normalized_path:
                raise FileBrowserError("GitHub returned content outside the requested directory")
        ordered = tuple(
            sorted(
                entries,
                key=lambda entry: (entry.kind is not ContentKind.DIRECTORY, entry.name.casefold()),
            )
        )
        return DirectoryView(repository, normalized_ref, resolved.commit_sha, normalized_path, ordered)

    async def view_file(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        path: str,
        ref: str | None = None,
    ) -> FileView:
        normalized_path = normalize_repository_path(path, allow_root=False)
        _, repository, token = await self._current_repository(user_id, github_repository_id)
        normalized_ref = normalize_repository_ref(ref or repository.default_branch)
        resolved = await self._contents_gateway.resolve_ref(
            token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            ref=normalized_ref,
        )
        file = await self._contents_gateway.get_file(
            token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            path=normalized_path,
            ref=resolved.commit_sha,
        )
        if normalize_repository_path(file.path, allow_root=False) != normalized_path:
            raise FileBrowserError("GitHub returned a different file path")
        display_kind, pages = _preview(file)
        return FileView(repository, normalized_ref, resolved.commit_sha, file, display_kind, pages)

    async def begin_create(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        branch: str,
        path: str,
        content: bytes,
        commit_message: str | None = None,
    ) -> FileWritePlan:
        normalized_path = normalize_repository_path(path, allow_root=False)
        normalized_branch = normalize_repository_ref(branch)
        _validate_content(content)
        context, repository, token = await self._current_repository(user_id, github_repository_id)
        _require_writable_repository(repository)
        branch_snapshot = await self._branch_snapshot(token, repository, normalized_branch)
        existing = await self._file_or_none(token, repository, normalized_path, branch_snapshot.commit_sha)
        if existing is not None:
            raise FileWriteValidationError("a file already exists at this path")
        risk_tier = 2 if normalized_branch == repository.default_branch else 1
        message = _normalize_commit_message(
            commit_message or f"Create {normalized_path} via GitDock"
        )
        return await self._stage_write(
            user_id=user_id,
            context=context,
            repository=repository,
            operation=FILE_CREATE_OPERATION,
            branch=normalized_branch,
            path=normalized_path,
            branch_head_sha=branch_snapshot.commit_sha,
            expected_file_sha=None,
            content=content,
            commit_message=message,
            risk_tier=risk_tier,
            diff=build_text_diff(None, content),
        )

    async def begin_update(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        branch: str,
        path: str,
        content: bytes,
        commit_message: str | None = None,
    ) -> FileWritePlan:
        normalized_path = normalize_repository_path(path, allow_root=False)
        normalized_branch = normalize_repository_ref(branch)
        _validate_content(content)
        context, repository, token = await self._current_repository(user_id, github_repository_id)
        _require_writable_repository(repository)
        branch_snapshot = await self._branch_snapshot(token, repository, normalized_branch)
        current = await self._contents_gateway.get_file(
            token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            path=normalized_path,
            ref=branch_snapshot.commit_sha,
        )
        risk_tier = 2 if normalized_branch == repository.default_branch else 1
        message = _normalize_commit_message(
            commit_message or f"Update {normalized_path} via GitDock"
        )
        return await self._stage_write(
            user_id=user_id,
            context=context,
            repository=repository,
            operation=FILE_UPDATE_OPERATION,
            branch=normalized_branch,
            path=normalized_path,
            branch_head_sha=branch_snapshot.commit_sha,
            expected_file_sha=current.sha,
            content=content,
            commit_message=message,
            risk_tier=risk_tier,
            diff=build_text_diff(current.content, content),
        )

    async def begin_delete(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        branch: str,
        path: str,
        commit_message: str | None = None,
    ) -> FileWritePlan:
        normalized_path = normalize_repository_path(path, allow_root=False)
        normalized_branch = normalize_repository_ref(branch)
        context, repository, token = await self._current_repository(user_id, github_repository_id)
        _require_writable_repository(repository)
        branch_snapshot = await self._branch_snapshot(token, repository, normalized_branch)
        current = await self._contents_gateway.get_file(
            token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            path=normalized_path,
            ref=branch_snapshot.commit_sha,
        )
        message = _normalize_commit_message(
            commit_message or f"Delete {normalized_path} via GitDock"
        )
        return await self._stage_write(
            user_id=user_id,
            context=context,
            repository=repository,
            operation=FILE_DELETE_OPERATION,
            branch=normalized_branch,
            path=normalized_path,
            branch_head_sha=branch_snapshot.commit_sha,
            expected_file_sha=current.sha,
            content=None,
            commit_message=message,
            risk_tier=2,
            diff=build_text_diff(current.content, None),
        )

    async def confirm_create(self, *, user_id: int, token: str) -> FileWriteOutcome:
        return await self._confirm_write(user_id, token, FILE_CREATE_OPERATION)

    async def confirm_update(self, *, user_id: int, token: str) -> FileWriteOutcome:
        return await self._confirm_write(user_id, token, FILE_UPDATE_OPERATION)

    async def confirm_delete(self, *, user_id: int, token: str) -> FileWriteOutcome:
        return await self._confirm_write(user_id, token, FILE_DELETE_OPERATION)

    async def cancel_create(self, *, user_id: int, token: str) -> bool:
        return await self._cancel_write(user_id, token, FILE_CREATE_OPERATION)

    async def cancel_update(self, *, user_id: int, token: str) -> bool:
        return await self._cancel_write(user_id, token, FILE_UPDATE_OPERATION)

    async def cancel_delete(self, *, user_id: int, token: str) -> bool:
        return await self._cancel_write(user_id, token, FILE_DELETE_OPERATION)

    async def _confirm_write(self, user_id: int, token: str, operation: str) -> FileWriteOutcome:
        staged = await self._consume_staged_write(user_id, token, operation)
        if staged is None:
            return FileWriteOutcome(FileWriteState.INVALID, operation, None, None, None)
        try:
            context, repository, read_token = await self._current_repository(
                user_id, staged.github_repository_id
            )
        except FileSelectionError:
            return FileWriteOutcome(
                FileWriteState.STALE, operation, None, staged.branch, staged.path
            )
        if (
            context.installation_id != staged.installation_id
            or repository.full_name != staged.repository_full_name
            or repository.default_branch != staged.repository_default_branch
        ):
            return FileWriteOutcome(
                FileWriteState.STALE, operation, repository, staged.branch, staged.path
            )
        try:
            branch_snapshot = await self._branch_snapshot(read_token, repository, staged.branch)
        except GitHubNotFoundError:
            return FileWriteOutcome(
                FileWriteState.STALE, operation, repository, staged.branch, staged.path
            )
        if branch_snapshot.commit_sha != staged.branch_head_sha:
            return FileWriteOutcome(
                FileWriteState.STALE, operation, repository, staged.branch, staged.path
            )

        if operation == FILE_CREATE_OPERATION:
            current = await self._file_or_none(
                read_token, repository, staged.path, branch_snapshot.commit_sha
            )
            if current is not None:
                return FileWriteOutcome(
                    FileWriteState.STALE, operation, repository, staged.branch, staged.path
                )
        else:
            try:
                current = await self._contents_gateway.get_file(
                    read_token,
                    owner_login=repository.owner_login,
                    repository_name=repository.name,
                    path=staged.path,
                    ref=branch_snapshot.commit_sha,
                )
            except GitHubNotFoundError:
                return FileWriteOutcome(
                    FileWriteState.STALE, operation, repository, staged.branch, staged.path
                )
            if current.sha != staged.expected_file_sha:
                return FileWriteOutcome(
                    FileWriteState.STALE, operation, repository, staged.branch, staged.path
                )

        write_token = await self._write_token(context, staged.path)
        try:
            if operation == FILE_DELETE_OPERATION:
                assert staged.expected_file_sha is not None
                response = await self._contents_gateway.delete_file(
                    write_token,
                    owner_login=repository.owner_login,
                    repository_name=repository.name,
                    path=staged.path,
                    branch=staged.branch,
                    message=staged.commit_message,
                    expected_sha=staged.expected_file_sha,
                )
            else:
                if staged.content is None or staged.desired_blob_sha is None:
                    return FileWriteOutcome(
                        FileWriteState.INVALID, operation, repository, staged.branch, staged.path
                    )
                response = await self._contents_gateway.put_file(
                    write_token,
                    owner_login=repository.owner_login,
                    repository_name=repository.name,
                    path=staged.path,
                    branch=staged.branch,
                    message=staged.commit_message,
                    content=staged.content,
                    expected_sha=staged.expected_file_sha,
                )
        except GitHubGatewayError as exc:
            if should_reconcile_write_error(exc):
                return await self._reconcile_write(
                    user_id=user_id,
                    staged=staged,
                    repository=repository,
                    read_token=read_token,
                    error=exc,
                )
            await self._audit_failure(user_id, staged, repository, exc)
            raise

        if operation != FILE_DELETE_OPERATION and response.data.content_sha != staged.desired_blob_sha:
            await self._audit_uncertain(
                user_id,
                staged,
                repository,
                request_id=response.request_id,
                original_error_kind="response_sha_mismatch",
            )
            return FileWriteOutcome(
                FileWriteState.UNCERTAIN, operation, repository, staged.branch, staged.path
            )
        await self._audit_success(
            user_id,
            staged,
            repository,
            request_id=response.request_id,
            commit_sha=response.data.commit_sha,
        )
        return FileWriteOutcome(
            FileWriteState.APPLIED,
            operation,
            repository,
            staged.branch,
            staged.path,
            response.data.commit_sha,
        )

    async def _reconcile_write(
        self,
        *,
        user_id: int,
        staged: _StagedWrite,
        repository: RepositorySnapshot,
        read_token: SecretStr,
        error: GitHubGatewayError,
    ) -> FileWriteOutcome:
        try:
            current = await self._contents_gateway.get_file(
                read_token,
                owner_login=repository.owner_login,
                repository_name=repository.name,
                path=staged.path,
                ref=staged.branch,
            )
        except GitHubNotFoundError:
            if staged.operation == FILE_DELETE_OPERATION:
                await self._audit_success(
                    user_id,
                    staged,
                    repository,
                    request_id=error.context.request_id,
                    commit_sha=None,
                    reconciled=True,
                    original_error_kind=error.kind.value,
                )
                return FileWriteOutcome(
                    FileWriteState.APPLIED,
                    staged.operation,
                    repository,
                    staged.branch,
                    staged.path,
                )
            await self._audit_uncertain(
                user_id,
                staged,
                repository,
                request_id=error.context.request_id,
                original_error_kind=error.kind.value,
            )
            return FileWriteOutcome(
                FileWriteState.UNCERTAIN,
                staged.operation,
                repository,
                staged.branch,
                staged.path,
            )
        except GitHubGatewayError:
            await self._audit_uncertain(
                user_id,
                staged,
                repository,
                request_id=error.context.request_id,
                original_error_kind=error.kind.value,
            )
            return FileWriteOutcome(
                FileWriteState.UNCERTAIN,
                staged.operation,
                repository,
                staged.branch,
                staged.path,
            )

        if staged.operation != FILE_DELETE_OPERATION and current.sha == staged.desired_blob_sha:
            await self._audit_success(
                user_id,
                staged,
                repository,
                request_id=error.context.request_id,
                commit_sha=None,
                reconciled=True,
                original_error_kind=error.kind.value,
            )
            return FileWriteOutcome(
                FileWriteState.APPLIED,
                staged.operation,
                repository,
                staged.branch,
                staged.path,
            )
        await self._audit_uncertain(
            user_id,
            staged,
            repository,
            request_id=error.context.request_id,
            original_error_kind=error.kind.value,
        )
        return FileWriteOutcome(
            FileWriteState.UNCERTAIN,
            staged.operation,
            repository,
            staged.branch,
            staged.path,
        )

    async def _stage_write(
        self,
        *,
        user_id: int,
        context: _InstalledRepositoryContext,
        repository: RepositorySnapshot,
        operation: str,
        branch: str,
        path: str,
        branch_head_sha: str,
        expected_file_sha: str | None,
        content: bytes | None,
        commit_message: str,
        risk_tier: int,
        diff: TextDiffPreview | None,
    ) -> FileWritePlan:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=FILE_WRITE_SESSION_TTL_SECONDS)
        desired_blob_sha = git_blob_sha(content) if content is not None else None
        digest = content_sha256(content) if content is not None else None
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    update(FileWriteSession)
                    .where(
                        FileWriteSession.user_id == user_id,
                        FileWriteSession.consumed_at.is_(None),
                        FileWriteSession.expires_at <= now,
                    )
                    .values(consumed_at=now, content_bytes=None)
                    .execution_options(synchronize_session=False)
                )
                await session.execute(
                    update(FileWriteSession)
                    .where(
                        FileWriteSession.user_id == user_id,
                        FileWriteSession.github_repository_id == repository.github_repository_id,
                        FileWriteSession.branch == branch,
                        FileWriteSession.path == path,
                        FileWriteSession.consumed_at.is_(None),
                    )
                    .values(consumed_at=now, content_bytes=None)
                    .execution_options(synchronize_session=False)
                )
                staged = FileWriteSession(
                    user_id=user_id,
                    operation=operation,
                    github_repository_id=repository.github_repository_id,
                    installation_id=context.installation_id,
                    repository_full_name=repository.full_name,
                    repository_default_branch=repository.default_branch,
                    branch=branch,
                    path=path,
                    branch_head_sha=branch_head_sha,
                    expected_file_sha=expected_file_sha,
                    desired_blob_sha=desired_blob_sha,
                    content_digest=digest,
                    content_bytes=content,
                    commit_message=commit_message,
                    risk_tier=risk_tier,
                    expires_at=expires_at,
                )
                session.add(staged)
                await session.flush()
                payload = _session_payload(staged)
                issued = await self._confirmations.create(
                    session,
                    user_id=user_id,
                    operation_type=operation,
                    target_fingerprint=_fingerprint(payload),
                    payload=payload,
                    risk_tier=risk_tier,
                )
        return FileWritePlan(
            issued.token,
            operation,
            repository,
            branch,
            path,
            risk_tier,
            diff,
        )

    async def _consume_staged_write(
        self,
        user_id: int,
        token: str,
        operation: str,
    ) -> _StagedWrite | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            async with session.begin():
                consumed = await self._confirmations.consume(
                    session,
                    user_id=user_id,
                    token=token,
                    expected_operation=operation,
                )
                if consumed is None or consumed.target_fingerprint != _fingerprint(consumed.payload):
                    return None
                session_id = _positive_int(consumed.payload.get("session_id"))
                if session_id is None:
                    return None
                row = await session.scalar(
                    select(FileWriteSession).where(
                        FileWriteSession.id == session_id,
                        FileWriteSession.user_id == user_id,
                        FileWriteSession.operation == operation,
                        FileWriteSession.consumed_at.is_(None),
                        FileWriteSession.expires_at > now,
                    )
                )
                if row is None or _session_payload(row) != consumed.payload:
                    return None
                content = bytes(row.content_bytes) if row.content_bytes is not None else None
                if content is not None:
                    if row.content_digest != content_sha256(content):
                        return None
                    if row.desired_blob_sha != git_blob_sha(content):
                        return None
                staged = _staged_copy(row, content)
                row.consumed_at = now
                row.content_bytes = None
                return staged

    async def _cancel_write(self, user_id: int, token: str, operation: str) -> bool:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            async with session.begin():
                consumed = await self._confirmations.consume(
                    session,
                    user_id=user_id,
                    token=token,
                    expected_operation=operation,
                )
                if consumed is None:
                    return False
                session_id = _positive_int(consumed.payload.get("session_id"))
                if session_id is not None:
                    await session.execute(
                        update(FileWriteSession)
                        .where(
                            FileWriteSession.id == session_id,
                            FileWriteSession.user_id == user_id,
                            FileWriteSession.operation == operation,
                            FileWriteSession.consumed_at.is_(None),
                        )
                        .values(consumed_at=now, content_bytes=None)
                        .execution_options(synchronize_session=False)
                    )
                return True

    async def _current_repository(
        self,
        user_id: int,
        github_repository_id: int,
    ) -> tuple[_InstalledRepositoryContext, RepositorySnapshot, SecretStr]:
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
            context = _InstalledRepositoryContext(
                installation.installation_id,
                github_repository_id,
                row.owner_login,
                row.name,
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
        return context, repository, token.token

    async def _branch_snapshot(
        self,
        token: SecretStr,
        repository: RepositorySnapshot,
        branch: str,
    ) -> RefSnapshot:
        return await self._contents_gateway.get_branch(
            token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            branch=branch,
        )

    async def _file_or_none(
        self,
        token: SecretStr,
        repository: RepositorySnapshot,
        path: str,
        ref: str,
    ) -> FileContent | None:
        try:
            return await self._contents_gateway.get_file(
                token,
                owner_login=repository.owner_login,
                repository_name=repository.name,
                path=path,
                ref=ref,
            )
        except GitHubNotFoundError:
            return None

    async def _write_token(
        self,
        context: _InstalledRepositoryContext,
        path: str,
    ) -> SecretStr:
        capabilities = {GitHubCapability.CONTENTS_WRITE}
        if is_workflow_path(path):
            capabilities.add(GitHubCapability.WORKFLOWS_WRITE)
        levels = combine_installation_permissions(capabilities)
        permissions = {name: level.value for name, level in levels.items()}
        token = await self._token_provider.get_token(
            context.installation_id,
            permissions=permissions,
            repository_ids=[context.github_repository_id],
        )
        return token.token

    async def _audit_success(
        self,
        user_id: int,
        staged: _StagedWrite,
        repository: RepositorySnapshot,
        *,
        request_id: str | None,
        commit_sha: str | None,
        reconciled: bool = False,
        original_error_kind: str | None = None,
    ) -> None:
        details: dict[str, Any] = _audit_details(staged)
        details["commit_sha"] = commit_sha
        if reconciled:
            details["reconciled"] = True
        if original_error_kind is not None:
            details["original_error_kind"] = original_error_kind
        await self._write_audit(
            user_id=user_id,
            staged=staged,
            repository=repository,
            status="success",
            request_id=request_id,
            details=details,
        )

    async def _audit_failure(
        self,
        user_id: int,
        staged: _StagedWrite,
        repository: RepositorySnapshot,
        error: GitHubGatewayError,
    ) -> None:
        details = _audit_details(staged)
        details["error_kind"] = error.kind.value
        await self._write_audit(
            user_id=user_id,
            staged=staged,
            repository=repository,
            status="failure",
            request_id=error.context.request_id,
            details=details,
        )

    async def _audit_uncertain(
        self,
        user_id: int,
        staged: _StagedWrite,
        repository: RepositorySnapshot,
        *,
        request_id: str | None,
        original_error_kind: str,
    ) -> None:
        details = _audit_details(staged)
        details.update({"reconciled": False, "original_error_kind": original_error_kind})
        await self._write_audit(
            user_id=user_id,
            staged=staged,
            repository=repository,
            status="uncertain",
            request_id=request_id,
            details=details,
        )

    async def _write_audit(
        self,
        *,
        user_id: int,
        staged: _StagedWrite,
        repository: RepositorySnapshot,
        status: str,
        request_id: str | None,
        details: dict[str, Any],
    ) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                session.add(
                    AuditLog(
                        user_id=user_id,
                        operation=staged.operation,
                        status=status,
                        installation_id=staged.installation_id,
                        github_repository_id=repository.github_repository_id,
                        repository_full_name=repository.full_name,
                        github_request_id=request_id,
                        details_json=details,
                    )
                )


def _preview(file: FileContent) -> tuple[FileDisplayKind, tuple[str, ...]]:
    if file.content is None:
        kind = FileDisplayKind.LARGE if file.size > FILE_TEXT_PREVIEW_MAX_BYTES else FileDisplayKind.UNAVAILABLE
        return kind, ()
    if len(file.content) > FILE_TEXT_PREVIEW_MAX_BYTES:
        return FileDisplayKind.LARGE, ()
    text = decode_utf8_text(file.content)
    if text is None:
        return FileDisplayKind.BINARY, ()
    return FileDisplayKind.TEXT, paginate_text(text)


def _validate_content(content: bytes) -> None:
    if not isinstance(content, bytes):
        raise FileWriteValidationError("file content must be bytes")
    if len(content) > FILE_SINGLE_UPLOAD_MAX_BYTES:
        raise FileWriteValidationError("file content exceeds the configured single-file limit")


def _require_writable_repository(repository: RepositorySnapshot) -> None:
    if repository.archived:
        raise FileWriteValidationError("archived repositories cannot be changed")


def _normalize_commit_message(value: str) -> str:
    normalized = value.strip()
    if not normalized or "\x00" in normalized or len(normalized) > FILE_COMMIT_MESSAGE_MAX_CHARS:
        raise FileWriteValidationError("commit message is invalid")
    return normalized


def _session_payload(session: FileWriteSession) -> dict[str, Any]:
    return {
        "session_id": session.id,
        "repository_id": session.github_repository_id,
        "installation_id": session.installation_id,
        "repository_full_name": session.repository_full_name,
        "repository_default_branch": session.repository_default_branch,
        "operation": session.operation,
        "branch": session.branch,
        "path": session.path,
        "branch_head_sha": session.branch_head_sha,
        "expected_file_sha": session.expected_file_sha,
        "desired_blob_sha": session.desired_blob_sha,
        "risk_tier": session.risk_tier,
    }


def _staged_copy(row: FileWriteSession, content: bytes | None) -> _StagedWrite:
    return _StagedWrite(
        session_id=row.id,
        user_id=row.user_id,
        operation=row.operation,
        github_repository_id=row.github_repository_id,
        installation_id=row.installation_id,
        repository_full_name=row.repository_full_name,
        repository_default_branch=row.repository_default_branch,
        branch=row.branch,
        path=row.path,
        branch_head_sha=row.branch_head_sha,
        expected_file_sha=row.expected_file_sha,
        desired_blob_sha=row.desired_blob_sha,
        content_digest=row.content_digest,
        content=content,
        commit_message=row.commit_message,
        risk_tier=row.risk_tier,
    )


def _audit_details(staged: _StagedWrite) -> dict[str, Any]:
    return {
        "branch": staged.branch,
        "path": staged.path,
        "expected_file_sha": staged.expected_file_sha,
        "desired_blob_sha": staged.desired_blob_sha,
        "risk_tier": staged.risk_tier,
        "workflow_path": is_workflow_path(staged.path),
    }


def _fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _positive_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None
