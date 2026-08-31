"""Owner-only Telegram authorization middleware for v1."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


def actor_id(event: TelegramObject) -> int | None:
    user = getattr(event, "from_user", None)
    return getattr(user, "id", None)


class OwnerOnlyMiddleware(BaseMiddleware):
    def __init__(self, owner_id: int) -> None:
        self.owner_id = owner_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if actor_id(event) != self.owner_id:
            return None
        return await handler(event, data)
