from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from gitdock.github.client import GitHubRestClient
from gitdock.github.repository_admin import GitHubRepositoryAdminGateway, RepositoryCreateRequest


def repository_payload() -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": 1351822222,
        "name": "OrgRepo",
        "full_name": "example-org/OrgRepo",
        "html_url": "https://github.com/example-org/OrgRepo",
        "private": True,
        "archived": False,
        "fork": False,
        "default_branch": "main",
        "language": None,
        "description": "org repo",
        "stargazers_count": 0,
        "forks_count": 0,
        "updated_at": now,
        "pushed_at": now,
        "owner": {"login": "example-org"},
    }


@pytest.mark.asyncio
async def test_organization_repository_creation_uses_user_token_and_org_endpoint() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json=repository_payload(), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        gateway = GitHubRepositoryAdminGateway(GitHubRestClient(http_client))
        response = await gateway.create_organization_repository(
            SecretStr("ghu_user"),
            organization="example-org",
            request=RepositoryCreateRequest("OrgRepo", "org repo", True),
        )

    assert response.data.full_name == "example-org/OrgRepo"
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url.path == "/orgs/example-org/repos"
    assert request.headers["Authorization"] == "Bearer ghu_user"
    assert json.loads(request.content) == {
        "name": "OrgRepo",
        "description": "org repo",
        "private": True,
    }
