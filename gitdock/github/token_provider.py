"""Expiry-aware installation access-token caching."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from gitdock.core.constants import INSTALLATION_TOKEN_REFRESH_MARGIN_SECONDS
from gitdock.github.auth import GitHubAuthClient, InstallationAccessToken

Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class InstallationTokenScope:
    installation_id: int
    permissions: tuple[tuple[str, str], ...]
    repository_ids: tuple[int, ...]

    @classmethod
    def create(
        cls,
        installation_id: int,
        permissions: Mapping[str, str] | None,
        repository_ids: Sequence[int] | None,
    ) -> InstallationTokenScope:
        if installation_id <= 0:
            raise ValueError("installation ID must be positive")
        normalized_permissions = tuple(sorted((permissions or {}).items()))
        normalized_repositories = tuple(sorted(set(repository_ids or ())))
        if any(repository_id <= 0 for repository_id in normalized_repositories):
            raise ValueError("repository IDs must be positive")
        return cls(installation_id, normalized_permissions, normalized_repositories)


class InstallationTokenProvider:
    """Reuse valid tokens and refresh before expiry without exposing token strings."""

    def __init__(
        self,
        client: GitHubAuthClient,
        *,
        refresh_margin: timedelta | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._client = client
        self._refresh_margin = refresh_margin or timedelta(
            seconds=INSTALLATION_TOKEN_REFRESH_MARGIN_SECONDS
        )
        if self._refresh_margin.total_seconds() < 0:
            raise ValueError("refresh margin must not be negative")
        self._clock = clock or (lambda: datetime.now(UTC))
        self._cache: dict[InstallationTokenScope, InstallationAccessToken] = {}
        self._locks: dict[InstallationTokenScope, asyncio.Lock] = {}

    async def get_token(
        self,
        installation_id: int,
        *,
        permissions: Mapping[str, str] | None = None,
        repository_ids: Sequence[int] | None = None,
    ) -> InstallationAccessToken:
        scope = InstallationTokenScope.create(installation_id, permissions, repository_ids)
        cached = self._cache.get(scope)
        if cached is not None and self._is_reusable(cached):
            return cached

        lock = self._locks.setdefault(scope, asyncio.Lock())
        async with lock:
            cached = self._cache.get(scope)
            if cached is not None and self._is_reusable(cached):
                return cached
            token = await self._client.create_installation_token(
                installation_id,
                permissions=dict(scope.permissions) or None,
                repository_ids=scope.repository_ids or None,
            )
            self._cache[scope] = token
            return token

    def invalidate(self, installation_id: int) -> None:
        """Drop cached tokens for one installation after suspension/auth failure."""

        scopes = [scope for scope in self._cache if scope.installation_id == installation_id]
        for scope in scopes:
            self._cache.pop(scope, None)
            self._locks.pop(scope, None)

    def _is_reusable(self, token: InstallationAccessToken) -> bool:
        now = self._clock().astimezone(UTC)
        expiry = token.expires_at.astimezone(UTC)
        return expiry - now > self._refresh_margin
