"""Inline keyboards for the home and installed-repository read screens."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from gitdock.core.constants import NAV_BACK, NAV_HOME, NAV_REFRESH
from gitdock.github.repositories import RepositorySnapshot
from gitdock.services.repositories import RepositoryFilter, RepositoryListPage
from gitdock.telegram import callbacks


def home_keyboard(*, connected: bool, can_connect: bool) -> InlineKeyboardMarkup:
    if not connected:
        rows: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton(text="🔎 البحث في GitHub", callback_data=callbacks.SEARCH_BEGIN)]
        ]
        if can_connect:
            rows.append(
                [InlineKeyboardButton(text="🔗 ربط GitHub", callback_data=callbacks.CONNECT_BEGIN)]
            )
        rows.append(
            [
                InlineKeyboardButton(
                    text="\u2139\ufe0f كيف يعمل الربط؟",
                    callback_data=callbacks.CONNECT_INFO,
                )
            ]
        )
        rows.append([InlineKeyboardButton(text=NAV_REFRESH, callback_data=callbacks.HOME_REFRESH)])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 مستودعاتي",
                    callback_data=callbacks.repository_list(RepositoryFilter.ALL, 1),
                ),
                InlineKeyboardButton(
                    text="🔎 البحث في GitHub",
                    callback_data=callbacks.SEARCH_BEGIN,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👤 حساب GitHub",
                    callback_data=callbacks.ACCOUNT_OPEN,
                ),
                InlineKeyboardButton(
                    text="🔔 التنبيهات", callback_data=callbacks.placeholder("notifications")
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 النشاط", callback_data=callbacks.placeholder("activity")
                ),
                InlineKeyboardButton(
                    text="\u2795 مستودع جديد", callback_data=callbacks.placeholder("repo-create")
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ الإعدادات", callback_data=callbacks.placeholder("settings")
                )
            ],
            [InlineKeyboardButton(text=NAV_REFRESH, callback_data=callbacks.HOME_REFRESH)],
        ]
    )


def repository_list_keyboard(page: RepositoryListPage) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    buttons = [
        InlineKeyboardButton(
            text=f"{index} • {_short(repository.name, 24)}",
            callback_data=callbacks.repository_open(
                repository.github_repository_id, page.repository_filter, page.page
            ),
        )
        for index, repository in enumerate(page.items, start=1)
    ]
    for index in range(0, len(buttons), 2):
        rows.append(buttons[index : index + 2])

    navigation: list[InlineKeyboardButton] = []
    if page.page > 1:
        navigation.append(
            InlineKeyboardButton(
                text="◀️ السابق",
                callback_data=callbacks.repository_list(page.repository_filter, page.page - 1),
            )
        )
    if page.page < page.total_pages:
        navigation.append(
            InlineKeyboardButton(
                text="التالي ▶️",
                callback_data=callbacks.repository_list(page.repository_filter, page.page + 1),
            )
        )
    if navigation:
        rows.append(navigation)

    rows.append(
        [
            InlineKeyboardButton(
                text="🎛 تصفية",
                callback_data=callbacks.repository_filters(page.repository_filter, page.page),
            ),
            InlineKeyboardButton(
                text=NAV_REFRESH,
                callback_data=callbacks.repository_list(page.repository_filter, page.page),
            ),
        ]
    )
    rows.append([InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def repository_filters_keyboard(
    current: RepositoryFilter,
    back_page: int,
) -> InlineKeyboardMarkup:
    labels = {
        RepositoryFilter.PRIVATE: "🔒 خاص",
        RepositoryFilter.PUBLIC: "🌐 عام",
        RepositoryFilter.ACTIVE: "🟢 نشط",
        RepositoryFilter.ARCHIVED: "📦 مؤرشف",
        RepositoryFilter.SOURCE: "🌿 المصدر",
        RepositoryFilter.FORK: "🍴 Fork",
    }
    filters = list(labels)
    rows: list[list[InlineKeyboardButton]] = []
    for index in range(0, len(filters), 2):
        row: list[InlineKeyboardButton] = []
        for repository_filter in filters[index : index + 2]:
            prefix = "✅ " if repository_filter is current else ""
            row.append(
                InlineKeyboardButton(
                    text=f"{prefix}{labels[repository_filter]}",
                    callback_data=callbacks.repository_filter(repository_filter),
                )
            )
        rows.append(row)
    rows.append(
        [
            InlineKeyboardButton(
                text="🧹 مسح التصفية",
                callback_data=callbacks.repository_filter(RepositoryFilter.ALL),
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=NAV_BACK,
                callback_data=callbacks.repository_list(current, back_page),
            ),
            InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def repository_detail_keyboard(
    repository: RepositorySnapshot,
    *,
    back_filter: RepositoryFilter,
    back_page: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📁 الملفات", callback_data=callbacks.placeholder("files")
                ),
                InlineKeyboardButton(
                    text="📝 Commits", callback_data=callbacks.placeholder("commits")
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌿 الفروع", callback_data=callbacks.placeholder("branches")
                ),
                InlineKeyboardButton(
                    text="⚙️ Actions", callback_data=callbacks.placeholder("actions")
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❗ Issues", callback_data=callbacks.placeholder("issues")
                ),
                InlineKeyboardButton(
                    text="🔀 Pull Requests", callback_data=callbacks.placeholder("pulls")
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏷️ Releases", callback_data=callbacks.placeholder("releases")
                ),
                InlineKeyboardButton(
                    text="📥 تشغيل/تنزيل", callback_data=callbacks.placeholder("run")
                ),
            ],
            [InlineKeyboardButton(text="🔗 فتح GitHub", url=repository.html_url)],
            [
                InlineKeyboardButton(
                    text=NAV_BACK,
                    callback_data=callbacks.repository_list(back_filter, back_page),
                ),
                InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
            ],
        ]
    )


def connection_ready_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 فتح GitHub", url=url)],
            [InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN)],
        ]
    )


def simple_back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
                InlineKeyboardButton(text=NAV_BACK, callback_data=callbacks.HOME_OPEN),
            ]
        ]
    )


def _short(value: str, limit: int) -> str:
    return value if len(value) <= limit else f"{value[: limit - 1]}…"
