"""Inline keyboards for GitHub user authorization/account controls."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from gitdock.core.constants import NAV_HOME, NAV_REFRESH
from gitdock.services.user_authorization import UserAuthorizationStatus
from gitdock.telegram import callbacks


def account_keyboard(
    status: UserAuthorizationStatus,
    *,
    can_authorize: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if can_authorize:
        authorize_label = "🔐 إعادة التفويض" if status.authorized else "🔐 تفعيل صلاحية المستخدم"
        rows.append(
            [InlineKeyboardButton(text=authorize_label, callback_data=callbacks.ACCOUNT_AUTHORIZE)]
        )

    if status.authorized:
        rows.append(
            [
                InlineKeyboardButton(
                    text=NAV_REFRESH,
                    callback_data=callbacks.ACCOUNT_REFRESH,
                )
            ]
        )

    if status.authorized or status.installation_count > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔌 قطع الربط المحلي",
                    callback_data=callbacks.ACCOUNT_DISCONNECT_BEGIN,
                )
            ]
        )

    rows.append([InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def authorization_ready_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 فتح GitHub", url=url)],
            [InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN)],
        ]
    )


def disconnect_confirmation_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأكيد قطع الربط",
                    callback_data=callbacks.account_disconnect_confirm(token),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ إلغاء",
                    callback_data=callbacks.account_disconnect_cancel(token),
                )
            ],
            [InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN)],
        ]
    )


def account_result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 حساب GitHub", callback_data=callbacks.ACCOUNT_OPEN)],
            [InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN)],
        ]
    )
