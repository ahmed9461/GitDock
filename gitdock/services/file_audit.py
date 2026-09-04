"""Secret-safe audit persistence for repository file writes."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.db.models import AuditLog
from gitdock.domain.files import is_workflow_path
from gitdock.github.errors import GitHubGatewayError
from gitdock.github.repositories import RepositorySnapshot
from gitdock.services.file_types import StagedWrite


class FileAuditWriter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def success(
        self,
        *,
        user_id: int,
        staged: StagedWrite,
        repository: RepositorySnapshot,
        request_id: str | None,
        commit_sha: str | None,
        reconciled: bool = False,
        original_error_kind: str | None = None,
    ) -> None:
        details = _details(staged)
        details["commit_sha"] = commit_sha
        if reconciled:
            details["reconciled"] = True
        if original_error_kind is not None:
            details["original_error_kind"] = original_error_kind
        await self._write(
            user_id=user_id,
            staged=staged,
            repository=repository,
            status="success",
            request_id=request_id,
            details=details,
        )

    async def failure(
        self,
        *,
        user_id: int,
        staged: StagedWrite,
        repository: RepositorySnapshot,
        error: GitHubGatewayError,
    ) -> None:
        details = _details(staged)
        details["error_kind"] = error.kind.value
        await self._write(
            user_id=user_id,
            staged=staged,
            repository=repository,
            status="failure",
            request_id=error.context.request_id,
            details=details,
        )

    async def uncertain(
        self,
        *,
        user_id: int,
        staged: StagedWrite,
        repository: RepositorySnapshot,
        request_id: str | None,
        original_error_kind: str,
    ) -> None:
        details = _details(staged)
        details.update({"reconciled": False, "original_error_kind": original_error_kind})
        await self._write(
            user_id=user_id,
            staged=staged,
            repository=repository,
            status="uncertain",
            request_id=request_id,
            details=details,
        )

    async def _write(
        self,
        *,
        user_id: int,
        staged: StagedWrite,
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


def _details(staged: StagedWrite) -> dict[str, Any]:
    return {
        "branch": staged.branch,
        "path": staged.path,
        "expected_file_sha": staged.expected_file_sha,
        "desired_blob_sha": staged.desired_blob_sha,
        "risk_tier": staged.risk_tier,
        "workflow_path": is_workflow_path(staged.path),
    }
