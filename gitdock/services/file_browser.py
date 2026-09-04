"""P4.1 facade combining repository file reads and safe writes."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.services.confirmations import ConfirmationService
from gitdock.services.file_audit import FileAuditWriter
from gitdock.services.file_context import FileRepositoryContextResolver
from gitdock.services.file_reads import FileReadService
from gitdock.services.file_types import (
    DirectoryView,
    FileDisplayKind,
    FileView,
    FileWriteOutcome,
    FileWritePlan,
    FileWriteState,
    RepositoryReadGateway,
)
from gitdock.services.file_write_store import FileWriteStore
from gitdock.services.file_writes import FileWriteService
from gitdock.services.file_types import ContentsGateway
from gitdock.github.token_provider import InstallationTokenProvider

__all__ = [
    "DirectoryView",
    "FileBrowserService",
    "FileDisplayKind",
    "FileView",
    "FileWriteOutcome",
    "FileWritePlan",
    "FileWriteState",
]


class FileBrowserService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        token_provider: InstallationTokenProvider,
        repository_gateway: RepositoryReadGateway,
        contents_gateway: ContentsGateway,
        confirmations: ConfirmationService,
    ) -> None:
        resolver = FileRepositoryContextResolver(
            session_factory,
            token_provider,
            repository_gateway,
        )
        self._reads = FileReadService(resolver, contents_gateway)
        store = FileWriteStore(session_factory, confirmations)
        audit = FileAuditWriter(session_factory)
        self._writes = FileWriteService(
            resolver,
            token_provider,
            contents_gateway,
            store,
            audit,
        )

    async def browse_directory(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        path: str = "",
        ref: str | None = None,
    ) -> DirectoryView:
        return await self._reads.browse_directory(
            user_id=user_id,
            github_repository_id=github_repository_id,
            path=path,
            ref=ref,
        )

    async def view_file(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        path: str,
        ref: str | None = None,
    ) -> FileView:
        return await self._reads.view_file(
            user_id=user_id,
            github_repository_id=github_repository_id,
            path=path,
            ref=ref,
        )

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
        return await self._writes.begin_create(
            user_id=user_id,
            github_repository_id=github_repository_id,
            branch=branch,
            path=path,
            content=content,
            commit_message=commit_message,
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
        return await self._writes.begin_update(
            user_id=user_id,
            github_repository_id=github_repository_id,
            branch=branch,
            path=path,
            content=content,
            commit_message=commit_message,
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
        return await self._writes.begin_delete(
            user_id=user_id,
            github_repository_id=github_repository_id,
            branch=branch,
            path=path,
            commit_message=commit_message,
        )

    async def confirm_create(self, *, user_id: int, token: str) -> FileWriteOutcome:
        return await self._writes.confirm_create(user_id=user_id, token=token)

    async def confirm_update(self, *, user_id: int, token: str) -> FileWriteOutcome:
        return await self._writes.confirm_update(user_id=user_id, token=token)

    async def confirm_delete(self, *, user_id: int, token: str) -> FileWriteOutcome:
        return await self._writes.confirm_delete(user_id=user_id, token=token)

    async def cancel_create(self, *, user_id: int, token: str) -> bool:
        return await self._writes.cancel_create(user_id=user_id, token=token)

    async def cancel_update(self, *, user_id: int, token: str) -> bool:
        return await self._writes.cancel_update(user_id=user_id, token=token)

    async def cancel_delete(self, *, user_id: int, token: str) -> bool:
        return await self._writes.cancel_delete(user_id=user_id, token=token)
