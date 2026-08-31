"""Typed transport models shared by the GitHub gateway."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GitHubRateLimit:
    """Rate-limit metadata captured from one GitHub REST response."""

    resource: str | None
    limit: int | None
    remaining: int | None
    used: int | None
    reset_at: datetime | None
    retry_after_seconds: float | None

    @property
    def exhausted(self) -> bool:
        return self.remaining == 0 or self.retry_after_seconds is not None


@dataclass(frozen=True, slots=True)
class GitHubPaginationLinks:
    """Validated pagination links extracted from GitHub's Link header."""

    next_url: str | None = None
    previous_url: str | None = None
    first_url: str | None = None
    last_url: str | None = None


@dataclass(frozen=True, slots=True)
class GitHubResponse[T]:
    """Parsed response plus transport metadata useful to higher layers."""

    data: T
    rate_limit: GitHubRateLimit
    pagination: GitHubPaginationLinks
    request_id: str | None
    status_code: int


@dataclass(frozen=True, slots=True)
class GitHubPage[T]:
    """One typed page of GitHub API results."""

    items: tuple[T, ...]
    rate_limit: GitHubRateLimit
    pagination: GitHubPaginationLinks
    request_id: str | None
    status_code: int
