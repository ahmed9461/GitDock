"""Minimal system router used by the P1 bootstrap."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="system")


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "🐙 GitDock\n\nتم تشغيل الأساس التقني للبوت.\nربط GitHub سيُضاف في المرحلة التالية."
    )
