from datetime import UTC, datetime

import httpx
import jwt
import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import SecretStr

from gitdock.core.config import Settings
from gitdock.core.constants import GITHUB_REST_API_VERSION
from gitdock.github.auth import GitHubAppJwtIssuer, GitHubAuthClient, GitHubAuthError

FIXED_NOW = datetime(2026, 8, 31, 1, 0, tzinfo=UTC)


def github_settings() -> Settings:
    return Settings(
        env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        telegram_bot_token="123456:abcdefghijklmnopqrstuvwxyzABCDEFGH",
        telegram_owner_id=123,
        github_app_id=12345,
        github_app_slug="gitdock-test",
        github_client_id="Iv1.test-client-id",
        github_client_secret="test-client-secret",
        github_private_key_path="/tmp/not-used-in-this-test.pem",
        credential_encryption_key=Fernet.generate_key().decode("ascii"),
    )


def rsa_private_key_pem() -> tuple[str, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def test_github_app_jwt_uses_rs256_client_id_and_bounded_lifetime() -> None:
    private_pem, public_pem = rsa_private_key_pem()
    issuer = GitHubAppJwtIssuer("Iv1.test-client-id", private_pem, clock=lambda: FIXED_NOW)

    token = issuer.issue()
    payload = jwt.decode(
        token,
        public_pem,
        algorithms=["RS256"],
        options={"verify_exp": False, "verify_iat": False},
    )

    assert payload["iss"] == "Iv1.test-client-id"
    assert payload["iat"] == int(FIXED_NOW.timestamp()) - 60
    assert payload["exp"] - int(FIXED_NOW.timestamp()) == 9 * 60


@pytest.mark.asyncio
async def test_installation_token_contract_uses_api_version_and_accepts_new_token_shapes() -> None:
    settings = github_settings()
    private_pem, _ = rsa_private_key_pem()
    issuer = GitHubAppJwtIssuer(
        settings.github_client_id or "", private_pem, clock=lambda: FIXED_NOW
    )
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["path"] = request.url.path
        observed["version"] = request.headers.get("X-GitHub-Api-Version")
        observed["authorization"] = request.headers.get("Authorization")
        return httpx.Response(
            201,
            request=request,
            json={
                "token": "ghs_APPID_JWT_stateless_format_not_fixed_to_legacy_length_123456789",
                "expires_at": "2026-08-31T02:00:00Z",
                "permissions": {"contents": "read"},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GitHubAuthClient(http_client, settings, issuer, clock=lambda: FIXED_NOW)
        token = await client.create_installation_token(
            99,
            permissions={"contents": "read"},
            repository_ids=[10, 20],
        )

    assert observed["path"] == "/app/installations/99/access_tokens"
    assert observed["version"] == GITHUB_REST_API_VERSION
    assert str(observed["authorization"]).startswith("Bearer ")
    assert token.token.get_secret_value().startswith("ghs_APPID_JWT_")
    assert token.expires_at == datetime(2026, 8, 31, 2, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_oauth_exchange_uses_pkce_and_never_echoes_error_body() -> None:
    settings = github_settings()
    private_pem, _ = rsa_private_key_pem()
    issuer = GitHubAppJwtIssuer(
        settings.github_client_id or "", private_pem, clock=lambda: FIXED_NOW
    )
    captured_body = b""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_body = request.content
        if request.url.path == "/login/oauth/access_token":
            return httpx.Response(
                200,
                request=request,
                json={
                    "access_token": "ghu_example_access",
                    "expires_in": 28800,
                    "refresh_token": "ghr_example_refresh",
                    "refresh_token_expires_in": 15897600,
                },
            )
        return httpx.Response(401, request=request, text="access_token=must-not-leak")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GitHubAuthClient(http_client, settings, issuer, clock=lambda: FIXED_NOW)
        token = await client.exchange_user_code(
            code="oauth-code-secret",
            redirect_uri="https://example.test/github/oauth/callback",
            code_verifier="pkce-verifier-secret",
        )

    assert b"code_verifier=pkce-verifier-secret" in captured_body
    assert token.token.get_secret_value() == "ghu_example_access"
    assert token.refresh_token is not None
    assert token.expires_at == FIXED_NOW.replace(hour=9)


@pytest.mark.asyncio
async def test_user_identity_and_refresh_use_user_context_and_rotation_grant() -> None:
    settings = github_settings()
    private_pem, _ = rsa_private_key_pem()
    issuer = GitHubAppJwtIssuer(
        settings.github_client_id or "", private_pem, clock=lambda: FIXED_NOW
    )
    observed: list[tuple[str, bytes, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append((request.url.path, request.content, request.headers.get("Authorization")))
        if request.url.path == "/user":
            return httpx.Response(200, request=request, json={"id": 55, "login": "octocat"})
        if request.url.path == "/login/oauth/access_token":
            return httpx.Response(
                200,
                request=request,
                json={
                    "access_token": "ghu_rotated_access",
                    "expires_in": 28800,
                    "refresh_token": "ghr_rotated_refresh",
                    "refresh_token_expires_in": 15897600,
                },
            )
        return httpx.Response(404, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GitHubAuthClient(http_client, settings, issuer, clock=lambda: FIXED_NOW)
        identity = await client.get_authenticated_user(SecretStr("ghu_identity"))
        refreshed = await client.refresh_user_access_token(SecretStr("ghr_old_refresh"))

    assert identity.github_user_id == 55
    assert identity.login == "octocat"
    assert observed[0][2] == "Bearer ghu_identity"
    assert b"grant_type=refresh_token" in observed[1][1]
    assert b"refresh_token=ghr_old_refresh" in observed[1][1]
    assert refreshed.token.get_secret_value() == "ghu_rotated_access"
    assert refreshed.refresh_token is not None
    assert refreshed.refresh_token.get_secret_value() == "ghr_rotated_refresh"


@pytest.mark.asyncio
async def test_auth_http_error_does_not_include_response_secret() -> None:
    settings = github_settings()
    private_pem, _ = rsa_private_key_pem()
    issuer = GitHubAppJwtIssuer(
        settings.github_client_id or "", private_pem, clock=lambda: FIXED_NOW
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, request=request, text="token=super-secret")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GitHubAuthClient(http_client, settings, issuer, clock=lambda: FIXED_NOW)
        with pytest.raises(GitHubAuthError) as exc_info:
            await client.get_app_installation(99)

    assert "super-secret" not in str(exc_info.value)
    assert "HTTP 401" in str(exc_info.value)
