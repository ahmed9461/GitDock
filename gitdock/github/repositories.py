"""Typed read-only GitHub repository endpoints built on the canonical REST gateway."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from urllib.parse import quote, urlparse

from pydantic import SecretStr

from gitdock.core.constants import GITHUB_REPOSITORY_FETCH_PAGE_SIZE
from gitdock.github.client import GitHubRestClient


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    github_repository_id: int
    owner_login: str
    name: str
    full_name: str
    html_url: str
    private: bool
    archived: bool
    fork: bool
    default_branch: str
    language: str | None
    description: str | None
    stars: int
    forks: int
    updated_at: datetime
    pushed_at: datetime | None


class GitHubRepositoryGateway:
    """Read repository metadata using installation access tokens only."""

    def __init__(self, client: GitHubRestClient) -> None:
        self._client = client

    async def list_installation_repositories(
        self,
        token: SecretStr,
    ) -> tuple[RepositorySnapshot, ...]:
        repositories: list[RepositorySnapshot] = []
        async for page in self._client.iter_pages(
            "/installation/repositories",
            item_parser=parse_repository,
            token=token,
            params={"per_page": GITHUB_REPOSITORY_FETCH_PAGE_SIZE},
            item_key="repositories",
        ):
            repositories.extend(page.items)
        return tuple(repositories)

    async def get_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ) -> RepositorySnapshot:
        owner = quote(_require_path_segment(owner_login, "owner"), safe="")
        repository = quote(_require_path_segment(name, "repository"), safe="")
        response = await self._client.get_json(
            f"/repos/{owner}/{repository}",
            parser=parse_repository,
            token=token,
        )
        return response.data


def parse_repository(payload: object) -> RepositorySnapshot:
    data = _require_dict(payload, "repository")
    owner = _require_dict(data.get("owner"), "repository owner")
    owner_login = _require_str(owner, "login")
    name = _require_str(data, "name")
    full_name = _require_str(data, "full_name")
    if full_name != f"{owner_login}/{name}":
        raise ValueError("repository full name did not match owner/name")

    return RepositorySnapshot(
        github_repository_id=_require_positive_int(data, "id"),
        owner_login=owner_login,
        name=name,
        full_name=full_name,
        html_url=_require_github_html_url(_require_str(data, "html_url")),
        private=_require_bool(data, "private"),
        archived=_require_bool(data, "archived"),
        fork=_require_bool(data, "fork"),
        default_branch=_require_str(data, "default_branch"),
        language=_optional_str(data.get("language")),
        description=_optional_str(data.get("description")),
        stars=_require_non_negative_int(data, "stargazers_count"),
        forks=_require_non_negative_int(data, "forks_count"),
        updated_at=_parse_datetime(_require_str(data, "updated_at")),
        pushed_at=_parse_optional_datetime(data.get("pushed_at")),
    )


def _require_path_segment(value: str, label: str) -> str:
    value = value.strip()
    if not value or "/" in value or "\\" in value or "\x00" in value:
        raise ValueError(f"{label} is not a valid repository path segment")
    return value


def _require_dict(payload: object, label: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError(f"expected {label} object")
    if not all(isinstance(key, str) for key in payload):
        raise ValueError(f"expected {label} string keys")
    return cast(dict[str, object], payload)


def _require_str(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing repository field {key}")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional repository text field had invalid type")
    return value or None


def _require_bool(data: dict[str, object], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"missing repository boolean field {key}")
    return value


def _require_positive_int(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"missing positive repository integer field {key}")
    return value


def _require_non_negative_int(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"missing repository integer field {key}")
    return value


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("repository timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError("repository timestamp is missing timezone")
    return parsed.astimezone(UTC)


def _parse_optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional repository timestamp had invalid type")
    return _parse_datetime(value)


def _require_github_html_url(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("repository HTML URL is not canonical GitHub HTTPS")
    return value
