"""Compact P4.2 Telegram callback helpers."""

from __future__ import annotations

from gitdock.services.repositories import RepositoryFilter
from gitdock.telegram.callbacks import PREFIX

ROOT = f"{PREFIX}:git"
_ROOT = ROOT
BRANCH_CREATE_BEGIN = f"{_ROOT}:bc:new"
BRANCH_SEARCH_BEGIN = f"{_ROOT}:bs:new"
COMPARE_BEGIN = f"{_ROOT}:cmp:new"
COMMIT_REF_BEGIN = f"{_ROOT}:cr:new"


def branches_open(repository_id: int, repository_filter: RepositoryFilter, page: int) -> str:
    return _repo_context("b", repository_id, repository_filter, page)


def commits_open(repository_id: int, repository_filter: RepositoryFilter, page: int) -> str:
    return _repo_context("c", repository_id, repository_filter, page)


def parse_repo_open(data: str, kind: str) -> tuple[int, RepositoryFilter, int] | None:
    prefix = f"{_ROOT}:{kind}:open:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 3:
        return None
    filter_raw, page_raw, repo_raw = parts
    try:
        repository_filter = RepositoryFilter(filter_raw)
        page = int(page_raw)
        repository_id = int(repo_raw, 36)
    except ValueError:
        return None
    if page <= 0 or repository_id <= 0:
        return None
    return repository_id, repository_filter, page


def branch_page(page: int) -> str:
    return _page("b", page)


def commit_page(page: int) -> str:
    return _page("c", page)


def item(kind: str, page: int, index: int) -> str:
    if kind not in {"b", "c"} or page <= 0 or index < 0:
        raise ValueError("invalid Git tools callback item")
    return f"{_ROOT}:{kind}:i:{page}:{index}"


def parse_item(data: str, kind: str) -> tuple[int, int] | None:
    prefix = f"{_ROOT}:{kind}:i:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2:
        return None
    try:
        page, index = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if page <= 0 or index < 0:
        return None
    return page, index


def parse_page(data: str, kind: str) -> int | None:
    prefix = f"{_ROOT}:{kind}:p:"
    if not data.startswith(prefix):
        return None
    try:
        page = int(data[len(prefix) :])
    except ValueError:
        return None
    return page if page > 0 else None


def branch_confirm(token: str) -> str:
    return f"{_ROOT}:bc:y:{token}"


def branch_cancel(token: str) -> str:
    return f"{_ROOT}:bc:n:{token}"


def parse_confirmation(data: str, answer: str) -> str | None:
    prefix = f"{_ROOT}:bc:{answer}:"
    if not data.startswith(prefix):
        return None
    token = data[len(prefix) :]
    if not (12 <= len(token) <= 32) or not token.replace("-", "").replace("_", "").isalnum():
        return None
    return token


def _repo_context(
    kind: str, repository_id: int, repository_filter: RepositoryFilter, page: int
) -> str:
    if kind not in {"b", "c"} or repository_id <= 0 or page <= 0:
        raise ValueError("invalid Git tools repository context")
    return f"{_ROOT}:{kind}:open:{repository_filter.value}:{page}:{_base36(repository_id)}"


def _page(kind: str, page: int) -> str:
    if kind not in {"b", "c"} or page <= 0:
        raise ValueError("invalid Git tools page")
    return f"{_ROOT}:{kind}:p:{page}"


def _base36(value: int) -> str:
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    result = ""
    while value:
        value, remainder = divmod(value, 36)
        result = alphabet[remainder] + result
    return result or "0"
