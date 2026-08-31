"""GitHub App setup and OAuth callback endpoints for the safe binding flow."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from gitdock.core.constants import GITHUB_OAUTH_CALLBACK_PATH, GITHUB_SETUP_CALLBACK_PATH
from gitdock.github.auth import GitHubAuthError
from gitdock.github.auth_state import InvalidAuthorizationState
from gitdock.github.binding import InstallationBindingError
from gitdock.github.connection import GitHubConnectionError

router = APIRouter()


@router.get(GITHUB_SETUP_CALLBACK_PATH)
async def github_setup_callback(
    request: Request,
    state: str = "",
    installation_id: int | None = None,
) -> RedirectResponse | HTMLResponse:
    service = request.app.state.runtime_services.github_connection
    settings = request.app.state.settings
    if service is None or settings.public_base_url is None:
        return _error_page("ربط GitHub غير مهيأ على الخادم.", status_code=503)
    if not state or installation_id is None or installation_id <= 0:
        return _error_page("بيانات جلسة الربط غير صالحة.", status_code=400)

    try:
        redirect = await service.continue_after_installation(
            state=state,
            candidate_installation_id=installation_id,
            redirect_uri=_absolute_callback_url(
                settings.public_base_url, GITHUB_OAUTH_CALLBACK_PATH
            ),
        )
    except (GitHubConnectionError, InvalidAuthorizationState, ValueError):
        return _error_page("انتهت جلسة الربط أو أصبحت غير صالحة.", status_code=400)
    return RedirectResponse(redirect.url, status_code=302)


@router.get(GITHUB_OAUTH_CALLBACK_PATH)
async def github_oauth_callback(
    request: Request,
    state: str = "",
    code: str = "",
    error: str = "",
) -> HTMLResponse:
    service = request.app.state.runtime_services.github_connection
    settings = request.app.state.settings
    if service is None or settings.public_base_url is None:
        return _error_page("ربط GitHub غير مهيأ على الخادم.", status_code=503)
    if error:
        return _error_page("تم إلغاء ربط GitHub. لم يتم حفظ أي ربط جديد.", status_code=400)
    if not state or not code:
        return _error_page("بيانات التحقق من GitHub غير مكتملة.", status_code=400)

    try:
        installation = await service.complete_user_authorization(
            state=state,
            code=code,
            redirect_uri=_absolute_callback_url(
                settings.public_base_url, GITHUB_OAUTH_CALLBACK_PATH
            ),
        )
    except (
        GitHubConnectionError,
        InvalidAuthorizationState,
        GitHubAuthError,
        InstallationBindingError,
        ValueError,
    ):
        return _error_page("تعذر إكمال ربط GitHub بأمان. ابدأ جلسة ربط جديدة من البوت.", 400)

    safe_login = installation.account_login.replace("<", "&lt;").replace(">", "&gt;")
    return HTMLResponse(
        "<!doctype html><html lang='ar' dir='rtl'><meta charset='utf-8'>"
        "<title>GitDock</title><body>"
        "<h2>✅ تم ربط GitHub بنجاح</h2>"
        f"<p>الحساب/التثبيت: <strong>{safe_login}</strong></p>"
        "<p>يمكنك الآن العودة إلى Telegram والضغط على تحديث.</p>"
        "</body></html>"
    )


def _absolute_callback_url(base_url: object, path: str) -> str:
    return f"{str(base_url).rstrip('/')}{path}"


def _error_page(message: str, status_code: int) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html lang='ar' dir='rtl'><meta charset='utf-8'>"
        "<title>GitDock</title><body>"
        f"<h2>⚠️ {message}</h2>"
        "<p>ارجع إلى Telegram وحاول من جديد.</p>"
        "</body></html>",
        status_code=status_code,
    )
