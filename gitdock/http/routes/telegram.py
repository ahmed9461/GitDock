"""Telegram webhook ingress."""

from __future__ import annotations

import secrets

from aiogram.types import Update
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gitdock.core.constants import TELEGRAM_WEBHOOK_PATH

router = APIRouter()


@router.post(TELEGRAM_WEBHOOK_PATH)
async def telegram_webhook(request: Request) -> JSONResponse:
    settings = request.app.state.settings
    expected = settings.telegram_webhook_secret
    if expected is None:
        return JSONResponse(status_code=503, content={"status": "webhook_not_configured"})

    supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not secrets.compare_digest(supplied, expected.get_secret_value()):
        return JSONResponse(status_code=401, content={"status": "unauthorized"})

    payload = await request.json()
    bot = request.app.state.telegram_bot
    dispatcher = request.app.state.telegram_dispatcher
    update = Update.model_validate(payload, context={"bot": bot})
    await dispatcher.feed_update(bot, update)
    return JSONResponse(content={"status": "ok"})
