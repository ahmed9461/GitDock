"""Inline keyboards for repository creation and administration."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from gitdock.core.constants import NAV_BACK, NAV_CANCEL, NAV_HOME
from gitdock.github.repositories import RepositorySnapshot
from gitdock.services.repositories import RepositoryFilter
from gitdock.telegram import callbacks


def create_name_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=NAV_CANCEL, callback_data=callbacks.HOME_OPEN)],
        ]
    )


def create_description_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="تخطي",
                    callback_data=callbacks.REPOSITORY_CREATE_SKIP_DESCRIPTION,
                )
            ],
            [
                InlineKeyboardButton(
                    text=NAV_BACK,
                    callback_data=callbacks.REPOSITORY_CREATE_BACK_NAME,
                ),
                InlineKeyboardButton(text=NAV_CANCEL, callback_data=callbacks.HOME_OPEN),
            ],
        ]
    )


def create_visibility_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔒 خاص",
                    callback_data=callbacks.REPOSITORY_CREATE_PRIVATE,
                ),
                InlineKeyboardButton(
                    text="🌐 عام",
                    callback_data=callbacks.REPOSITORY_CREATE_PUBLIC,
                ),
            ],
            [
                InlineKeyboardButton(
                    text=NAV_BACK,
                    callback_data=callbacks.REPOSITORY_CREATE_BACK_DESCRIPTION,
                ),
                InlineKeyboardButton(text=NAV_CANCEL, callback_data=callbacks.HOME_OPEN),
            ],
        ]
    )


def create_confirmation_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ إنشاء المستودع",
                    callback_data=callbacks.repository_create_confirm(token),
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ تعديل البيانات",
                    callback_data=callbacks.REPOSITORY_CREATE_EDIT,
                )
            ],
            [InlineKeyboardButton(text=NAV_CANCEL, callback_data=callbacks.HOME_OPEN)],
        ]
    )


def repository_settings_keyboard(
    repository: RepositorySnapshot,
    *,
    back_filter: RepositoryFilter,
    back_page: int,
) -> InlineKeyboardMarkup:
    repository_id = repository.github_repository_id
    action = callbacks.repository_setting_action
    archive_label = "📤 إلغاء الأرشفة" if repository.archived else "📦 أرشفة"
    visibility_label = "🌐 جعله عامًا" if repository.private else "🔒 جعله خاصًا"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ الاسم",
                    callback_data=action(repository_id, "name", back_filter, back_page),
                ),
                InlineKeyboardButton(
                    text="📝 الوصف",
                    callback_data=action(repository_id, "desc", back_filter, back_page),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=visibility_label,
                    callback_data=action(repository_id, "visibility", back_filter, back_page),
                ),
                InlineKeyboardButton(
                    text=archive_label,
                    callback_data=action(repository_id, "archive", back_filter, back_page),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌿 الفرع الافتراضي",
                    callback_data=action(repository_id, "branch", back_filter, back_page),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 حذف المستودع",
                    callback_data=action(repository_id, "delete", back_filter, back_page),
                )
            ],
            [
                InlineKeyboardButton(
                    text=NAV_BACK,
                    callback_data=callbacks.repository_open(repository_id, back_filter, back_page),
                ),
                InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
            ],
        ]
    )


def settings_input_keyboard(
    repository_id: int,
    *,
    back_filter: RepositoryFilter,
    back_page: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=NAV_BACK,
                    callback_data=callbacks.repository_settings(
                        repository_id,
                        back_filter,
                        back_page,
                    ),
                ),
                InlineKeyboardButton(text=NAV_CANCEL, callback_data=callbacks.HOME_OPEN),
            ]
        ]
    )


def update_confirmation_keyboard(
    token: str,
    repository_id: int,
    *,
    back_filter: RepositoryFilter,
    back_page: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تطبيق التغيير",
                    callback_data=callbacks.repository_update_confirm(token),
                )
            ],
            [
                InlineKeyboardButton(
                    text=NAV_BACK,
                    callback_data=callbacks.repository_settings(
                        repository_id,
                        back_filter,
                        back_page,
                    ),
                ),
                InlineKeyboardButton(text=NAV_CANCEL, callback_data=callbacks.HOME_OPEN),
            ],
        ]
    )


def delete_confirmation_keyboard(
    token: str,
    repository_id: int,
    *,
    back_filter: RepositoryFilter,
    back_page: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 تأكيد الحذف نهائيًا",
                    callback_data=callbacks.repository_delete_confirm(token),
                )
            ],
            [
                InlineKeyboardButton(
                    text=NAV_BACK,
                    callback_data=callbacks.repository_settings(
                        repository_id,
                        back_filter,
                        back_page,
                    ),
                ),
                InlineKeyboardButton(text=NAV_CANCEL, callback_data=callbacks.HOME_OPEN),
            ],
        ]
    )


def repository_admin_result_keyboard(
    repository: RepositorySnapshot | None,
    *,
    back_filter: RepositoryFilter = RepositoryFilter.ALL,
    back_page: int = 1,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if repository is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text="⚙️ إعدادات المستودع",
                    callback_data=callbacks.repository_settings(
                        repository.github_repository_id,
                        back_filter,
                        back_page,
                    ),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="📦 مستودعاتي",
                callback_data=callbacks.repository_list(RepositoryFilter.ALL, 1),
            ),
            InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
