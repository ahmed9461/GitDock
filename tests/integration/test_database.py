import pytest
from sqlalchemy import select

from gitdock.db.base import Base
from gitdock.db.models import TelegramAccount, User
from gitdock.db.session import create_engine, create_session_factory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_identity_models_persist_with_async_sqlalchemy() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    sessions = create_session_factory(engine)
    async with sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        session.add(TelegramAccount(user_id=user.id, telegram_user_id=123456))
        await session.commit()

        result = await session.scalar(
            select(TelegramAccount).where(TelegramAccount.telegram_user_id == 123456)
        )
        assert result is not None
        assert result.user_id == user.id

    await engine.dispose()
