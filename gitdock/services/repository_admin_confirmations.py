"""Lifecycle controls for repository-administration confirmation authority."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.services.confirmations import ConfirmationService
from gitdock.services.repository_admin import CREATE_OPERATION, DELETE_OPERATION, UPDATE_OPERATION


class RepositoryAdminConfirmationService:
    """Cancel one pending repository-admin confirmation without executing its write."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        confirmations: ConfirmationService,
    ) -> None:
        self._session_factory = session_factory
        self._confirmations = confirmations

    async def cancel_create(self, *, user_id: int, token: str) -> bool:
        return await self._cancel(user_id=user_id, token=token, operation=CREATE_OPERATION)

    async def cancel_update(self, *, user_id: int, token: str) -> bool:
        return await self._cancel(user_id=user_id, token=token, operation=UPDATE_OPERATION)

    async def cancel_delete(self, *, user_id: int, token: str) -> bool:
        return await self._cancel(user_id=user_id, token=token, operation=DELETE_OPERATION)

    async def _cancel(self, *, user_id: int, token: str, operation: str) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                return await self._confirmations.cancel(
                    session,
                    user_id=user_id,
                    token=token,
                    expected_operation=operation,
                )
