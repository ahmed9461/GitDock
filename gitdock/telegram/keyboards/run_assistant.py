"""Inline keyboards for P4.3 clone/setup/run guidance."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from gitdock.core.constants import NAV_BACK, NAV_HOME
from gitdock.domain.run_assistant import TargetOS
from gitdock.services.repositories import RepositoryFilter
from gitdock.telegram import callbacks, run_callbacks

_OS_LABELS = {
    TargetOS.WINDOWS: "🪟 Windows PowerShell",
    TargetOS.LINUX: "🐧 Linux",
    TargetOS.MACOS: "🍎 macOS",
}


def repository_os_keyboard(
    *,
    repository_id: int,
    repository_filter: RepositoryFilter,
    page: int,
    selected: TargetOS | None = None,
) -> InlineKeyboardMarkup:
    rows = _os_rows(
        lambda target_os: run_callbacks.repository_os(
            target_os,
            repository_id,
            repository_filter,
            page,
        ),
        selected,
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=NAV_BACK,
                callback_data=callbacks.repository_open(repository_id, repository_filter, page),
            ),
            InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def search_os_keyboard(
    *,
    session_id: str,
    page: int,
    repository_id: int,
    selected: TargetOS | None = None,
) -> InlineKeyboardMarkup:
    rows = _os_rows(
        lambda target_os: run_callbacks.search_os(target_os, session_id, page, repository_id),
        selected,
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=NAV_BACK,
                callback_data=callbacks.search_open(session_id, page, repository_id),
            ),
            InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _os_rows(callback_factory, selected: TargetOS | None) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for target_os in (TargetOS.WINDOWS, TargetOS.LINUX, TargetOS.MACOS):
        prefix = "✅ " if selected is target_os else ""
        buttons.append(
            InlineKeyboardButton(
                text=f"{prefix}{_OS_LABELS[target_os]}",
                callback_data=callback_factory(target_os),
            )
        )
    return [buttons[:2], buttons[2:]]
