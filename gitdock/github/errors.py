"""Stable GitDock error categories for GitHub transport failures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import httpx

from gitdock.github.models import GitHubRateLimit


class GitHubErrorKind(StrEnum):
    AUTHENTICATION = "authentication_required"
    PERMISSION = "missing_permission"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    VALIDATION = "validation_error"
    RATE_LIMITED = "rate_limited"
    TRANSIENT = "transient_failure"
    UNEXPECTED = "unexpected_failure"


@dataclass(frozen=True, slots=True)
class GitHubErrorContext:
    status_code: int | None
    request_id: str | None
    rate_limit: GitHubRateLimit | None


class GitHubGatewayError(RuntimeError):
    """Base error with safe metadata and no raw GitHub response body."""

    def __init__(
        self,
        kind: GitHubErrorKind,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
        rate_limit: GitHubRateLimit | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.context = GitHubErrorContext(
            status_code=status_code,
            request_id=request_id,
            rate_limit=rate_limit,
        )


class GitHubAuthenticationError(GitHubGatewayError):
    pass


class GitHubPermissionError(GitHubGatewayError):
    pass


class GitHubNotFoundError(GitHubGatewayError):
    pass


class GitHubConflictError(GitHubGatewayError):
    pass


class GitHubValidationError(GitHubGatewayError):
    pass


class GitHubRateLimitedError(GitHubGatewayError):
    pass


class GitHubTransientError(GitHubGatewayError):
    pass


class GitHubUnexpectedError(GitHubGatewayError):
    pass


def translate_http_error(
    response: httpx.Response,
    *,
    rate_limit: GitHubRateLimit,
    request_id: str | None,
) -> GitHubGatewayError:
    """Translate one non-success GitHub response without exposing its body."""

    status = response.status_code

    if status == 401:
        return GitHubAuthenticationError(
            GitHubErrorKind.AUTHENTICATION,
            "GitHub authentication is required or no longer valid",
            status_code=status,
            request_id=request_id,
            rate_limit=rate_limit,
        )
    if status == 429 or (status == 403 and rate_limit.exhausted):
        return GitHubRateLimitedError(
            GitHubErrorKind.RATE_LIMITED,
            "GitHub rate limit is currently preventing this request",
            status_code=status,
            request_id=request_id,
            rate_limit=rate_limit,
        )
    if status == 403:
        return GitHubPermissionError(
            GitHubErrorKind.PERMISSION,
            "GitHub denied this request because required access is unavailable",
            status_code=status,
            request_id=request_id,
            rate_limit=rate_limit,
        )
    if status == 404:
        return GitHubNotFoundError(
            GitHubErrorKind.NOT_FOUND,
            "The requested GitHub resource was not found or is not accessible",
            status_code=status,
            request_id=request_id,
            rate_limit=rate_limit,
        )
    if status in {409, 412}:
        return GitHubConflictError(
            GitHubErrorKind.CONFLICT,
            "GitHub rejected the request because the resource state changed",
            status_code=status,
            request_id=request_id,
            rate_limit=rate_limit,
        )
    if status in {400, 422}:
        return GitHubValidationError(
            GitHubErrorKind.VALIDATION,
            "GitHub rejected the request as invalid",
            status_code=status,
            request_id=request_id,
            rate_limit=rate_limit,
        )
    if status in {408, 500, 502, 503, 504}:
        return GitHubTransientError(
            GitHubErrorKind.TRANSIENT,
            "GitHub is temporarily unavailable for this request",
            status_code=status,
            request_id=request_id,
            rate_limit=rate_limit,
        )
    return GitHubUnexpectedError(
        GitHubErrorKind.UNEXPECTED,
        f"GitHub request failed with HTTP {status}",
        status_code=status,
        request_id=request_id,
        rate_limit=rate_limit,
    )
