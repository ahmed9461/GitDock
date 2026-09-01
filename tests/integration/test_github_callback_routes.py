from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from gitdock.github.connection import ConnectionCompletion, ConnectionRedirect
from gitdock.http.routes.github import router


class FakeConnectionService:
    def __init__(self) -> None:
        self.install_call: tuple[str, int, str] | None = None
        self.oauth_call: tuple[str, str, str] | None = None

    async def continue_after_installation(
        self,
        *,
        state: str,
        candidate_installation_id: int,
        redirect_uri: str,
    ) -> ConnectionRedirect:
        self.install_call = (state, candidate_installation_id, redirect_uri)
        return ConnectionRedirect("https://github.com/login/oauth/authorize?client_id=test")

    async def complete_user_authorization(
        self,
        *,
        state: str,
        code: str,
        redirect_uri: str,
    ) -> ConnectionCompletion:
        self.oauth_call = (state, code, redirect_uri)
        return ConnectionCompletion(
            account_login="ahmed9461",
            installation_account_login="ahmed-org",
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_setup_callback_redirects_only_through_connection_service() -> None:
    service = FakeConnectionService()
    app = FastAPI()
    app.include_router(router)
    app.state.runtime_services = type("Runtime", (), {"github_connection": service})()
    app.state.settings = type("Settings", (), {"public_base_url": "https://gitdock.example/"})()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://gitdock.example") as client:
        response = await client.get(
            "/github/setup/callback",
            params={"state": "opaque", "installation_id": 99},
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["location"].startswith("https://github.com/login/oauth/authorize")
    assert service.install_call == (
        "opaque",
        99,
        "https://gitdock.example/github/oauth/callback",
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_oauth_callback_returns_safe_user_and_installation_success_copy() -> None:
    service = FakeConnectionService()
    app = FastAPI()
    app.include_router(router)
    app.state.runtime_services = type("Runtime", (), {"github_connection": service})()
    app.state.settings = type("Settings", (), {"public_base_url": "https://gitdock.example"})()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://gitdock.example") as client:
        response = await client.get(
            "/github/oauth/callback",
            params={"state": "opaque", "code": "secret-code"},
        )

    assert response.status_code == 200
    assert "تم تفويض GitHub بنجاح" in response.text
    assert "حساب GitHub" in response.text
    assert "ahmed9461" in response.text
    assert "تثبيت GitHub App" in response.text
    assert "ahmed-org" in response.text
    assert "secret-code" not in response.text
    assert service.oauth_call == (
        "opaque",
        "secret-code",
        "https://gitdock.example/github/oauth/callback",
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_oauth_cancellation_does_not_call_connection_service_or_echo_error() -> None:
    service = FakeConnectionService()
    app = FastAPI()
    app.include_router(router)
    app.state.runtime_services = type("Runtime", (), {"github_connection": service})()
    app.state.settings = type("Settings", (), {"public_base_url": "https://gitdock.example"})()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://gitdock.example") as client:
        response = await client.get(
            "/github/oauth/callback",
            params={"state": "opaque", "error": "access_denied"},
        )

    assert response.status_code == 400
    assert "access_denied" not in response.text
    assert service.oauth_call is None
