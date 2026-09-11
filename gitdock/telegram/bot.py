"""aiogram bootstrap."""

from aiogram import Bot, Dispatcher

from gitdock.core.config import Settings
from gitdock.services.runtime import RuntimeServices
from gitdock.telegram.middleware.owner import OwnerOnlyMiddleware
from gitdock.telegram.routers.files import create_file_browser_router
from gitdock.telegram.routers.repository_admin import create_repository_admin_router
from gitdock.telegram.routers.search import create_search_router
from gitdock.telegram.routers.system import create_system_router


def create_bot(settings: Settings) -> Bot:
    return Bot(token=settings.telegram_bot_token.get_secret_value())


def create_dispatcher(
    settings: Settings,
    services: RuntimeServices | None = None,
) -> Dispatcher:
    dispatcher = Dispatcher()
    owner_middleware = OwnerOnlyMiddleware(settings.telegram_owner_id)
    dispatcher.message.outer_middleware(owner_middleware)
    dispatcher.callback_query.outer_middleware(owner_middleware)
    dispatcher.include_router(create_system_router(settings, services))
    dispatcher.include_router(create_repository_admin_router(services))
    dispatcher.include_router(create_file_browser_router(services))
    dispatcher.include_router(create_search_router(services))
    return dispatcher
