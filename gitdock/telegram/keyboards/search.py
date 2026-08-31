"""Inline keyboards for public GitHub repository search."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from gitdock.core.constants import NAV_BACK, NAV_HOME
from gitdock.github.search import RepositorySearchResult
from gitdock.services.search import SearchCriteria, SearchLanguage, SearchResultPage, SearchSort
from gitdock.telegram import callbacks


def search_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN)]]
    )


def search_results_keyboard(session_id: str, page: SearchResultPage) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    buttons = [
        InlineKeyboardButton(
            text=f"{index} • {_short(repository.full_name, 25)}",
            callback_data=callbacks.search_open(
                session_id,
                page.page,
                repository.github_repository_id,
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
                callback_data=callbacks.search_results(session_id, page.page - 1),
            )
        )
    if page.page < page.total_pages:
        navigation.append(
            InlineKeyboardButton(
                text="التالي ▶️",
                callback_data=callbacks.search_results(session_id, page.page + 1),
            )
        )
    if navigation:
        rows.append(navigation)

    stars_prefix = "✅ " if page.criteria.sort is SearchSort.STARS else ""
    updated_prefix = "✅ " if page.criteria.sort is SearchSort.UPDATED else ""
    rows.append(
        [
            InlineKeyboardButton(
                text=f"{stars_prefix}⭐ الأكثر نجومًا",
                callback_data=callbacks.search_sort(session_id, SearchSort.STARS),
            ),
            InlineKeyboardButton(
                text=f"{updated_prefix}🔄 آخر تحديث",
                callback_data=callbacks.search_sort(session_id, SearchSort.UPDATED),
            ),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="🎛 التصفية",
                callback_data=callbacks.search_filters(session_id, page.page),
            ),
            InlineKeyboardButton(text="🔎 بحث جديد", callback_data=callbacks.SEARCH_BEGIN),
        ]
    )
    rows.append([InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def search_detail_keyboard(
    session_id: str,
    page: int,
    repository: RepositorySearchResult,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 فتح GitHub", url=repository.html_url)],
            [
                InlineKeyboardButton(
                    text="📥 أوامر التنزيل",
                    callback_data=callbacks.placeholder("clone"),
                )
            ],
            [
                InlineKeyboardButton(
                    text=NAV_BACK,
                    callback_data=callbacks.search_results(session_id, page),
                ),
                InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
            ],
        ]
    )


def search_filters_keyboard(
    session_id: str,
    criteria: SearchCriteria,
    *,
    back_page: int,
) -> InlineKeyboardMarkup:
    languages = [
        (SearchLanguage.PYTHON, "🐍 Python"),
        (SearchLanguage.JAVASCRIPT, "🟨 JavaScript"),
        (SearchLanguage.TYPESCRIPT, "🔷 TypeScript"),
        (SearchLanguage.KOTLIN, "🤖 Kotlin"),
    ]
    rows: list[list[InlineKeyboardButton]] = []
    for index in range(0, len(languages), 2):
        row: list[InlineKeyboardButton] = []
        for language, label in languages[index : index + 2]:
            prefix = "✅ " if criteria.language is language else ""
            row.append(
                InlineKeyboardButton(
                    text=f"{prefix}{label}",
                    callback_data=callbacks.search_language(session_id, language),
                )
            )
        rows.append(row)
    rows.append(
        [
            InlineKeyboardButton(
                text="🧹 كل اللغات",
                callback_data=callbacks.search_language(session_id, None),
            )
        ]
    )
    stars = criteria.min_stars if criteria.min_stars is not None else "—"
    owner = _short(criteria.owner_scope or "—", 16)
    topic = _short(criteria.topic or "—", 16)
    rows.append(
        [
            InlineKeyboardButton(
                text=f"⭐ حد أدنى: {stars}",
                callback_data=callbacks.search_filter_action(session_id, "stars"),
            ),
            InlineKeyboardButton(
                text=f"👤 {owner}",
                callback_data=callbacks.search_filter_action(session_id, "owner"),
            ),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=f"🏷 {topic}",
                callback_data=callbacks.search_filter_action(session_id, "topic"),
            ),
            InlineKeyboardButton(
                text=("✅ 📦 إظهار المؤرشف" if criteria.include_archived else "📦 إظهار المؤرشف"),
                callback_data=callbacks.search_filter_action(session_id, "arch"),
            ),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="🧹 مسح الفلاتر",
                callback_data=callbacks.search_filter_action(session_id, "clear"),
            ),
            InlineKeyboardButton(
                text="✅ تطبيق",
                callback_data=callbacks.search_filter_action(session_id, "apply"),
            ),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=NAV_BACK,
                callback_data=callbacks.search_results(session_id, back_page),
            ),
            InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def filter_input_keyboard(session_id: str, back_page: int = 1) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=NAV_BACK,
                    callback_data=callbacks.search_filters(session_id, back_page),
                ),
                InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
            ]
        ]
    )


def _short(value: str, limit: int) -> str:
    return value if len(value) <= limit else f"{value[: limit - 1]}…"
