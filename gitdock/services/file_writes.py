"""Validated, stale-safe, reconciled one-file GitHub writes for P4.1."""

from __future__ import annotations

from pydantic import SecretStr

from gitdock.core.constants import FILE_COMMIT_MESSAGE_MAX_CHARS, FILE_SINGLE_UPLOAD_MAX_BYTES
from gitdock.domain.files import (
    build_text_diff,
    is_workflow_path,
    normalize_repository_path,
    normalize_repository_ref,
)
from gitdock.github.contents import FileContent, FileWriteResult, RefSnapshot
from gitdock.github.errors import GitHubGatewayError, GitHubNotFoundError
from gitdock.github.models import GitHubResponse
from gitdock.github.permissions import GitHubCapability, combine_installation_permissions
from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.token_provider import InstallationTokenProvider
from gitdock.services.file_audit import FileAuditWriter
from gitdock.services.file_context import FileRepositoryContextResolver
from gitdock.services.file_types import (
    FILE_CREATE_OPERATION,
    FILE_DELETE_OPERATION,
    FILE_UPDATE_OPERATION,
    ContentsGateway,
    FileSelectionError,
    FileWriteOutcome,
    FileWritePlan,
    FileWriteState,
    FileWriteValidationError,
    InstalledRepositoryContext,
    StagedWrite,
)
from gitdock.services.file_write_store import FileWriteStore
from gitdock.services.repository_reconciliation import should_reconcile_write_error


class FileWriteService:
    def __init__(
        self,
        resolver: FileRepositoryContextResolver,
        token_provider: InstallationTokenProvider,
        contents_gateway: ContentsGateway,
        store: FileWriteStore,
        audit: FileAuditWriter,
    ) -> None:
        self._resolver = resolver
        self._token_provider = token_provider
        self._contents_gateway = contents_gateway
        self._store = store
        self._audit = audit

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
        current = await self._resolver.resolve(
            user_id=user_id,
            github_repository_id=github_repository_id,
        )
        _require_writable_repository(current.repository)
        branch_snapshot = await self._branch_snapshot(
            current.read_token,
            current.repository,
            normalized_branch,
        )
        existing = await self._file_or_none(
            current.read_token,
            current.repository,
            normalized_path,
            branch_snapshot.commit_sha,
        )
        if existing is not None:
            raise FileWriteValidationError("a file already exists at this path")
        risk_tier = 2 if normalized_branch == current.repository.default_branch else 1
        message = _normalize_commit_message(
            commit_message or f"Create {normalized_path} via GitDock"
        )
        token = await self._store.stage(
            user_id=user_id,
            context=current.context,
            repository=current.repository,
            operation=FILE_CREATE_OPERATION,
            branch=normalized_branch,
            path=normalized_path,
            branch_head_sha=branch_snapshot.commit_sha,
            expected_file_sha=None,
            content=content,
            commit_message=message,
            risk_tier=risk_tier,
        )
        return FileWritePlan(
            token=token,
            operation=FILE_CREATE_OPERATION,
            repository=current.repository,
            branch=normalized_branch,
            path=normalized_path,
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
        current = await self._resolver.resolve(
            user_id=user_id,
            github_repository_id=github_repository_id,
        )
        _require_writable_repository(current.repository)
        branch_snapshot = await self._branch_snapshot(
            current.read_token,
            current.repository,
            normalized_branch,
        )
        file = await self._contents_gateway.get_file(
            current.read_token,
            owner_login=current.repository.owner_login,
            repository_name=current.repository.name,
            path=normalized_path,
            ref=branch_snapshot.commit_sha,
        )
        risk_tier = 2 if normalized_branch == current.repository.default_branch else 1
        message = _normalize_commit_message(
            commit_message or f"Update {normalized_path} via GitDock"
        )
        token = await self._store.stage(
            user_id=user_id,
            context=current.context,
            repository=current.repository,
            operation=FILE_UPDATE_OPERATION,
            branch=normalized_branch,
            path=normalized_path,
            branch_head_sha=branch_snapshot.commit_sha,
            expected_file_sha=file.sha,
            content=content,
            commit_message=message,
            risk_tier=risk_tier,
        )
        return FileWritePlan(
            token=token,
            operation=FILE_UPDATE_OPERATION,
            repository=current.repository,
            branch=normalized_branch,
            path=normalized_path,
            risk_tier=risk_tier,
            diff=build_text_diff(file.content, content),
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
        current = await self._resolver.resolve(
            user_id=user_id,
            github_repository_id=github_repository_id,
        )
        _require_writable_repository(current.repository)
        branch_snapshot = await self._branch_snapshot(
            current.read_token,
            current.repository,
            normalized_branch,
        )
        file = await self._contents_gateway.get_file(
            current.read_token,
            owner_login=current.repository.owner_login,
            repository_name=current.repository.name,
            path=normalized_path,
            ref=branch_snapshot.commit_sha,
        )
        message = _normalize_commit_message(
            commit_message or f"Delete {normalized_path} via GitDock"
        )
        token = await self._store.stage(
            user_id=user_id,
            context=current.context,
            repository=current.repository,
            operation=FILE_DELETE_OPERATION,
            branch=normalized_branch,
            path=normalized_path,
            branch_head_sha=branch_snapshot.commit_sha,
            expected_file_sha=file.sha,
            content=None,
            commit_message=message,
            risk_tier=2,
        )
        return FileWritePlan(
            token=token,
            operation=FILE_DELETE_OPERATION,
            repository=current.repository,
            branch=normalized_branch,
            path=normalized_path,
            risk_tier=2,
            diff=build_text_diff(file.content, None),
        )

    async def confirm_create(self, *, user_id: int, token: str) -> FileWriteOutcome:
        return await self._confirm(user_id=user_id, token=token, operation=FILE_CREATE_OPERATION)

    async def confirm_update(self, *, user_id: int, token: str) -> FileWriteOutcome:
        return await self._confirm(user_id=user_id, token=token, operation=FILE_UPDATE_OPERATION)

    async def confirm_delete(self, *, user_id: int, token: str) -> FileWriteOutcome:
        return await self._confirm(user_id=user_id, token=token, operation=FILE_DELETE_OPERATION)

    async def cancel_create(self, *, user_id: int, token: str) -> bool:
        return await self._store.cancel(
            user_id=user_id,
            token=token,
            operation=FILE_CREATE_OPERATION,
        )

    async def cancel_update(self, *, user_id: int, token: str) -> bool:
        return await self._store.cancel(
            user_id=user_id,
            token=token,
            operation=FILE_UPDATE_OPERATION,
        )

    async def cancel_delete(self, *, user_id: int, token: str) -> bool:
        return await self._store.cancel(
            user_id=user_id,
            token=token,
            operation=FILE_DELETE_OPERATION,
        )

    async def _confirm(
        self,
        *,
        user_id: int,
        token: str,
        operation: str,
    ) -> FileWriteOutcome:
        staged = await self._store.consume(
            user_id=user_id,
            token=token,
            operation=operation,
        )
        if staged is None:
            return FileWriteOutcome(FileWriteState.INVALID, operation, None, None, None)
        try:
            current = await self._resolver.resolve(
                user_id=user_id,
                github_repository_id=staged.github_repository_id,
            )
        except FileSelectionError:
            return _outcome(FileWriteState.STALE, staged, None)
        repository = current.repository
        if (
            current.context.installation_id != staged.installation_id
            or repository.full_name != staged.repository_full_name
            or repository.default_branch != staged.repository_default_branch
        ):
            return _outcome(FileWriteState.STALE, staged, repository)
        try:
            branch_snapshot = await self._branch_snapshot(
                current.read_token,
                repository,
                staged.branch,
            )
        except GitHubNotFoundError:
            return _outcome(FileWriteState.STALE, staged, repository)
        if branch_snapshot.commit_sha != staged.branch_head_sha:
            return _outcome(FileWriteState.STALE, staged, repository)
        if not await self._preconditions_match(
            staged=staged,
            repository=repository,
            read_token=current.read_token,
            branch_head_sha=branch_snapshot.commit_sha,
        ):
            return _outcome(FileWriteState.STALE, staged, repository)

        write_token = await self._write_token(current.context, staged.path)
        try:
            response = await self._execute_write(
                staged=staged,
                repository=repository,
                write_token=write_token,
            )
        except GitHubGatewayError as exc:
            if should_reconcile_write_error(exc):
                return await self._reconcile(
                    user_id=user_id,
                    staged=staged,
                    repository=repository,
                    read_token=current.read_token,
                    error=exc,
                )
            await self._audit.failure(
                user_id=user_id,
                staged=staged,
                repository=repository,
                error=exc,
            )
            raise

        if (
            staged.operation != FILE_DELETE_OPERATION
            and response.data.content_sha != staged.desired_blob_sha
        ):
            await self._audit.uncertain(
                user_id=user_id,
                staged=staged,
                repository=repository,
                request_id=response.request_id,
                original_error_kind="response_sha_mismatch",
            )
            return _outcome(FileWriteState.UNCERTAIN, staged, repository)
        await self._audit.success(
            user_id=user_id,
            staged=staged,
            repository=repository,
            request_id=response.request_id,
            commit_sha=response.data.commit_sha,
        )
        return _outcome(
            FileWriteState.APPLIED,
            staged,
            repository,
            commit_sha=response.data.commit_sha,
        )

    async def _preconditions_match(
        self,
        *,
        staged: StagedWrite,
        repository: RepositorySnapshot,
        read_token: SecretStr,
        branch_head_sha: str,
    ) -> bool:
        if staged.operation == FILE_CREATE_OPERATION:
            file = await self._file_or_none(
                read_token,
                repository,
                staged.path,
                branch_head_sha,
            )
            return file is None
        try:
            file = await self._contents_gateway.get_file(
                read_token,
                owner_login=repository.owner_login,
                repository_name=repository.name,
                path=staged.path,
                ref=branch_head_sha,
            )
        except GitHubNotFoundError:
            return False
        return file.sha == staged.expected_file_sha

    async def _execute_write(
        self,
        *,
        staged: StagedWrite,
        repository: RepositorySnapshot,
        write_token: SecretStr,
    ) -> GitHubResponse[FileWriteResult]:
        if staged.operation == FILE_DELETE_OPERATION:
            if staged.expected_file_sha is None:
                raise FileWriteValidationError("delete staging lost its expected file SHA")
            return await self._contents_gateway.delete_file(
                write_token,
                owner_login=repository.owner_login,
                repository_name=repository.name,
                path=staged.path,
                branch=staged.branch,
                message=staged.commit_message,
                expected_sha=staged.expected_file_sha,
            )
        if staged.content is None or staged.desired_blob_sha is None:
            raise FileWriteValidationError("file staging lost its desired content")
        return await self._contents_gateway.put_file(
            write_token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            path=staged.path,
            branch=staged.branch,
            message=staged.commit_message,
            content=staged.content,
            expected_sha=staged.expected_file_sha,
        )

    async def _reconcile(
        self,
        *,
        user_id: int,
        staged: StagedWrite,
        repository: RepositorySnapshot,
        read_token: SecretStr,
        error: GitHubGatewayError,
    ) -> FileWriteOutcome:
        try:
            file = await self._contents_gateway.get_file(
                read_token,
                owner_login=repository.owner_login,
                repository_name=repository.name,
                path=staged.path,
                ref=staged.branch,
            )
        except GitHubNotFoundError:
            if staged.operation == FILE_DELETE_OPERATION:
                await self._audit.success(
                    user_id=user_id,
                    staged=staged,
                    repository=repository,
                    request_id=error.context.request_id,
                    commit_sha=None,
                    reconciled=True,
                    original_error_kind=error.kind.value,
                )
                return _outcome(FileWriteState.APPLIED, staged, repository)
            return await self._uncertain(user_id, staged, repository, error)
        except GitHubGatewayError:
            return await self._uncertain(user_id, staged, repository, error)

        if staged.operation != FILE_DELETE_OPERATION and file.sha == staged.desired_blob_sha:
            await self._audit.success(
                user_id=user_id,
                staged=staged,
                repository=repository,
                request_id=error.context.request_id,
                commit_sha=None,
                reconciled=True,
                original_error_kind=error.kind.value,
            )
            return _outcome(FileWriteState.APPLIED, staged, repository)
        return await self._uncertain(user_id, staged, repository, error)

    async def _uncertain(
        self,
        user_id: int,
        staged: StagedWrite,
        repository: RepositorySnapshot,
        error: GitHubGatewayError,
    ) -> FileWriteOutcome:
        await self._audit.uncertain(
            user_id=user_id,
            staged=staged,
            repository=repository,
            request_id=error.context.request_id,
            original_error_kind=error.kind.value,
        )
        return _outcome(FileWriteState.UNCERTAIN, staged, repository)

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
        context: InstalledRepositoryContext,
        path: str,
    ) -> SecretStr:
        capabilities = {GitHubCapability.CONTENTS_WRITE}
        if is_workflow_path(path):
            capabilities.add(GitHubCapability.WORKFLOWS_WRITE)
        levels = combine_installation_permissions(capabilities)
        token = await self._token_provider.get_token(
            context.installation_id,
            permissions={name: level.value for name, level in levels.items()},
            repository_ids=[context.github_repository_id],
        )
        return token.token


def _validate_content(content: bytes) -> None:
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


def _outcome(
    state: FileWriteState,
    staged: StagedWrite,
    repository: RepositorySnapshot | None,
    *,
    commit_sha: str | None = None,
) -> FileWriteOutcome:
    return FileWriteOutcome(
        state=state,
        operation=staged.operation,
        repository=repository,
        branch=staged.branch,
        path=staged.path,
        commit_sha=commit_sha,
    )
