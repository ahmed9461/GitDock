from __future__ import annotations

from datetime import UTC

import httpx
import pytest

from gitdock.github.client import GitHubRestClient
from gitdock.github.search import GitHubRepositorySearchGateway, parse_search_repository


def search_repository_payload(repository_id: int = 1296269) -> dict[str, object]:
    return {
        "id": repository_id,
        "owner": {"login": "octocat"},
        "name": "Hello-World",
        "full_name": "octocat/Hello-World",
        "html_url": "https://github.com/octocat/Hello-World",
        "private": False,
        "archived": False,
        "fork": False,
        "default_branch": "main",
        "language": "Python",
        "description": "Example repository",
        "stargazers_count": 4200,
        "forks_count": 300,
        "license": {"spdx_id": "MIT", "key": "mit"},
        "topics": ["telegram", "python"],
        "updated_at": "2026-08-31T15:00:00Z",
        "pushed_at": "2026-08-31T14:00:00Z",
    }


@pytest.mark.asyncio
async def test_search_gateway_uses_public_search_endpoint_without_authorization() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "total_count": 1,
                "incomplete_results": False,
                "items": [search_repository_payload()],
            },
            headers={"X-RateLimit-Resource": "search", "X-RateLimit-Remaining": "9"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        gateway = GitHubRepositorySearchGateway(GitHubRestClient(http))
        result = await gateway.search_repositories(
            query='telegram language:"Python" archived:false',
            page=2,
            per_page=6,
            sort="stars",
            order="desc",
        )

    assert result.total_count == 1
    assert result.incomplete_results is False
    assert result.items[0].license_spdx == "MIT"
    assert result.items[0].topics == ("telegram", "python")
    assert result.items[0].updated_at.tzinfo is UTC
    assert seen[0].url.path == "/search/repositories"
    assert seen[0].url.params["q"] == 'telegram language:"Python" archived:false'
    assert seen[0].url.params["page"] == "2"
    assert seen[0].url.params["per_page"] == "6"
    assert seen[0].url.params["sort"] == "stars"
    assert seen[0].url.params["order"] == "desc"
    assert "Authorization" not in seen[0].headers


@pytest.mark.asyncio
async def test_search_gateway_gets_public_detail_through_canonical_repo_path() -> None:
    seen_path = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_path
        seen_path = request.url.path
        return httpx.Response(200, json=search_repository_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        gateway = GitHubRepositorySearchGateway(GitHubRestClient(http))
        repository = await gateway.get_public_repository(
            owner_login="octocat",
            name="Hello-World",
        )

    assert seen_path == "/repos/octocat/Hello-World"
    assert repository.full_name == "octocat/Hello-World"


def test_search_parser_rejects_private_repository() -> None:
    payload = search_repository_payload()
    payload["private"] = True

    with pytest.raises(ValueError, match="non-public"):
        parse_search_repository(payload)


def test_search_parser_rejects_noncanonical_html_url() -> None:
    payload = search_repository_payload()
    payload["html_url"] = "https://evil.example/octocat/Hello-World"

    with pytest.raises(ValueError, match="canonical GitHub"):
        parse_search_repository(payload)
