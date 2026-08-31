"""GitDock development/production entrypoints."""

from __future__ import annotations

import argparse
import asyncio

import uvicorn

from gitdock.core.config import get_settings
from gitdock.core.logging import configure_logging
from gitdock.telegram.bot import create_bot, create_dispatcher


async def run_polling() -> None:
    settings = get_settings()
    if settings.env == "production":
        raise RuntimeError("polling is disabled in production; use the FastAPI webhook deployment")
    configure_logging(settings.log_level)
    bot = create_bot(settings)
    dispatcher = create_dispatcher(settings)
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


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
