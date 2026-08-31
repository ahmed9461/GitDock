from __future__ import annotations

from datetime import UTC, datetime, timedelta

from gitdock.github.repositories import RepositorySnapshot
from gitdock.services.repositories import HomeStatus, RepositoryFilter, RepositoryListPage
from gitdock.telegram import callbacks
from gitdock.telegram.keyboards.repositories import repository_list_keyboard
from gitdock.telegram.renderers.repositories import (
    render_home,
    render_repository_detail,
    render_repository_list,
)


def snapshot(name: str, repository_id: int = 1351822221) -> RepositorySnapshot:
    now = datetime.now(UTC)
    return RepositorySnapshot(
        github_repository_id=repository_id,
        owner_login="ahmed9461",
        name=name,
        full_name=f"ahmed9461/{name}",
        html_url=f"https://github.com/ahmed9461/{name}",
        private=True,
        archived=False,
        fork=False,
        default_branch="main",
        language="Python",
        description="Repository description",
        stars=12,
        forks=3,
        updated_at=now - timedelta(minutes=8),
        pushed_at=now - timedelta(minutes=10),
    )


def test_repository_callbacks_round_trip_and_remain_under_telegram_limit() -> None:
    callback = callbacks.repository_open(
        2**63 - 1,
        RepositoryFilter.ARCHIVED,
        9999,
    )

    assert len(callback.encode("utf-8")) <= 64
    assert callbacks.parse_repository_open(callback) == (
        2**63 - 1,
        RepositoryFilter.ARCHIVED,
        9999,
    )
    assert callbacks.parse_repository_open("gd:v0:repo:open:bad") is None


def test_repository_list_callback_round_trip() -> None:
    callback = callbacks.repository_list(RepositoryFilter.PRIVATE, 7)
    assert callbacks.parse_repository_list(callback) == (RepositoryFilter.PRIVATE, 7)


def test_long_repository_name_is_not_embedded_in_callback_payload() -> None:
    repository = snapshot("x" * 200)
    page = RepositoryListPage(
        items=(repository,),
        page=1,
        total_pages=1,
        total_items=1,
        repository_filter=RepositoryFilter.ALL,
    )

    keyboard = repository_list_keyboard(page)
    button = keyboard.inline_keyboard[0][0]
    assert button.callback_data is not None
    assert repository.name not in button.callback_data
    assert len(button.callback_data.encode("utf-8")) <= 64


def test_arabic_renderers_cover_connected_empty_and_repository_states() -> None:
    connected = render_home(HomeStatus(True, "ahmed9461", 1, 3))
    disconnected = render_home(HomeStatus(False, None, 0, 0))
    repository = snapshot("GitDock")
    page = RepositoryListPage(
        items=(repository,),
        page=1,
        total_pages=1,
        total_items=1,
        repository_filter=RepositoryFilter.PRIVATE,
    )

    assert "👤 GitHub: ahmed9461" in connected
    assert "📦 المستودعات: 3" in connected
    assert "لم يتم ربط حساب GitHub" in disconnected
    assert "التصفية: خاص" in render_repository_list(page)
    detail = render_repository_detail(repository)
    assert "📦 ahmed9461/GitDock" in detail
    assert "🔒 خاص" in detail
    assert "🌿 الفرع الافتراضي: main" in detail
