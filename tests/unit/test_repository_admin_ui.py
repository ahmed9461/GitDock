from __future__ import annotations

from datetime import UTC, datetime

from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.repository_admin import RepositoryCreateRequest, RepositoryUpdateRequest
from gitdock.services.repositories import RepositoryFilter
from gitdock.services.repository_admin import (
    RepositoryAdminResult,
    RepositoryAdminState,
    RepositoryCreatePlan,
    RepositoryUpdatePlan,
)
from gitdock.telegram import callbacks
from gitdock.telegram.keyboards.repositories import home_keyboard, repository_detail_keyboard
from gitdock.telegram.keyboards.repository_admin import (
    create_confirmation_keyboard,
    repository_settings_keyboard,
    update_confirmation_keyboard,
)
from gitdock.telegram.renderers.repository_admin import (
    render_create_preview,
    render_repository_admin_result,
    render_repository_settings,
    render_update_preview,
)


def snapshot() -> RepositorySnapshot:
    now = datetime(2026, 9, 4, 13, 0, tzinfo=UTC)
    return RepositorySnapshot(
        github_repository_id=1351822221,
        owner_login="ahmed9461",
        name="GitDock",
        full_name="ahmed9461/GitDock",
        html_url="https://github.com/ahmed9461/GitDock",
        private=True,
        archived=False,
        fork=False,
        default_branch="main",
        language="Python",
        description="Repository description",
        stars=0,
        forks=0,
        updated_at=now,
        pushed_at=now,
    )


def test_repository_admin_callbacks_round_trip_under_telegram_limit() -> None:
    settings = callbacks.repository_settings(2**63 - 1, RepositoryFilter.ARCHIVED, 9999)
    action = callbacks.repository_setting_action(
        2**63 - 1,
        "visibility",
        RepositoryFilter.ARCHIVED,
        9999,
    )
    token = "AbCdEfGhIjKlMnOp"
    confirmations = [
        callbacks.repository_create_confirm(token),
        callbacks.repository_update_confirm(token),
        callbacks.repository_delete_confirm(token),
    ]

    assert len(settings.encode("utf-8")) <= 64
    assert len(action.encode("utf-8")) <= 64
    assert all(len(value.encode("utf-8")) <= 64 for value in confirmations)
    assert callbacks.parse_repository_settings(settings) == (
        2**63 - 1,
        RepositoryFilter.ARCHIVED,
        9999,
    )
    assert callbacks.parse_repository_setting_action(action) == (
        2**63 - 1,
        "visibility",
        RepositoryFilter.ARCHIVED,
        9999,
    )
    assert callbacks.parse_repository_create_confirm(confirmations[0]) == token
    assert callbacks.parse_repository_update_confirm(confirmations[1]) == token
    assert callbacks.parse_repository_delete_confirm(confirmations[2]) == token


def test_home_and_repository_dashboard_expose_real_p33_actions() -> None:
    repository = snapshot()
    home = home_keyboard(connected=True, can_connect=True)
    detail = repository_detail_keyboard(
        repository,
        back_filter=RepositoryFilter.ALL,
        back_page=1,
    )

    home_callbacks = {
        button.callback_data
        for row in home.inline_keyboard
        for button in row
        if button.callback_data is not None
    }
    detail_callbacks = {
        button.callback_data
        for row in detail.inline_keyboard
        for button in row
        if button.callback_data is not None
    }
    assert callbacks.REPOSITORY_CREATE_BEGIN in home_callbacks
    assert callbacks.placeholder("repo-create") not in home_callbacks
    assert callbacks.repository_settings(repository.github_repository_id, RepositoryFilter.ALL, 1) in (
        detail_callbacks
    )


def test_repository_settings_keep_delete_isolated_and_confirmations_explicit() -> None:
    repository = snapshot()
    settings = repository_settings_keyboard(
        repository,
        back_filter=RepositoryFilter.ALL,
        back_page=1,
    )
    token = "AbCdEfGhIjKlMnOp"
    create = create_confirmation_keyboard(token)
    update = update_confirmation_keyboard(
        token,
        repository.github_repository_id,
        back_filter=RepositoryFilter.ALL,
        back_page=1,
    )

    delete_rows = [
        row
        for row in settings.inline_keyboard
        if any(button.text == "🗑 حذف المستودع" for button in row)
    ]
    assert len(delete_rows) == 1
    assert len(delete_rows[0]) == 1
    assert create.inline_keyboard[0][0].callback_data == callbacks.repository_create_confirm(token)
    assert update.inline_keyboard[0][0].callback_data == callbacks.repository_update_confirm(token)


def test_repository_admin_renderers_show_preview_settings_and_uncertain_state() -> None:
    repository = snapshot()
    create_plan = RepositoryCreatePlan(
        "AbCdEfGhIjKlMnOp",
        "ahmed9461",
        RepositoryCreateRequest("NewRepo", "desc", True),
        None,
    )
    update_plan = RepositoryUpdatePlan(
        "AbCdEfGhIjKlMnOp",
        repository,
        RepositoryUpdateRequest(archived=True),
    )

    assert "✅ مراجعة الإنشاء" in render_create_preview(create_plan)
    assert "المالك: ahmed9461" in render_create_preview(create_plan)
    settings_text = render_repository_settings(repository)
    assert "⚙️ إعدادات GitDock" in settings_text
    assert "🔒 خاص" in settings_text
    assert "📦 مؤرشف" in render_update_preview(update_plan)

    uncertain = render_repository_admin_result(
        RepositoryAdminResult(RepositoryAdminState.UNCERTAIN),
        "update",
    )
    assert "غير محسومة" in uncertain
    assert "إعادة تنفيذ العملية بشكل أعمى" in uncertain
