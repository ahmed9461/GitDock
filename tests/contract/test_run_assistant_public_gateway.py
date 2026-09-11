from __future__ import annotations

import base64

import httpx
import pytest

from gitdock.github.client import GitHubRestClient
from gitdock.github.contents import GitHubContentsGateway


@pytest.mark.asyncio
async def test_public_contents_reads_send_no_authorization_header() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/contents/package.json"):
            body = b'{"scripts":{"start":"node server.js"}}'
            return httpx.Response(
                200,
                json={
                    "type": "file",
                    "name": "package.json",
                    "path": "package.json",
                    "sha": "a" * 40,
                    "size": len(body),
                    "encoding": "base64",
                    "content": base64.b64encode(body).decode("ascii"),
                    "html_url": "https://github.com/octocat/Hello-World/blob/main/package.json",
                },
                request=request,
            )
        return httpx.Response(
            200,
            json=[
                {
                    "type": "file",
                    "name": "package.json",
                    "path": "package.json",
                    "sha": "a" * 40,
                    "size": 40,
                    "html_url": "https://github.com/octocat/Hello-World/blob/main/package.json",
                }
            ],
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        gateway = GitHubContentsGateway(GitHubRestClient(http_client))
        entries = await gateway.list_directory(
            None,
            owner_login="octocat",
            repository_name="Hello-World",
            path="",
            ref="main",
        )
        file = await gateway.get_file(
            None,
            owner_login="octocat",
            repository_name="Hello-World",
            path="package.json",
            ref="main",
        )

    assert entries[0].name == "package.json"
    assert file.content is not None
    assert all("Authorization" not in request.headers for request in requests)
    assert all(request.url.params["ref"] == "main" for request in requests)
