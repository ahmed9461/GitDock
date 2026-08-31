"""Telegram flow for Tier 0 public GitHub repository search."""

from __future__ import annotations

import secrets
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from gitdock.core.constants import SEARCH_SESSION_ID_BYTES
from gitdock.github.errors import GitHubGatewayError
from gitdock.services.runtime import RuntimeServices
from gitdock.services.search import (
    SearchCriteria,
    SearchSelectionError,
    SearchSort,
    SearchValidationError,
    deserialize_criteria,
    normalize_min_stars_input,
    normalize_owner_scope_input,
    normalize_topic_input,
    serialize_criteria,
)
from gitdock.telegram import callbacks
from gitdock.telegram.keyboards.repositories import simple_back_home_keyboard
from gitdock.telegram.keyboards.search import (
    filter_input_keyboard,
    search_detail_keyboard,
    search_filters_keyboard,
    search_prompt_keyboard,
    search_results_keyboard,
)
from gitdock.telegram.renderers.repositories import render_github_error
from gitdock.telegram.renderers.search import (
    render_min_stars_prompt,
    render_owner_prompt,
    render_search_detail,
    render_search_expired,
    render_search_filters,
    render_search_prompt,
    render_search_results,
    render_search_validation_error,
    render_topic_prompt,
)
from gitdock.telegram.states.search import RepositorySearchFlow

_SESSION_KEY = "repository_search_session"
_CRITERIA_KEY = "repository_search_criteria"
_RESULTS_KEY = "repository_search_results"
_FILTER_BACK_PAGE_KEY = "repository_search_filter_back_page"


def create_search_router(services: RuntimeServices | None = None) -> Router:
    router = Router(name="repository-search")

    @router.message(Command("search"))
    async def search_command(message: Message, state: FSMContext) -> None:
        if services is None:
            return
        await _start_search_message(message, state)

    @router.callback_query(F.data == callbacks.SEARCH_BEGIN)
    async def search_begin(callback: CallbackQuery, state: FSMContext) -> None:
        if services is None:
            await callback.answer()
            return
        session_id = _new_session_id()
        await state.set_state(RepositorySearchFlow.waiting_query)
        await state.set_data({_SESSION_KEY: session_id})
        await _edit_callback(callback, render_search_prompt(), search_prompt_keyboard())

    @router.message(RepositorySearchFlow.waiting_query, F.text)
    async def search_query(message: Message, state: FSMContext) -> None:
        if services is None or message.text is None:
            return
        data = await state.get_data()
        session_id = _session_from_data(data)
        if session_id is None:
            await state.clear()
            await message.answer(render_search_expired(), reply_markup=search_prompt_keyboard())
            return
        criteria = SearchCriteria(query=message.text)
        try:
            result = await services.repository_search.search(criteria, page=1)
        except SearchValidationError:
            await message.answer(
                render_search_validation_error("اكتب عبارة أقصر وواضحة ثم حاول من جديد."),
                reply_markup=search_prompt_keyboard(),
            )
            return
        except GitHubGatewayError as exc:
            await message.answer(render_github_error(exc), reply_markup=simple_back_home_keyboard())
            return
        await state.set_state(RepositorySearchFlow.active)
        await state.update_data(
            {
                _CRITERIA_KEY: serialize_criteria(result.criteria),
                _FILTER_BACK_PAGE_KEY: 1,
                _RESULTS_KEY: _result_context(result.items),
            }
        )
        await message.answer(
            render_search_results(result),
            reply_markup=search_results_keyboard(session_id, result),
        )

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:search:list:"))
    async def search_page(callback: CallbackQuery, state: FSMContext) -> None:
        if services is None or callback.data is None:
            await callback.answer()
            return
        parsed = callbacks.parse_search_results(callback.data)
        if parsed is None:
            await callback.answer("الزر غير صالح", show_alert=True)
            return
        session_id, page = parsed
        await _show_results_callback(callback, state, services, session_id, page)

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:search:sort:"))
    async def search_sort(callback: CallbackQuery, state: FSMContext) -> None:
        if services is None or callback.data is None:
            await callback.answer()
            return
        parsed = callbacks.parse_search_sort(callback.data)
        if parsed is None:
            await callback.answer("الزر غير صالح", show_alert=True)
            return
        session_id, sort = parsed
        criteria = await _criteria_for_session(state, session_id)
        if criteria is None:
            await _show_expired(callback)
            return
        criteria = criteria.with_sort(sort)
        await state.update_data({_CRITERIA_KEY: serialize_criteria(criteria)})
        await _show_results_callback(callback, state, services, session_id, 1)

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:search:filters:"))
    async def search_filters(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.data is None:
            await callback.answer()
            return
        parsed = callbacks.parse_search_filters(callback.data)
        if parsed is None:
            await callback.answer("الزر غير صالح", show_alert=True)
            return
        session_id, page = parsed
        criteria = await _criteria_for_session(state, session_id)
        if criteria is None:
            await _show_expired(callback)
            return
        await state.set_state(RepositorySearchFlow.active)
        await state.update_data({_FILTER_BACK_PAGE_KEY: page})
        await _edit_callback(
            callback,
            render_search_filters(criteria),
            search_filters_keyboard(session_id, criteria, back_page=page),
        )

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:search:lang:"))
    async def search_language(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.data is None:
            await callback.answer()
            return
        parsed = callbacks.parse_search_language(callback.data)
        if parsed is None:
            await callback.answer("اللغة غير صالحة", show_alert=True)
            return
        session_id, language = parsed
        criteria = await _criteria_for_session(state, session_id)
        if criteria is None:
            await _show_expired(callback)
            return
        criteria = criteria.with_language(language)
        await state.set_state(RepositorySearchFlow.active)
        await state.update_data({_CRITERIA_KEY: serialize_criteria(criteria)})
        back_page = await _filter_back_page(state)
        await _edit_callback(
            callback,
            render_search_filters(criteria),
            search_filters_keyboard(session_id, criteria, back_page=back_page),
        )

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:search:flt:"))
    async def search_filter_action(callback: CallbackQuery, state: FSMContext) -> None:
        if services is None or callback.data is None:
            await callback.answer()
            return
        parsed = callbacks.parse_search_filter_action(callback.data)
        if parsed is None:
            await callback.answer("الزر غير صالح", show_alert=True)
            return
        session_id, action = parsed
        criteria = await _criteria_for_session(state, session_id)
        if criteria is None:
            await _show_expired(callback)
            return
        back_page = await _filter_back_page(state)

        if action == "stars":
            await state.set_state(RepositorySearchFlow.waiting_min_stars)
            await _edit_callback(
                callback,
                render_min_stars_prompt(),
                filter_input_keyboard(session_id, back_page),
            )
            return
        if action == "owner":
            await state.set_state(RepositorySearchFlow.waiting_owner)
            await _edit_callback(
                callback,
                render_owner_prompt(),
                filter_input_keyboard(session_id, back_page),
            )
            return
        if action == "topic":
            await state.set_state(RepositorySearchFlow.waiting_topic)
            await _edit_callback(
                callback,
                render_topic_prompt(),
                filter_input_keyboard(session_id, back_page),
            )
            return
        if action == "arch":
            criteria = criteria.with_include_archived(not criteria.include_archived)
            await state.update_data({_CRITERIA_KEY: serialize_criteria(criteria)})
            await _edit_callback(
                callback,
                render_search_filters(criteria),
                search_filters_keyboard(session_id, criteria, back_page=back_page),
            )
            return
        if action == "clear":
            criteria = SearchCriteria(query=criteria.query, sort=criteria.sort)
            await state.update_data({_CRITERIA_KEY: serialize_criteria(criteria)})
            await _edit_callback(
                callback,
                render_search_filters(criteria),
                search_filters_keyboard(session_id, criteria, back_page=back_page),
            )
            return
        if action == "apply":
            await state.set_state(RepositorySearchFlow.active)
            await _show_results_callback(callback, state, services, session_id, 1)
            return

    @router.message(RepositorySearchFlow.waiting_min_stars, F.text)
    async def search_min_stars(message: Message, state: FSMContext) -> None:
        if message.text is None:
            return
        await _apply_text_filter(message, state, "stars", message.text)

    @router.message(RepositorySearchFlow.waiting_owner, F.text)
    async def search_owner(message: Message, state: FSMContext) -> None:
        if message.text is None:
            return
        await _apply_text_filter(message, state, "owner", message.text)

    @router.message(RepositorySearchFlow.waiting_topic, F.text)
    async def search_topic(message: Message, state: FSMContext) -> None:
        if message.text is None:
            return
        await _apply_text_filter(message, state, "topic", message.text)

    @router.callback_query(F.data.startswith(f"{callbacks.PREFIX}:search:open:"))
    async def search_detail(callback: CallbackQuery, state: FSMContext) -> None:
        if services is None or callback.data is None:
            await callback.answer()
            return
        parsed = callbacks.parse_search_open(callback.data)
        if parsed is None:
            await callback.answer("الاختيار غير صالح", show_alert=True)
            return
        session_id, page, repository_id = parsed
        if await _criteria_for_session(state, session_id) is None:
            await _show_expired(callback)
            return
        target = await _search_result_target(state, repository_id)
        if target is None:
            await _show_expired(callback)
            return
        owner_login, name = target
        try:
            repository = await services.repository_search.detail(
                owner_login=owner_login,
                name=name,
            )
        except (SearchValidationError, SearchSelectionError):
            await _show_expired(callback)
            return
        except GitHubGatewayError as exc:
            await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
            return
        if repository.github_repository_id != repository_id:
            await _show_expired(callback)
            return
        await _edit_callback(
            callback,
            render_search_detail(repository),
            search_detail_keyboard(session_id, page, repository),
        )

    return router


async def _start_search_message(message: Message, state: FSMContext) -> None:
    session_id = _new_session_id()
    await state.set_state(RepositorySearchFlow.waiting_query)
    await state.set_data({_SESSION_KEY: session_id})
    await message.answer(render_search_prompt(), reply_markup=search_prompt_keyboard())


async def _show_results_callback(
    callback: CallbackQuery,
    state: FSMContext,
    services: RuntimeServices,
    session_id: str,
    page: int,
) -> None:
    criteria = await _criteria_for_session(state, session_id)
    if criteria is None:
        await _show_expired(callback)
        return
    try:
        result = await services.repository_search.search(criteria, page=page)
    except SearchValidationError:
        await _show_expired(callback)
        return
    except GitHubGatewayError as exc:
        await _edit_callback(callback, render_github_error(exc), simple_back_home_keyboard())
        return
    await state.set_state(RepositorySearchFlow.active)
    await state.update_data(
        {
            _CRITERIA_KEY: serialize_criteria(result.criteria),
            _RESULTS_KEY: _result_context(result.items),
        }
    )
    await _edit_callback(
        callback,
        render_search_results(result),
        search_results_keyboard(session_id, result),
    )


async def _apply_text_filter(
    message: Message,
    state: FSMContext,
    kind: str,
    raw_value: str,
) -> None:
    data = await state.get_data()
    session_id = _session_from_data(data)
    criteria = _criteria_from_data(data)
    if session_id is None or criteria is None:
        await state.clear()
        await message.answer(render_search_expired(), reply_markup=search_prompt_keyboard())
        return
    try:
        if kind == "stars":
            minimum = normalize_min_stars_input(raw_value)
            criteria = criteria.with_min_stars(None if minimum == 0 else minimum)
        elif kind == "owner":
            criteria = criteria.with_owner_scope(
                None if raw_value.strip() == "-" else normalize_owner_scope_input(raw_value)
            )
        elif kind == "topic":
            criteria = criteria.with_topic(
                None if raw_value.strip() == "-" else normalize_topic_input(raw_value)
            )
        else:
            raise SearchValidationError("unknown filter")
        serialized = serialize_criteria(criteria)
    except SearchValidationError:
        await message.answer(
            render_search_validation_error(_filter_validation_message(kind)),
            reply_markup=filter_input_keyboard(session_id, await _filter_back_page(state)),
        )
        return

    await state.set_state(RepositorySearchFlow.active)
    await state.update_data({_CRITERIA_KEY: serialized})
    back_page = await _filter_back_page(state)
    await message.answer(
        render_search_filters(criteria),
        reply_markup=search_filters_keyboard(session_id, criteria, back_page=back_page),
    )


async def _criteria_for_session(state: FSMContext, session_id: str) -> SearchCriteria | None:
    data = await state.get_data()
    if _session_from_data(data) != session_id:
        return None
    return _criteria_from_data(data)


def _criteria_from_data(data: dict[str, Any]) -> SearchCriteria | None:
    try:
        return deserialize_criteria(data.get(_CRITERIA_KEY))
    except SearchValidationError:
        return None


def _session_from_data(data: dict[str, Any]) -> str | None:
    value = data.get(_SESSION_KEY)
    return value if isinstance(value, str) else None


async def _search_result_target(
    state: FSMContext,
    repository_id: int,
) -> tuple[str, str] | None:
    data = await state.get_data()
    results = data.get(_RESULTS_KEY)
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


async def _filter_back_page(state: FSMContext) -> int:
    data = await state.get_data()
    value = data.get(_FILTER_BACK_PAGE_KEY, 1)
    return value if isinstance(value, int) and value > 0 else 1


def _result_context(items: tuple[Any, ...]) -> dict[str, dict[str, str]]:
    context: dict[str, dict[str, str]] = {}
    for item in items:
        repository_id = getattr(item, "github_repository_id", None)
        owner = getattr(item, "owner_login", None)
        name = getattr(item, "name", None)
        if isinstance(repository_id, int) and isinstance(owner, str) and isinstance(name, str):
            context[str(repository_id)] = {"owner": owner, "name": name}
    return context


def _new_session_id() -> str:
    return secrets.token_urlsafe(SEARCH_SESSION_ID_BYTES)


async def _show_expired(callback: CallbackQuery) -> None:
    await _edit_callback(callback, render_search_expired(), search_prompt_keyboard())


async def _edit_callback(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=reply_markup)


def _filter_validation_message(kind: str) -> str:
    if kind == "stars":
        return "أرسل رقمًا صحيحًا غير سالب، أو 0 لإزالة الحد."
    if kind == "owner":
        return "استخدم user:USERNAME أو org:ORGNAME، أو أرسل - للإزالة."
    if kind == "topic":
        return "استخدم حروفًا إنجليزية صغيرة وأرقامًا وشرطة - فقط، أو أرسل - للإزالة."
    return "تحقق من القيمة وحاول مجددًا."
