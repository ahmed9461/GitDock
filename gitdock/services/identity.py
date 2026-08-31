"""Owner identity resolution for Telegram-driven use cases."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.db.models.identity import TelegramAccount, User


@dataclass(frozen=True, slots=True)
class ResolvedUser:
    user_id: int
    telegram_user_id: int


class OwnerIdentityService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def resolve(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        display_name: str | None,
    ) -> ResolvedUser:
        if telegram_user_id <= 0:
            raise ValueError("Telegram user ID must be positive")

        async with self._session_factory() as session:
            async with session.begin():
                account = await session.scalar(
                    select(TelegramAccount).where(
                        TelegramAccount.telegram_user_id == telegram_user_id
                    )
                )
                if account is None:
                    user = User()
                    session.add(user)
                    await session.flush()
                    account = TelegramAccount(
                        user_id=user.id,
                        telegram_user_id=telegram_user_id,
                        username=username,
                        display_name=display_name,
                    )
                    session.add(account)
                    await session.flush()
                else:
                    account.username = username
                    account.display_name = display_name

                return ResolvedUser(
                    user_id=account.user_id,
                    telegram_user_id=account.telegram_user_id,
                )
