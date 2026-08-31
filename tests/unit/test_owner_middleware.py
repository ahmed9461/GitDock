from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gitdock.telegram.middleware.owner import OwnerOnlyMiddleware, actor_id


class FakeEvent:
    def __init__(self, user_id: int | None) -> None:
        self.from_user = None if user_id is None else SimpleNamespace(id=user_id)


def test_actor_id_reads_from_user_id() -> None:
    assert actor_id(FakeEvent(42)) == 42  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_owner_is_allowed() -> None:
    middleware = OwnerOnlyMiddleware(42)
    handler = AsyncMock(return_value="ok")
    event = FakeEvent(42)
    result = await middleware(handler, event, {})  # type: ignore[arg-type]
    assert result == "ok"
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_non_owner_is_ignored() -> None:
    middleware = OwnerOnlyMiddleware(42)
    handler = AsyncMock(return_value="ok")
    event = FakeEvent(99)
    result = await middleware(handler, event, {})  # type: ignore[arg-type]
    assert result is None
    handler.assert_not_called()
