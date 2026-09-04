"""Telegram repository creation and administration router for P3.3."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.types import User as TelegramUser

from gitdock.github.errors import GitHubGatewayError
from gitdock.github.repository_admin import RepositoryCreateRequest, RepositoryUpdateRequest
from gitdock.services.repositories import RepositoryFilter, RepositorySelectionError
from gitdock.services.repository_admin import (
    RepositoryAdminSelectionError,
    RepositoryAdminState,
)
from gitdock.services.runtime import RuntimeServices
from gitdock.services.user_authorization import ReauthorizationRequired
from gitdock.telegram import callbacks
from gitdock.telegram.keyboards.repositories import simple_back_home_keyboard
from gitdock.telegram.keyboards.repository_admin import (
    create_confirmation_keyboard,
    create_description_keyboard,
    create_name_keyboard,
    create_visibility_keyboard,
    delete_confirmation_keyboard,
    repository_admin_result_keyboard,
    repository_settings_keyboard,
    settings_input_keyboard,
    update_confirmation_keyboard,
)
from gitdock.telegram.renderers.repositories import render_github_error, render_stale_selection
from gitdock.telegram.renderers.repository_admin import (
    render_create_description_prompt,
    render_create_name_prompt,
    render_create_preview,
    render_create_visibility_prompt,
    render_delete_preview,
    render_invalid_repository_admin_input,
    render_repository_admin_result,
    render_repository_settings,
    render_setting_input,
    render_update_preview,
)
from gitdock.telegram.states.repository_admin import RepositoryCreateFlow, RepositorySettingsFlow


def create_repository_admin_router(services: RuntimeServices | None = None) -> Router:
    router = Router(name="repository-admin")

    @router.callback_query(F.data == callbacks.REPOSITORY_CREATE_BEGIN)
    async def create_begin(callback: CallbackQuery, state: FSMContext) -> None:
        if not _admin_available(services):
            await callback.answer("إدارة المستودعات غير متاحة حاليًا", show_alert=True)
            return
        await state.clear()
        await state.set_state(RepositoryCreateFlow.name)
        await _edit_callback(callback, render_create_name_prompt(), create_name_keyboard())

    @router.message(RepositoryCreateFlow.name)
    async def create_name(message: Message, state: FSMContext) -> None:
        if not _admin_available(services) or message.text is None:
            return
        name = message.text.strip()
        if not _valid_repository_name(name):
            await message.answer(
                render_invalid_repository_admin_input(
                    "اسم المستودع غير صالح. استخدم اسمًا غير فارغ بدون / أو \\ وبحد أقصى 100 حرف."
                ),
                reply_markup=create_name_keyboard(),
            )
            return
        await state.update_data(create_name=name)
        await state.set_state(RepositoryCreateFlow.description)
        await message.answer(
            render_create_description_prompt(name),
            reply_markup=create_description_keyboard(),
        )

    @router.callback_query(F.data == callbacks.REPOSITORY_CREATE_BACK_NAME)
    async def create_back_name(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(RepositoryCreateFlow.name)
        await _edit_callback(callback, render_create_name_prompt(), create_name_keyboard())

    @router.message(RepositoryCreateFlow.description)
    async def create_description(message: Message, state: FSMContext) -> None:
        if not _admin_available(services) or message.text is None:
            return
        data = await state.get_data()
        name = _state_text(data, "create_name")
        if name is None:
            await state.clear()
            await message.answer(
                render_invalid_repository_admin_input(
                    "انتهت بيانات الإنشاء. ابدأ العملية من جديد."
                ),
                reply_markup=simple_back_home_keyboard(),
            )
            return
        description = message.text.strip()
        if len(description) > 350:
            await message.answer(
                render_invalid_repository_admin_input("الوصف يجب ألا يتجاوز 350 حرفًا."),
                reply_markup=create_description_keyboard(),
            )
            return
        await state.update_data(create_description=description or None)
        await state.set_state(None)
        await message.answer(
            render_create_visibility_prompt(name, description or None),
            reply_markup=create_visibility_keyboard(),
        )

    @router.callback_query(F.data == callbacks.REPOSITORY_CREATE_SKIP_DESCRIPTION)
    async def create_skip_description(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        name = _state_text(data, "create_name")
        if name is None:
            await state.clear()
            await callback.answer("انتهت بيانات الإنشاء", show_alert=True)
            return
        await state.update_data(create_description=None)
        await state.set_state(None)
        await _edit_callback(
            callback,
            render_create_visibility_prompt(name, None),
            create_visibility_keyboard(),
        )

    @router.callback_query(F.data == callbacks.REPOSITORY_CREATE_BACK_DESCRIPTION)
    async def create_back_description(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        name = _state_text(data, "create_name")
        if name is None:
            await state.clear()
            await callback.answer("انتهت بيانات الإنشاء", show_alert=True)
            return
        await state.set_state(RepositoryCreateFlow.description)
        await _edit_callback(
            callback,
            render_create_description_prompt(name),
            create_description_keyboard(),
        )

    @router.callback_query(
        F.data.in_({callbacks.REPOSITORY_CREATE_PRIVATE, callbacks.REPOSITORY_CREATE_PUBLIC})
    )
    async def create_visibility(callback: CallbackQuery, state: FSMContext) -> None:
        if not _admin_available(services):
            await callback.answer("إدارة المستودعات غير متاحة", show_alert=True)
            return
        assert services is not None and services.repository_admin is not None
        data = await state.get_data()
        name = _state_text(data, "create_name")
        description = _state_optional_text(data, "create_description")
        if name is None:
            await state.clear()
            await callback.answer("انتهت بيانات الإنشاء", show_alert=True)
            return
        request = RepositoryCreateRequest(
            name=name,
            description=description,
            private=callback.data == callbacks.REPOSITORY_CREATE_PRIVATE,
        )
        user_id = await _resolve_user(callback.from_user, services)
        try:
            plan = await services.repository_admin.begin_create(user_id=user_id, request=request)
        except (ReauthorizationRequired, ValueError):
            await _edit_callback(
                callback,
                render_invalid_repository_admin_input(
                    "تعذر تجهيز الإنشاء. تحقق من صلاحية حساب GitHub والبيانات ثم حاول مجددًا."
                ),
                simple_back_home_keyboard(),
            )
            return
        await state.set_state(None)
        await _edit_callback(
            callback,
            render_create_preview(plan),
            create_confirmation_keyboard(plan.token),
        )

    @router.callback_query(F.data == callbacks.REPOSITORY_CREATE_EDIT)
    async def create_edit(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(RepositoryCreateFlow.name)
        await _edit_callback(callback, render_create_name_prompt(), create_name_keyboard())

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:repo:create:confirm:"))
    async def create_confirm(callback: CallbackQuery, state: FSMContext) -> None:
        if not _admin_available(services) or callback.data is None:
            await callback.answer()
            return
        token = callbacks.parse_repository_create_confirm(callback.data)
        if token is None:
            await callback.answer("التأكيد غير صالح", show_alert=True)
            return
        assert services is not None and services.repository_admin is not None
        user_id = await _resolve_user(callback.from_user, services)
        try:
            result = await services.repository_admin.confirm_create(user_id=user_id, token=token)
        except ReauthorizationRequired:
            await _edit_callback(
                callback,
                render_invalid_repository_admin_input("صلاحية GitHub تحتاج إلى إعادة تفويض."),
                simple_back_home_keyboard(),
            )
            return
        except GitHubGatewayError as exc:
            await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
            return
        await state.clear()
        await _edit_callback(
            callback,
            render_repository_admin_result(result, "create"),
            repository_admin_result_keyboard(None),
        )

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:repo:settings:"))
    async def settings_open(callback: CallbackQuery, state: FSMContext) -> None:
        if services is None or services.repository_read is None or callback.data is None:
            await callback.answer()
            return
        parsed = callbacks.parse_repository_settings(callback.data)
        if parsed is None:
            await callback.answer("الاختيار غير صالح", show_alert=True)
            return
        repository_id, back_filter, back_page = parsed
        await state.clear()
        await _show_settings(callback, services, repository_id, back_filter, back_page)

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:repo:set:"))
    async def settings_action(callback: CallbackQuery, state: FSMContext) -> None:
        if not _admin_available(services) or services is None or services.repository_read is None:
            await callback.answer()
            return
        if callback.data is None:
            await callback.answer()
            return
        parsed = callbacks.parse_repository_setting_action(callback.data)
        if parsed is None:
            await callback.answer("الإجراء غير صالح", show_alert=True)
            return
        repository_id, action, back_filter, back_page = parsed
        user_id = await _resolve_user(callback.from_user, services)
        try:
            repository = await services.repository_read.repository_detail(
                user_id=user_id,
                github_repository_id=repository_id,
            )
        except (RepositorySelectionError, RepositoryAdminSelectionError):
            await _edit_callback(callback, render_stale_selection(), simple_back_home_keyboard())
            return
        except GitHubGatewayError as exc:
            await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
            return

        await state.update_data(
            admin_repository_id=repository_id,
            admin_back_filter=back_filter.value,
            admin_back_page=back_page,
        )
        if action in {"name", "desc", "branch", "delete"}:
            target_state = {
                "name": RepositorySettingsFlow.rename,
                "desc": RepositorySettingsFlow.description,
                "branch": RepositorySettingsFlow.default_branch,
                "delete": RepositorySettingsFlow.delete_name,
            }[action]
            await state.set_state(target_state)
            await _edit_callback(
                callback,
                render_setting_input(action, repository),
                settings_input_keyboard(
                    repository_id,
                    back_filter=back_filter,
                    back_page=back_page,
                ),
            )
            return

        request = (
            RepositoryUpdateRequest(private=not repository.private)
            if action == "visibility"
            else RepositoryUpdateRequest(archived=not repository.archived)
        )
        await _begin_update_preview(
            callback,
            state,
            services,
            user_id,
            repository_id,
            request,
            back_filter,
            back_page,
        )

    @router.message(RepositorySettingsFlow.rename)
    async def rename_input(message: Message, state: FSMContext) -> None:
        if message.text is None:
            return
        value = message.text.strip()
        if not _valid_repository_name(value):
            await message.answer(
                render_invalid_repository_admin_input("اسم المستودع الجديد غير صالح.")
            )
            return
        await _update_from_message(message, state, services, RepositoryUpdateRequest(name=value))

    @router.message(RepositorySettingsFlow.description)
    async def description_input(message: Message, state: FSMContext) -> None:
        if message.text is None:
            return
        value = message.text.strip()
        if len(value) > 350:
            await message.answer(
                render_invalid_repository_admin_input("الوصف يجب ألا يتجاوز 350 حرفًا.")
            )
            return
        await _update_from_message(
            message,
            state,
            services,
            RepositoryUpdateRequest(description="" if value == "-" else value),
        )

    @router.message(RepositorySettingsFlow.default_branch)
    async def branch_input(message: Message, state: FSMContext) -> None:
        if message.text is None:
            return
        value = message.text.strip()
        if not value or len(value) > 255 or "\x00" in value:
            await message.answer(render_invalid_repository_admin_input("اسم الفرع غير صالح."))
            return
        await _update_from_message(
            message,
            state,
            services,
            RepositoryUpdateRequest(default_branch=value),
        )

    @router.message(RepositorySettingsFlow.delete_name)
    async def delete_name_input(message: Message, state: FSMContext) -> None:
        if not _admin_available(services) or services is None or message.text is None:
            return
        context = _admin_context(await state.get_data())
        if context is None:
            await state.clear()
            await message.answer(
                render_invalid_repository_admin_input(
                    "انتهت بيانات الحذف. افتح الإعدادات من جديد."
                ),
                reply_markup=simple_back_home_keyboard(),
            )
            return
        repository_id, back_filter, back_page = context
        user_id = await _resolve_message_user(message, services)
        if user_id is None:
            return
        assert services.repository_admin is not None
        try:
            plan = await services.repository_admin.begin_delete(
                user_id=user_id,
                github_repository_id=repository_id,
                typed_full_name=message.text.strip(),
            )
        except (RepositoryAdminSelectionError, GitHubGatewayError):
            await state.clear()
            await message.answer(render_stale_selection(), reply_markup=simple_back_home_keyboard())
            return
        if plan is None:
            await message.answer(
                render_invalid_repository_admin_input(
                    "الاسم الكامل لا يطابق المستودع. اكتب الاسم كما ظهر تمامًا."
                ),
                reply_markup=settings_input_keyboard(
                    repository_id,
                    back_filter=back_filter,
                    back_page=back_page,
                ),
            )
            return
        await state.set_state(None)
        await message.answer(
            render_delete_preview(plan),
            reply_markup=delete_confirmation_keyboard(
                plan.token,
                repository_id,
                back_filter=back_filter,
                back_page=back_page,
            ),
        )

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:repo:update:confirm:"))
    async def update_confirm(callback: CallbackQuery, state: FSMContext) -> None:
        if not _admin_available(services) or callback.data is None:
            await callback.answer()
            return
        token = callbacks.parse_repository_update_confirm(callback.data)
        if token is None:
            await callback.answer("التأكيد غير صالح", show_alert=True)
            return
        assert services is not None and services.repository_admin is not None
        context = _admin_context(await state.get_data())
        user_id = await _resolve_user(callback.from_user, services)
        try:
            result = await services.repository_admin.confirm_update(user_id=user_id, token=token)
        except GitHubGatewayError as exc:
            await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
            return
        await state.clear()
        back_filter, back_page = _result_back_context(context)
        await _edit_callback(
            callback,
            render_repository_admin_result(result, "update"),
            repository_admin_result_keyboard(
                result.repository if result.state is RepositoryAdminState.APPLIED else None,
                back_filter=back_filter,
                back_page=back_page,
            ),
        )

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:repo:delete:confirm:"))
    async def delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
        if not _admin_available(services) or callback.data is None:
            await callback.answer()
            return
        token = callbacks.parse_repository_delete_confirm(callback.data)
        if token is None:
            await callback.answer("التأكيد غير صالح", show_alert=True)
            return
        assert services is not None and services.repository_admin is not None
        user_id = await _resolve_user(callback.from_user, services)
        try:
            result = await services.repository_admin.confirm_delete(user_id=user_id, token=token)
        except GitHubGatewayError as exc:
            await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
            return
        await state.clear()
        await _edit_callback(
            callback,
            render_repository_admin_result(result, "delete"),
            repository_admin_result_keyboard(None),
        )

    return router


async def _begin_update_preview(
    callback: CallbackQuery,
    state: FSMContext,
    services: RuntimeServices,
    user_id: int,
    repository_id: int,
    request: RepositoryUpdateRequest,
    back_filter: RepositoryFilter,
    back_page: int,
) -> None:
    assert services.repository_admin is not None
    try:
        plan = await services.repository_admin.begin_update(
            user_id=user_id,
            github_repository_id=repository_id,
            request=request,
        )
    except (RepositoryAdminSelectionError, ValueError):
        await _edit_callback(callback, render_stale_selection(), simple_back_home_keyboard())
        return
    except GitHubGatewayError as exc:
        await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
        return
    await state.set_state(None)
    await _edit_callback(
        callback,
        render_update_preview(plan),
        update_confirmation_keyboard(
            plan.token,
            repository_id,
            back_filter=back_filter,
            back_page=back_page,
        ),
    )


async def _update_from_message(
    message: Message,
    state: FSMContext,
    services: RuntimeServices | None,
    request: RepositoryUpdateRequest,
) -> None:
    if not _admin_available(services) or services is None:
        return
    context = _admin_context(await state.get_data())
    if context is None:
        await state.clear()
        await message.answer(
            render_invalid_repository_admin_input("انتهت بيانات التعديل. افتح الإعدادات من جديد."),
            reply_markup=simple_back_home_keyboard(),
        )
        return
    repository_id, back_filter, back_page = context
    user_id = await _resolve_message_user(message, services)
    if user_id is None:
        return
    assert services.repository_admin is not None
    try:
        plan = await services.repository_admin.begin_update(
            user_id=user_id,
            github_repository_id=repository_id,
            request=request,
        )
    except (RepositoryAdminSelectionError, ValueError):
        await state.clear()
        await message.answer(render_stale_selection(), reply_markup=simple_back_home_keyboard())
        return
    except GitHubGatewayError as exc:
        await state.clear()
        await message.answer(render_github_error(exc), reply_markup=simple_back_home_keyboard())
        return
    await state.set_state(None)
    await message.answer(
        render_update_preview(plan),
        reply_markup=update_confirmation_keyboard(
            plan.token,
            repository_id,
            back_filter=back_filter,
            back_page=back_page,
        ),
    )


async def _show_settings(
    callback: CallbackQuery,
    services: RuntimeServices,
    repository_id: int,
    back_filter: RepositoryFilter,
    back_page: int,
) -> None:
    assert services.repository_read is not None
    user_id = await _resolve_user(callback.from_user, services)
    try:
        repository = await services.repository_read.repository_detail(
            user_id=user_id,
            github_repository_id=repository_id,
        )
    except RepositorySelectionError:
        await _edit_callback(callback, render_stale_selection(), simple_back_home_keyboard())
        return
    except GitHubGatewayError as exc:
        await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
        return
    await _edit_callback(
        callback,
        render_repository_settings(repository),
        repository_settings_keyboard(
            repository,
            back_filter=back_filter,
            back_page=back_page,
        ),
    )


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


async def _edit_callback(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=reply_markup)


def _admin_available(services: RuntimeServices | None) -> bool:
    return services is not None and services.repository_admin is not None


def _valid_repository_name(value: str) -> bool:
    return (
        bool(value) and len(value) <= 100 and all(char not in value for char in ("/", "\\", "\x00"))
    )


def _state_text(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) and value else None


def _state_optional_text(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) else None


def _admin_context(data: dict[str, object]) -> tuple[int, RepositoryFilter, int] | None:
    repository_id = data.get("admin_repository_id")
    filter_raw = data.get("admin_back_filter")
    page = data.get("admin_back_page")
    if (
        not isinstance(repository_id, int)
        or isinstance(repository_id, bool)
        or repository_id <= 0
        or not isinstance(filter_raw, str)
        or not isinstance(page, int)
        or isinstance(page, bool)
        or page <= 0
    ):
        return None
    try:
        repository_filter = RepositoryFilter(filter_raw)
    except ValueError:
        return None
    return repository_id, repository_filter, page


def _result_back_context(
    context: tuple[int, RepositoryFilter, int] | None,
) -> tuple[RepositoryFilter, int]:
    if context is None:
        return RepositoryFilter.ALL, 1
    return context[1], context[2]
