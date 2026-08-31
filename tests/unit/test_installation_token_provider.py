from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr

from gitdock.github.auth import InstallationAccessToken
from gitdock.github.token_provider import InstallationTokenProvider


class FakeTokenSource:
    def __init__(self, now: list[datetime]) -> None:
        self.now = now
        self.calls = 0

    async def create_installation_token(
        self,
        installation_id: int,
        *,
        permissions: Mapping[str, str] | None = None,
        repository_ids: Sequence[int] | None = None,
    ) -> InstallationAccessToken:
        self.calls += 1
        return InstallationAccessToken(
            token=SecretStr(f"token-{self.calls}"),
            expires_at=self.now[0] + timedelta(hours=1),
            permissions=dict(permissions or {}),
        )


@pytest.mark.asyncio
async def test_token_provider_reuses_valid_token_and_refreshes_near_expiry() -> None:
    now = [datetime(2026, 8, 31, 1, 0, tzinfo=UTC)]
    source = FakeTokenSource(now)
    provider = InstallationTokenProvider(source, clock=lambda: now[0])

    first = await provider.get_token(77, permissions={"contents": "read"})
    second = await provider.get_token(77, permissions={"contents": "read"})

    assert source.calls == 1
    assert first.token.get_secret_value() == second.token.get_secret_value()

    now[0] += timedelta(minutes=56)
    refreshed = await provider.get_token(77, permissions={"contents": "read"})

    assert source.calls == 2
    assert refreshed.token.get_secret_value() == "token-2"


@pytest.mark.asyncio
async def test_token_provider_scopes_cache_by_permissions_and_repositories() -> None:
    now = [datetime(2026, 8, 31, 1, 0, tzinfo=UTC)]
    source = FakeTokenSource(now)
    provider = InstallationTokenProvider(source, clock=lambda: now[0])

    await provider.get_token(77, permissions={"contents": "read"}, repository_ids=[2, 1])
    await provider.get_token(77, permissions={"issues": "read"}, repository_ids=[1, 2])

    assert source.calls == 2
