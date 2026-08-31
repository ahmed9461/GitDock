from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from gitdock.github.client import GitHubRestClient, RetryMode
from gitdock.github.errors import (
    GitHubAuthenticationError,
    GitHubConflictError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitedError,
    GitHubTransientError,
    GitHubValidationError,
)
from gitdock.github.pagination import validate_github_api_target

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "github" / "repositories_page.json"


def _repo_parser(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ValueError("repository payload must be an object")
    full_name = payload.get("full_name")
    if not isinstance(full_name, str):
        raise ValueError("repository full_name is missing")
    return full_name


def _object_parser(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    return payload


@pytest.mark.asyncio
async def test_get_json_sends_canonical_headers_and_hides_token() -> None:
    seen_headers: httpx.Headers | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_headers
        seen_headers = request.headers
        return httpx.Response(
            200,
            json={"ok": True},
            headers={"X-GitHub-Request-Id": "REQ_123"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = GitHubRestClient(http)
        result = await client.get_json(
            "/rate_limit",
            parser=_object_parser,
            token=SecretStr("ghs_super_secret_test_token"),
        )

    assert result.data == {"ok": True}
    assert result.request_id == "REQ_123"
    assert seen_headers is not None
    assert seen_headers["Accept"] == "application/vnd.github+json"
    assert seen_headers["X-GitHub-Api-Version"] == "2026-03-10"
    assert seen_headers["User-Agent"] == "GitDock/0.1"
    assert seen_headers["Authorization"] == "Bearer ghs_super_secret_test_token"
    assert "ghs_super_secret_test_token" not in repr(result)


@pytest.mark.asyncio
async def test_get_page_parses_fixture_and_validated_next_link() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=payload,
            headers={
                "Link": (
                    '<https://api.github.com/installation/repositories?per_page=2&page=2>; '
                    'rel="next", '
                    '<https://api.github.com/installation/repositories?per_page=2&page=4>; '
                    'rel="last"'
                ),
                "X-RateLimit-Limit": "5000",
                "X-RateLimit-Remaining": "4999",
                "X-RateLimit-Used": "1",
                "X-RateLimit-Resource": "core",
                "X-RateLimit-Reset": "1788145200",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = GitHubRestClient(http)
        page = await client.get_page(
            "/installation/repositories",
            item_parser=_repo_parser,
            item_key="repositories",
        )

    assert page.items == ("ahmed9461/GitDock", "ahmed9461/WebHub")
    assert page.pagination.next_url is not None
    assert page.pagination.next_url.endswith("page=2")
    assert page.rate_limit.limit == 5000
    assert page.rate_limit.remaining == 4999
    assert page.rate_limit.resource == "core"
    assert page.rate_limit.reset_at is not None


@pytest.mark.asyncio
async def test_iter_pages_follows_next_link_without_reusing_first_params() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.params.get("page") == "2":
            return httpx.Response(200, json=[{"full_name": "o/two"}])
        return httpx.Response(
            200,
            json=[{"full_name": "o/one"}],
            headers={"Link": '<https://api.github.com/repos/o/r?page=2>; rel="next"'},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = GitHubRestClient(http)
        pages = [
            page
            async for page in client.iter_pages(
                "/repos/o/r",
                item_parser=_repo_parser,
                params={"per_page": 1},
            )
        ]

    assert [page.items for page in pages] == [("o/one",), ("o/two",)]
    assert "per_page=1" in seen[0]
    assert seen[1] == "https://api.github.com/repos/o/r?page=2"


def test_pagination_rejects_external_or_credentialed_urls() -> None:
    with pytest.raises(ValueError):
        validate_github_api_target("https://evil.example/repos?page=2")
    with pytest.raises(ValueError):
        validate_github_api_target("https://user:pass@api.github.com/repos?page=2")
    with pytest.raises(ValueError):
        validate_github_api_target("//evil.example/repos?page=2")


@pytest.mark.asyncio
async def test_rate_limit_403_translates_separately_from_permission_403() -> None:
    responses = iter(
        [
            httpx.Response(
                403,
                json={"message": "rate limited"},
                headers={"X-RateLimit-Remaining": "0", "Retry-After": "2"},
            ),
            httpx.Response(
                403,
                json={"message": "permission denied"},
                headers={"X-RateLimit-Remaining": "4990"},
            ),
        ]
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return next(responses)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = GitHubRestClient(http)
        with pytest.raises(GitHubRateLimitedError) as rate_exc:
            await client.get_json("/one", parser=_object_parser)
        with pytest.raises(GitHubPermissionError):
            await client.get_json("/two", parser=_object_parser)

    assert rate_exc.value.context.rate_limit is not None
    assert rate_exc.value.context.rate_limit.retry_after_seconds == 2.0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (404, GitHubNotFoundError),
        (409, GitHubConflictError),
        (422, GitHubValidationError),
    ],
)
async def test_common_statuses_translate_to_stable_error_types(
    status_code: int,
    error_type: type[Exception],
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"message": "do not surface raw body"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = GitHubRestClient(http)
        with pytest.raises(error_type):
            await client.get_json("/resource", parser=_object_parser)


@pytest.mark.asyncio
async def test_401_error_never_contains_response_body_or_token() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"message": "token ghs_do_not_echo"},
            headers={"X-GitHub-Request-Id": "SAFE_REQ_ID"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = GitHubRestClient(http)
        with pytest.raises(GitHubAuthenticationError) as exc_info:
            await client.get_json(
                "/user",
                parser=_object_parser,
                token=SecretStr("ghs_do_not_echo"),
            )

    rendered = f"{exc_info.value!r} {exc_info.value}"
    assert "ghs_do_not_echo" not in rendered
    assert exc_info.value.context.request_id == "SAFE_REQ_ID"


@pytest.mark.asyncio
async def test_safe_get_retries_transient_status_with_bounded_backoff() -> None:
    calls = 0
    delays: list[float] = []

    async def sleeper(delay: float) -> None:
        delays.append(delay)

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503, json={"message": "temporary"})
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = GitHubRestClient(http, sleeper=sleeper, jitter=lambda: 0.0)
        result = await client.get_json("/repos/o/r", parser=_object_parser)

    assert result.data == {"ok": True}
    assert calls == 3
    assert delays == [0.5, 1.0]


@pytest.mark.asyncio
async def test_write_is_not_retried_by_default() -> None:
    calls = 0
    delays: list[float] = []

    async def sleeper(delay: float) -> None:
        delays.append(delay)

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"message": "temporary"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = GitHubRestClient(http, sleeper=sleeper, jitter=lambda: 0.0)
        with pytest.raises(GitHubTransientError):
            await client.request_json(
                "POST",
                "/repos/o/r/issues",
                parser=_object_parser,
                json_body={"title": "x"},
            )

    assert calls == 1
    assert delays == []


@pytest.mark.asyncio
async def test_explicit_safe_retry_mode_can_be_used_for_known_safe_operation() -> None:
    calls = 0

    async def sleeper(_: float) -> None:
        return None

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(502, json={"message": "temporary"})
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = GitHubRestClient(http, sleeper=sleeper, jitter=lambda: 0.0)
        result = await client.request_json(
            "POST",
            "/safe-endpoint",
            parser=_object_parser,
            retry_mode=RetryMode.SAFE,
        )

    assert result.data == {"ok": True}
    assert calls == 2
