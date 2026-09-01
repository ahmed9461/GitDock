from __future__ import annotations

from datetime import UTC, datetime, timedelta

from gitdock.services.user_authorization import (
    DisconnectRequest,
    DisconnectResult,
    DisconnectState,
    UserAuthorizationStatus,
)
from gitdock.telegram import callbacks
from gitdock.telegram.keyboards.account import (
    account_keyboard,
    disconnect_confirmation_keyboard,
)
from gitdock.telegram.keyboards.repositories import home_keyboard
from gitdock.telegram.renderers.account import (
    render_account,
    render_disconnect_confirmation,
    render_disconnect_result,
)


def status(*, authorized: bool = True, installations: int = 1) -> UserAuthorizationStatus:
    now = datetime.now(UTC)
    return UserAuthorizationStatus(
        authorized=authorized,
        login="octocat" if authorized else None,
        github_user_id=55 if authorized else None,
        access_expires_at=now + timedelta(hours=7) if authorized else None,
        refresh_expires_at=now + timedelta(days=170) if authorized else None,
        refresh_available=authorized,
        installation_count=installations,
    )


def test_account_callbacks_are_compact_and_confirmation_round_trips() -> None:
    token = "AbCdEf12_-xyZ789"
    confirm = callbacks.account_disconnect_confirm(token)
    cancel = callbacks.account_disconnect_cancel(token)

    assert len(confirm.encode("utf-8")) <= 64
    assert len(cancel.encode("utf-8")) <= 64
    assert callbacks.parse_account_disconnect_confirm(confirm) == token
    assert callbacks.parse_account_disconnect_cancel(cancel) == token
    assert callbacks.parse_account_disconnect_confirm("gd:v1:account:disconnect:yes:bad!") is None


def test_connected_home_exposes_real_github_account_entry() -> None:
    keyboard = home_keyboard(connected=True, can_connect=True)
    buttons = [button for row in keyboard.inline_keyboard for button in row]

    account_button = next(button for button in buttons if button.text == "👤 حساب GitHub")
    assert account_button.callback_data == callbacks.ACCOUNT_OPEN


def test_account_keyboard_separates_disconnect_and_authorization_actions() -> None:
    keyboard = account_keyboard(status(), can_authorize=True)
    rows = keyboard.inline_keyboard

    assert any(
        button.callback_data == callbacks.ACCOUNT_AUTHORIZE for row in rows for button in row
    )
    disconnect_row = next(
        row
        for row in rows
        if any(button.callback_data == callbacks.ACCOUNT_DISCONNECT_BEGIN for button in row)
    )
    assert len(disconnect_row) == 1
    assert disconnect_row[0].text == "🔌 قطع الربط المحلي"


def test_legacy_installation_account_screen_offers_user_authorization_and_disconnect() -> None:
    legacy = status(authorized=False, installations=1)
    text = render_account(legacy)
    keyboard = account_keyboard(legacy, can_authorize=True)
    callback_values = {
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data
    }

    assert "صلاحية المستخدم الدائمة غير مفعلة" in text
    assert callbacks.ACCOUNT_AUTHORIZE in callback_values
    assert callbacks.ACCOUNT_DISCONNECT_BEGIN in callback_values


def test_disconnect_confirmation_states_local_only_scope_and_stale_safety() -> None:
    request = DisconnectRequest(
        token="AbCdEf12_-xyZ789",
        account_login="octocat",
        installation_count=2,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    text = render_disconnect_confirmation(request)
    keyboard = disconnect_confirmation_keyboard(request.token)

    assert "لن يقوم هذا بإلغاء تثبيت GitHub App" in text
    assert "أي زر تأكيد قديم يصبح غير صالح" in text
    assert len(keyboard.inline_keyboard[0]) == 1
    assert (
        callbacks.parse_account_disconnect_confirm(
            keyboard.inline_keyboard[0][0].callback_data or ""
        )
        == request.token
    )


def test_disconnect_result_renderer_never_claims_stale_or_invalid_deleted_data() -> None:
    success = render_disconnect_result(DisconnectResult(DisconnectState.DISCONNECTED, "octocat", 1))
    stale = render_disconnect_result(DisconnectResult(DisconnectState.STALE))
    invalid = render_disconnect_result(DisconnectResult(DisconnectState.INVALID))

    assert "تم حذف بيانات التفويض المحلية" in success
    assert "لم يتم حذف أي ربط أو رمز" in stale
    assert "لم يتم حذف أي شيء" in invalid
