"""Typed branch/commit GitHub endpoints for P4.2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from urllib.parse import quote

from pydantic import SecretStr

from gitdock.github.client import GitHubRestClient


@dataclass(frozen=True, slots=True)
class BranchSnapshot:
    name: str
    sha: str
    protected: bool


@dataclass(frozen=True, slots=True)
class CommitSummary:
    sha: str
    message: str
    author_name: str
    authored_at: datetime
    html_url: str


@dataclass(frozen=True, slots=True)
class CommitDetail:
    sha: str
    message: str
    author_name: str
    authored_at: datetime
    html_url: str
    parents: tuple[str, ...]
    additions: int
    deletions: int
    changed_files: int


@dataclass(frozen=True, slots=True)
class CompareFile:
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int


@dataclass(frozen=True, slots=True)
class CompareSnapshot:
    status: str
    ahead_by: int
    behind_by: int
    total_commits: int
    files: tuple[CompareFile, ...]


@dataclass(frozen=True, slots=True)
class CreatedBranch:
    name: str
    sha: str
    request_id: str | None


class GitHubGitToolsGateway:
    """Branch/commit operations through the canonical REST transport."""

    def __init__(self, client: GitHubRestClient) -> None:
        self._client = client

    async def list_branches(
        self, token: SecretStr, *, owner_login: str, name: str
    ) -> tuple[BranchSnapshot, ...]:
        owner, repo = _repo_path(owner_login, name)
        items: list[BranchSnapshot] = []
        async for page in self._client.iter_pages(
            f"/repos/{owner}/{repo}/branches",
            item_parser=parse_branch,
            token=token,
            params={"per_page": 100},
            max_pages=10,
        ):
            items.extend(page.items)
        return tuple(items)

    async def get_branch(
        self, token: SecretStr, *, owner_login: str, name: str, branch: str
    ) -> BranchSnapshot:
        owner, repo = _repo_path(owner_login, name)
        encoded = quote(validate_ref(branch), safe="")
        response = await self._client.get_json(
            f"/repos/{owner}/{repo}/branches/{encoded}", parser=parse_branch, token=token
        )
        return response.data

    async def recent_commits(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        ref: str | None = None,
        limit: int = 30,
    ) -> tuple[CommitSummary, ...]:
        owner, repo = _repo_path(owner_login, name)
        params: dict[str, str | int] = {"per_page": max(1, min(limit, 100))}
        if ref is not None:
            params["sha"] = validate_ref(ref)
        page = await self._client.get_page(
            f"/repos/{owner}/{repo}/commits",
            item_parser=parse_commit_summary,
            token=token,
            params=params,
        )
        return page.items

    async def get_commit(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        ref: str,
    ) -> CommitDetail:
        owner, repo = _repo_path(owner_login, name)
        encoded = quote(validate_ref(ref), safe="")
        response = await self._client.get_json(
            f"/repos/{owner}/{repo}/commits/{encoded}", parser=parse_commit_detail, token=token
        )
        return response.data

    async def compare(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        base: str,
        head: str,
    ) -> CompareSnapshot:
        owner, repo = _repo_path(owner_login, name)
        base_encoded = quote(validate_ref(base), safe="")
        head_encoded = quote(validate_ref(head), safe="")
        response = await self._client.get_json(
            f"/repos/{owner}/{repo}/compare/{base_encoded}...{head_encoded}",
            parser=parse_compare,
            token=token,
        )
        return response.data

    async def create_branch(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        branch: str,
        sha: str,
    ) -> CreatedBranch:
        owner, repo = _repo_path(owner_login, name)
        response = await self._client.request_json(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            parser=lambda payload: parse_created_branch(payload, expected_branch=branch),
            token=token,
            json_body={
                "ref": f"refs/heads/{validate_branch_name(branch)}",
                "sha": _require_sha(sha),
            },
        )
        created = response.data
        return CreatedBranch(created.name, created.sha, response.request_id)


def parse_branch(payload: object) -> BranchSnapshot:
    data = _dict(payload, "branch")
    commit = _dict(data.get("commit"), "branch commit")
    return BranchSnapshot(
        name=_str(data, "name"),
        sha=_sha(_str(commit, "sha")),
        protected=_bool(data, "protected"),
    )


def parse_commit_summary(payload: object) -> CommitSummary:
    data = _dict(payload, "commit summary")
    commit = _dict(data.get("commit"), "commit")
    author = _dict(commit.get("author"), "commit author")
    return CommitSummary(
        sha=_sha(_str(data, "sha")),
        message=_str(commit, "message"),
        author_name=_str(author, "name"),
        authored_at=_datetime(_str(author, "date")),
        html_url=_github_url(_str(data, "html_url")),
    )


def parse_commit_detail(payload: object) -> CommitDetail:
    data = _dict(payload, "commit detail")
    summary = parse_commit_summary(data)
    parents_raw = data.get("parents")
    if not isinstance(parents_raw, list):
        raise ValueError("commit parents missing")
    parents = tuple(_sha(_str(_dict(item, "parent"), "sha")) for item in parents_raw)
    stats = _dict(data.get("stats"), "commit stats")
    files = data.get("files")
    if not isinstance(files, list):
        raise ValueError("commit files missing")
    return CommitDetail(
        sha=summary.sha,
        message=summary.message,
        author_name=summary.author_name,
        authored_at=summary.authored_at,
        html_url=summary.html_url,
        parents=parents,
        additions=_nonneg(stats, "additions"),
        deletions=_nonneg(stats, "deletions"),
        changed_files=len(files),
    )


def parse_compare(payload: object) -> CompareSnapshot:
    data = _dict(payload, "compare")
    files_raw = data.get("files")
    if not isinstance(files_raw, list):
        raise ValueError("compare files missing")
    files = tuple(
        CompareFile(
            filename=_str(item_data, "filename"),
            status=_str(item_data, "status"),
            additions=_nonneg(item_data, "additions"),
            deletions=_nonneg(item_data, "deletions"),
            changes=_nonneg(item_data, "changes"),
        )
        for item_data in (_dict(item, "compare file") for item in files_raw)
    )
    return CompareSnapshot(
        status=_str(data, "status"),
        ahead_by=_nonneg(data, "ahead_by"),
        behind_by=_nonneg(data, "behind_by"),
        total_commits=_nonneg(data, "total_commits"),
        files=files,
    )


def parse_created_branch(payload: object, *, expected_branch: str) -> CreatedBranch:
    data = _dict(payload, "created ref")
    expected = validate_branch_name(expected_branch)
    if _str(data, "ref") != f"refs/heads/{expected}":
        raise ValueError("created ref did not match requested branch")
    obj = _dict(data.get("object"), "created ref object")
    return CreatedBranch(expected, _sha(_str(obj, "sha")), None)


def _repo_path(owner_login: str, name: str) -> tuple[str, str]:
    return quote(_segment(owner_login), safe=""), quote(_segment(name), safe="")


def _segment(value: str) -> str:
    value = value.strip()
    if not value or "/" in value or "\\" in value or "\x00" in value:
        raise ValueError("invalid repository path segment")
    return value


def validate_ref(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 255 or "\x00" in value or "\n" in value or "\r" in value:
        raise ValueError("invalid Git ref")
    return value


def validate_branch_name(value: str) -> str:
    value = validate_ref(value)
    if (
        value.startswith("-")
        or value.startswith("/")
        or value.endswith("/")
        or value.endswith(".")
        or ".." in value
        or "//" in value
        or "@{" in value
        or any(ch in value for ch in " ~^:?*[\\")
    ):
        raise ValueError("invalid branch name")
    return value


def _require_sha(value: str) -> str:
    return _sha(value.strip())


def _sha(value: str) -> str:
    if len(value) != 40 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise ValueError("invalid Git SHA")
    return value.lower()


def _dict(payload: object, label: str) -> dict[str, object]:
    if not isinstance(payload, dict) or not all(isinstance(k, str) for k in payload):
        raise ValueError(f"expected {label} object")
    return cast(dict[str, object], payload)


def _str(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing field {key}")
    return value


def _bool(data: dict[str, object], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"missing boolean {key}")
    return value


def _nonneg(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"missing non-negative integer {key}")
    return value


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp is missing timezone")
    return parsed.astimezone(UTC)


def _github_url(value: str) -> str:
    if not value.startswith("https://github.com/"):
        raise ValueError("commit URL is not canonical GitHub HTTPS")
    return value
