"""Inline keyboards for P4.2 Git tools."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from gitdock.core.constants import NAV_BACK, NAV_HOME, NAV_REFRESH
from gitdock.github.git_tools import BranchSnapshot, CommitSummary
from gitdock.services.repositories import RepositoryFilter
from gitdock.telegram import callbacks, git_callbacks

_PAGE_SIZE = 8


def branches_keyboard(
    branches: tuple[BranchSnapshot, ...],
    *,
    page: int,
    repository_id: int,
    back_filter: RepositoryFilter,
    back_page: int,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(
        [
            InlineKeyboardButton(
                text="➕ فرع جديد", callback_data=git_callbacks.BRANCH_CREATE_BEGIN
            ),
            InlineKeyboardButton(text="🔎 بحث", callback_data=git_callbacks.BRANCH_SEARCH_BEGIN),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(text="🔀 مقارنة refs", callback_data=git_callbacks.COMPARE_BEGIN),
            InlineKeyboardButton(text=NAV_REFRESH, callback_data=git_callbacks.branch_page(page)),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=NAV_BACK,
                callback_data=callbacks.repository_open(repository_id, back_filter, back_page),
            ),
            InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def branch_detail_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=NAV_BACK, callback_data=git_callbacks.branch_page(1))],
            [InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN)],
        ]
    )


def commits_keyboard(
    commits: tuple[CommitSummary, ...],
    *,
    page: int,
    repository_id: int,
    back_filter: RepositoryFilter,
    back_page: int,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    start = (page - 1) * _PAGE_SIZE
    visible = commits[start : start + _PAGE_SIZE]
    for index, commit in enumerate(visible, start=start):
        title = commit.message.strip().splitlines()[0]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{commit.sha[:7]} • {_short(title, 32)}",
                    callback_data=git_callbacks.item("c", page, index),
                )
            ]
        )
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(text="◀️ السابق", callback_data=git_callbacks.commit_page(page - 1))
        )
    if start + _PAGE_SIZE < len(commits):
        nav.append(
            InlineKeyboardButton(text="التالي ▶️", callback_data=git_callbacks.commit_page(page + 1))
        )
    if nav:
        rows.append(nav)
    rows.append(
        [
            InlineKeyboardButton(text="🌿 تغيير ref", callback_data=git_callbacks.COMMIT_REF_BEGIN),
            InlineKeyboardButton(text=NAV_REFRESH, callback_data=git_callbacks.commit_page(page)),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=NAV_BACK,
                callback_data=callbacks.repository_open(repository_id, back_filter, back_page),
            ),
            InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def commit_detail_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 فتح Commit", url=url)],
            [InlineKeyboardButton(text=NAV_BACK, callback_data=git_callbacks.commit_page(1))],
            [InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN)],
        ]
    )


def branch_confirmation_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ إنشاء الفرع", callback_data=git_callbacks.branch_confirm(token)
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ إلغاء", callback_data=git_callbacks.branch_cancel(token)
                )
            ],
        ]
    )


def result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌿 تحديث الفروع", callback_data=git_callbacks.branch_page(1)
                )
            ],
            [InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN)],
        ]
    )


def _short(value: str, limit: int) -> str:
    return value if len(value) <= limit else f"{value[: limit - 1]}…"
