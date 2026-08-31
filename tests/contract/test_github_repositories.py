from __future__ import annotations

from datetime import UTC

import httpx
import pytest
from pydantic import SecretStr

from gitdock.github.client import GitHubRestClient
from gitdock.github.repositories import GitHubRepositoryGateway, parse_repository


def repository_payload(
    repository_id: int,
    name: str,
    *,
    private: bool = False,
) -> dict[str, object]:
    return {
        "id": repository_id,
        "owner": {"login": "ahmed9461"},
        "name": name,
        "full_name": f"ahmed9461/{name}",
        "html_url": f"https://github.com/ahmed9461/{name}",
        "private": private,
        "archived": False,
        "fork": False,
        "default_branch": "main",
        "language": "Python",
        "description": "test repository",
        "stargazers_count": 12,
        "forks_count": 3,
        "updated_at": "2026-08-31T15:00:00Z",
        "pushed_at": "2026-08-31T14:00:00Z",
    }


@pytest.mark.asyncio
async def test_repository_gateway_lists_all_installation_pages_with_metadata_token() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.params.get("page") == "2":
            return httpx.Response(
                200,
                json={"total_count": 2, "repositories": [repository_payload(2, "WebHub")]},
            )
        return httpx.Response(
            200,
            json={"total_count": 2, "repositories": [repository_payload(1, "GitDock")]},
            headers={
                "Link": (
                    "<https://api.github.com/installation/repositories?per_page=100&page=2>; "
                    'rel="next"'
                )
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        gateway = GitHubRepositoryGateway(GitHubRestClient(http))
        repositories = await gateway.list_installation_repositories(
            SecretStr("ghs_repository_read")
        )

    assert [repository.full_name for repository in repositories] == [
        "ahmed9461/GitDock",
        "ahmed9461/WebHub",
    ]
    assert seen[0].url.params["per_page"] == "100"
    assert seen[0].headers["Authorization"] == "Bearer ghs_repository_read"
    assert "per_page=100" in str(seen[1].url)


@pytest.mark.asyncio
async def test_repository_gateway_gets_detail_through_canonical_repo_path() -> None:
    seen_path = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_path
        seen_path = request.url.path
        return httpx.Response(200, json=repository_payload(1351822221, "GitDock", private=True))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        gateway = GitHubRepositoryGateway(GitHubRestClient(http))
        repository = await gateway.get_repository(
            SecretStr("ghs_repository_read"),
            owner_login="ahmed9461",
            name="GitDock",
        )

    assert seen_path == "/repos/ahmed9461/GitDock"
    assert repository.github_repository_id == 1351822221
    assert repository.private is True
    assert repository.updated_at.tzinfo is UTC


def test_repository_parser_rejects_noncanonical_html_url() -> None:
    payload = repository_payload(1, "GitDock")
    payload["html_url"] = "https://evil.example/ahmed9461/GitDock"

    with pytest.raises(ValueError, match="canonical GitHub"):
        parse_repository(payload)


def test_repository_parser_rejects_inconsistent_full_name() -> None:
    payload = repository_payload(1, "GitDock")
    payload["full_name"] = "other/GitDock"

    with pytest.raises(ValueError, match="owner/name"):
        parse_repository(payload)
