"""Compact callback payloads for P4.1 file browsing and one-file writes."""

from __future__ import annotations

import re

from gitdock.services.repositories import RepositoryFilter
from gitdock.telegram.callbacks import PREFIX

FILE_PREFIX = f"{PREFIX}:file"
_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{6,16}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{12,24}$")
_DIRECTORY_ACTIONS = {"create": "c", "upload": "u", "up": "p", "refresh": "r", "ref": "f"}
_DIRECTORY_ACTIONS_BY_CODE = {value: key for key, value in _DIRECTORY_ACTIONS.items()}
_FILE_ACTIONS = {
    "edit": "e",
    "replace": "r",
    "ref": "f",
    "download": "d",
    "delete": "x",
    "back": "b",
}
_FILE_ACTIONS_BY_CODE = {value: key for key, value in _FILE_ACTIONS.items()}
_WRITE_OPERATIONS = {"create": "c", "update": "u", "delete": "d"}
_WRITE_OPERATIONS_BY_CODE = {value: key for key, value in _WRITE_OPERATIONS.items()}
_WIZARD_ACTIONS = {"back": "b", "cancel": "c"}
_WIZARD_ACTIONS_BY_CODE = {value: key for key, value in _WIZARD_ACTIONS.items()}


def browser_open(repository_id: int, repository_filter: RepositoryFilter, page: int) -> str:
    if repository_id <= 0 or page <= 0:
        raise ValueError("repository ID and page must be positive")
    return f"{FILE_PREFIX}:open:{repository_filter.value}:{page}:{_base36(repository_id)}"


def parse_browser_open(data: str) -> tuple[int, RepositoryFilter, int] | None:
    prefix = f"{FILE_PREFIX}:open:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 3:
        return None
    try:
        repository_filter = RepositoryFilter(parts[0])
        page = int(parts[1])
        repository_id = int(parts[2], 36)
    except ValueError:
        return None
    if page <= 0 or repository_id <= 0:
        return None
    return repository_id, repository_filter, page


def entry(session_id: str, index: int) -> str:
    _require_session(session_id)
    if index < 0:
        raise ValueError("entry index must not be negative")
    return f"{FILE_PREFIX}:e:{session_id}:{_base36(index)}"


def parse_entry(data: str) -> tuple[str, int] | None:
    prefix = f"{FILE_PREFIX}:e:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2 or _SESSION_RE.fullmatch(parts[0]) is None:
        return None
    try:
        index = int(parts[1], 36)
    except ValueError:
        return None
    return (parts[0], index) if index >= 0 else None


def directory_action(session_id: str, action: str) -> str:
    _require_session(session_id)
    code = _DIRECTORY_ACTIONS.get(action)
    if code is None:
        raise ValueError("directory action is invalid")
    return f"{FILE_PREFIX}:d:{code}:{session_id}"


def parse_directory_action(data: str) -> tuple[str, str] | None:
    prefix = f"{FILE_PREFIX}:d:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2 or _SESSION_RE.fullmatch(parts[1]) is None:
        return None
    action = _DIRECTORY_ACTIONS_BY_CODE.get(parts[0])
    return (parts[1], action) if action is not None else None


def file_action(session_id: str, action: str) -> str:
    _require_session(session_id)
    code = _FILE_ACTIONS.get(action)
    if code is None:
        raise ValueError("file action is invalid")
    return f"{FILE_PREFIX}:a:{code}:{session_id}"


def parse_file_action(data: str) -> tuple[str, str] | None:
    prefix = f"{FILE_PREFIX}:a:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2 or _SESSION_RE.fullmatch(parts[1]) is None:
        return None
    action = _FILE_ACTIONS_BY_CODE.get(parts[0])
    return (parts[1], action) if action is not None else None


def preview_page(session_id: str, page: int) -> str:
    _require_session(session_id)
    if page <= 0:
        raise ValueError("preview page must be positive")
    return f"{FILE_PREFIX}:p:{session_id}:{_base36(page)}"


def parse_preview_page(data: str) -> tuple[str, int] | None:
    prefix = f"{FILE_PREFIX}:p:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2 or _SESSION_RE.fullmatch(parts[0]) is None:
        return None
    try:
        page = int(parts[1], 36)
    except ValueError:
        return None
    return (parts[0], page) if page > 0 else None


def wizard(session_id: str, action: str) -> str:
    _require_session(session_id)
    code = _WIZARD_ACTIONS.get(action)
    if code is None:
        raise ValueError("wizard action is invalid")
    return f"{FILE_PREFIX}:w:{code}:{session_id}"


def parse_wizard(data: str) -> tuple[str, str] | None:
    prefix = f"{FILE_PREFIX}:w:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2 or _SESSION_RE.fullmatch(parts[1]) is None:
        return None
    action = _WIZARD_ACTIONS_BY_CODE.get(parts[0])
    return (parts[1], action) if action is not None else None


def confirm(operation: str, token: str) -> str:
    code = _write_code(operation)
    _require_token(token)
    return f"{FILE_PREFIX}:y:{code}:{token}"


def parse_confirm(data: str) -> tuple[str, str] | None:
    return _parse_write_token(data, f"{FILE_PREFIX}:y:")


def cancel(operation: str, token: str) -> str:
    code = _write_code(operation)
    _require_token(token)
    return f"{FILE_PREFIX}:n:{code}:{token}"


def parse_cancel(data: str) -> tuple[str, str] | None:
    return _parse_write_token(data, f"{FILE_PREFIX}:n:")


def diff(session_id: str) -> str:
    _require_session(session_id)
    return f"{FILE_PREFIX}:diff:{session_id}"


def parse_diff(data: str) -> str | None:
    prefix = f"{FILE_PREFIX}:diff:"
    if not data.startswith(prefix):
        return None
    session_id = data[len(prefix) :]
    return session_id if _SESSION_RE.fullmatch(session_id) is not None else None


def _parse_write_token(data: str, prefix: str) -> tuple[str, str] | None:
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2 or _TOKEN_RE.fullmatch(parts[1]) is None:
        return None
    operation = _WRITE_OPERATIONS_BY_CODE.get(parts[0])
    return (operation, parts[1]) if operation is not None else None


def _write_code(operation: str) -> str:
    code = _WRITE_OPERATIONS.get(operation)
    if code is None:
        raise ValueError("file write operation is invalid")
    return code


def _require_session(session_id: str) -> None:
    if _SESSION_RE.fullmatch(session_id) is None:
        raise ValueError("file session ID is invalid")


def _require_token(token: str) -> None:
    if _TOKEN_RE.fullmatch(token) is None:
        raise ValueError("file confirmation token is invalid")


def _base36(value: int) -> str:
    if value == 0:
        return "0"
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    encoded = ""
    while value:
        value, remainder = divmod(value, 36)
        encoded = alphabet[remainder] + encoded
    return encoded
