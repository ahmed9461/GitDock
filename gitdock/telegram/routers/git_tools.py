"""Telegram router for P4.2 branch/commit tools."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from gitdock.github.errors import GitHubGatewayError
from gitdock.services.repositories import RepositoryFilter
from gitdock.services.runtime import RuntimeServices
from gitdock.telegram import git_callbacks
from gitdock.telegram.keyboards.git_tools import (
    branch_confirmation_keyboard,
    branches_keyboard,
    commit_detail_keyboard,
    commits_keyboard,
    result_keyboard,
)
from gitdock.telegram.renderers.git_tools import (
    render_branch_outcome,
    render_branch_plan,
    render_branches,
    render_commit,
    render_commits,
    render_compare,
)
from gitdock.telegram.states.git_tools import GitToolsStates


def create_git_tools_router(services: RuntimeServices | None) -> Router:
    router = Router(name="git-tools")

    @router.callback_query(F.data.startswith(f"{git_callbacks.ROOT}:b:open:"))
    async def branches_open(callback: CallbackQuery, state: FSMContext) -> None:
        parsed = _parse_open(callback, "b")
        if parsed is None or services is None or services.git_tools is None:
            return
        repository_id, back_filter, back_page = parsed
        await state.set_data(_context(repository_id, back_filter, back_page))
        await _show_branches(callback, state, services, 1)

    @router.callback_query(F.data.startswith(f"{git_callbacks.ROOT}:c:open:"))
    async def commits_open(callback: CallbackQuery, state: FSMContext) -> None:
        parsed = _parse_open(callback, "c")
        if parsed is None or services is None or services.git_tools is None:
            return
        repository_id, back_filter, back_page = parsed
        await state.set_data(_context(repository_id, back_filter, back_page))
        await _show_commits(callback, state, services, 1, None)

    @router.callback_query(F.data.startswith(f"{git_callbacks.ROOT}:b:p:"))
    async def branches_page(callback: CallbackQuery, state: FSMContext) -> None:
        if services is None or services.git_tools is None or callback.data is None:
            return
        page = git_callbacks.parse_page(callback.data, "b")
        if page is None:
            await callback.answer("الصفحة غير صالحة", show_alert=True)
            return
        await _show_branches(callback, state, services, page)

    @router.callback_query(F.data.startswith(f"{git_callbacks.ROOT}:c:p:"))
    async def commits_page(callback: CallbackQuery, state: FSMContext) -> None:
        if services is None or services.git_tools is None or callback.data is None:
            return
        page = git_callbacks.parse_page(callback.data, "c")
        if page is None:
            await callback.answer("الصفحة غير صالحة", show_alert=True)
            return
        data = await state.get_data()
        ref = data.get("git_commit_ref")
        await _show_commits(callback, state, services, page, ref if isinstance(ref, str) else None)

    @router.callback_query(F.data.startswith(f"{git_callbacks.ROOT}:c:i:"))
    async def commit_detail(callback: CallbackQuery, state: FSMContext) -> None:
        if services is None or services.git_tools is None or callback.data is None:
            return
        parsed = git_callbacks.parse_item(callback.data, "c")
        data = await state.get_data()
        repository_id = _positive(data.get("git_repository_id"))
        commits = data.get("git_commits")
        if parsed is None or repository_id is None or not isinstance(commits, list):
            await callback.answer("انتهت جلسة الـCommits", show_alert=True)
            return
        _, index = parsed
        if not 0 <= index < len(commits) or not isinstance(commits[index], str):
            await callback.answer("الـCommit غير صالح", show_alert=True)
            return
        try:
            view = await services.git_tools.commit_detail(
                user_id=await _user_id(callback, services),
                github_repository_id=repository_id,
                ref=commits[index],
            )
        except (GitHubGatewayError, ValueError):
            await callback.answer("تعذر تحميل تفاصيل الـCommit", show_alert=True)
            return
        await _edit(
            callback, render_commit(view.commit), commit_detail_keyboard(view.commit.html_url)
        )

    @router.callback_query(F.data == git_callbacks.BRANCH_SEARCH_BEGIN)
    async def search_begin(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(GitToolsStates.branch_search)
        await _prompt(callback, "🔎 اكتب جزءًا من اسم الفرع للبحث.")

    @router.message(GitToolsStates.branch_search)
    async def search_input(message: Message, state: FSMContext) -> None:
        if services is None or services.git_tools is None or message.from_user is None:
            return
        query = (message.text or "").strip()
        data = await state.get_data()
        repository_id = _positive(data.get("git_repository_id"))
        if not query or repository_id is None:
            await message.answer("نص البحث غير صالح أو انتهت الجلسة.")
            return
        user_id = await _message_user_id(message, services)
        try:
            view = await services.git_tools.list_branches(
                user_id=user_id, github_repository_id=repository_id, query=query
            )
        except (GitHubGatewayError, ValueError):
            await message.answer("تعذر البحث في الفروع.")
            return
        await state.update_data(git_branch_query=query)
        await state.set_state(None)
        back_filter, back_page = _navigation(data)
        await message.answer(
            render_branches(view, query=query),
            reply_markup=branches_keyboard(
                view.branches,
                page=1,
                repository_id=repository_id,
                back_filter=back_filter,
                back_page=back_page,
            ),
        )

    @router.callback_query(F.data == git_callbacks.COMMIT_REF_BEGIN)
    async def ref_begin(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(GitToolsStates.commit_ref)
        await _prompt(callback, "🌿 اكتب branch أو tag أو SHA لعرض الـCommits منه.")

    @router.message(GitToolsStates.commit_ref)
    async def ref_input(message: Message, state: FSMContext) -> None:
        if services is None or services.git_tools is None or message.from_user is None:
            return
        ref = (message.text or "").strip()
        data = await state.get_data()
        repository_id = _positive(data.get("git_repository_id"))
        if not ref or repository_id is None:
            await message.answer("المرجع غير صالح أو انتهت الجلسة.")
            return
        user_id = await _message_user_id(message, services)
        try:
            view = await services.git_tools.recent_commits(
                user_id=user_id, github_repository_id=repository_id, ref=ref
            )
        except (GitHubGatewayError, ValueError):
            await message.answer("تعذر العثور على هذا ref في GitHub.")
            return
        await state.update_data(
            git_commit_ref=view.ref, git_commits=[item.sha for item in view.commits]
        )
        await state.set_state(None)
        back_filter, back_page = _navigation(data)
        await message.answer(
            render_commits(view),
            reply_markup=commits_keyboard(
                view.commits,
                page=1,
                repository_id=repository_id,
                back_filter=back_filter,
                back_page=back_page,
            ),
        )

    @router.callback_query(F.data == git_callbacks.BRANCH_CREATE_BEGIN)
    async def create_begin(callback: CallbackQuery, state: FSMContext) -> None:
        if _positive((await state.get_data()).get("git_repository_id")) is None:
            await callback.answer("انتهت جلسة المستودع", show_alert=True)
            return
        await state.set_state(GitToolsStates.branch_name)
        await _prompt(callback, "➕ اكتب اسم الفرع الجديد.")

    @router.message(GitToolsStates.branch_name)
    async def create_name(message: Message, state: FSMContext) -> None:
        name = (message.text or "").strip()
        if not name or len(name) > 255:
            await message.answer("اسم الفرع غير صالح.")
            return
        await state.update_data(git_new_branch=name)
        await state.set_state(GitToolsStates.branch_base)
        await message.answer("اكتب الـbase: branch/tag أو SHA حالي من GitHub.")

    @router.message(GitToolsStates.branch_base)
    async def create_base(message: Message, state: FSMContext) -> None:
        if services is None or services.git_tools is None or message.from_user is None:
            return
        base_ref = (message.text or "").strip()
        data = await state.get_data()
        repository_id = _positive(data.get("git_repository_id"))
        branch = data.get("git_new_branch")
        if repository_id is None or not isinstance(branch, str) or not base_ref:
            await message.answer("بيانات إنشاء الفرع غير مكتملة.")
            return
        try:
            plan = await services.git_tools.begin_create_branch(
                user_id=await _message_user_id(message, services),
                github_repository_id=repository_id,
                branch=branch,
                base_ref=base_ref,
            )
        except ValueError as exc:
            await message.answer(
                "الفرع موجود بالفعل." if "exists" in str(exc) else "اسم الفرع أو الـbase غير صالح."
            )
            return
        except GitHubGatewayError:
            await message.answer("تعذر التحقق من الـbase أو صلاحيات GitHub.")
            return
        await state.set_state(None)
        await message.answer(
            render_branch_plan(plan),
            reply_markup=branch_confirmation_keyboard(plan.confirmation_token),
        )

    @router.callback_query(F.data.startswith(f"{git_callbacks.ROOT}:bc:y:"))
    async def create_confirm(callback: CallbackQuery) -> None:
        if services is None or services.git_tools is None or callback.data is None:
            return
        token = git_callbacks.parse_confirmation(callback.data, "y")
        if token is None:
            await callback.answer("التأكيد غير صالح", show_alert=True)
            return
        try:
            outcome = await services.git_tools.confirm_create_branch(
                user_id=await _user_id(callback, services), token=token
            )
        except GitHubGatewayError:
            await callback.answer("تعذر التحقق من GitHub", show_alert=True)
            return
        await _edit(callback, render_branch_outcome(outcome), result_keyboard())

    @router.callback_query(F.data.startswith(f"{git_callbacks.ROOT}:bc:n:"))
    async def create_cancel(callback: CallbackQuery) -> None:
        if services is None or services.git_tools is None or callback.data is None:
            return
        token = git_callbacks.parse_confirmation(callback.data, "n")
        if token is None:
            await callback.answer("الإلغاء غير صالح", show_alert=True)
            return
        await services.git_tools.cancel_create_branch(
            user_id=await _user_id(callback, services), token=token
        )
        await _edit(
            callback, "تم إلغاء إنشاء الفرع. لم يتم إجراء أي تغيير على GitHub.", result_keyboard()
        )

    @router.callback_query(F.data == git_callbacks.COMPARE_BEGIN)
    async def compare_begin(callback: CallbackQuery, state: FSMContext) -> None:
        if _positive((await state.get_data()).get("git_repository_id")) is None:
            await callback.answer("انتهت جلسة المستودع", show_alert=True)
            return
        await state.set_state(GitToolsStates.compare_base)
        await _prompt(callback, "🔀 اكتب الـbase للمقارنة.")

    @router.message(GitToolsStates.compare_base)
    async def compare_base(message: Message, state: FSMContext) -> None:
        base = (message.text or "").strip()
        if not base:
            await message.answer("اكتب base صالحًا.")
            return
        await state.update_data(git_compare_base=base)
        await state.set_state(GitToolsStates.compare_head)
        await message.answer("اكتب الـhead للمقارنة.")

    @router.message(GitToolsStates.compare_head)
    async def compare_head(message: Message, state: FSMContext) -> None:
        if services is None or services.git_tools is None or message.from_user is None:
            return
        head = (message.text or "").strip()
        data = await state.get_data()
        base = data.get("git_compare_base")
        repository_id = _positive(data.get("git_repository_id"))
        if not head or not isinstance(base, str) or repository_id is None:
            await message.answer("بيانات المقارنة غير مكتملة.")
            return
        try:
            view = await services.git_tools.compare(
                user_id=await _message_user_id(message, services),
                github_repository_id=repository_id,
                base=base,
                head=head,
            )
        except (GitHubGatewayError, ValueError):
            await message.answer("تعذر مقارنة هذه المراجع في GitHub.")
            return
        await state.set_state(None)
        await message.answer(render_compare(view), reply_markup=result_keyboard())

    return router


async def _show_branches(
    callback: CallbackQuery, state: FSMContext, services: RuntimeServices, page: int
) -> None:
    data = await state.get_data()
    repository_id = _positive(data.get("git_repository_id"))
    if repository_id is None or services.git_tools is None:
        await callback.answer("انتهت جلسة الفروع", show_alert=True)
        return
    query = data.get("git_branch_query")
    try:
        view = await services.git_tools.list_branches(
            user_id=await _user_id(callback, services),
            github_repository_id=repository_id,
            query=query if isinstance(query, str) else None,
        )
    except (GitHubGatewayError, ValueError):
        await callback.answer("تعذر تحميل الفروع من GitHub", show_alert=True)
        return
    back_filter, back_page = _navigation(data)
    await _edit(
        callback,
        render_branches(view, query=query if isinstance(query, str) else None),
        branches_keyboard(
            view.branches,
            page=page,
            repository_id=repository_id,
            back_filter=back_filter,
            back_page=back_page,
        ),
    )


async def _show_commits(
    callback: CallbackQuery,
    state: FSMContext,
    services: RuntimeServices,
    page: int,
    ref: str | None,
) -> None:
    data = await state.get_data()
    repository_id = _positive(data.get("git_repository_id"))
    if repository_id is None or services.git_tools is None:
        await callback.answer("انتهت جلسة الـCommits", show_alert=True)
        return
    try:
        view = await services.git_tools.recent_commits(
            user_id=await _user_id(callback, services),
            github_repository_id=repository_id,
            ref=ref,
        )
    except (GitHubGatewayError, ValueError):
        await callback.answer("تعذر تحميل الـCommits من GitHub", show_alert=True)
        return
    await state.update_data(
        git_commit_ref=view.ref, git_commits=[item.sha for item in view.commits]
    )
    back_filter, back_page = _navigation(data)
    await _edit(
        callback,
        render_commits(view),
        commits_keyboard(
            view.commits,
            page=page,
            repository_id=repository_id,
            back_filter=back_filter,
            back_page=back_page,
        ),
    )


def _parse_open(callback: CallbackQuery, kind: str) -> tuple[int, RepositoryFilter, int] | None:
    if callback.data is None:
        return None
    return git_callbacks.parse_repo_open(callback.data, kind)


def _context(
    repository_id: int, repository_filter: RepositoryFilter, page: int
) -> dict[str, object]:
    return {
        "git_repository_id": repository_id,
        "git_back_filter": repository_filter.value,
        "git_back_page": page,
    }


async def _user_id(callback: CallbackQuery, services: RuntimeServices) -> int:
    user = await services.identity.resolve(
        telegram_user_id=callback.from_user.id,
        username=callback.from_user.username,
        display_name=callback.from_user.full_name,
    )
    return user.user_id


async def _message_user_id(message: Message, services: RuntimeServices) -> int:
    assert message.from_user is not None
    user = await services.identity.resolve(
        telegram_user_id=message.from_user.id,
        username=message.from_user.username,
        display_name=message.from_user.full_name,
    )
    return user.user_id


async def _prompt(callback: CallbackQuery, text: str) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text)


async def _edit(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=reply_markup)


def _positive(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _navigation(data: dict[str, object]) -> tuple[RepositoryFilter, int]:
    try:
        repository_filter = RepositoryFilter(str(data.get("git_back_filter")))
    except ValueError:
        repository_filter = RepositoryFilter.ALL
    return repository_filter, _positive(data.get("git_back_page")) or 1
