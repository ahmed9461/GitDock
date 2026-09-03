from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from gitdock.github.client import GitHubRestClient
from gitdock.github.repository_admin import (
    GitHubRepositoryAdminGateway,
    RepositoryCreateRequest,
    RepositoryUpdateRequest,
)


def repository_payload(name: str = "GitDock") -> dict[str, object]:
    return {
        "id": 1351822221,
        "name": name,
        "full_name": f"ahmed9461/{name}",
        "html_url": f"https://github.com/ahmed9461/{name}",
        "private": True,
        "archived": False,
        "fork": False,
        "default_branch": "main",
        "language": "Python",
        "description": "repo",
        "stargazers_count": 1,
        "forks_count": 0,
        "updated_at": datetime.now(UTC).isoformat(),
        "pushed_at": datetime.now(UTC).isoformat(),
        "owner": {"login": "ahmed9461"},
    }


@pytest.mark.asyncio
async def test_repository_admin_gateway_uses_canonical_write_endpoints_without_retry() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "DELETE":
            return httpx.Response(204, request=request)
        return httpx.Response(200, json=repository_payload(), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        gateway = GitHubRepositoryAdminGateway(GitHubRestClient(http_client))
        token = SecretStr("ghu_test")
        created = await gateway.create_personal_repository(
            token,
            RepositoryCreateRequest("GitDock", "repo", True),
        )
        updated = await gateway.update_repository(
            token,
            owner_login="ahmed9461",
            name="GitDock",
            request=RepositoryUpdateRequest(archived=True),
        )
        deleted = await gateway.delete_repository(
            token,
            owner_login="ahmed9461",
            name="GitDock",
        )

    assert created.data.full_name == "ahmed9461/GitDock"
    assert updated.data.github_repository_id == 1351822221
    assert deleted.status_code == 204
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/user/repos"),
        ("PATCH", "/repos/ahmed9461/GitDock"),
        ("DELETE", "/repos/ahmed9461/GitDock"),
    ]
    assert json.loads(requests[0].content) == {
        "name": "GitDock",
        "description": "repo",
        "private": True,
    }
    assert json.loads(requests[1].content) == {"archived": True}
    assert all(request.headers["Authorization"] == "Bearer ghu_test" for request in requests)


@pytest.mark.asyncio
async def test_no_content_transport_rejects_unexpected_body() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"unexpected", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GitHubRestClient(http_client)
        with pytest.raises(RuntimeError, match="unexpected non-empty response"):
            await client.request_empty("DELETE", "/repos/a/b")
