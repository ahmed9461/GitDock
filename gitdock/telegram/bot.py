"""aiogram bootstrap."""

from aiogram import Bot, Dispatcher

from gitdock.core.config import Settings
from gitdock.telegram.middleware.owner import OwnerOnlyMiddleware
from gitdock.telegram.routers.system import router as system_router


def create_bot(settings: Settings) -> Bot:
    return Bot(token=settings.telegram_bot_token.get_secret_value())


def create_dispatcher(settings: Settings) -> Dispatcher:
    dispatcher = Dispatcher()
    owner_middleware = OwnerOnlyMiddleware(settings.telegram_owner_id)
    dispatcher.message.outer_middleware(owner_middleware)
    dispatcher.callback_query.outer_middleware(owner_middleware)
    dispatcher.include_router(system_router)
    return dispatcher
