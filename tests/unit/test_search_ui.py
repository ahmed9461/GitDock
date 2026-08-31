from __future__ import annotations

from datetime import UTC, datetime

from gitdock.github.search import RepositorySearchResult
from gitdock.services.search import (
    SearchCriteria,
    SearchLanguage,
    SearchResultPage,
    SearchSort,
)
from gitdock.telegram import callbacks
from gitdock.telegram.keyboards.repositories import home_keyboard
from gitdock.telegram.keyboards.search import (
    search_filters_keyboard,
    search_results_keyboard,
)
from gitdock.telegram.renderers.search import (
    render_search_detail,
    render_search_filters,
    render_search_results,
)


def repository(name: str = "Hello-World", repository_id: int = 1296269) -> RepositorySearchResult:
    return RepositorySearchResult(
        github_repository_id=repository_id,
        owner_login="octocat",
        name=name,
        full_name=f"octocat/{name}",
        html_url=f"https://github.com/octocat/{name}",
        archived=False,
        fork=False,
        default_branch="main",
        language="Python",
        description="Example repository",
        stars=4200,
        forks=300,
        license_spdx="MIT",
        topics=("telegram", "python"),
        updated_at=datetime(2026, 8, 31, 15, tzinfo=UTC),
        pushed_at=datetime(2026, 8, 31, 14, tzinfo=UTC),
    )


def page(*, criteria: SearchCriteria | None = None) -> SearchResultPage:
    return SearchResultPage(
        items=(repository(),),
        page=1,
        total_pages=2,
        total_items=7,
        incomplete_results=False,
        criteria=criteria or SearchCriteria(query="telegram"),
    )


def test_search_callbacks_round_trip_and_stay_under_telegram_limit() -> None:
    session_id = "AbCd_123"
    open_callback = callbacks.search_open(session_id, 99, 2**63 - 1)
    list_callback = callbacks.search_results(session_id, 99)
    sort_callback = callbacks.search_sort(session_id, SearchSort.UPDATED)
    filter_callback = callbacks.search_filters(session_id, 99)

    for value in (open_callback, list_callback, sort_callback, filter_callback):
        assert len(value.encode("utf-8")) <= 64

    assert callbacks.parse_search_open(open_callback) == (session_id, 99, 2**63 - 1)
    assert callbacks.parse_search_results(list_callback) == (session_id, 99)
    assert callbacks.parse_search_sort(sort_callback) == (session_id, SearchSort.UPDATED)
    assert callbacks.parse_search_filters(filter_callback) == (session_id, 99)
    assert callbacks.parse_search_open("gd:v0:search:open:old:1:1") is None


def test_search_result_keyboard_does_not_embed_repository_name() -> None:
    long_name = "x" * 200
    result = page()
    result = SearchResultPage(
        items=(repository(long_name),),
        page=result.page,
        total_pages=result.total_pages,
        total_items=result.total_items,
        incomplete_results=result.incomplete_results,
        criteria=result.criteria,
    )

    keyboard = search_results_keyboard("AbCd_123", result)
    button = keyboard.inline_keyboard[0][0]

    assert button.callback_data is not None
    assert long_name not in button.callback_data
    assert len(button.callback_data.encode("utf-8")) <= 64


def test_search_renderers_show_metadata_filters_and_detail() -> None:
    criteria = SearchCriteria(
        query="telegram bot",
        sort=SearchSort.STARS,
        language=SearchLanguage.PYTHON,
        min_stars=100,
        owner_scope="org:github",
        topic="bots",
    )
    result_page = page(criteria=criteria)

    rendered = render_search_results(result_page)
    assert "🔎 نتائج: telegram bot" in rendered
    assert "⭐ 4200" in rendered
    assert "MIT" in rendered
    assert "Python" in rendered
    assert "org:github" in rendered

    detail = render_search_detail(repository())
    assert "📦 octocat/Hello-World" in detail
    assert "License: MIT" in detail
    assert "telegram, python" in detail

    filters = render_search_filters(criteria)
    assert "Python" in filters
    assert "100" in filters
    assert "org:github" in filters
    assert "bots" in filters


def test_search_filter_keyboard_uses_compact_callbacks() -> None:
    criteria = SearchCriteria(query="telegram", language=SearchLanguage.KOTLIN)
    keyboard = search_filters_keyboard("AbCd_123", criteria, back_page=3)

    callback_values = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]
    assert callback_values
    assert all(len(value.encode("utf-8")) <= 64 for value in callback_values)
    assert callbacks.search_language("AbCd_123", SearchLanguage.KOTLIN) in callback_values


def test_public_search_is_available_from_disconnected_home() -> None:
    keyboard = home_keyboard(connected=False, can_connect=False)
    callback_values = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]
    assert callbacks.SEARCH_BEGIN in callback_values
