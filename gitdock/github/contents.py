"""Typed GitHub repository-contents endpoints for P4.1."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import StrEnum
from typing import cast
from urllib.parse import quote, urlparse

from pydantic import SecretStr

from gitdock.github.client import GitHubRestClient
from gitdock.github.errors import GitHubErrorKind, GitHubGatewayError
from gitdock.github.models import GitHubResponse


class ContentKind(StrEnum):
    FILE = "file"
    DIRECTORY = "dir"
    SYMLINK = "symlink"
    SUBMODULE = "submodule"


@dataclass(frozen=True, slots=True)
class ContentEntry:
    name: str
    path: str
    sha: str
    size: int
    kind: ContentKind
    html_url: str


@dataclass(frozen=True, slots=True)
class FileContent:
    name: str
    path: str
    sha: str
    size: int
    content: bytes | None
    html_url: str


@dataclass(frozen=True, slots=True)
class RefSnapshot:
    ref: str
    commit_sha: str


@dataclass(frozen=True, slots=True)
class FileWriteResult:
    content_sha: str | None
    commit_sha: str
    commit_html_url: str


class GitHubContentsGateway:
    def __init__(self, client: GitHubRestClient) -> None:
        self._client = client

    async def list_directory(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        ref: str,
    ) -> tuple[ContentEntry, ...]:
        response = await self._client.get_json(
            _contents_target(owner_login, repository_name, path),
            parser=parse_directory,
            token=token,
            params={"ref": ref},
        )
        return response.data

    async def get_file(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        ref: str,
    ) -> FileContent:
        response = await self._client.get_json(
            _contents_target(owner_login, repository_name, path),
            parser=parse_file,
            token=token,
            params={"ref": ref},
        )
        return response.data

    async def resolve_ref(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        ref: str,
    ) -> RefSnapshot:
        owner, repository = _repository_segments(owner_login, repository_name)
        encoded_ref = quote(_require_ref(ref), safe="")
        response = await self._client.get_json(
            f"/repos/{owner}/{repository}/commits/{encoded_ref}",
            parser=lambda payload: parse_ref(payload, ref),
            token=token,
        )
        return response.data

    async def get_branch(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        branch: str,
    ) -> RefSnapshot:
        owner, repository = _repository_segments(owner_login, repository_name)
        encoded_branch = quote(_require_ref(branch), safe="")
        response = await self._client.get_json(
            f"/repos/{owner}/{repository}/branches/{encoded_branch}",
            parser=lambda payload: parse_branch(payload, branch),
            token=token,
        )
        return response.data

    async def put_file(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        branch: str,
        message: str,
        content: bytes,
        expected_sha: str | None = None,
    ) -> GitHubResponse[FileWriteResult]:
        body: dict[str, object] = {
            "message": message,
            "content": base64.b64encode(content).decode("ascii"),
            "branch": branch,
        }
        if expected_sha is not None:
            body["sha"] = expected_sha
        response = await self._client.request_json(
            "PUT",
            _contents_target(owner_login, repository_name, path),
            parser=parse_write_result,
            token=token,
            json_body=body,
        )
        if response.data.content_sha is None:
            raise GitHubGatewayError(
                GitHubErrorKind.UNEXPECTED,
                "GitHub file write response did not identify the written content",
                status_code=response.status_code,
                request_id=response.request_id,
                rate_limit=response.rate_limit,
            )
        return response

    async def delete_file(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        branch: str,
        message: str,
        expected_sha: str,
    ) -> GitHubResponse[FileWriteResult]:
        return await self._client.request_json(
            "DELETE",
            _contents_target(owner_login, repository_name, path),
            parser=parse_write_result,
            token=token,
            json_body={"message": message, "sha": expected_sha, "branch": branch},
        )


def parse_directory(payload: object) -> tuple[ContentEntry, ...]:
    if not isinstance(payload, list):
        raise ValueError("expected directory listing")
    return tuple(parse_content_entry(item) for item in payload)


def parse_content_entry(payload: object) -> ContentEntry:
    data = _require_dict(payload, "content entry")
    kind = ContentKind(_require_str(data, "type"))
    return ContentEntry(
        name=_require_str(data, "name"),
        path=_require_str(data, "path"),
        sha=_require_sha(data, "sha"),
        size=_require_non_negative_int(data, "size"),
        kind=kind,
        html_url=_require_github_html_url(_require_str(data, "html_url")),
    )


def parse_file(payload: object) -> FileContent:
    data = _require_dict(payload, "file content")
    if data.get("type") != ContentKind.FILE.value:
        raise ValueError("requested content is not a file")
    encoding = data.get("encoding")
    encoded_content = data.get("content")
    content: bytes | None = None
    if encoding == "base64":
        if not isinstance(encoded_content, str):
            raise ValueError("base64 file content is missing")
        compact = "".join(encoded_content.split())
        try:
            content = base64.b64decode(compact, validate=True)
        except ValueError as exc:
            raise ValueError("base64 file content is invalid") from exc
    elif encoding not in {None, "none"}:
        raise ValueError("unsupported GitHub file encoding")
    return FileContent(
        name=_require_str(data, "name"),
        path=_require_str(data, "path"),
        sha=_require_sha(data, "sha"),
        size=_require_non_negative_int(data, "size"),
        content=content,
        html_url=_require_github_html_url(_require_str(data, "html_url")),
    )


def parse_ref(payload: object, ref: str) -> RefSnapshot:
    data = _require_dict(payload, "commit")
    return RefSnapshot(ref=ref, commit_sha=_require_sha(data, "sha"))


def parse_branch(payload: object, branch: str) -> RefSnapshot:
    data = _require_dict(payload, "branch")
    commit = _require_dict(data.get("commit"), "branch commit")
    return RefSnapshot(ref=branch, commit_sha=_require_sha(commit, "sha"))


def parse_write_result(payload: object) -> FileWriteResult:
    data = _require_dict(payload, "file write result")
    commit = _require_dict(data.get("commit"), "file write commit")
    content_payload = data.get("content")
    content_sha: str | None = None
    if content_payload is not None:
        content = _require_dict(content_payload, "written content")
        content_sha = _require_sha(content, "sha")
    return FileWriteResult(
        content_sha=content_sha,
        commit_sha=_require_sha(commit, "sha"),
        commit_html_url=_require_github_html_url(_require_str(commit, "html_url")),
    )


def _contents_target(owner_login: str, repository_name: str, path: str) -> str:
    owner, repository = _repository_segments(owner_login, repository_name)
    if not path:
        return f"/repos/{owner}/{repository}/contents"
    encoded_path = "/".join(quote(segment, safe="") for segment in path.split("/"))
    return f"/repos/{owner}/{repository}/contents/{encoded_path}"


def _repository_segments(owner_login: str, repository_name: str) -> tuple[str, str]:
    return (
        quote(_require_path_segment(owner_login, "owner"), safe=""),
        quote(_require_path_segment(repository_name, "repository"), safe=""),
    )


def _require_ref(value: str) -> str:
    if not value or "\x00" in value or "\\" in value:
        raise ValueError("Git ref is invalid")
    return value


def _require_path_segment(value: str, label: str) -> str:
    if not value or "/" in value or "\\" in value or "\x00" in value:
        raise ValueError(f"{label} is not a valid repository path segment")
    return value


def _require_dict(payload: object, label: str) -> dict[str, object]:
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise ValueError(f"expected {label} object")
    return cast(dict[str, object], payload)


def _require_str(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing content field {key}")
    return value


def _require_sha(data: dict[str, object], key: str) -> str:
    value = _require_str(data, key)
    if len(value) < 7 or len(value) > 128 or any(char not in "0123456789abcdefABCDEF" for char in value):
        raise ValueError(f"invalid Git SHA field {key}")
    return value.lower()


def _require_non_negative_int(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"invalid content integer field {key}")
    return value


def _require_github_html_url(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("GitHub HTML URL is not canonical HTTPS")
    return value
