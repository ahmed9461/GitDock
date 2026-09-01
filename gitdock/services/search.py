"""Application service and validation rules for public GitHub repository search."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import StrEnum
from math import ceil
from typing import Protocol

from gitdock.core.constants import (
    SEARCH_COMPILED_QUERY_MAX_CHARS,
    SEARCH_MIN_STARS_MAX,
    SEARCH_OWNER_LOGIN_MAX_CHARS,
    SEARCH_PAGE_SIZE,
    SEARCH_QUERY_MAX_CHARS,
    SEARCH_TOPIC_MAX_CHARS,
)
from gitdock.github.search import RepositorySearchResponse, RepositorySearchResult

_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$")
_TOPIC_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


class SearchValidationError(ValueError):
    """Raised when a user-controlled search/filter value is invalid."""


class SearchSelectionError(RuntimeError):
    """Raised when a repository callback no longer belongs to active search context."""


class SearchSort(StrEnum):
    BEST_MATCH = "best"
    STARS = "stars"
    UPDATED = "updated"

    @property
    def api_value(self) -> str | None:
        if self is SearchSort.BEST_MATCH:
            return None
        return self.value


class SearchLanguage(StrEnum):
    PYTHON = "Python"
    JAVASCRIPT = "JavaScript"
    TYPESCRIPT = "TypeScript"
    KOTLIN = "Kotlin"


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    query: str
    sort: SearchSort = SearchSort.BEST_MATCH
    language: SearchLanguage | None = None
    min_stars: int | None = None
    owner_scope: str | None = None
    topic: str | None = None
    include_archived: bool = False

    def with_sort(self, value: SearchSort) -> SearchCriteria:
        return replace(self, sort=value)

    def with_language(self, value: SearchLanguage | None) -> SearchCriteria:
        return replace(self, language=value)

    def with_min_stars(self, value: int | None) -> SearchCriteria:
        return replace(self, min_stars=value)

    def with_owner_scope(self, value: str | None) -> SearchCriteria:
        return replace(self, owner_scope=value)

    def with_topic(self, value: str | None) -> SearchCriteria:
        return replace(self, topic=value)

    def with_include_archived(self, value: bool) -> SearchCriteria:
        return replace(self, include_archived=value)


@dataclass(frozen=True, slots=True)
class SearchResultPage:
    items: tuple[RepositorySearchResult, ...]
    page: int
    total_pages: int
    total_items: int
    incomplete_results: bool
    criteria: SearchCriteria


class SearchGateway(Protocol):
    async def search_repositories(
        self,
        *,
        query: str,
        page: int,
        per_page: int,
        sort: str | None = None,
        order: str | None = None,
    ) -> RepositorySearchResponse: ...

    async def get_public_repository(
        self,
        *,
        owner_login: str,
        name: str,
    ) -> RepositorySearchResult: ...


class RepositorySearchService:
    def __init__(self, gateway: SearchGateway) -> None:
        self._gateway = gateway

    async def search(self, criteria: SearchCriteria, *, page: int = 1) -> SearchResultPage:
        if page <= 0:
            raise SearchValidationError("page must be positive")
        normalized = normalize_criteria(criteria)
        compiled_query = build_search_query(normalized)
        response = await self._gateway.search_repositories(
            query=compiled_query,
            page=page,
            per_page=SEARCH_PAGE_SIZE,
            sort=normalized.sort.api_value,
            order="desc" if normalized.sort.api_value is not None else None,
        )
        total_pages = max(1, ceil(response.total_count / SEARCH_PAGE_SIZE))
        return SearchResultPage(
            items=response.items,
            page=page,
            total_pages=total_pages,
            total_items=response.total_count,
            incomplete_results=response.incomplete_results,
            criteria=normalized,
        )

    async def detail(self, *, owner_login: str, name: str) -> RepositorySearchResult:
        owner = _normalize_login(owner_login)
        repository = _normalize_repository_name(name)
        return await self._gateway.get_public_repository(owner_login=owner, name=repository)


def normalize_criteria(criteria: SearchCriteria) -> SearchCriteria:
    query = _normalize_query(criteria.query)
    language = criteria.language
    min_stars = _normalize_min_stars(criteria.min_stars)
    owner_scope = _normalize_owner_scope(criteria.owner_scope)
    topic = _normalize_topic(criteria.topic)
    normalized = SearchCriteria(
        query=query,
        sort=SearchSort(criteria.sort),
        language=language,
        min_stars=min_stars,
        owner_scope=owner_scope,
        topic=topic,
        include_archived=bool(criteria.include_archived),
    )
    build_search_query(normalized)
    return normalized


def build_search_query(criteria: SearchCriteria) -> str:
    query = _normalize_query(criteria.query)
    parts = [query]
    if criteria.language is not None:
        parts.append(f'language:"{criteria.language.value}"')
    if criteria.min_stars is not None:
        parts.append(f"stars:>={_normalize_min_stars(criteria.min_stars)}")
    owner_scope = _normalize_owner_scope(criteria.owner_scope)
    if owner_scope is not None:
        parts.append(owner_scope)
    topic = _normalize_topic(criteria.topic)
    if topic is not None:
        parts.append(f"topic:{topic}")
    if not criteria.include_archived:
        parts.append("archived:false")
    compiled = " ".join(parts)
    if len(compiled) > SEARCH_COMPILED_QUERY_MAX_CHARS:
        raise SearchValidationError("search query is too long after filters")
    return compiled


def serialize_criteria(criteria: SearchCriteria) -> dict[str, object]:
    normalized = normalize_criteria(criteria)
    return {
        "query": normalized.query,
        "sort": normalized.sort.value,
        "language": normalized.language.value if normalized.language else None,
        "min_stars": normalized.min_stars,
        "owner_scope": normalized.owner_scope,
        "topic": normalized.topic,
        "include_archived": normalized.include_archived,
    }


def deserialize_criteria(data: object) -> SearchCriteria:
    if not isinstance(data, dict):
        raise SearchValidationError("search context is invalid")
    try:
        sort = SearchSort(data.get("sort", SearchSort.BEST_MATCH.value))
        language_raw = data.get("language")
        language = SearchLanguage(language_raw) if isinstance(language_raw, str) else None
        min_stars_raw = data.get("min_stars")
        min_stars = min_stars_raw if isinstance(min_stars_raw, int) else None
        owner_raw = data.get("owner_scope")
        owner = owner_raw if isinstance(owner_raw, str) else None
        topic_raw = data.get("topic")
        topic = topic_raw if isinstance(topic_raw, str) else None
        include_archived = data.get("include_archived", False)
        if not isinstance(include_archived, bool):
            raise SearchValidationError("search context is invalid")
        query = data.get("query")
        if not isinstance(query, str):
            raise SearchValidationError("search context is invalid")
    except ValueError as exc:
        raise SearchValidationError("search context is invalid") from exc
    return normalize_criteria(
        SearchCriteria(
            query=query,
            sort=sort,
            language=language,
            min_stars=min_stars,
            owner_scope=owner,
            topic=topic,
            include_archived=include_archived,
        )
    )


def normalize_owner_scope_input(value: str) -> str:
    return _normalize_owner_scope(value) or ""


def normalize_topic_input(value: str) -> str:
    return _normalize_topic(value) or ""


def normalize_min_stars_input(value: str) -> int:
    stripped = value.strip()
    if not stripped.isdigit():
        raise SearchValidationError("minimum stars must be a non-negative integer")
    return _normalize_min_stars(int(stripped)) or 0


def _normalize_query(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise SearchValidationError("search query is empty")
    if len(normalized) > SEARCH_QUERY_MAX_CHARS:
        raise SearchValidationError("search query is too long")
    if any(ord(character) < 32 for character in normalized):
        raise SearchValidationError("search query contains control characters")
    return normalized


def _normalize_min_stars(value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or value < 0 or value > SEARCH_MIN_STARS_MAX:
        raise SearchValidationError("minimum stars is outside the allowed range")
    return value


def _normalize_owner_scope(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    prefix, separator, login = normalized.partition(":")
    if separator != ":" or prefix not in {"user", "org"}:
        raise SearchValidationError("owner must use user:NAME or org:NAME")
    return f"{prefix}:{_normalize_login(login)}"


def _normalize_login(value: str) -> str:
    normalized = value.strip()
    if (
        not normalized
        or len(normalized) > SEARCH_OWNER_LOGIN_MAX_CHARS
        or _OWNER_RE.fullmatch(normalized) is None
    ):
        raise SearchValidationError("GitHub owner login is invalid")
    return normalized


def _normalize_repository_name(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > 100 or "/" in normalized or "\\" in normalized:
        raise SearchValidationError("repository name is invalid")
    return normalized


def _normalize_topic(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if len(normalized) > SEARCH_TOPIC_MAX_CHARS or _TOPIC_RE.fullmatch(normalized) is None:
        raise SearchValidationError("topic is invalid")
    return normalized
