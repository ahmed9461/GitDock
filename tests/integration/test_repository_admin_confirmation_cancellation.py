from __future__ import annotations

import pytest

from gitdock.db.base import Base
from gitdock.db.models import User
from gitdock.db.session import create_engine, create_session_factory
from gitdock.services.confirmations import ConfirmationService
from gitdock.services.repository_admin import CREATE_OPERATION, DELETE_OPERATION, UPDATE_OPERATION
from gitdock.services.repository_admin_confirmations import RepositoryAdminConfirmationService


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "cancel_method"),
    [
        (CREATE_OPERATION, "cancel_create"),
        (UPDATE_OPERATION, "cancel_update"),
        (DELETE_OPERATION, "cancel_delete"),
    ],
)
async def test_cancelled_repository_confirmation_cannot_be_reused(
    operation: str,
    cancel_method: str,
) -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    confirmations = ConfirmationService()
    cancellation = RepositoryAdminConfirmationService(sessions, confirmations)

    async with sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        user_id = user.id
        issued = await confirmations.create(
            session,
            user_id=user_id,
            operation_type=operation,
            target_fingerprint="fingerprint",
            payload={"safe": True},
            risk_tier=3,
        )
        await session.commit()

    cancel = getattr(cancellation, cancel_method)
    assert await cancel(user_id=user_id, token=issued.token) is True
    assert await cancel(user_id=user_id, token=issued.token) is False

    async with sessions() as session:
        consumed = await confirmations.consume(
            session,
            user_id=user_id,
            token=issued.token,
            expected_operation=operation,
        )
        assert consumed is None

    await engine.dispose()
