"""Telegram home/repository/account router for the owner-first GitDock experience."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.types import User as TelegramUser

from gitdock.core.config import Settings
from gitdock.core.constants import GITHUB_OAUTH_CALLBACK_PATH
from gitdock.github.auth import GitHubAuthError
from gitdock.github.errors import GitHubGatewayError
from gitdock.services.repositories import HomeStatus, RepositorySelectionError
from gitdock.services.runtime import RuntimeServices
from gitdock.services.user_authorization import (
    DisconnectResult,
    DisconnectState,
    ReauthorizationRequired,
    UserAuthorizationChanged,
    UserAuthorizationError,
    UserAuthorizationStatus,
)
from gitdock.telegram import callbacks
from gitdock.telegram.keyboards.account import (
    account_keyboard,
    account_result_keyboard,
    authorization_ready_keyboard,
    disconnect_confirmation_keyboard,
)
from gitdock.telegram.keyboards.repositories import (
    connection_ready_keyboard,
    home_keyboard,
    repository_detail_keyboard,
    repository_filters_keyboard,
    repository_list_keyboard,
    simple_back_home_keyboard,
)
from gitdock.telegram.renderers.account import (
    render_account,
    render_authorization_changed,
    render_authorization_error,
    render_authorization_ready,
    render_disconnect_confirmation,
    render_disconnect_result,
    render_reauthorization_required,
)
from gitdock.telegram.renderers.repositories import (
    render_connection_info,
    render_connection_ready,
    render_filter_screen,
    render_github_error,
    render_home,
    render_repository_detail,
    render_repository_list,
    render_stale_selection,
)


def create_system_router(
    settings: Settings | None = None,
    services: RuntimeServices | None = None,
) -> Router:
    """Create a fresh system router for one dispatcher instance."""

    router = Router(name="system")

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext) -> None:
        await state.clear()
        if settings is None or services is None:
            await message.answer("🐙 GitDock\n\nتم تشغيل الأساس التقني للبوت.")
            return
        await _show_home_message(message, settings, services)

    @router.callback_query(F.data.in_({callbacks.HOME_OPEN, callbacks.HOME_REFRESH}))
    async def home(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        if settings is None or services is None:
            await callback.answer()
            return
        await _show_home_callback(callback, settings, services)

    @router.callback_query(F.data == callbacks.CONNECT_INFO)
    async def connect_info(callback: CallbackQuery) -> None:
        if settings is None:
            await callback.answer()
            return
        await _edit_callback(
            callback,
            render_connection_info(_can_connect(settings, services)),
            simple_back_home_keyboard(),
        )

    @router.callback_query(F.data == callbacks.CONNECT_BEGIN)
    async def connect_begin(callback: CallbackQuery) -> None:
        if settings is None or services is None or services.github_connection is None:
            await _edit_callback(
                callback,
                render_connection_info(False),
                simple_back_home_keyboard(),
            )
            return
        if settings.public_base_url is None:
            await _edit_callback(
                callback,
                render_connection_info(False),
                simple_back_home_keyboard(),
            )
            return
        user_id = await _resolve_user(callback.from_user, services)
        await _cancel_disconnect_on_navigation(services, user_id)
        redirect = await services.github_connection.begin_installation(user_id=user_id)
        await _edit_callback(
            callback,
            render_connection_ready(),
            connection_ready_keyboard(redirect.url),
        )

    @router.callback_query(F.data == callbacks.ACCOUNT_OPEN)
    async def account_open(callback: CallbackQuery) -> None:
        if settings is None or services is None:
            await callback.answer()
            return
        await _show_account_callback(callback, settings, services)

    @router.callback_query(F.data == callbacks.ACCOUNT_REFRESH)
    async def account_refresh(callback: CallbackQuery) -> None:
        if settings is None or services is None or services.user_authorization is None:
            await callback.answer()
            return
        user_id = await _resolve_user(callback.from_user, services)
        try:
            status = await services.user_authorization.refresh_if_needed(user_id=user_id)
        except ReauthorizationRequired:
            status = await services.user_authorization.status(user_id=user_id)
            await _edit_callback(
                callback,
                render_reauthorization_required(),
                account_keyboard(status, can_authorize=_can_authorize(settings, services)),
            )
            return
        except UserAuthorizationChanged:
            await _edit_callback(
                callback,
                render_authorization_changed(),
                account_result_keyboard(),
            )
            return
        except (GitHubAuthError, UserAuthorizationError):
            await _edit_callback(
                callback,
                render_authorization_error(),
                account_result_keyboard(),
            )
            return
        await _edit_callback(
            callback,
            render_account(status),
            account_keyboard(status, can_authorize=_can_authorize(settings, services)),
        )

    @router.callback_query(F.data == callbacks.ACCOUNT_AUTHORIZE)
    async def account_authorize(callback: CallbackQuery) -> None:
        if not _can_authorize(settings, services):
            await _edit_callback(
                callback,
                render_authorization_error(),
                account_result_keyboard(),
            )
            return
        assert settings is not None
        assert settings.public_base_url is not None
        assert services is not None
        assert services.github_connection is not None
        user_id = await _resolve_user(callback.from_user, services)
        await _cancel_disconnect_on_navigation(services, user_id)
        try:
            redirect = await services.github_connection.begin_user_authorization(
                user_id=user_id,
                redirect_uri=_oauth_callback_url(settings),
            )
        except (GitHubAuthError, ValueError):
            await _edit_callback(
                callback,
                render_authorization_error(),
                account_result_keyboard(),
            )
            return
        await _edit_callback(
            callback,
            render_authorization_ready(),
            authorization_ready_keyboard(redirect.url),
        )

    @router.callback_query(F.data == callbacks.ACCOUNT_DISCONNECT_BEGIN)
    async def account_disconnect_begin(callback: CallbackQuery) -> None:
        if services is None or services.user_authorization is None:
            await callback.answer()
            return
        user_id = await _resolve_user(callback.from_user, services)
        try:
            request = await services.user_authorization.begin_disconnect(user_id=user_id)
        except UserAuthorizationError:
            await _edit_callback(
                callback,
                render_authorization_error(),
                account_result_keyboard(),
            )
            return
        if request is None:
            await _edit_callback(
                callback,
                render_disconnect_result(DisconnectResult(DisconnectState.INVALID)),
                account_result_keyboard(),
            )
            return
        await _edit_callback(
            callback,
            render_disconnect_confirmation(request),
            disconnect_confirmation_keyboard(request.token),
        )

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:account:disconnect:yes:"))
    async def account_disconnect_confirm(callback: CallbackQuery) -> None:
        if services is None or services.user_authorization is None or callback.data is None:
            await callback.answer()
            return
        token = callbacks.parse_account_disconnect_confirm(callback.data)
        if token is None:
            await callback.answer("التأكيد غير صالح", show_alert=True)
            return
        user_id = await _resolve_user(callback.from_user, services)
        try:
            result = await services.user_authorization.confirm_disconnect(
                user_id=user_id,
                token=token,
            )
        except UserAuthorizationError:
            await _edit_callback(
                callback,
                render_authorization_error(),
                account_result_keyboard(),
            )
            return
        await _edit_callback(
            callback,
            render_disconnect_result(result),
            account_result_keyboard(),
        )

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:account:disconnect:no:"))
    async def account_disconnect_cancel(callback: CallbackQuery) -> None:
        if settings is None or services is None or services.user_authorization is None:
            await callback.answer()
            return
        if callback.data is None:
            await callback.answer()
            return
        token = callbacks.parse_account_disconnect_cancel(callback.data)
        if token is None:
            await callback.answer("الإلغاء غير صالح", show_alert=True)
            return
        user_id = await _resolve_user(callback.from_user, services)
        await services.user_authorization.cancel_disconnect(user_id=user_id, token=token)
        await _show_account_callback(callback, settings, services, user_id=user_id)

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:repos:list:"))
    async def repositories(callback: CallbackQuery) -> None:
        if services is None or services.repository_read is None or callback.data is None:
            await callback.answer()
            return
        parsed = callbacks.parse_repository_list(callback.data)
        if parsed is None:
            await callback.answer("الزر غير صالح", show_alert=True)
            return
        repository_filter, page = parsed
        user_id = await _resolve_user(callback.from_user, services)
        try:
            result = await services.repository_read.list_repositories(
                user_id=user_id,
                page=page,
                repository_filter=repository_filter,
            )
        except GitHubGatewayError as exc:
            await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
            return
        await _edit_callback(
            callback,
            render_repository_list(result),
            repository_list_keyboard(result),
        )

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:repos:filters:"))
    async def repository_filters(callback: CallbackQuery) -> None:
        if callback.data is None:
            await callback.answer()
            return
        parsed = callbacks.parse_repository_filters(callback.data)
        if parsed is None:
            await callback.answer("الزر غير صالح", show_alert=True)
            return
        repository_filter, page = parsed
        await _edit_callback(
            callback,
            render_filter_screen(repository_filter),
            repository_filters_keyboard(repository_filter, page),
        )

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:repos:filter:"))
    async def apply_repository_filter(callback: CallbackQuery) -> None:
        if services is None or services.repository_read is None or callback.data is None:
            await callback.answer()
            return
        repository_filter = callbacks.parse_repository_filter(callback.data)
        if repository_filter is None:
            await callback.answer("التصفية غير صالحة", show_alert=True)
            return
        user_id = await _resolve_user(callback.from_user, services)
        try:
            result = await services.repository_read.list_repositories(
                user_id=user_id,
                page=1,
                repository_filter=repository_filter,
            )
        except GitHubGatewayError as exc:
            await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
            return
        await _edit_callback(
            callback,
            render_repository_list(result),
            repository_list_keyboard(result),
        )

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:repo:open:"))
    async def repository_detail(callback: CallbackQuery) -> None:
        if services is None or services.repository_read is None or callback.data is None:
            await callback.answer()
            return
        parsed = callbacks.parse_repository_open(callback.data)
        if parsed is None:
            await callback.answer("الاختيار غير صالح", show_alert=True)
            return
        repository_id, back_filter, back_page = parsed
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
            render_repository_detail(repository),
            repository_detail_keyboard(repository, back_filter=back_filter, back_page=back_page),
        )

    @router.callback_query(F.data.startswith(callbacks.PLACEHOLDER_PREFIX))
    async def placeholder(callback: CallbackQuery) -> None:
        await callback.answer(
            "هذه الميزة ضمن مرحلة لاحقة ولم يتم تنفيذ أي تغيير على GitHub.",
            show_alert=True,
        )

    return router


async def _show_home_message(
    message: Message,
    settings: Settings,
    services: RuntimeServices,
) -> None:
    if message.from_user is None:
        return
    user_id = await _resolve_user(message.from_user, services)
    await _cancel_disconnect_on_navigation(services, user_id)
    if services.repository_read is None:
        status = HomeStatus(False, None, 0, 0)
    else:
        try:
            status = await services.repository_read.home(user_id=user_id)
        except GitHubGatewayError as exc:
            await message.answer(render_github_error(exc), reply_markup=simple_back_home_keyboard())
            return
    await message.answer(
        render_home(status),
        reply_markup=home_keyboard(
            connected=status.connected,
            can_connect=_can_connect(settings, services),
        ),
    )


async def _show_home_callback(
    callback: CallbackQuery,
    settings: Settings,
    services: RuntimeServices,
) -> None:
    user_id = await _resolve_user(callback.from_user, services)
    await _cancel_disconnect_on_navigation(services, user_id)
    if services.repository_read is None:
        status = HomeStatus(False, None, 0, 0)
    else:
        try:
            status = await services.repository_read.home(user_id=user_id)
        except GitHubGatewayError as exc:
            await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
            return
    await _edit_callback(
        callback,
        render_home(status),
        home_keyboard(
            connected=status.connected,
            can_connect=_can_connect(settings, services),
        ),
    )


async def _show_account_callback(
    callback: CallbackQuery,
    settings: Settings,
    services: RuntimeServices,
    *,
    user_id: int | None = None,
) -> None:
    if services.user_authorization is None:
        status = UserAuthorizationStatus(False, None, None, None, None, False, 0)
    else:
        resolved_user_id = user_id or await _resolve_user(callback.from_user, services)
        try:
            status = await services.user_authorization.status(user_id=resolved_user_id)
        except UserAuthorizationError:
            await _edit_callback(
                callback,
                render_authorization_error(),
                account_result_keyboard(),
            )
            return
    await _edit_callback(
        callback,
        render_account(status),
        account_keyboard(status, can_authorize=_can_authorize(settings, services)),
    )


async def _cancel_disconnect_on_navigation(services: RuntimeServices, user_id: int) -> None:
    if services.user_authorization is not None:
        await services.user_authorization.cancel_pending_disconnects(user_id=user_id)


async def _resolve_user(user: TelegramUser, services: RuntimeServices) -> int:
    resolved = await services.identity.resolve(
        telegram_user_id=user.id,
        username=user.username,
        display_name=user.full_name,
    )
    return resolved.user_id


async def _edit_callback(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=reply_markup)


def _can_connect(settings: Settings, services: RuntimeServices | None) -> bool:
    return (
        settings.github_auth_configured
        and settings.public_base_url is not None
        and services is not None
        and services.github_connection is not None
    )


def _can_authorize(settings: Settings | None, services: RuntimeServices | None) -> bool:
    return (
        settings is not None
        and settings.github_auth_configured
        and settings.public_base_url is not None
        and services is not None
        and services.github_connection is not None
        and services.user_authorization is not None
    )


def _oauth_callback_url(settings: Settings) -> str:
    if settings.public_base_url is None:
        raise ValueError("public base URL is required")
    return f"{str(settings.public_base_url).rstrip('/')}{GITHUB_OAUTH_CALLBACK_PATH}"
