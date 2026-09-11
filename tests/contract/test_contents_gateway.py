from __future__ import annotations

import base64
import json

import httpx
import pytest
from pydantic import SecretStr

from gitdock.github.client import GitHubRestClient
from gitdock.github.contents import GitHubContentsGateway

_BRANCH_SHA = "a" * 40
_FILE_SHA = "b" * 40
_NEW_FILE_SHA = "c" * 40
_COMMIT_SHA = "d" * 40


def _file_payload(*, content: bytes = b"hello\n", sha: str = _FILE_SHA) -> dict[str, object]:
    return {
        "type": "file",
        "name": "README.md",
        "path": "docs/README.md",
        "sha": sha,
        "size": len(content),
        "encoding": "base64",
        "content": base64.b64encode(content).decode("ascii"),
        "html_url": "https://github.com/ahmed9461/GitDock/blob/main/docs/README.md",
    }


def _write_payload(content_sha: str | None) -> dict[str, object]:
    return {
        "content": None if content_sha is None else {"sha": content_sha},
        "commit": {
            "sha": _COMMIT_SHA,
            "html_url": f"https://github.com/ahmed9461/GitDock/commit/{_COMMIT_SHA}",
        },
    }


@pytest.mark.asyncio
async def test_contents_gateway_reads_refs_directories_and_files() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/commits/main"):
            return httpx.Response(200, json={"sha": _BRANCH_SHA}, request=request)
        if "/branches/" in request.url.path:
            return httpx.Response(
                200,
                json={"name": "feature/docs", "commit": {"sha": _BRANCH_SHA}},
                request=request,
            )
        if request.url.path.endswith("/contents/docs/README.md"):
            return httpx.Response(200, json=_file_payload(), request=request)
        return httpx.Response(
            200,
            json=[
                {
                    "type": "dir",
                    "name": "api",
                    "path": "docs/api",
                    "sha": "e" * 40,
                    "size": 0,
                    "html_url": "https://github.com/ahmed9461/GitDock/tree/main/docs/api",
                },
                _file_payload(),
            ],
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        gateway = GitHubContentsGateway(GitHubRestClient(http_client))
        token = SecretStr("ghs_read")
        resolved = await gateway.resolve_ref(
            token, owner_login="ahmed9461", repository_name="GitDock", ref="main"
        )
        branch = await gateway.get_branch(
            token,
            owner_login="ahmed9461",
            repository_name="GitDock",
            branch="feature/docs",
        )
        directory = await gateway.list_directory(
            token,
            owner_login="ahmed9461",
            repository_name="GitDock",
            path="docs",
            ref=_BRANCH_SHA,
        )
        file = await gateway.get_file(
            token,
            owner_login="ahmed9461",
            repository_name="GitDock",
            path="docs/README.md",
            ref=_BRANCH_SHA,
        )

    assert resolved.commit_sha == _BRANCH_SHA
    assert branch.commit_sha == _BRANCH_SHA
    assert [entry.name for entry in directory] == ["api", "README.md"]
    assert file.content == b"hello\n"
    assert requests[2].url.params["ref"] == _BRANCH_SHA
    assert requests[3].url.params["ref"] == _BRANCH_SHA
    assert all(request.headers["Authorization"] == "Bearer ghs_read" for request in requests)
    assert "feature%2Fdocs" in str(requests[1].url)


@pytest.mark.asyncio
async def test_contents_gateway_writes_once_with_expected_sha_and_branch() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "PUT":
            return httpx.Response(200, json=_write_payload(_NEW_FILE_SHA), request=request)
        return httpx.Response(200, json=_write_payload(None), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        gateway = GitHubContentsGateway(GitHubRestClient(http_client))
        token = SecretStr("ghs_write")
        updated = await gateway.put_file(
            token,
            owner_login="ahmed9461",
            repository_name="GitDock",
            path="docs/README.md",
            branch="feature/docs",
            message="Update docs/README.md via GitDock",
            content=b"new\n",
            expected_sha=_FILE_SHA,
        )
        deleted = await gateway.delete_file(
            token,
            owner_login="ahmed9461",
            repository_name="GitDock",
            path="docs/README.md",
            branch="feature/docs",
            message="Delete docs/README.md via GitDock",
            expected_sha=_NEW_FILE_SHA,
        )

    assert updated.data.content_sha == _NEW_FILE_SHA
    assert deleted.data.content_sha is None
    assert [(request.method, request.url.path) for request in requests] == [
        ("PUT", "/repos/ahmed9461/GitDock/contents/docs/README.md"),
        ("DELETE", "/repos/ahmed9461/GitDock/contents/docs/README.md"),
    ]
    update_body = json.loads(requests[0].content)
    assert update_body == {
        "message": "Update docs/README.md via GitDock",
        "content": base64.b64encode(b"new\n").decode("ascii"),
        "branch": "feature/docs",
        "sha": _FILE_SHA,
    }
    delete_body = json.loads(requests[1].content)
    assert delete_body == {
        "message": "Delete docs/README.md via GitDock",
        "sha": _NEW_FILE_SHA,
        "branch": "feature/docs",
    }
    assert all(request.headers["Authorization"] == "Bearer ghs_write" for request in requests)


@pytest.mark.asyncio
async def test_contents_gateway_write_transport_does_not_retry_transient_failure() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"message": "temporary"}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        gateway = GitHubContentsGateway(GitHubRestClient(http_client, sleeper=lambda _: _done()))
        with pytest.raises(RuntimeError):
            await gateway.put_file(
                SecretStr("ghs_write"),
                owner_login="ahmed9461",
                repository_name="GitDock",
                path="README.md",
                branch="main",
                message="Update README.md via GitDock",
                content=b"x",
            )
    assert calls == 1


async def _done() -> None:
    return None
