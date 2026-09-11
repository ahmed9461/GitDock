from __future__ import annotations

from datetime import UTC, datetime

from gitdock.domain.files import TextDiffPreview
from gitdock.github.contents import ContentEntry, ContentKind, FileContent
from gitdock.github.repositories import RepositorySnapshot
from gitdock.services.file_types import (
    DirectoryView,
    FileDisplayKind,
    FileView,
    FileWriteOutcome,
    FileWritePlan,
    FileWriteState,
)
from gitdock.services.repositories import RepositoryFilter
from gitdock.telegram import file_callbacks
from gitdock.telegram.keyboards.files import (
    directory_keyboard,
    file_keyboard,
    write_confirmation_keyboard,
)
from gitdock.telegram.keyboards.repositories import repository_detail_keyboard
from gitdock.telegram.renderers.files import (
    render_directory,
    render_file,
    render_write_outcome,
    render_write_preview,
)


def snapshot() -> RepositorySnapshot:
    now = datetime(2026, 9, 4, 17, 0, tzinfo=UTC)
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
        description="repo",
        stars=0,
        forks=0,
        updated_at=now,
        pushed_at=now,
    )


def test_file_callbacks_round_trip_and_stay_under_telegram_limit() -> None:
    session = "AbCdEf12"
    token = "AbCdEfGhIjKlMnOp"
    values = [
        file_callbacks.browser_open(2**63 - 1, RepositoryFilter.ARCHIVED, 9999),
        file_callbacks.entry(session, 9999),
        file_callbacks.directory_action(session, "upload"),
        file_callbacks.file_action(session, "replace"),
        file_callbacks.preview_page(session, 9999),
        file_callbacks.wizard(session, "cancel"),
        file_callbacks.confirm("update", token),
        file_callbacks.cancel("delete", token),
        file_callbacks.diff(session),
    ]

    assert all(len(value.encode("utf-8")) <= 64 for value in values)
    assert file_callbacks.parse_browser_open(values[0]) == (
        2**63 - 1,
        RepositoryFilter.ARCHIVED,
        9999,
    )
    assert file_callbacks.parse_entry(values[1]) == (session, 9999)
    assert file_callbacks.parse_directory_action(values[2]) == (session, "upload")
    assert file_callbacks.parse_file_action(values[3]) == (session, "replace")
    assert file_callbacks.parse_preview_page(values[4]) == (session, 9999)
    assert file_callbacks.parse_wizard(values[5]) == (session, "cancel")
    assert file_callbacks.parse_confirm(values[6]) == ("update", token)
    assert file_callbacks.parse_cancel(values[7]) == ("delete", token)
    assert file_callbacks.parse_diff(values[8]) == session


def test_repository_dashboard_exposes_real_file_browser_action() -> None:
    repository = snapshot()
    keyboard = repository_detail_keyboard(
        repository,
        back_filter=RepositoryFilter.ALL,
        back_page=1,
    )
    callbacks = {
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    }
    assert (
        file_callbacks.browser_open(repository.github_repository_id, RepositoryFilter.ALL, 1)
        in callbacks
    )


def test_directory_keyboard_never_embeds_long_repository_path_in_callbacks() -> None:
    repository = snapshot()
    long_path = "docs/" + "x" * 180
    view = DirectoryView(
        repository=repository,
        ref="main",
        ref_commit_sha="a" * 40,
        path="docs",
        entries=(
            ContentEntry(
                name="x" * 180,
                path=long_path,
                sha="b" * 40,
                size=12,
                kind=ContentKind.FILE,
                html_url="https://github.com/ahmed9461/GitDock/blob/main/docs/file.txt",
            ),
        ),
    )
    keyboard = directory_keyboard(
        view,
        "AbCdEf12",
        page=1,
        back_filter=RepositoryFilter.ALL,
        back_page=1,
    )
    callback_values = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]

    assert long_path not in "".join(callback_values)
    assert all(len(value.encode("utf-8")) <= 64 for value in callback_values)


def test_directory_renderer_and_keyboard_paginate_large_folders() -> None:
    repository = snapshot()
    entries = tuple(
        ContentEntry(
            name=f"file-{index}.txt",
            path=f"docs/file-{index}.txt",
            sha=f"{index + 1:x}".rjust(40, "a")[-40:],
            size=index,
            kind=ContentKind.FILE,
            html_url=f"https://github.com/ahmed9461/GitDock/blob/main/docs/file-{index}.txt",
        )
        for index in range(12)
    )
    view = DirectoryView(repository, "main", "a" * 40, "docs", entries)
    text = render_directory(view, page=2)
    keyboard = directory_keyboard(
        view,
        "AbCdEf12",
        page=2,
        back_filter=RepositoryFilter.ALL,
        back_page=1,
    )

    assert "الصفحة 2 من 2" in text
    assert "file-8.txt" in text
    assert "file-0.txt" not in text
    assert any(button.text == "◀️ السابق" for row in keyboard.inline_keyboard for button in row)


def test_file_view_binary_fallback_and_delete_isolation() -> None:
    repository = snapshot()
    file = FileContent(
        name="asset.bin",
        path="assets/asset.bin",
        sha="b" * 40,
        size=2048,
        content=b"\x00binary",
        html_url="https://github.com/ahmed9461/GitDock/blob/main/assets/asset.bin",
    )
    view = FileView(repository, "main", "a" * 40, file, FileDisplayKind.BINARY, ())
    text = render_file(view)
    keyboard = file_keyboard(view, "AbCdEf12", page=1)

    assert "ملف ثنائي" in text
    assert all(button.text != "✏️ تعديل" for row in keyboard.inline_keyboard for button in row)
    delete_rows = [
        row for row in keyboard.inline_keyboard if any(button.text == "🗑 حذف" for button in row)
    ]
    assert len(delete_rows) == 1
    assert len(delete_rows[0]) == 1


def test_write_preview_shows_diff_target_and_persisted_confirmation() -> None:
    repository = snapshot()
    plan = FileWritePlan(
        token="AbCdEfGhIjKlMnOp",
        operation="file.update",
        repository=repository,
        branch="feature/docs",
        path="docs/README.md",
        risk_tier=1,
        diff=TextDiffPreview(8, 3, "@@\n-old\n+new\n"),
    )
    text = render_write_preview(plan)
    keyboard = write_confirmation_keyboard(plan, "AbCdEf12")

    assert "✏️ مراجعة التغيير" in text
    assert "🌿 feature/docs" in text
    assert "+ 8 أسطر" in text
    assert "- 3 أسطر" in text
    assert "Update docs/README.md via GitDock" in text
    assert keyboard.inline_keyboard[0][0].callback_data == file_callbacks.diff("AbCdEf12")
    assert keyboard.inline_keyboard[1][0].callback_data == file_callbacks.confirm(
        "update", plan.token
    )
    assert keyboard.inline_keyboard[2][0].callback_data == file_callbacks.cancel(
        "update", plan.token
    )


def test_write_outcomes_are_explicit_for_stale_uncertain_and_invalid() -> None:
    repository = snapshot()
    stale = FileWriteOutcome(
        FileWriteState.STALE, "file.update", repository, "main", "docs/README.md"
    )
    uncertain = FileWriteOutcome(
        FileWriteState.UNCERTAIN, "file.update", repository, "main", "docs/README.md"
    )
    invalid = FileWriteOutcome(FileWriteState.INVALID, "file.update", None, None, None)

    assert "لم يتم استبدال أو حذف أي شيء" in render_write_outcome(stale)
    assert "لا تعِد تنفيذ العملية بشكل أعمى" in render_write_outcome(uncertain)
    assert "لم يُنفذ تغيير جديد" in render_write_outcome(invalid)
