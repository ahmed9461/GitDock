"""Telegram flows for P4.3 clone/setup/run command generation."""

from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from gitdock.github.errors import GitHubGatewayError
from gitdock.services.file_types import FileSelectionError
from gitdock.services.repositories import RepositorySelectionError
from gitdock.services.run_assistant import RunAssistantUnavailable
from gitdock.services.runtime import RuntimeServices
from gitdock.services.search import SearchSelectionError, SearchValidationError
from gitdock.telegram import run_callbacks
from gitdock.telegram.keyboards.run_assistant import repository_os_keyboard, search_os_keyboard
from gitdock.telegram.keyboards.search import search_prompt_keyboard
from gitdock.telegram.renderers.repositories import render_github_error, render_stale_selection
from gitdock.telegram.renderers.run_assistant import render_command_plan, render_os_prompt
from gitdock.telegram.renderers.search import render_search_expired

_SEARCH_SESSION_KEY = "repository_search_session"
_SEARCH_RESULTS_KEY = "repository_search_results"


def create_run_assistant_router(services: RuntimeServices | None) -> Router:
    router = Router(name="run-assistant")

    @router.callback_query(F.data.startswith(f"{run_callbacks.ROOT}:r:"))
    async def repository_run(callback: CallbackQuery) -> None:
        if callback.data is None or services is None:
            await callback.answer()
            return
        parsed = run_callbacks.parse_repository(callback.data)
        if parsed is None:
            await callback.answer("الاختيار غير صالح", show_alert=True)
            return
        target_os, repository_id, back_filter, back_page = parsed
        if services.repository_read is None or services.run_assistant is None:
            await callback.answer("الميزة غير متاحة دون ربط GitHub", show_alert=True)
            return

        user = await services.identity.resolve(
            telegram_user_id=callback.from_user.id,
            username=callback.from_user.username,
            display_name=callback.from_user.full_name,
        )

        if target_os is None:
            try:
                repository = await services.repository_read.repository_detail(
                    user_id=user.user_id,
                    github_repository_id=repository_id,
                )
            except RepositorySelectionError:
                await _edit(
                    callback,
                    render_stale_selection(),
                    repository_os_keyboard(
                        repository_id=repository_id,
                        repository_filter=back_filter,
                        page=back_page,
                    ),
                )
                return
            except GitHubGatewayError as exc:
                await _edit(
                    callback,
                    render_github_error(exc),
                    repository_os_keyboard(
                        repository_id=repository_id,
                        repository_filter=back_filter,
                        page=back_page,
                    ),
                )
                return
            await _edit(
                callback,
                render_os_prompt(repository.full_name),
                repository_os_keyboard(
                    repository_id=repository_id,
                    repository_filter=back_filter,
                    page=back_page,
                ),
            )
            return

        try:
            plan = await services.run_assistant.plan_installed(
                user_id=user.user_id,
                github_repository_id=repository_id,
                target_os=target_os,
            )
        except (FileSelectionError, RunAssistantUnavailable):
            await _edit(
                callback,
                render_stale_selection(),
                repository_os_keyboard(
                    repository_id=repository_id,
                    repository_filter=back_filter,
                    page=back_page,
                ),
            )
            return
        except GitHubGatewayError as exc:
            await _edit(
                callback,
                render_github_error(exc),
                repository_os_keyboard(
                    repository_id=repository_id,
                    repository_filter=back_filter,
                    page=back_page,
                ),
            )
            return

        await _edit(
            callback,
            render_command_plan(plan),
            repository_os_keyboard(
                repository_id=repository_id,
                repository_filter=back_filter,
                page=back_page,
                selected=target_os,
            ),
            html=True,
        )

    @router.callback_query(F.data.startswith(f"{run_callbacks.ROOT}:s:"))
    async def public_search_run(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.data is None or services is None or services.run_assistant is None:
            await callback.answer()
            return
        parsed = run_callbacks.parse_search(callback.data)
        if parsed is None:
            await callback.answer("الاختيار غير صالح", show_alert=True)
            return
        target_os, session_id, page, repository_id = parsed
        target = await _search_target(state, session_id, repository_id)
        if target is None:
            await _show_search_expired(callback)
            return
        owner_login, repository_name = target
        try:
            repository = await services.repository_search.detail(
                owner_login=owner_login,
                name=repository_name,
            )
        except (SearchValidationError, SearchSelectionError):
            await _show_search_expired(callback)
            return
        except GitHubGatewayError as exc:
            await _edit(
                callback,
                render_github_error(exc),
                search_os_keyboard(
                    session_id=session_id,
                    page=page,
                    repository_id=repository_id,
                ),
            )
            return
        if repository.github_repository_id != repository_id:
            await _show_search_expired(callback)
            return

        if target_os is None:
            await _edit(
                callback,
                render_os_prompt(repository.full_name),
                search_os_keyboard(
                    session_id=session_id,
                    page=page,
                    repository_id=repository_id,
                ),
            )
            return

        try:
            plan = await services.run_assistant.plan_public(
                repository=repository,
                target_os=target_os,
            )
        except GitHubGatewayError as exc:
            await _edit(
                callback,
                render_github_error(exc),
                search_os_keyboard(
                    session_id=session_id,
                    page=page,
                    repository_id=repository_id,
                ),
            )
            return
        await _edit(
            callback,
            render_command_plan(plan),
            search_os_keyboard(
                session_id=session_id,
                page=page,
                repository_id=repository_id,
                selected=target_os,
            ),
            html=True,
        )

    return router


async def _search_target(
    state: FSMContext,
    session_id: str,
    repository_id: int,
) -> tuple[str, str] | None:
    data: dict[str, Any] = await state.get_data()
    if data.get(_SEARCH_SESSION_KEY) != session_id:
        return None
    results = data.get(_SEARCH_RESULTS_KEY)
    if not isinstance(results, dict):
        return None
    target = results.get(str(repository_id))
    if not isinstance(target, dict):
        return None
    owner = target.get("owner")
    name = target.get("name")
    if not isinstance(owner, str) or not isinstance(name, str):
        return None
    return owner, name


async def _show_search_expired(callback: CallbackQuery) -> None:
    await _edit(callback, render_search_expired(), search_prompt_keyboard())


async def _edit(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    *,
    html: bool = False,
) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode="HTML" if html else None,
        )
