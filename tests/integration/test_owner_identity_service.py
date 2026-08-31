from __future__ import annotations

import pytest
from sqlalchemy import func, select

from gitdock.db.base import Base
from gitdock.db.models import TelegramAccount, User
from gitdock.db.session import create_engine, create_session_factory
from gitdock.services.identity import OwnerIdentityService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_owner_identity_is_created_once_and_profile_metadata_refreshes() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    service = OwnerIdentityService(sessions)

    first = await service.resolve(
        telegram_user_id=123,
        username="old_name",
        display_name="Old Name",
    )
    second = await service.resolve(
        telegram_user_id=123,
        username="new_name",
        display_name="New Name",
    )

    assert first.user_id == second.user_id
    async with sessions() as session:
        user_count = await session.scalar(select(func.count()).select_from(User))
        account_count = await session.scalar(select(func.count()).select_from(TelegramAccount))
        account = await session.scalar(select(TelegramAccount))
        assert user_count == 1
        assert account_count == 1
        assert account is not None
        assert account.username == "new_name"
        assert account.display_name == "New Name"

    await engine.dispose()
