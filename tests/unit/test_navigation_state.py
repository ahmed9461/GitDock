from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from gitdock.telegram.routers.system import create_system_router


@pytest.mark.asyncio
async def test_start_clears_transient_fsm_state() -> None:
    router = create_system_router()
    handler = router.message.handlers[0].callback
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()
    state = AsyncMock(spec=FSMContext)

    await handler(message, state)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_home_callback_clears_transient_fsm_state() -> None:
    router = create_system_router()
    handler = router.callback_query.handlers[0].callback
    callback = AsyncMock(spec=CallbackQuery)
    callback.answer = AsyncMock()
    state = AsyncMock(spec=FSMContext)

    await handler(callback, state)

    state.clear.assert_awaited_once()
    callback.answer.assert_awaited_once()
