"""GitHub App JWT, OAuth, installation discovery, and token primitives."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from pydantic import SecretStr

from gitdock.core.config import Settings
from gitdock.core.constants import (
    GITHUB_ACCEPT_HEADER,
    GITHUB_API_BASE_URL,
    GITHUB_APP_JWT_IAT_SKEW_SECONDS,
    GITHUB_APP_JWT_LIFETIME_SECONDS,
    GITHUB_OAUTH_ACCESS_TOKEN_URL,
    GITHUB_OAUTH_AUTHORIZE_URL,
    GITHUB_REST_API_VERSION,
    GITHUB_WEB_BASE_URL,
)

Clock = Callable[[], datetime]


class GitHubAuthError(RuntimeError):
    """Stable authentication-layer failure without response/token leakage."""


@dataclass(frozen=True, slots=True)
class InstallationIdentity:
    installation_id: int
    account_id: int
    account_login: str
    account_type: str
    suspended: bool
    permissions: dict[str, str]


@dataclass(frozen=True, slots=True)
class InstallationAccessToken:
    token: SecretStr
    expires_at: datetime
    permissions: dict[str, str]


@dataclass(frozen=True, slots=True)
class UserAccessToken:
    token: SecretStr
    expires_at: datetime | None
    refresh_token: SecretStr | None
    refresh_expires_at: datetime | None


class GitHubAppJwtIssuer:
    """Issue short-lived RS256 GitHub App JWTs using the app client ID as issuer."""

    def __init__(
        self,
        issuer: str,
        private_key_pem: str,
        clock: Clock | None = None,
    ) -> None:
        if not issuer.strip():
            raise ValueError("GitHub App JWT issuer must not be empty")
        if not private_key_pem.strip():
            raise ValueError("GitHub App private key must not be empty")
        self._issuer = issuer
        self._private_key_pem = private_key_pem
        self._clock = clock or (lambda: datetime.now(UTC))

    @classmethod
    def from_settings(cls, settings: Settings, clock: Clock | None = None) -> GitHubAppJwtIssuer:
        if not settings.github_auth_configured:
            raise GitHubAuthError("GitHub App authentication is not configured")
        if settings.github_client_id is None or settings.github_private_key_path is None:
            raise GitHubAuthError("GitHub App authentication configuration is incomplete")
        try:
            private_key_pem = Path(settings.github_private_key_path).read_text(encoding="utf-8")
        except OSError as exc:
            raise GitHubAuthError("GitHub App private key could not be read") from exc
        return cls(settings.github_client_id, private_key_pem, clock=clock)

    def issue(self) -> str:
        now = self._clock().astimezone(UTC)
        payload = {
            "iat": int(now.timestamp()) - GITHUB_APP_JWT_IAT_SKEW_SECONDS,
            "exp": int(now.timestamp()) + GITHUB_APP_JWT_LIFETIME_SECONDS,
            "iss": self._issuer,
        }
        try:
            encoded = jwt.encode(payload, self._private_key_pem, algorithm="RS256")
        except Exception as exc:
            raise GitHubAuthError("GitHub App JWT could not be signed") from exc
        if not isinstance(encoded, str):
            raise GitHubAuthError("GitHub App JWT encoder returned an invalid value")
        return encoded


class GitHubAuthUrlBuilder:
    """Build trusted GitHub-owned install and user-authorization URLs."""

    def __init__(self, settings: Settings) -> None:
        if not settings.github_auth_configured:
            raise GitHubAuthError("GitHub App authentication is not configured")
        if settings.github_app_slug is None or settings.github_client_id is None:
            raise GitHubAuthError("GitHub App authentication configuration is incomplete")
        self._app_slug = settings.github_app_slug
        self._client_id = settings.github_client_id

    def installation_url(self, state: str) -> str:
        if not state:
            raise ValueError("state must not be empty")
        query = urlencode({"state": state})
        return f"{GITHUB_WEB_BASE_URL}/apps/{self._app_slug}/installations/new?{query}"

    def user_authorization_url(self, state: str, code_challenge: str, redirect_uri: str) -> str:
        if not state or not code_challenge or not redirect_uri:
            raise ValueError("state, code challenge, and redirect URI are required")
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{GITHUB_OAUTH_AUTHORIZE_URL}?{query}"


class GitHubAuthClient:
    """Narrow HTTP client for GitHub App authentication endpoints only."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        settings: Settings,
        jwt_issuer: GitHubAppJwtIssuer,
        clock: Clock | None = None,
    ) -> None:
        if not settings.github_auth_configured:
            raise GitHubAuthError("GitHub App authentication is not configured")
        if settings.github_client_id is None or settings.github_client_secret is None:
            raise GitHubAuthError("GitHub OAuth configuration is incomplete")
        self._http = http_client
        self._settings = settings
        self._jwt_issuer = jwt_issuer
        self._clock = clock or (lambda: datetime.now(UTC))

    async def list_app_installations(self) -> list[InstallationIdentity]:
        response = await self._http.get(
            f"{GITHUB_API_BASE_URL}/app/installations",
            headers=self._app_headers(),
        )
        payload = self._json(response)
        if not isinstance(payload, list):
            raise GitHubAuthError("GitHub installation response had an unexpected shape")
        return [self._parse_installation(item) for item in payload]

    async def get_app_installation(self, installation_id: int) -> InstallationIdentity:
        self._validate_installation_id(installation_id)
        response = await self._http.get(
            f"{GITHUB_API_BASE_URL}/app/installations/{installation_id}",
            headers=self._app_headers(),
        )
        return self._parse_installation(self._json(response))

    async def get_user_installation(
        self,
        user_token: SecretStr,
        installation_id: int,
    ) -> InstallationIdentity:
        self._validate_installation_id(installation_id)
        response = await self._http.get(
            f"{GITHUB_API_BASE_URL}/user/installations/{installation_id}",
            headers=self._user_headers(user_token),
        )
        return self._parse_installation(self._json(response))

    async def list_user_installations(self, user_token: SecretStr) -> list[InstallationIdentity]:
        response = await self._http.get(
            f"{GITHUB_API_BASE_URL}/user/installations",
            headers=self._user_headers(user_token),
        )
        payload = self._json(response)
        data = self._require_dict(payload, "GitHub user installations response")
        installations = data.get("installations")
        if not isinstance(installations, list):
            raise GitHubAuthError("GitHub user installations response had an unexpected shape")
        return [self._parse_installation(item) for item in installations]

    async def create_installation_token(
        self,
        installation_id: int,
        *,
        permissions: Mapping[str, str] | None = None,
        repository_ids: Sequence[int] | None = None,
    ) -> InstallationAccessToken:
        self._validate_installation_id(installation_id)
        body: dict[str, object] = {}
        if permissions:
            body["permissions"] = dict(permissions)
        if repository_ids:
            if any(repository_id <= 0 for repository_id in repository_ids):
                raise ValueError("repository IDs must be positive")
            body["repository_ids"] = list(repository_ids)
        response = await self._http.post(
            f"{GITHUB_API_BASE_URL}/app/installations/{installation_id}/access_tokens",
            headers=self._app_headers(),
            json=body,
        )
        data = self._require_dict(self._json(response), "GitHub installation token response")
        token = self._require_str(data, "token")
        expires_at = self._parse_datetime(self._require_str(data, "expires_at"))
        parsed_permissions = self._parse_permissions(data.get("permissions"))
        return InstallationAccessToken(
            token=SecretStr(token),
            expires_at=expires_at,
            permissions=parsed_permissions,
        )

    async def exchange_user_code(
        self,
        *,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> UserAccessToken:
        if not code or not redirect_uri or not code_verifier:
            raise ValueError("OAuth code, redirect URI, and PKCE verifier are required")
        assert self._settings.github_client_id is not None
        assert self._settings.github_client_secret is not None
        response = await self._http.post(
            GITHUB_OAUTH_ACCESS_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": self._settings.github_client_id,
                "client_secret": self._settings.github_client_secret.get_secret_value(),
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
        )
        data = self._require_dict(self._json(response), "GitHub OAuth token response")
        access_token = SecretStr(self._require_str(data, "access_token"))
        now = self._clock().astimezone(UTC)
        expires_at = self._expiry_from_seconds(now, data.get("expires_in"))
        refresh_raw = data.get("refresh_token")
        refresh_token = SecretStr(refresh_raw) if isinstance(refresh_raw, str) and refresh_raw else None
        refresh_expires_at = self._expiry_from_seconds(now, data.get("refresh_token_expires_in"))
        return UserAccessToken(
            token=access_token,
            expires_at=expires_at,
            refresh_token=refresh_token,
            refresh_expires_at=refresh_expires_at,
        )

    def _app_headers(self) -> dict[str, str]:
        return {
            "Accept": GITHUB_ACCEPT_HEADER,
            "Authorization": f"Bearer {self._jwt_issuer.issue()}",
            "X-GitHub-Api-Version": GITHUB_REST_API_VERSION,
        }

    @staticmethod
    def _user_headers(token: SecretStr) -> dict[str, str]:
        return {
            "Accept": GITHUB_ACCEPT_HEADER,
            "Authorization": f"Bearer {token.get_secret_value()}",
            "X-GitHub-Api-Version": GITHUB_REST_API_VERSION,
        }

    @staticmethod
    def _validate_installation_id(installation_id: int) -> None:
        if installation_id <= 0:
            raise ValueError("installation ID must be positive")

    @staticmethod
    def _json(response: httpx.Response) -> Any:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubAuthError(
                f"GitHub authentication request failed with HTTP {response.status_code}"
            ) from exc
        try:
            return response.json()
        except ValueError as exc:
            raise GitHubAuthError("GitHub authentication response was not valid JSON") from exc

    @classmethod
    def _parse_installation(cls, payload: Any) -> InstallationIdentity:
        data = cls._require_dict(payload, "GitHub installation response")
        account = cls._require_dict(data.get("account"), "GitHub installation account")
        suspended = data.get("suspended_at") is not None
        return InstallationIdentity(
            installation_id=cls._require_int(data, "id"),
            account_id=cls._require_int(account, "id"),
            account_login=cls._require_str(account, "login"),
            account_type=cls._require_str(account, "type"),
            suspended=suspended,
            permissions=cls._parse_permissions(data.get("permissions")),
        )

    @staticmethod
    def _require_dict(payload: Any, label: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise GitHubAuthError(f"{label} had an unexpected shape")
        return payload

    @staticmethod
    def _require_str(data: Mapping[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise GitHubAuthError(f"GitHub authentication response is missing {key}")
        return value

    @staticmethod
    def _require_int(data: Mapping[str, Any], key: str) -> int:
        value = data.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise GitHubAuthError(f"GitHub authentication response is missing {key}")
        return value

    @staticmethod
    def _parse_permissions(payload: Any) -> dict[str, str]:
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise GitHubAuthError("GitHub permissions response had an unexpected shape")
        parsed: dict[str, str] = {}
        for key, value in payload.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise GitHubAuthError("GitHub permissions response had invalid values")
            parsed[key] = value
        return parsed

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise GitHubAuthError("GitHub token expiry timestamp is invalid") from exc
        if parsed.tzinfo is None:
            raise GitHubAuthError("GitHub token expiry timestamp is missing timezone")
        return parsed.astimezone(UTC)

    @staticmethod
    def _expiry_from_seconds(now: datetime, raw: Any) -> datetime | None:
        if raw is None:
            return None
        if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
            raise GitHubAuthError("GitHub OAuth expiry value is invalid")
        return now + timedelta(seconds=raw)
