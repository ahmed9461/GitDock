"""Compact callback helpers for P4.3 command generation."""

from __future__ import annotations

import re

from gitdock.domain.run_assistant import TargetOS
from gitdock.services.repositories import RepositoryFilter
from gitdock.telegram.callbacks import PREFIX

ROOT = f"{PREFIX}:run"
_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{6,16}$")
_OS_CODES = {
    TargetOS.WINDOWS: "w",
    TargetOS.LINUX: "l",
    TargetOS.MACOS: "m",
}
_OS_BY_CODE = {value: key for key, value in _OS_CODES.items()}


def repository_open(
    repository_id: int,
    repository_filter: RepositoryFilter,
    page: int,
) -> str:
    return _repository_callback("o", repository_id, repository_filter, page)


def repository_os(
    target_os: TargetOS,
    repository_id: int,
    repository_filter: RepositoryFilter,
    page: int,
) -> str:
    return _repository_callback(
        _OS_CODES[TargetOS(target_os)], repository_id, repository_filter, page
    )


def parse_repository(
    data: str,
) -> tuple[TargetOS | None, int, RepositoryFilter, int] | None:
    prefix = f"{ROOT}:r:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 4:
        return None
    os_code, filter_raw, page_raw, repository_raw = parts
    target_os = None if os_code == "o" else _OS_BY_CODE.get(os_code)
    if os_code != "o" and target_os is None:
        return None
    try:
        repository_filter = RepositoryFilter(filter_raw)
        page = int(page_raw)
        repository_id = int(repository_raw, 36)
    except ValueError:
        return None
    if page <= 0 or repository_id <= 0:
        return None
    return target_os, repository_id, repository_filter, page


def search_open(session_id: str, page: int, repository_id: int) -> str:
    return _search_callback("o", session_id, page, repository_id)


def search_os(target_os: TargetOS, session_id: str, page: int, repository_id: int) -> str:
    return _search_callback(_OS_CODES[TargetOS(target_os)], session_id, page, repository_id)


def parse_search(data: str) -> tuple[TargetOS | None, str, int, int] | None:
    prefix = f"{ROOT}:s:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 4:
        return None
    os_code, session_id, page_raw, repository_raw = parts
    if _SESSION_RE.fullmatch(session_id) is None:
        return None
    target_os = None if os_code == "o" else _OS_BY_CODE.get(os_code)
    if os_code != "o" and target_os is None:
        return None
    try:
        page = int(page_raw)
        repository_id = int(repository_raw, 36)
    except ValueError:
        return None
    if page <= 0 or repository_id <= 0:
        return None
    return target_os, session_id, page, repository_id


def _repository_callback(
    os_code: str,
    repository_id: int,
    repository_filter: RepositoryFilter,
    page: int,
) -> str:
    if os_code not in {"o", *_OS_BY_CODE} or repository_id <= 0 or page <= 0:
        raise ValueError("run repository callback is invalid")
    return f"{ROOT}:r:{os_code}:{repository_filter.value}:{page}:{_base36(repository_id)}"


def _search_callback(os_code: str, session_id: str, page: int, repository_id: int) -> str:
    if (
        os_code not in {"o", *_OS_BY_CODE}
        or _SESSION_RE.fullmatch(session_id) is None
        or page <= 0
        or repository_id <= 0
    ):
        raise ValueError("run search callback is invalid")
    return f"{ROOT}:s:{os_code}:{session_id}:{page}:{_base36(repository_id)}"


def _base36(value: int) -> str:
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    result = ""
    while value:
        value, remainder = divmod(value, 36)
        result = alphabet[remainder] + result
    return result or "0"
