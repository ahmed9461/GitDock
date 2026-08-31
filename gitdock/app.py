"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from gitdock.core.config import Settings, get_settings
from gitdock.core.constants import APP_NAME
from gitdock.core.logging import configure_logging
from gitdock.db.session import create_engine, create_session_factory
from gitdock.http.routes.health import router as health_router
from gitdock.http.routes.telegram import router as telegram_router
from gitdock.telegram.bot import create_bot, create_dispatcher


def create_app(settings: Settings | None = None) -> FastAPI:
    configured_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(configured_settings.log_level)
        engine = create_engine(configured_settings.database_url)
        bot = create_bot(configured_settings)
        dispatcher = create_dispatcher(configured_settings)

        app.state.settings = configured_settings
        app.state.db_engine = engine
        app.state.db_session_factory = create_session_factory(engine)
        app.state.telegram_bot = bot
        app.state.telegram_dispatcher = dispatcher
        try:
            yield
        finally:
            await bot.session.close()
            await engine.dispose()

    app = FastAPI(title=APP_NAME, version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(telegram_router)
    return app
