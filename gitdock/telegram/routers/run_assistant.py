"""Telegram flow for installed-repository P4.3 command generation."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from gitdock.github.errors import GitHubGatewayError
from gitdock.services.file_types import FileSelectionError
from gitdock.services.repositories import RepositorySelectionError
from gitdock.services.run_assistant import RunAssistantUnavailable
from gitdock.services.runtime import RuntimeServices
from gitdock.telegram import run_callbacks
from gitdock.telegram.keyboards.run_assistant import repository_os_keyboard
from gitdock.telegram.renderers.repositories import render_github_error, render_stale_selection
from gitdock.telegram.renderers.run_assistant import render_command_plan, render_os_prompt


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

    return router


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
