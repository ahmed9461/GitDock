"""GitDock development/production entrypoints."""

from __future__ import annotations

import argparse
import asyncio

import uvicorn

from gitdock.core.config import get_settings
from gitdock.core.logging import configure_logging
from gitdock.db.session import create_engine, create_session_factory
from gitdock.services.runtime import create_runtime_services
from gitdock.telegram.bot import create_bot, create_dispatcher


async def run_polling() -> None:
    settings = get_settings()
    if settings.env == "production":
        raise RuntimeError("polling is disabled in production; use the FastAPI webhook deployment")
    configure_logging(settings.log_level)
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    runtime_services = create_runtime_services(settings, session_factory)
    bot = create_bot(settings)
    dispatcher = create_dispatcher(settings, runtime_services)
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await runtime_services.close()
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="gitdock")
    parser.add_argument("mode", choices=("api", "poll"), help="runtime mode")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()

    if args.mode == "poll":
        asyncio.run(run_polling())
        return

    uvicorn.run("gitdock.app:create_app", factory=True, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
