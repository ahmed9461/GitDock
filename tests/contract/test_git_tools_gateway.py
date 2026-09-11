from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from gitdock.github.client import GitHubRestClient
from gitdock.github.git_tools import GitHubGitToolsGateway

_SHA = "a" * 40


def _commit_payload(sha: str = _SHA) -> dict[str, object]:
    return {
        "sha": sha,
        "html_url": f"https://github.com/ahmed9461/GitDock/commit/{sha}",
        "commit": {
            "message": "feat: test",
            "author": {"name": "Ahmed", "date": "2026-09-11T20:00:00Z"},
        },
        "parents": [],
        "stats": {"additions": 1, "deletions": 0},
        "files": [{"filename": "README.md"}],
    }


@pytest.mark.asyncio
async def test_git_tools_gateway_reads_branches_commits_and_compare() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path.endswith("/branches"):
            return httpx.Response(
                200,
                json=[
                    {
                        "name": "main",
                        "protected": True,
                        "commit": {"sha": _SHA},
                    }
                ],
                request=request,
            )
        if path.endswith("/commits"):
            return httpx.Response(200, json=[_commit_payload()], request=request)
        if "/compare/" in path:
            return httpx.Response(
                200,
                json={
                    "status": "ahead",
                    "ahead_by": 1,
                    "behind_by": 0,
                    "total_commits": 1,
                    "files": [
                        {
                            "filename": "README.md",
                            "status": "modified",
                            "additions": 1,
                            "deletions": 0,
                            "changes": 1,
                        }
                    ],
                },
                request=request,
            )
        return httpx.Response(200, json=_commit_payload(), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        gateway = GitHubGitToolsGateway(GitHubRestClient(http_client))
        token = SecretStr("ghs_read")
        branches = await gateway.list_branches(token, owner_login="ahmed9461", name="GitDock")
        commits = await gateway.recent_commits(
            token, owner_login="ahmed9461", name="GitDock", ref="main"
        )
        commit = await gateway.get_commit(token, owner_login="ahmed9461", name="GitDock", ref=_SHA)
        comparison = await gateway.compare(
            token,
            owner_login="ahmed9461",
            name="GitDock",
            base="main",
            head="feature/x",
        )

    assert branches[0].name == "main"
    assert commits[0].sha == _SHA
    assert commit.changed_files == 1
    assert comparison.ahead_by == 1
    assert requests[1].url.params["sha"] == "main"
    assert all(request.headers["Authorization"] == "Bearer ghs_read" for request in requests)
    assert requests[-1].url.raw_path.endswith(b"/compare/main...feature%2Fx")


@pytest.mark.asyncio
async def test_git_tools_gateway_branch_create_uses_one_post_and_expected_body() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            201,
            json={"ref": "refs/heads/feature/new", "object": {"sha": _SHA}},
            headers={"X-GitHub-Request-Id": "create-ref"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        gateway = GitHubGitToolsGateway(GitHubRestClient(http_client))
        created = await gateway.create_branch(
            SecretStr("ghs_write"),
            owner_login="ahmed9461",
            name="GitDock",
            branch="feature/new",
            sha=_SHA,
        )

    assert created.name == "feature/new"
    assert created.sha == _SHA
    assert created.request_id == "create-ref"
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].url.path == "/repos/ahmed9461/GitDock/git/refs"
    assert json.loads(requests[0].content) == {
        "ref": "refs/heads/feature/new",
        "sha": _SHA,
    }


@pytest.mark.asyncio
async def test_git_tools_gateway_create_does_not_retry_transient_failure() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"message": "temporary"}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        gateway = GitHubGitToolsGateway(GitHubRestClient(http_client, sleeper=_done))
        with pytest.raises(RuntimeError):
            await gateway.create_branch(
                SecretStr("ghs_write"),
                owner_login="ahmed9461",
                name="GitDock",
                branch="feature/new",
                sha=_SHA,
            )
    assert calls == 1


async def _done(_: float) -> None:
    return None
