from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from gitdock.db.base import Base
from gitdock.db.models import FileWriteSession, User
from gitdock.db.session import create_engine, create_session_factory
from gitdock.github.repositories import RepositorySnapshot
from gitdock.services.confirmations import ConfirmationService
from gitdock.services.file_types import InstalledRepositoryContext
from gitdock.services.file_write_store import FileWriteStore


@pytest.mark.integration
@pytest.mark.asyncio
async def test_new_same_path_stage_invalidates_older_write_authority() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)

    async with sessions() as session:
        user = User()
        session.add(user)
        await session.commit()
        user_id = user.id

    store = FileWriteStore(sessions, ConfirmationService())
    context = InstalledRepositoryContext(
        installation_id=99,
        github_repository_id=1351822221,
        owner_login="ahmed9461",
        repository_name="GitDock",
    )
    now = datetime(2026, 9, 11, tzinfo=UTC)
    repository = RepositorySnapshot(
        github_repository_id=1351822221,
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
        stars=0,
        forks=0,
        updated_at=now,
        pushed_at=now,
    )

    first_token = await store.stage(
        user_id=user_id,
        context=context,
        repository=repository,
        operation="file.update",
        branch="main",
        path="docs/README.md",
        branch_head_sha="a" * 40,
        expected_file_sha="b" * 40,
        content=b"first\n",
        commit_message="Update docs/README.md via GitDock",
        risk_tier=2,
    )
    second_token = await store.stage(
        user_id=user_id,
        context=context,
        repository=repository,
        operation="file.update",
        branch="main",
        path="docs/README.md",
        branch_head_sha="a" * 40,
        expected_file_sha="b" * 40,
        content=b"second\n",
        commit_message="Update docs/README.md via GitDock",
        risk_tier=2,
    )

    assert (
        await store.consume(
            user_id=user_id,
            token=first_token,
            operation="file.update",
        )
        is None
    )

    latest = await store.consume(
        user_id=user_id,
        token=second_token,
        operation="file.update",
    )
    assert latest is not None
    assert latest.content == b"second\n"

    async with sessions() as session:
        rows = (await session.scalars(select(FileWriteSession).order_by(FileWriteSession.id))).all()
        assert len(rows) == 2
        assert rows[0].consumed_at is not None
        assert rows[0].content_bytes is None
        assert rows[1].consumed_at is not None
        assert rows[1].content_bytes is None

    await engine.dispose()
