"""Restart-safe staging and confirmation consumption for one-file writes."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.core.constants import FILE_WRITE_SESSION_TTL_SECONDS
from gitdock.db.models import FileWriteSession
from gitdock.domain.files import content_sha256, git_blob_sha
from gitdock.github.repositories import RepositorySnapshot
from gitdock.services.confirmations import ConfirmationService
from gitdock.services.file_types import InstalledRepositoryContext, StagedWrite


class FileWriteStore:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        confirmations: ConfirmationService,
    ) -> None:
        self._session_factory = session_factory
        self._confirmations = confirmations

    async def stage(
        self,
        *,
        user_id: int,
        context: InstalledRepositoryContext,
        repository: RepositorySnapshot,
        operation: str,
        branch: str,
        path: str,
        branch_head_sha: str,
        expected_file_sha: str | None,
        content: bytes | None,
        commit_message: str,
        risk_tier: int,
    ) -> str:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=FILE_WRITE_SESSION_TTL_SECONDS)
        desired_blob_sha = git_blob_sha(content) if content is not None else None
        digest = content_sha256(content) if content is not None else None
        async with self._session_factory() as session:
            async with session.begin():
                await self._expire_old_sessions(session, user_id=user_id, now=now)
                await self._supersede_target(
                    session,
                    user_id=user_id,
                    github_repository_id=repository.github_repository_id,
                    branch=branch,
                    path=path,
                    now=now,
                )
                row = FileWriteSession(
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
                session.add(row)
                await session.flush()
                payload = _session_payload(row)
                issued = await self._confirmations.create(
                    session,
                    user_id=user_id,
                    operation_type=operation,
                    target_fingerprint=_fingerprint(payload),
                    payload=payload,
                    risk_tier=risk_tier,
                )
                return issued.token

    async def consume(
        self,
        *,
        user_id: int,
        token: str,
        operation: str,
    ) -> StagedWrite | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            async with session.begin():
                confirmation = await self._confirmations.consume(
                    session,
                    user_id=user_id,
                    token=token,
                    expected_operation=operation,
                )
                if confirmation is None:
                    return None
                if confirmation.target_fingerprint != _fingerprint(confirmation.payload):
                    return None
                session_id = _positive_int(confirmation.payload.get("session_id"))
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
                if row is None or _session_payload(row) != confirmation.payload:
                    return None
                content = bytes(row.content_bytes) if row.content_bytes is not None else None
                if not _content_is_intact(row, content):
                    row.consumed_at = now
                    row.content_bytes = None
                    return None
                staged = _copy_staged(row, content)
                row.consumed_at = now
                row.content_bytes = None
                return staged

    async def cancel(
        self,
        *,
        user_id: int,
        token: str,
        operation: str,
    ) -> bool:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            async with session.begin():
                confirmation = await self._confirmations.consume(
                    session,
                    user_id=user_id,
                    token=token,
                    expected_operation=operation,
                )
                if confirmation is None:
                    return False
                session_id = _positive_int(confirmation.payload.get("session_id"))
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

    async def _expire_old_sessions(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        now: datetime,
    ) -> None:
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

    async def _supersede_target(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        github_repository_id: int,
        branch: str,
        path: str,
        now: datetime,
    ) -> None:
        await session.execute(
            update(FileWriteSession)
            .where(
                FileWriteSession.user_id == user_id,
                FileWriteSession.github_repository_id == github_repository_id,
                FileWriteSession.branch == branch,
                FileWriteSession.path == path,
                FileWriteSession.consumed_at.is_(None),
            )
            .values(consumed_at=now, content_bytes=None)
            .execution_options(synchronize_session=False)
        )


def _session_payload(row: FileWriteSession) -> dict[str, Any]:
    return {
        "session_id": row.id,
        "repository_id": row.github_repository_id,
        "installation_id": row.installation_id,
        "repository_full_name": row.repository_full_name,
        "repository_default_branch": row.repository_default_branch,
        "operation": row.operation,
        "branch": row.branch,
        "path": row.path,
        "branch_head_sha": row.branch_head_sha,
        "expected_file_sha": row.expected_file_sha,
        "desired_blob_sha": row.desired_blob_sha,
        "risk_tier": row.risk_tier,
    }


def _copy_staged(row: FileWriteSession, content: bytes | None) -> StagedWrite:
    return StagedWrite(
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


def _content_is_intact(row: FileWriteSession, content: bytes | None) -> bool:
    if content is None:
        return row.content_digest is None and row.desired_blob_sha is None
    return row.content_digest == content_sha256(content) and row.desired_blob_sha == git_blob_sha(
        content
    )


def _fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _positive_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None
