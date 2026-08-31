from __future__ import annotations

from datetime import UTC, datetime

import pytest

from gitdock.github.search import RepositorySearchResponse, RepositorySearchResult
from gitdock.services.search import (
    RepositorySearchService,
    SearchCriteria,
    SearchLanguage,
    SearchSort,
    SearchValidationError,
    build_search_query,
    deserialize_criteria,
    normalize_owner_scope_input,
    normalize_topic_input,
    serialize_criteria,
)


def result(repository_id: int = 1) -> RepositorySearchResult:
    return RepositorySearchResult(
        github_repository_id=repository_id,
        owner_login="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        html_url="https://github.com/octocat/Hello-World",
        archived=False,
        fork=False,
        default_branch="main",
        language="Python",
        description="Example",
        stars=100,
        forks=10,
        license_spdx="MIT",
        topics=("telegram",),
        updated_at=datetime(2026, 8, 31, 15, tzinfo=UTC),
        pushed_at=datetime(2026, 8, 31, 14, tzinfo=UTC),
    )


class FakeSearchGateway:
    def __init__(self) -> None:
        self.search_calls: list[dict[str, object]] = []
        self.detail_calls: list[tuple[str, str]] = []

    async def search_repositories(
        self,
        *,
        query: str,
        page: int,
        per_page: int,
        sort: str | None = None,
        order: str | None = None,
    ) -> RepositorySearchResponse:
        self.search_calls.append(
            {
                "query": query,
                "page": page,
                "per_page": per_page,
                "sort": sort,
                "order": order,
            }
        )
        return RepositorySearchResponse(
            items=(result(),),
            total_count=13,
            incomplete_results=False,
        )

    async def get_public_repository(
        self,
        *,
        owner_login: str,
        name: str,
    ) -> RepositorySearchResult:
        self.detail_calls.append((owner_login, name))
        return result()


@pytest.mark.asyncio
async def test_search_service_builds_filters_sort_and_pagination() -> None:
    gateway = FakeSearchGateway()
    service = RepositorySearchService(gateway)
    criteria = SearchCriteria(
        query="telegram bot",
        sort=SearchSort.STARS,
        language=SearchLanguage.PYTHON,
        min_stars=1000,
        owner_scope="org:github",
        topic="machine-learning",
        include_archived=False,
    )

    page = await service.search(criteria, page=2)

    assert page.page == 2
    assert page.total_pages == 3
    assert page.total_items == 13
    assert gateway.search_calls == [
        {
            "query": (
                'telegram bot language:"Python" stars:>=1000 org:github '
                "topic:machine-learning archived:false"
            ),
            "page": 2,
            "per_page": 6,
            "sort": "stars",
            "order": "desc",
        }
    ]


@pytest.mark.asyncio
async def test_search_service_best_match_omits_sort_and_can_include_archived() -> None:
    gateway = FakeSearchGateway()
    service = RepositorySearchService(gateway)

    await service.search(SearchCriteria(query="aiogram", include_archived=True))

    call = gateway.search_calls[0]
    assert call["query"] == "aiogram"
    assert call["sort"] is None
    assert call["order"] is None


@pytest.mark.asyncio
async def test_search_detail_validates_owner_and_repository_segments() -> None:
    gateway = FakeSearchGateway()
    service = RepositorySearchService(gateway)

    repository = await service.detail(owner_login="octocat", name="Hello-World")

    assert repository.github_repository_id == 1
    assert gateway.detail_calls == [("octocat", "Hello-World")]
    with pytest.raises(SearchValidationError):
        await service.detail(owner_login="octocat/evil", name="Hello-World")


def test_search_criteria_serialization_round_trip() -> None:
    criteria = SearchCriteria(
        query="telegram",
        sort=SearchSort.UPDATED,
        language=SearchLanguage.TYPESCRIPT,
        min_stars=50,
        owner_scope="user:octocat",
        topic="bots",
        include_archived=True,
    )

    assert deserialize_criteria(serialize_criteria(criteria)) == criteria


def test_search_validation_rejects_unsafe_or_invalid_filter_values() -> None:
    with pytest.raises(SearchValidationError):
        build_search_query(SearchCriteria(query="   "))
    with pytest.raises(SearchValidationError):
        normalize_owner_scope_input("owner:octocat")
    with pytest.raises(SearchValidationError):
        normalize_owner_scope_input("org:bad/name")
    with pytest.raises(SearchValidationError):
        normalize_topic_input("Bad Topic!")
