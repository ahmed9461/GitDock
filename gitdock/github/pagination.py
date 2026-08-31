"""Pagination parsing and trusted-target validation for GitHub REST."""

from __future__ import annotations

from urllib.parse import urlsplit

import httpx

from gitdock.core.constants import GITHUB_API_BASE_URL
from gitdock.github.models import GitHubPaginationLinks

_API_PARTS = urlsplit(GITHUB_API_BASE_URL)


def validate_github_api_target(target: str) -> str:
    """Allow relative API paths or absolute HTTPS links to the canonical GitHub API only."""

    if not target:
        raise ValueError("GitHub API target must not be empty")

    if target.startswith("/"):
        if target.startswith("//"):
            raise ValueError("GitHub API target must not be protocol-relative")
        return target

    parts = urlsplit(target)
    if (
        parts.scheme != _API_PARTS.scheme
        or parts.hostname != _API_PARTS.hostname
        or parts.port not in {None, 443}
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
        or not parts.path.startswith("/")
    ):
        raise ValueError("GitHub pagination target must use the canonical GitHub API host")
    return target


def parse_pagination_links(response: httpx.Response) -> GitHubPaginationLinks:
    """Return only validated GitHub API links from the response Link header."""

    validated: dict[str, str | None] = {
        "next": None,
        "prev": None,
        "first": None,
        "last": None,
    }
    for relation in validated:
        link = response.links.get(relation)
        if link is None:
            continue
        raw_url = link.get("url")
        if not isinstance(raw_url, str):
            continue
        validated[relation] = validate_github_api_target(raw_url)

    return GitHubPaginationLinks(
        next_url=validated["next"],
        previous_url=validated["prev"],
        first_url=validated["first"],
        last_url=validated["last"],
    )
