"""Inline keyboards for P4.1 file browsing and safe one-file writes."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from gitdock.core.constants import NAV_BACK, NAV_CANCEL, NAV_HOME, NAV_REFRESH
from gitdock.github.contents import ContentKind
from gitdock.services.file_types import DirectoryView, FileDisplayKind, FileView, FileWritePlan
from gitdock.services.repositories import RepositoryFilter
from gitdock.telegram import callbacks, file_callbacks
from gitdock.telegram.renderers.files import DIRECTORY_PAGE_SIZE, directory_page_numbers


def directory_keyboard(
    view: DirectoryView,
    session_id: str,
    *,
    page: int,
    back_filter: RepositoryFilter,
    back_page: int,
) -> InlineKeyboardMarkup:
    effective, total_pages = directory_page_numbers(len(view.entries), page)
    start = (effective - 1) * DIRECTORY_PAGE_SIZE
    stop = min(start + DIRECTORY_PAGE_SIZE, len(view.entries))
    rows: list[list[InlineKeyboardButton]] = []
    directory_buttons: list[InlineKeyboardButton] = []
    for index in range(start, stop):
        entry = view.entries[index]
        button = InlineKeyboardButton(
            text=f"{'📁' if entry.kind is ContentKind.DIRECTORY else '📄'} {_short(entry.name, 32)}",
            callback_data=file_callbacks.entry(session_id, index),
        )
        if entry.kind is ContentKind.DIRECTORY:
            directory_buttons.append(button)
        else:
            if directory_buttons:
                rows.extend(_pairs(directory_buttons))
                directory_buttons = []
            rows.append([button])
    if directory_buttons:
        rows.extend(_pairs(directory_buttons))

    nav: list[InlineKeyboardButton] = []
    if effective > 1:
        nav.append(
            InlineKeyboardButton(
                text="◀️ السابق",
                callback_data=file_callbacks.preview_page(session_id, effective - 1),
            )
        )
    if effective < total_pages:
        nav.append(
            InlineKeyboardButton(
                text="التالي ▶️",
                callback_data=file_callbacks.preview_page(session_id, effective + 1),
            )
        )
    if nav:
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(
                text="➕ ملف", callback_data=file_callbacks.directory_action(session_id, "create")
            ),
            InlineKeyboardButton(
                text="⬆️ رفع/استبدال",
                callback_data=file_callbacks.directory_action(session_id, "upload"),
            ),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="🌿 تغيير الفرع",
                callback_data=file_callbacks.directory_action(session_id, "ref"),
            ),
            InlineKeyboardButton(
                text=NAV_REFRESH,
                callback_data=file_callbacks.directory_action(session_id, "refresh"),
            ),
        ]
    )
    if view.path:
        rows.append(
            [
                InlineKeyboardButton(
                    text="⬅️ مجلد أعلى",
                    callback_data=file_callbacks.directory_action(session_id, "up"),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
            InlineKeyboardButton(
                text=NAV_BACK,
                callback_data=callbacks.repository_open(
                    view.repository.github_repository_id,
                    back_filter,
                    back_page,
                ),
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def file_keyboard(
    view: FileView,
    session_id: str,
    *,
    page: int,
) -> InlineKeyboardMarkup:
    total_pages = max(1, len(view.preview_pages))
    effective = min(max(page, 1), total_pages)
    rows: list[list[InlineKeyboardButton]] = []
    page_buttons: list[InlineKeyboardButton] = []
    if effective > 1:
        page_buttons.append(
            InlineKeyboardButton(
                text="◀️", callback_data=file_callbacks.preview_page(session_id, effective - 1)
            )
        )
    if effective < total_pages:
        page_buttons.append(
            InlineKeyboardButton(
                text="▶️", callback_data=file_callbacks.preview_page(session_id, effective + 1)
            )
        )
    if page_buttons:
        rows.append(page_buttons)

    edit_row: list[InlineKeyboardButton] = []
    if view.display_kind is FileDisplayKind.TEXT:
        edit_row.append(
            InlineKeyboardButton(
                text="✏️ تعديل", callback_data=file_callbacks.file_action(session_id, "edit")
            )
        )
    edit_row.append(
        InlineKeyboardButton(
            text="♻️ استبدال", callback_data=file_callbacks.file_action(session_id, "replace")
        )
    )
    rows.append(edit_row)
    rows.append(
        [
            InlineKeyboardButton(
                text="🌿 تغيير الفرع", callback_data=file_callbacks.file_action(session_id, "ref")
            ),
            InlineKeyboardButton(
                text="📥 تنزيل", callback_data=file_callbacks.file_action(session_id, "download")
            ),
        ]
    )
    rows.append([InlineKeyboardButton(text="🔗 فتح GitHub", url=view.file.html_url)])
    rows.append(
        [
            InlineKeyboardButton(
                text="🗑 حذف", callback_data=file_callbacks.file_action(session_id, "delete")
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN),
            InlineKeyboardButton(
                text=NAV_BACK, callback_data=file_callbacks.file_action(session_id, "back")
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wizard_keyboard(session_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=NAV_CANCEL, callback_data=file_callbacks.wizard(session_id, "cancel")
                ),
                InlineKeyboardButton(
                    text=NAV_BACK, callback_data=file_callbacks.wizard(session_id, "back")
                ),
            ]
        ]
    )


def write_confirmation_keyboard(
    plan: FileWritePlan,
    session_id: str,
) -> InlineKeyboardMarkup:
    operation = _operation_name(plan.operation)
    rows: list[list[InlineKeyboardButton]] = []
    if plan.diff is not None and plan.diff.preview:
        rows.append(
            [InlineKeyboardButton(text="👁️ عرض Diff", callback_data=file_callbacks.diff(session_id))]
        )
    label = "🗑 تأكيد الحذف" if operation == "delete" else "✅ تطبيق التغيير"
    rows.append(
        [
            InlineKeyboardButton(
                text=label, callback_data=file_callbacks.confirm(operation, plan.token)
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=NAV_CANCEL, callback_data=file_callbacks.cancel(operation, plan.token)
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def result_keyboard(
    repository_id: int | None,
    back_filter: RepositoryFilter | None,
    back_page: int | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if repository_id is not None and back_filter is not None and back_page is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📦 المستودع",
                    callback_data=callbacks.repository_open(repository_id, back_filter, back_page),
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=NAV_HOME, callback_data=callbacks.HOME_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _operation_name(operation: str) -> str:
    mapping = {"file.create": "create", "file.update": "update", "file.delete": "delete"}
    value = mapping.get(operation)
    if value is None:
        raise ValueError("unsupported file write operation")
    return value


def _pairs(buttons: list[InlineKeyboardButton]) -> list[list[InlineKeyboardButton]]:
    return [buttons[index : index + 2] for index in range(0, len(buttons), 2)]


def _short(value: str, limit: int) -> str:
    return value if len(value) <= limit else f"{value[: limit - 1]}…"
