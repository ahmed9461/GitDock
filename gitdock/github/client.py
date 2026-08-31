"""Typed GitHub REST gateway with safe retries, pagination, and error translation."""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from enum import StrEnum
from typing import TypeVar

import httpx
from pydantic import SecretStr

from gitdock.core.constants import (
    GITHUB_ACCEPT_HEADER,
    GITHUB_API_BASE_URL,
    GITHUB_MAX_PAGES,
    GITHUB_MAX_RETRIES,
    GITHUB_REST_API_VERSION,
    GITHUB_USER_AGENT,
    HTTP_CONNECT_TIMEOUT_SECONDS,
    HTTP_READ_TIMEOUT_SECONDS,
    RETRY_BASE_DELAY_SECONDS,
    RETRY_MAX_DELAY_SECONDS,
)
from gitdock.github.errors import (
    GitHubErrorKind,
    GitHubGatewayError,
    GitHubTransientError,
    translate_http_error,
)
from gitdock.github.models import GitHubPage, GitHubRateLimit, GitHubResponse
from gitdock.github.pagination import parse_pagination_links, validate_github_api_target

T = TypeVar("T")
Parser = Callable[[object], T]
Sleeper = Callable[[float], Awaitable[None]]
Jitter = Callable[[], float]
QueryParamValue = str | int | float | bool | None
QueryParams = Mapping[str, QueryParamValue]


class RetryMode(StrEnum):
    NEVER = "never"
    SAFE = "safe"


class GitHubRestClient:
    """GitHub REST transport boundary. Higher layers provide payload parsers."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        *,
        sleeper: Sleeper | None = None,
        jitter: Jitter | None = None,
    ) -> None:
        self._http = http_client
        self._sleep = sleeper or asyncio.sleep
        self._jitter = jitter or random.random
        self._timeout = httpx.Timeout(
            connect=HTTP_CONNECT_TIMEOUT_SECONDS,
            read=HTTP_READ_TIMEOUT_SECONDS,
            write=HTTP_READ_TIMEOUT_SECONDS,
            pool=HTTP_CONNECT_TIMEOUT_SECONDS,
        )

    async def request_json(
        self,
        method: str,
        target: str,
        *,
        parser: Parser[T],
        token: SecretStr | None = None,
        params: QueryParams | None = None,
        json_body: object | None = None,
        retry_mode: RetryMode | None = None,
    ) -> GitHubResponse[T]:
        method_upper = method.upper()
        target = validate_github_api_target(target)
        effective_retry = retry_mode or (
            RetryMode.SAFE if method_upper in {"GET", "HEAD"} else RetryMode.NEVER
        )

        response = await self._send_with_retry(
            method_upper,
            target,
            token=token,
            params=params,
            json_body=json_body,
            retry_mode=effective_retry,
        )
        rate_limit = _parse_rate_limit(response)
        request_id = response.headers.get("X-GitHub-Request-Id")

        if not 200 <= response.status_code < 300:
            raise translate_http_error(
                response,
                rate_limit=rate_limit,
                request_id=request_id,
            )

        try:
            payload: object = response.json()
        except ValueError as exc:
            raise GitHubGatewayError(
                GitHubErrorKind.UNEXPECTED,
                "GitHub returned a response that was not valid JSON",
                status_code=response.status_code,
                request_id=request_id,
                rate_limit=rate_limit,
            ) from exc

        try:
            parsed = parser(payload)
        except GitHubGatewayError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise GitHubGatewayError(
                GitHubErrorKind.UNEXPECTED,
                "GitHub returned an unexpected response shape",
                status_code=response.status_code,
                request_id=request_id,
                rate_limit=rate_limit,
            ) from exc

        return GitHubResponse(
            data=parsed,
            rate_limit=rate_limit,
            pagination=parse_pagination_links(response),
            request_id=request_id,
            status_code=response.status_code,
        )

    async def get_json(
        self,
        target: str,
        *,
        parser: Parser[T],
        token: SecretStr | None = None,
        params: QueryParams | None = None,
    ) -> GitHubResponse[T]:
        return await self.request_json(
            "GET",
            target,
            parser=parser,
            token=token,
            params=params,
        )

    async def get_page(
        self,
        target: str,
        *,
        item_parser: Parser[T],
        token: SecretStr | None = None,
        params: QueryParams | None = None,
        item_key: str | None = None,
    ) -> GitHubPage[T]:
        response = await self.get_json(
            target,
            parser=lambda payload: _parse_page_items(payload, item_parser, item_key),
            token=token,
            params=params,
        )
        return GitHubPage(
            items=response.data,
            rate_limit=response.rate_limit,
            pagination=response.pagination,
            request_id=response.request_id,
            status_code=response.status_code,
        )

    async def iter_pages(
        self,
        target: str,
        *,
        item_parser: Parser[T],
        token: SecretStr | None = None,
        params: QueryParams | None = None,
        item_key: str | None = None,
        max_pages: int = GITHUB_MAX_PAGES,
    ) -> AsyncIterator[GitHubPage[T]]:
        if max_pages <= 0:
            raise ValueError("max_pages must be positive")

        current_target = target
        current_params = params
        seen: set[str] = set()

        for _ in range(max_pages):
            normalized = validate_github_api_target(current_target)
            seen_key = _resolve_target(normalized)
            if seen_key in seen:
                raise GitHubGatewayError(
                    GitHubErrorKind.UNEXPECTED,
                    "GitHub pagination returned a repeated next-page link",
                )
            seen.add(seen_key)

            page = await self.get_page(
                normalized,
                item_parser=item_parser,
                token=token,
                params=current_params,
                item_key=item_key,
            )
            yield page

            next_url = page.pagination.next_url
            if next_url is None:
                return
            current_target = next_url
            current_params = None

        raise GitHubGatewayError(
            GitHubErrorKind.UNEXPECTED,
            "GitHub pagination exceeded the configured page safety limit",
        )

    async def _send_with_retry(
        self,
        method: str,
        target: str,
        *,
        token: SecretStr | None,
        params: QueryParams | None,
        json_body: object | None,
        retry_mode: RetryMode,
    ) -> httpx.Response:
        url = _resolve_target(target)
        retries_used = 0

        while True:
            try:
                response = await self._http.request(
                    method,
                    url,
                    headers=_build_headers(token),
                    params=params,
                    json=json_body,
                    timeout=self._timeout,
                    follow_redirects=False,
                )
            except (httpx.NetworkError, httpx.TimeoutException) as exc:
                if retry_mode is RetryMode.NEVER or retries_used >= GITHUB_MAX_RETRIES:
                    raise GitHubTransientError(
                        GitHubErrorKind.TRANSIENT,
                        "GitHub request failed because of a temporary network error",
                    ) from exc
                await self._wait_before_retry(retries_used)
                retries_used += 1
                continue

            if (
                response.status_code in {408, 500, 502, 503, 504}
                and retry_mode is RetryMode.SAFE
                and retries_used < GITHUB_MAX_RETRIES
            ):
                await self._wait_before_retry(retries_used)
                retries_used += 1
                continue
            return response

    async def _wait_before_retry(self, retries_used: int) -> None:
        base = RETRY_BASE_DELAY_SECONDS * (2**retries_used)
        delay = min(base + (base * self._jitter()), RETRY_MAX_DELAY_SECONDS)
        await self._sleep(delay)


def _resolve_target(target: str) -> str:
    if target.startswith("/"):
        return f"{GITHUB_API_BASE_URL}{target}"
    return target


def _build_headers(token: SecretStr | None) -> dict[str, str]:
    headers = {
        "Accept": GITHUB_ACCEPT_HEADER,
        "X-GitHub-Api-Version": GITHUB_REST_API_VERSION,
        "User-Agent": GITHUB_USER_AGENT,
    }
    if token is not None:
        headers["Authorization"] = f"Bearer {token.get_secret_value()}"
    return headers


def _parse_page_items[T](
    payload: object,
    item_parser: Parser[T],
    item_key: str | None,
) -> tuple[T, ...]:
    if item_key is None:
        raw_items = payload
    else:
        if not isinstance(payload, dict):
            raise ValueError("expected an object payload for keyed pagination")
        raw_items = payload.get(item_key)

    if not isinstance(raw_items, list):
        raise ValueError("expected a list payload")
    return tuple(item_parser(item) for item in raw_items)


def _parse_optional_non_negative_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _parse_reset_at(value: str | None) -> datetime | None:
    parsed = _parse_optional_non_negative_int(value)
    if parsed is None:
        return None
    try:
        return datetime.fromtimestamp(parsed, tz=UTC)
    except (OSError, OverflowError, ValueError):
        return None


def _parse_retry_after(value: str | None, *, now: datetime) -> float | None:
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        seconds = (when.astimezone(UTC) - now).total_seconds()
    return max(seconds, 0.0)


def _parse_rate_limit(response: httpx.Response) -> GitHubRateLimit:
    now = datetime.now(UTC)
    return GitHubRateLimit(
        resource=response.headers.get("X-RateLimit-Resource"),
        limit=_parse_optional_non_negative_int(response.headers.get("X-RateLimit-Limit")),
        remaining=_parse_optional_non_negative_int(response.headers.get("X-RateLimit-Remaining")),
        used=_parse_optional_non_negative_int(response.headers.get("X-RateLimit-Used")),
        reset_at=_parse_reset_at(response.headers.get("X-RateLimit-Reset")),
        retry_after_seconds=_parse_retry_after(
            response.headers.get("Retry-After"),
            now=now,
        ),
    )
