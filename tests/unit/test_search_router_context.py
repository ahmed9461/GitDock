from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from gitdock.github.search import RepositorySearchResult
from gitdock.services.search import SearchCriteria, serialize_criteria
from gitdock.telegram.routers.search import (
    _criteria_for_session,
    _result_context,
    _search_result_target,
)


class FakeState:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    async def get_data(self) -> dict[str, Any]:
        return self.data


def repository(repository_id: int = 1296269) -> RepositorySearchResult:
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
        description=None,
        stars=1,
        forks=0,
        license_spdx="MIT",
        topics=(),
        updated_at=datetime(2026, 8, 31, 15, tzinfo=UTC),
        pushed_at=None,
    )


@pytest.mark.asyncio
async def test_old_search_session_cannot_resolve_newer_search_context() -> None:
    criteria = SearchCriteria(query="telegram")
    state = FakeState(
        {
            "repository_search_session": "New_1234",
            "repository_search_criteria": serialize_criteria(criteria),
        }
    )

    current = await _criteria_for_session(state, "New_1234")  # type: ignore[arg-type]
    stale = await _criteria_for_session(state, "Old_1234")  # type: ignore[arg-type]

    assert current == criteria
    assert stale is None


@pytest.mark.asyncio
async def test_search_detail_target_must_exist_in_current_result_context() -> None:
    item = repository()
    state = FakeState({"repository_search_results": _result_context((item,))})

    target = await _search_result_target(state, item.github_repository_id)  # type: ignore[arg-type]
    missing = await _search_result_target(state, 999999)  # type: ignore[arg-type]

    assert target == ("octocat", "Hello-World")
    assert missing is None
