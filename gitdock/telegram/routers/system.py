"""Telegram home/repository router for the owner-first P2.3 experience."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, User as TelegramUser

from gitdock.core.config import Settings
from gitdock.github.errors import GitHubGatewayError
from gitdock.services.repositories import HomeStatus, RepositoryFilter, RepositorySelectionError
from gitdock.services.runtime import RuntimeServices
from gitdock.telegram import callbacks
from gitdock.telegram.keyboards.repositories import (
    connection_ready_keyboard,
    home_keyboard,
    repository_detail_keyboard,
    repository_filters_keyboard,
    repository_list_keyboard,
    simple_back_home_keyboard,
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
    async def start(message: Message) -> None:
        if settings is None or services is None:
            await message.answer("🐙 GitDock\n\nتم تشغيل الأساس التقني للبوت.")
            return
        await _show_home_message(message, settings, services)

    @router.callback_query(F.data.in_({callbacks.HOME_OPEN, callbacks.HOME_REFRESH}))
    async def home(callback: CallbackQuery) -> None:
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
        redirect = await services.github_connection.begin_installation(user_id=user_id)
        await _edit_callback(
            callback,
            render_connection_ready(),
            connection_ready_keyboard(redirect.url),
        )

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
            repository_detail_keyboard(
                repository, back_filter=back_filter, back_page=back_page
            ),
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
