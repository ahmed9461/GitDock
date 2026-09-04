"""Telegram P4.1 repository file browser and one-file write flows."""

from __future__ import annotations

import secrets
from io import BytesIO
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.types import User as TelegramUser

from gitdock.core.constants import FILE_BROWSE_SESSION_ID_BYTES, FILE_SINGLE_UPLOAD_MAX_BYTES
from gitdock.domain.files import (
    RepositoryPathError,
    RepositoryRefError,
    join_repository_path,
    parent_repository_path,
)
from gitdock.github.errors import GitHubGatewayError, GitHubNotFoundError
from gitdock.services.file_types import (
    DirectoryView,
    FileSelectionError,
    FileView,
    FileWriteOutcome,
    FileWritePlan,
    FileWriteState,
    FileWriteValidationError,
)
from gitdock.services.repositories import RepositoryFilter
from gitdock.services.runtime import RuntimeServices
from gitdock.telegram import file_callbacks
from gitdock.telegram.keyboards.files import (
    directory_keyboard,
    file_keyboard,
    result_keyboard,
    wizard_keyboard,
    write_confirmation_keyboard,
)
from gitdock.telegram.keyboards.repositories import simple_back_home_keyboard
from gitdock.telegram.renderers.files import (
    render_create_content_prompt,
    render_create_name_prompt,
    render_directory,
    render_document_prompt,
    render_edit_prompt,
    render_file,
    render_file_cancelled,
    render_file_error,
    render_ref_prompt,
    render_write_outcome,
    render_write_preview,
)
from gitdock.telegram.renderers.repositories import render_github_error, render_stale_selection
from gitdock.telegram.states.files import FileBrowserFlow

_SESSION = "file_session"
_REPOSITORY_ID = "file_repository_id"
_REF = "file_ref"
_DIRECTORY_PATH = "file_directory_path"
_ENTRIES = "file_entries"
_VIEW_KIND = "file_view_kind"
_PAGE = "file_page"
_CURRENT_FILE = "file_current_path"
_BACK_FILTER = "file_back_filter"
_BACK_PAGE = "file_back_page"
_REF_RETURN = "file_ref_return"
_PENDING_PATH = "file_pending_path"
_WRITE_DIFF = "file_write_diff"


def create_file_browser_router(services: RuntimeServices | None = None) -> Router:
    router = Router(name="file-browser")

    @router.callback_query(F.data.startswith(f"{file_callbacks.FILE_PREFIX}:open:"))
    async def browser_open(callback: CallbackQuery, state: FSMContext) -> None:
        if not _available(services) or callback.data is None:
            await callback.answer("متصفح الملفات غير متاح حاليًا", show_alert=True)
            return
        parsed = file_callbacks.parse_browser_open(callback.data)
        if parsed is None:
            await callback.answer("الاختيار غير صالح", show_alert=True)
            return
        repository_id, back_filter, back_page = parsed
        assert services is not None
        session_id = secrets.token_urlsafe(FILE_BROWSE_SESSION_ID_BYTES)
        await state.clear()
        await state.set_state(FileBrowserFlow.active)
        await state.set_data(
            {
                _SESSION: session_id,
                _REPOSITORY_ID: repository_id,
                _BACK_FILTER: back_filter.value,
                _BACK_PAGE: back_page,
                _DIRECTORY_PATH: "",
                _PAGE: 1,
                _VIEW_KIND: "directory",
            }
        )
        await _show_directory_callback(callback, state, services, path="", ref=None, page=1)

    @router.callback_query(F.data.startswith(f"{file_callbacks.FILE_PREFIX}:e:"))
    async def entry_open(callback: CallbackQuery, state: FSMContext) -> None:
        if not _available(services) or callback.data is None:
            await callback.answer()
            return
        parsed = file_callbacks.parse_entry(callback.data)
        if parsed is None:
            await callback.answer("العنصر غير صالح", show_alert=True)
            return
        session_id, index = parsed
        data = await state.get_data()
        if not _session_matches(data, session_id):
            await _expired(callback)
            return
        entries = _entries(data)
        if index >= len(entries):
            await _expired(callback)
            return
        target = entries[index]
        path = target.get("path")
        kind = target.get("kind")
        if not path:
            await _expired(callback)
            return
        assert services is not None
        if kind == "dir":
            await _show_directory_callback(
                callback,
                state,
                services,
                path=path,
                ref=_state_text(data, _REF),
                page=1,
            )
            return
        await _show_file_callback(
            callback,
            state,
            services,
            path=path,
            ref=_state_text(data, _REF),
            page=1,
        )

    @router.callback_query(F.data.startswith(f"{file_callbacks.FILE_PREFIX}:p:"))
    async def browser_page(callback: CallbackQuery, state: FSMContext) -> None:
        if not _available(services) or callback.data is None:
            await callback.answer()
            return
        parsed = file_callbacks.parse_preview_page(callback.data)
        if parsed is None:
            await callback.answer("الصفحة غير صالحة", show_alert=True)
            return
        session_id, page = parsed
        data = await state.get_data()
        if not _session_matches(data, session_id):
            await _expired(callback)
            return
        assert services is not None
        if _state_text(data, _VIEW_KIND) == "file":
            path = _state_text(data, _CURRENT_FILE)
            if path is None:
                await _expired(callback)
                return
            await _show_file_callback(
                callback,
                state,
                services,
                path=path,
                ref=_state_text(data, _REF),
                page=page,
            )
            return
        await _show_directory_callback(
            callback,
            state,
            services,
            path=_state_text(data, _DIRECTORY_PATH) or "",
            ref=_state_text(data, _REF),
            page=page,
        )

    @router.callback_query(F.data.startswith(f"{file_callbacks.FILE_PREFIX}:d:"))
    async def directory_action(callback: CallbackQuery, state: FSMContext) -> None:
        if not _available(services) or callback.data is None:
            await callback.answer()
            return
        parsed = file_callbacks.parse_directory_action(callback.data)
        if parsed is None:
            await callback.answer("الإجراء غير صالح", show_alert=True)
            return
        session_id, action = parsed
        data = await state.get_data()
        if not _session_matches(data, session_id):
            await _expired(callback)
            return
        assert services is not None
        path = _state_text(data, _DIRECTORY_PATH) or ""
        ref = _state_text(data, _REF)
        if action == "refresh":
            await _show_directory_callback(callback, state, services, path=path, ref=ref, page=1)
            return
        if action == "up":
            await _show_directory_callback(
                callback,
                state,
                services,
                path=parent_repository_path(path),
                ref=ref,
                page=1,
            )
            return
        if action == "ref":
            await state.update_data({_REF_RETURN: "directory"})
            await state.set_state(FileBrowserFlow.ref_input)
            await _edit_callback(callback, render_ref_prompt(ref or "main"), wizard_keyboard(session_id))
            return
        if action == "create":
            await state.set_state(FileBrowserFlow.create_name)
            await _edit_callback(callback, render_create_name_prompt(path), wizard_keyboard(session_id))
            return
        await state.set_state(FileBrowserFlow.upload_document)
        await _edit_callback(callback, render_document_prompt(), wizard_keyboard(session_id))

    @router.callback_query(F.data.startswith(f"{file_callbacks.FILE_PREFIX}:a:"))
    async def file_action(callback: CallbackQuery, state: FSMContext) -> None:
        if not _available(services) or callback.data is None:
            await callback.answer()
            return
        parsed = file_callbacks.parse_file_action(callback.data)
        if parsed is None:
            await callback.answer("الإجراء غير صالح", show_alert=True)
            return
        session_id, action = parsed
        data = await state.get_data()
        if not _session_matches(data, session_id):
            await _expired(callback)
            return
        path = _state_text(data, _CURRENT_FILE)
        if path is None:
            await _expired(callback)
            return
        assert services is not None and services.file_browser is not None
        if action == "back":
            await _show_directory_callback(
                callback,
                state,
                services,
                path=_state_text(data, _DIRECTORY_PATH) or parent_repository_path(path),
                ref=_state_text(data, _REF),
                page=1,
            )
            return
        if action == "ref":
            await state.update_data({_REF_RETURN: "file"})
            await state.set_state(FileBrowserFlow.ref_input)
            await _edit_callback(
                callback,
                render_ref_prompt(_state_text(data, _REF) or "main"),
                wizard_keyboard(session_id),
            )
            return
        if action == "edit":
            await state.set_state(FileBrowserFlow.edit_content)
            await _edit_callback(callback, render_edit_prompt(path), wizard_keyboard(session_id))
            return
        if action == "replace":
            await state.set_state(FileBrowserFlow.replace_document)
            await _edit_callback(
                callback,
                render_document_prompt(replace_path=path),
                wizard_keyboard(session_id),
            )
            return
        if action == "download":
            await _download_file(callback, state, services, data, path)
            return
        user_id = await _resolve_user(callback.from_user, services)
        repository_id = _state_int(data, _REPOSITORY_ID)
        ref = _state_text(data, _REF)
        if repository_id is None or ref is None:
            await _expired(callback)
            return
        try:
            plan = await services.file_browser.begin_delete(
                user_id=user_id,
                github_repository_id=repository_id,
                branch=ref,
                path=path,
            )
        except FileWriteValidationError as exc:
            await _edit_callback(callback, render_file_error(str(exc)), simple_back_home_keyboard())
            return
        except GitHubGatewayError as exc:
            await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
            return
        await _show_plan_callback(callback, state, plan, session_id)

    @router.message(FileBrowserFlow.ref_input, F.text)
    async def ref_input(message: Message, state: FSMContext) -> None:
        if not _available(services) or message.text is None:
            return
        data = await state.get_data()
        session_id = _state_text(data, _SESSION)
        repository_id = _state_int(data, _REPOSITORY_ID)
        if session_id is None or repository_id is None:
            await state.clear()
            return
        assert services is not None
        ref = message.text.strip()
        return_kind = _state_text(data, _REF_RETURN) or "directory"
        try:
            if return_kind == "file":
                path = _state_text(data, _CURRENT_FILE)
                if path is None:
                    raise RepositoryPathError("file path is no longer available")
                await _show_file_message(message, state, services, path=path, ref=ref, page=1)
            else:
                await _show_directory_message(
                    message,
                    state,
                    services,
                    path=_state_text(data, _DIRECTORY_PATH) or "",
                    ref=ref,
                    page=1,
                )
        except (RepositoryRefError, RepositoryPathError):
            await message.answer(
                render_file_error("اسم الفرع / Tag / SHA غير صالح."),
                reply_markup=wizard_keyboard(session_id),
            )

    @router.message(FileBrowserFlow.create_name, F.text)
    async def create_name(message: Message, state: FSMContext) -> None:
        if message.text is None:
            return
        data = await state.get_data()
        session_id = _state_text(data, _SESSION)
        if session_id is None:
            return
        try:
            path = join_repository_path(
                _state_text(data, _DIRECTORY_PATH) or "",
                message.text.strip(),
            )
        except RepositoryPathError:
            await message.answer(
                render_file_error("اسم الملف غير صالح. أرسل اسم ملف واحد بدون مسارات إضافية."),
                reply_markup=wizard_keyboard(session_id),
            )
            return
        await state.update_data({_PENDING_PATH: path})
        await state.set_state(FileBrowserFlow.create_content)
        await message.answer(render_create_content_prompt(path), reply_markup=wizard_keyboard(session_id))

    @router.message(FileBrowserFlow.create_content, F.text)
    async def create_content(message: Message, state: FSMContext) -> None:
        if not _available(services) or message.text is None:
            return
        data = await state.get_data()
        path = _state_text(data, _PENDING_PATH)
        if path is None:
            await state.clear()
            return
        await _begin_message_write(message, state, services, data, "create", path, message.text.encode())

    @router.message(FileBrowserFlow.edit_content, F.text)
    async def edit_content(message: Message, state: FSMContext) -> None:
        if not _available(services) or message.text is None:
            return
        data = await state.get_data()
        path = _state_text(data, _CURRENT_FILE)
        if path is None:
            await state.clear()
            return
        await _begin_message_write(message, state, services, data, "update", path, message.text.encode())

    @router.message(FileBrowserFlow.upload_document, F.document)
    async def upload_document(message: Message, state: FSMContext) -> None:
        if not _available(services) or message.document is None:
            return
        data = await state.get_data()
        filename = message.document.file_name
        session_id = _state_text(data, _SESSION)
        if not filename or session_id is None:
            await message.answer(render_file_error("تعذر تحديد اسم الملف."))
            return
        try:
            path = join_repository_path(_state_text(data, _DIRECTORY_PATH) or "", filename)
        except RepositoryPathError:
            await message.answer(
                render_file_error("اسم الملف المرفوع غير صالح."),
                reply_markup=wizard_keyboard(session_id),
            )
            return
        content = await _document_bytes(message)
        if content is None:
            await message.answer(
                render_file_error("حجم الملف يتجاوز حد الرفع المسموح."),
                reply_markup=wizard_keyboard(session_id),
            )
            return
        await _begin_upload(message, state, services, data, path, content)

    @router.message(FileBrowserFlow.replace_document, F.document)
    async def replace_document(message: Message, state: FSMContext) -> None:
        if not _available(services) or message.document is None:
            return
        data = await state.get_data()
        path = _state_text(data, _CURRENT_FILE)
        session_id = _state_text(data, _SESSION)
        if path is None or session_id is None:
            await state.clear()
            return
        content = await _document_bytes(message)
        if content is None:
            await message.answer(
                render_file_error("حجم الملف يتجاوز حد الرفع المسموح."),
                reply_markup=wizard_keyboard(session_id),
            )
            return
        await _begin_message_write(message, state, services, data, "update", path, content)

    @router.callback_query(F.data.startswith(f"{file_callbacks.FILE_PREFIX}:w:"))
    async def wizard_navigation(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.data is None or not _available(services):
            await callback.answer()
            return
        parsed = file_callbacks.parse_wizard(callback.data)
        if parsed is None:
            await callback.answer("الإجراء غير صالح", show_alert=True)
            return
        session_id, action = parsed
        data = await state.get_data()
        if not _session_matches(data, session_id):
            await _expired(callback)
            return
        current_state = await state.get_state()
        if action == "back" and current_state == FileBrowserFlow.create_content.state:
            await state.set_state(FileBrowserFlow.create_name)
            await _edit_callback(
                callback,
                render_create_name_prompt(_state_text(data, _DIRECTORY_PATH) or ""),
                wizard_keyboard(session_id),
            )
            return
        assert services is not None
        await _return_to_browser_callback(callback, state, services, data)

    @router.callback_query(F.data.startswith(f"{file_callbacks.FILE_PREFIX}:diff:"))
    async def show_diff(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.data is None:
            await callback.answer()
            return
        session_id = file_callbacks.parse_diff(callback.data)
        data = await state.get_data()
        if session_id is None or not _session_matches(data, session_id):
            await _expired(callback)
            return
        preview = _state_text(data, _WRITE_DIFF)
        await callback.answer()
        if isinstance(callback.message, Message):
            await callback.message.answer(
                f"👁️ Diff\n\n{preview or 'لا توجد معاينة نصية متاحة.'}"
            )

    @router.callback_query(F.data.startswith(f"{file_callbacks.FILE_PREFIX}:n:"))
    async def write_cancel(callback: CallbackQuery, state: FSMContext) -> None:
        if not _available(services) or callback.data is None:
            await callback.answer()
            return
        parsed = file_callbacks.parse_cancel(callback.data)
        if parsed is None:
            await callback.answer("الإلغاء غير صالح", show_alert=True)
            return
        operation, token = parsed
        assert services is not None and services.file_browser is not None
        user_id = await _resolve_user(callback.from_user, services)
        cancelled = await _cancel_write(services, operation, user_id, token)
        data = await state.get_data()
        if cancelled and _state_text(data, _SESSION) is not None:
            await _return_to_browser_callback(callback, state, services, data)
            return
        await state.clear()
        await _edit_callback(
            callback,
            render_file_cancelled() if cancelled else render_write_outcome(_invalid_outcome(operation)),
            simple_back_home_keyboard(),
        )

    @router.callback_query(F.data.startswith(f"{file_callbacks.FILE_PREFIX}:y:"))
    async def write_confirm(callback: CallbackQuery, state: FSMContext) -> None:
        if not _available(services) or callback.data is None:
            await callback.answer()
            return
        parsed = file_callbacks.parse_confirm(callback.data)
        if parsed is None:
            await callback.answer("التأكيد غير صالح", show_alert=True)
            return
        operation, token = parsed
        assert services is not None and services.file_browser is not None
        user_id = await _resolve_user(callback.from_user, services)
        try:
            outcome = await _confirm_write(services, operation, user_id, token)
        except GitHubGatewayError as exc:
            await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
            return
        data = await state.get_data()
        repository_id = _state_int(data, _REPOSITORY_ID)
        back_filter, back_page = _back_context(data)
        if outcome.state is FileWriteState.APPLIED:
            await state.clear()
        await _edit_callback(
            callback,
            render_write_outcome(outcome),
            result_keyboard(repository_id, back_filter, back_page),
        )

    return router


async def _show_directory_callback(
    callback: CallbackQuery,
    state: FSMContext,
    services: RuntimeServices,
    *,
    path: str,
    ref: str | None,
    page: int,
) -> None:
    user_id = await _resolve_user(callback.from_user, services)
    try:
        view = await _browse(services, user_id, _required_repository_id(await state.get_data()), path, ref)
    except FileSelectionError:
        await _edit_callback(callback, render_stale_selection(), simple_back_home_keyboard())
        return
    except GitHubGatewayError as exc:
        await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
        return
    data = await state.get_data()
    await _save_directory(state, view, page)
    back_filter, back_page = _required_back_context(data)
    await _edit_callback(
        callback,
        render_directory(view, page=page),
        directory_keyboard(
            view,
            _required_session(data),
            page=page,
            back_filter=back_filter,
            back_page=back_page,
        ),
    )


async def _show_directory_message(
    message: Message,
    state: FSMContext,
    services: RuntimeServices,
    *,
    path: str,
    ref: str | None,
    page: int,
) -> None:
    user_id = await _resolve_message_user(message, services)
    if user_id is None:
        return
    data = await state.get_data()
    try:
        view = await _browse(services, user_id, _required_repository_id(data), path, ref)
    except GitHubGatewayError as exc:
        await message.answer(render_github_error(exc), reply_markup=simple_back_home_keyboard())
        return
    await state.set_state(FileBrowserFlow.active)
    await _save_directory(state, view, page)
    back_filter, back_page = _required_back_context(data)
    await message.answer(
        render_directory(view, page=page),
        reply_markup=directory_keyboard(
            view,
            _required_session(data),
            page=page,
            back_filter=back_filter,
            back_page=back_page,
        ),
    )


async def _show_file_callback(
    callback: CallbackQuery,
    state: FSMContext,
    services: RuntimeServices,
    *,
    path: str,
    ref: str | None,
    page: int,
) -> None:
    user_id = await _resolve_user(callback.from_user, services)
    data = await state.get_data()
    try:
        view = await _view(services, user_id, _required_repository_id(data), path, ref)
    except FileSelectionError:
        await _edit_callback(callback, render_stale_selection(), simple_back_home_keyboard())
        return
    except GitHubGatewayError as exc:
        await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
        return
    await _save_file(state, view, page)
    await _edit_callback(
        callback,
        render_file(view, page=page),
        file_keyboard(view, _required_session(data), page=page),
    )


async def _show_file_message(
    message: Message,
    state: FSMContext,
    services: RuntimeServices,
    *,
    path: str,
    ref: str | None,
    page: int,
) -> None:
    user_id = await _resolve_message_user(message, services)
    if user_id is None:
        return
    data = await state.get_data()
    try:
        view = await _view(services, user_id, _required_repository_id(data), path, ref)
    except GitHubGatewayError as exc:
        await message.answer(render_github_error(exc), reply_markup=simple_back_home_keyboard())
        return
    await state.set_state(FileBrowserFlow.active)
    await _save_file(state, view, page)
    await message.answer(
        render_file(view, page=page),
        reply_markup=file_keyboard(view, _required_session(data), page=page),
    )


async def _return_to_browser_callback(
    callback: CallbackQuery,
    state: FSMContext,
    services: RuntimeServices,
    data: dict[str, Any],
) -> None:
    await state.set_state(FileBrowserFlow.active)
    path = _state_text(data, _CURRENT_FILE)
    if _state_text(data, _VIEW_KIND) == "file" and path is not None:
        await _show_file_callback(
            callback,
            state,
            services,
            path=path,
            ref=_state_text(data, _REF),
            page=_state_int(data, _PAGE) or 1,
        )
        return
    await _show_directory_callback(
        callback,
        state,
        services,
        path=_state_text(data, _DIRECTORY_PATH) or "",
        ref=_state_text(data, _REF),
        page=_state_int(data, _PAGE) or 1,
    )


async def _begin_message_write(
    message: Message,
    state: FSMContext,
    services: RuntimeServices | None,
    data: dict[str, Any],
    operation: str,
    path: str,
    content: bytes,
) -> None:
    if not _available(services):
        return
    assert services is not None and services.file_browser is not None
    user_id = await _resolve_message_user(message, services)
    if user_id is None:
        return
    repository_id = _state_int(data, _REPOSITORY_ID)
    ref = _state_text(data, _REF)
    session_id = _state_text(data, _SESSION)
    if repository_id is None or ref is None or session_id is None:
        await state.clear()
        return
    try:
        if operation == "create":
            plan = await services.file_browser.begin_create(
                user_id=user_id,
                github_repository_id=repository_id,
                branch=ref,
                path=path,
                content=content,
            )
        else:
            plan = await services.file_browser.begin_update(
                user_id=user_id,
                github_repository_id=repository_id,
                branch=ref,
                path=path,
                content=content,
            )
    except FileWriteValidationError as exc:
        await message.answer(render_file_error(str(exc)), reply_markup=wizard_keyboard(session_id))
        return
    except GitHubGatewayError as exc:
        await message.answer(render_github_error(exc), reply_markup=wizard_keyboard(session_id))
        return
    await _show_plan_message(message, state, plan, session_id)


async def _begin_upload(
    message: Message,
    state: FSMContext,
    services: RuntimeServices | None,
    data: dict[str, Any],
    path: str,
    content: bytes,
) -> None:
    if not _available(services):
        return
    assert services is not None and services.file_browser is not None
    user_id = await _resolve_message_user(message, services)
    if user_id is None:
        return
    repository_id = _required_repository_id(data)
    ref = _state_text(data, _REF)
    session_id = _required_session(data)
    if ref is None:
        await state.clear()
        return
    try:
        await services.file_browser.view_file(
            user_id=user_id,
            github_repository_id=repository_id,
            path=path,
            ref=ref,
        )
    except GitHubNotFoundError:
        operation = "create"
    except GitHubGatewayError as exc:
        await message.answer(render_github_error(exc), reply_markup=wizard_keyboard(session_id))
        return
    else:
        operation = "update"
    await _begin_message_write(message, state, services, data, operation, path, content)


async def _show_plan_callback(
    callback: CallbackQuery,
    state: FSMContext,
    plan: FileWritePlan,
    session_id: str,
) -> None:
    await state.set_state(FileBrowserFlow.active)
    await state.update_data({_WRITE_DIFF: plan.diff.preview if plan.diff is not None else None})
    await _edit_callback(
        callback,
        render_write_preview(plan),
        write_confirmation_keyboard(plan, session_id),
    )


async def _show_plan_message(
    message: Message,
    state: FSMContext,
    plan: FileWritePlan,
    session_id: str,
) -> None:
    await state.set_state(FileBrowserFlow.active)
    await state.update_data({_WRITE_DIFF: plan.diff.preview if plan.diff is not None else None})
    await message.answer(
        render_write_preview(plan),
        reply_markup=write_confirmation_keyboard(plan, session_id),
    )


async def _download_file(
    callback: CallbackQuery,
    state: FSMContext,
    services: RuntimeServices,
    data: dict[str, Any],
    path: str,
) -> None:
    assert services.file_browser is not None
    user_id = await _resolve_user(callback.from_user, services)
    try:
        view = await services.file_browser.view_file(
            user_id=user_id,
            github_repository_id=_required_repository_id(data),
            path=path,
            ref=_state_text(data, _REF),
        )
    except GitHubGatewayError as exc:
        await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
        return
    if view.file.content is None or len(view.file.content) > FILE_SINGLE_UPLOAD_MAX_BYTES:
        await callback.answer(
            "GitHub لم يُرجع بايتات قابلة للتنزيل هنا؛ استخدم زر فتح GitHub.",
            show_alert=True,
        )
        return
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer_document(
            BufferedInputFile(view.file.content, filename=view.file.name),
            caption=f"📄 {view.file.path}\n🌿 {view.ref}",
        )


async def _document_bytes(message: Message) -> bytes | None:
    document = message.document
    if document is None:
        return None
    if document.file_size is not None and document.file_size > FILE_SINGLE_UPLOAD_MAX_BYTES:
        return None
    buffer = BytesIO()
    await message.bot.download(document, destination=buffer)
    content = buffer.getvalue()
    return content if len(content) <= FILE_SINGLE_UPLOAD_MAX_BYTES else None


async def _browse(
    services: RuntimeServices,
    user_id: int,
    repository_id: int,
    path: str,
    ref: str | None,
) -> DirectoryView:
    if services.file_browser is None:
        raise FileSelectionError("file browser is unavailable")
    return await services.file_browser.browse_directory(
        user_id=user_id,
        github_repository_id=repository_id,
        path=path,
        ref=ref,
    )


async def _view(
    services: RuntimeServices,
    user_id: int,
    repository_id: int,
    path: str,
    ref: str | None,
) -> FileView:
    if services.file_browser is None:
        raise FileSelectionError("file browser is unavailable")
    return await services.file_browser.view_file(
        user_id=user_id,
        github_repository_id=repository_id,
        path=path,
        ref=ref,
    )


async def _save_directory(state: FSMContext, view: DirectoryView, page: int) -> None:
    await state.set_state(FileBrowserFlow.active)
    await state.update_data(
        {
            _REF: view.ref,
            _DIRECTORY_PATH: view.path,
            _ENTRIES: [
                {"path": entry.path, "kind": entry.kind.value} for entry in view.entries
            ],
            _VIEW_KIND: "directory",
            _PAGE: page,
            _CURRENT_FILE: None,
            _WRITE_DIFF: None,
        }
    )


async def _save_file(state: FSMContext, view: FileView, page: int) -> None:
    await state.set_state(FileBrowserFlow.active)
    await state.update_data(
        {
            _REF: view.ref,
            _DIRECTORY_PATH: parent_repository_path(view.file.path),
            _VIEW_KIND: "file",
            _CURRENT_FILE: view.file.path,
            _PAGE: page,
            _WRITE_DIFF: None,
        }
    )


async def _confirm_write(
    services: RuntimeServices,
    operation: str,
    user_id: int,
    token: str,
) -> FileWriteOutcome:
    assert services.file_browser is not None
    if operation == "create":
        return await services.file_browser.confirm_create(user_id=user_id, token=token)
    if operation == "update":
        return await services.file_browser.confirm_update(user_id=user_id, token=token)
    return await services.file_browser.confirm_delete(user_id=user_id, token=token)


async def _cancel_write(
    services: RuntimeServices,
    operation: str,
    user_id: int,
    token: str,
) -> bool:
    assert services.file_browser is not None
    if operation == "create":
        return await services.file_browser.cancel_create(user_id=user_id, token=token)
    if operation == "update":
        return await services.file_browser.cancel_update(user_id=user_id, token=token)
    return await services.file_browser.cancel_delete(user_id=user_id, token=token)


async def _resolve_user(user: TelegramUser, services: RuntimeServices) -> int:
    resolved = await services.identity.resolve(
        telegram_user_id=user.id,
        username=user.username,
        display_name=user.full_name,
    )
    return resolved.user_id


async def _resolve_message_user(message: Message, services: RuntimeServices) -> int | None:
    if message.from_user is None:
        return None
    return await _resolve_user(message.from_user, services)


async def _edit_callback(callback: CallbackQuery, text: str, reply_markup) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=reply_markup)


async def _expired(callback: CallbackQuery) -> None:
    await callback.answer("انتهت جلسة التصفح. افتح الملفات من المستودع مجددًا.", show_alert=True)


def _available(services: RuntimeServices | None) -> bool:
    return services is not None and services.file_browser is not None


def _entries(data: dict[str, Any]) -> list[dict[str, str]]:
    raw = data.get(_ENTRIES)
    if not isinstance(raw, list):
        return []
    result: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        kind = item.get("kind")
        if isinstance(path, str) and isinstance(kind, str):
            result.append({"path": path, "kind": kind})
    return result


def _session_matches(data: dict[str, Any], session_id: str) -> bool:
    return _state_text(data, _SESSION) == session_id


def _required_session(data: dict[str, Any]) -> str:
    value = _state_text(data, _SESSION)
    if value is None:
        raise RuntimeError("file browse session is unavailable")
    return value


def _required_repository_id(data: dict[str, Any]) -> int:
    value = _state_int(data, _REPOSITORY_ID)
    if value is None:
        raise RuntimeError("file repository context is unavailable")
    return value


def _back_context(data: dict[str, Any]) -> tuple[RepositoryFilter | None, int | None]:
    raw_filter = _state_text(data, _BACK_FILTER)
    page = _state_int(data, _BACK_PAGE)
    if raw_filter is None or page is None:
        return None, None
    try:
        return RepositoryFilter(raw_filter), page
    except ValueError:
        return None, None


def _required_back_context(data: dict[str, Any]) -> tuple[RepositoryFilter, int]:
    repository_filter, page = _back_context(data)
    if repository_filter is None or page is None:
        raise RuntimeError("file browser back context is unavailable")
    return repository_filter, page


def _state_text(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) else None


def _state_int(data: dict[str, Any], key: str) -> int | None:
    value = data.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _invalid_outcome(operation: str) -> FileWriteOutcome:
    operation_type = {
        "create": "file.create",
        "update": "file.update",
        "delete": "file.delete",
    }.get(operation, "file.update")
    return FileWriteOutcome(FileWriteState.INVALID, operation_type, None, None, None)
