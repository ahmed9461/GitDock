"""Compact versioned Telegram callback helpers."""

from __future__ import annotations

import re

from gitdock.core.constants import CALLBACK_SCHEMA_VERSION, TELEGRAM_CALLBACK_PREFIX
from gitdock.services.repositories import RepositoryFilter
from gitdock.services.search import SearchLanguage, SearchSort

PREFIX = f"{TELEGRAM_CALLBACK_PREFIX}:{CALLBACK_SCHEMA_VERSION}"
HOME_OPEN = f"{PREFIX}:home:open"
HOME_REFRESH = f"{PREFIX}:home:refresh"
CONNECT_BEGIN = f"{PREFIX}:connect:begin"
CONNECT_INFO = f"{PREFIX}:connect:info"
ACCOUNT_OPEN = f"{PREFIX}:account:open"
ACCOUNT_REFRESH = f"{PREFIX}:account:refresh"
ACCOUNT_AUTHORIZE = f"{PREFIX}:account:authorize"
ACCOUNT_DISCONNECT_BEGIN = f"{PREFIX}:account:disconnect:begin"
SEARCH_BEGIN = f"{PREFIX}:search:begin"
REPOSITORY_CREATE_BEGIN = f"{PREFIX}:repo:create:begin"
REPOSITORY_CREATE_SKIP_DESCRIPTION = f"{PREFIX}:repo:create:skip"
REPOSITORY_CREATE_PRIVATE = f"{PREFIX}:repo:create:private"
REPOSITORY_CREATE_PUBLIC = f"{PREFIX}:repo:create:public"
REPOSITORY_CREATE_BACK_NAME = f"{PREFIX}:repo:create:back:name"
REPOSITORY_CREATE_BACK_DESCRIPTION = f"{PREFIX}:repo:create:back:description"
PLACEHOLDER_PREFIX = f"{PREFIX}:later:"

_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{6,16}$")
_CONFIRMATION_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{12,24}$")
_LANGUAGE_CODES = {
    SearchLanguage.PYTHON: "py",
    SearchLanguage.JAVASCRIPT: "js",
    SearchLanguage.TYPESCRIPT: "ts",
    SearchLanguage.KOTLIN: "kt",
}
_LANGUAGE_BY_CODE = {value: key for key, value in _LANGUAGE_CODES.items()}
_REPOSITORY_SETTING_ACTIONS = {"name", "desc", "visibility", "archive", "branch", "delete"}
_ADMIN_CANCEL_OPERATION_CODES = {"create": "c", "update": "u", "delete": "d"}
_ADMIN_CANCEL_OPERATION_BY_CODE = {
    value: key for key, value in _ADMIN_CANCEL_OPERATION_CODES.items()
}
_ADMIN_CANCEL_DESTINATION_CODES = {"home": "h", "edit": "e", "settings": "s"}
_ADMIN_CANCEL_DESTINATION_BY_CODE = {
    value: key for key, value in _ADMIN_CANCEL_DESTINATION_CODES.items()
}


def repository_list(repository_filter: RepositoryFilter, page: int) -> str:
    if page <= 0:
        raise ValueError("page must be positive")
    return f"{PREFIX}:repos:list:{repository_filter.value}:{page}"


def parse_repository_list(data: str) -> tuple[RepositoryFilter, int] | None:
    parts = data.split(":")
    if len(parts) != 6 or ":".join(parts[:4]) != f"{PREFIX}:repos:list":
        return None
    try:
        repository_filter = RepositoryFilter(parts[4])
        page = int(parts[5])
    except (ValueError, TypeError):
        return None
    if page <= 0:
        return None
    return repository_filter, page


def repository_open(
    github_repository_id: int,
    repository_filter: RepositoryFilter,
    page: int,
) -> str:
    if github_repository_id <= 0 or page <= 0:
        raise ValueError("repository ID and page must be positive")
    return f"{PREFIX}:repo:open:{repository_filter.value}:{page}:{_base36(github_repository_id)}"


def parse_repository_open(data: str) -> tuple[int, RepositoryFilter, int] | None:
    prefix = f"{PREFIX}:repo:open:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 3:
        return None
    filter_raw, page_raw, encoded = parts
    try:
        repository_filter = RepositoryFilter(filter_raw)
        page = int(page_raw)
        value = int(encoded, 36)
    except ValueError:
        return None
    if page <= 0 or value <= 0:
        return None
    return value, repository_filter, page


def repository_settings(
    github_repository_id: int,
    repository_filter: RepositoryFilter,
    page: int,
) -> str:
    if github_repository_id <= 0 or page <= 0:
        raise ValueError("repository ID and page must be positive")
    return (
        f"{PREFIX}:repo:settings:{repository_filter.value}:{page}:{_base36(github_repository_id)}"
    )


def parse_repository_settings(data: str) -> tuple[int, RepositoryFilter, int] | None:
    prefix = f"{PREFIX}:repo:settings:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 3:
        return None
    filter_raw, page_raw, encoded = parts
    try:
        repository_filter = RepositoryFilter(filter_raw)
        page = int(page_raw)
        repository_id = int(encoded, 36)
    except ValueError:
        return None
    if page <= 0 or repository_id <= 0:
        return None
    return repository_id, repository_filter, page


def repository_setting_action(
    github_repository_id: int,
    action: str,
    repository_filter: RepositoryFilter,
    page: int,
) -> str:
    if github_repository_id <= 0 or page <= 0 or action not in _REPOSITORY_SETTING_ACTIONS:
        raise ValueError("repository setting action is invalid")
    return (
        f"{PREFIX}:repo:set:{action}:{repository_filter.value}:{page}:"
        f"{_base36(github_repository_id)}"
    )


def parse_repository_setting_action(
    data: str,
) -> tuple[int, str, RepositoryFilter, int] | None:
    prefix = f"{PREFIX}:repo:set:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 4:
        return None
    action, filter_raw, page_raw, encoded = parts
    if action not in _REPOSITORY_SETTING_ACTIONS:
        return None
    try:
        repository_filter = RepositoryFilter(filter_raw)
        page = int(page_raw)
        repository_id = int(encoded, 36)
    except ValueError:
        return None
    if page <= 0 or repository_id <= 0:
        return None
    return repository_id, action, repository_filter, page


def repository_create_confirm(token: str) -> str:
    _require_confirmation_token(token)
    return f"{PREFIX}:repo:create:confirm:{token}"


def parse_repository_create_confirm(data: str) -> str | None:
    return _parse_token_suffix(data, f"{PREFIX}:repo:create:confirm:")


def repository_update_confirm(token: str) -> str:
    _require_confirmation_token(token)
    return f"{PREFIX}:repo:update:confirm:{token}"


def parse_repository_update_confirm(data: str) -> str | None:
    return _parse_token_suffix(data, f"{PREFIX}:repo:update:confirm:")


def repository_delete_confirm(token: str) -> str:
    _require_confirmation_token(token)
    return f"{PREFIX}:repo:delete:confirm:{token}"


def parse_repository_delete_confirm(data: str) -> str | None:
    return _parse_token_suffix(data, f"{PREFIX}:repo:delete:confirm:")


def repository_admin_cancel(operation: str, destination: str, token: str) -> str:
    _require_confirmation_token(token)
    operation_code = _ADMIN_CANCEL_OPERATION_CODES.get(operation)
    destination_code = _ADMIN_CANCEL_DESTINATION_CODES.get(destination)
    if operation_code is None or destination_code is None:
        raise ValueError("repository cancellation callback is invalid")
    return f"{PREFIX}:repo:cancel:{operation_code}:{destination_code}:{token}"


def parse_repository_admin_cancel(data: str) -> tuple[str, str, str] | None:
    prefix = f"{PREFIX}:repo:cancel:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 3:
        return None
    operation = _ADMIN_CANCEL_OPERATION_BY_CODE.get(parts[0])
    destination = _ADMIN_CANCEL_DESTINATION_BY_CODE.get(parts[1])
    token = parts[2]
    if operation is None or destination is None or _CONFIRMATION_TOKEN_RE.fullmatch(token) is None:
        return None
    return operation, destination, token


def repository_filters(repository_filter: RepositoryFilter, page: int) -> str:
    if page <= 0:
        raise ValueError("page must be positive")
    return f"{PREFIX}:repos:filters:{repository_filter.value}:{page}"


def parse_repository_filters(data: str) -> tuple[RepositoryFilter, int] | None:
    prefix = f"{PREFIX}:repos:filters:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2:
        return None
    try:
        repository_filter = RepositoryFilter(parts[0])
        page = int(parts[1])
    except ValueError:
        return None
    if page <= 0:
        return None
    return repository_filter, page


def repository_filter(repository_filter: RepositoryFilter) -> str:
    return f"{PREFIX}:repos:filter:{repository_filter.value}"


def parse_repository_filter(data: str) -> RepositoryFilter | None:
    prefix = f"{PREFIX}:repos:filter:"
    if not data.startswith(prefix):
        return None
    try:
        return RepositoryFilter(data[len(prefix) :])
    except ValueError:
        return None


def account_disconnect_confirm(token: str) -> str:
    _require_confirmation_token(token)
    return f"{PREFIX}:account:disconnect:yes:{token}"


def parse_account_disconnect_confirm(data: str) -> str | None:
    return _parse_confirmation_callback(data, "yes")


def account_disconnect_cancel(token: str) -> str:
    _require_confirmation_token(token)
    return f"{PREFIX}:account:disconnect:no:{token}"


def parse_account_disconnect_cancel(data: str) -> str | None:
    return _parse_confirmation_callback(data, "no")


def search_results(session_id: str, page: int) -> str:
    _require_session_id(session_id)
    if page <= 0:
        raise ValueError("page must be positive")
    return f"{PREFIX}:search:list:{session_id}:{page}"


def parse_search_results(data: str) -> tuple[str, int] | None:
    prefix = f"{PREFIX}:search:list:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2 or not _is_session_id(parts[0]):
        return None
    try:
        page = int(parts[1])
    except ValueError:
        return None
    return (parts[0], page) if page > 0 else None


def search_open(session_id: str, page: int, github_repository_id: int) -> str:
    _require_session_id(session_id)
    if page <= 0 or github_repository_id <= 0:
        raise ValueError("page and repository ID must be positive")
    return f"{PREFIX}:search:open:{session_id}:{page}:{_base36(github_repository_id)}"


def parse_search_open(data: str) -> tuple[str, int, int] | None:
    prefix = f"{PREFIX}:search:open:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 3 or not _is_session_id(parts[0]):
        return None
    try:
        page = int(parts[1])
        repository_id = int(parts[2], 36)
    except ValueError:
        return None
    if page <= 0 or repository_id <= 0:
        return None
    return parts[0], page, repository_id


def search_sort(session_id: str, sort: SearchSort) -> str:
    _require_session_id(session_id)
    return f"{PREFIX}:search:sort:{session_id}:{sort.value}"


def parse_search_sort(data: str) -> tuple[str, SearchSort] | None:
    prefix = f"{PREFIX}:search:sort:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2 or not _is_session_id(parts[0]):
        return None
    try:
        return parts[0], SearchSort(parts[1])
    except ValueError:
        return None


def search_filters(session_id: str, page: int) -> str:
    _require_session_id(session_id)
    if page <= 0:
        raise ValueError("page must be positive")
    return f"{PREFIX}:search:filters:{session_id}:{page}"


def parse_search_filters(data: str) -> tuple[str, int] | None:
    prefix = f"{PREFIX}:search:filters:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2 or not _is_session_id(parts[0]):
        return None
    try:
        page = int(parts[1])
    except ValueError:
        return None
    return (parts[0], page) if page > 0 else None


def search_language(session_id: str, language: SearchLanguage | None) -> str:
    _require_session_id(session_id)
    code = "all" if language is None else _LANGUAGE_CODES[language]
    return f"{PREFIX}:search:lang:{session_id}:{code}"


def parse_search_language(data: str) -> tuple[str, SearchLanguage | None] | None:
    prefix = f"{PREFIX}:search:lang:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2 or not _is_session_id(parts[0]):
        return None
    if parts[1] == "all":
        return parts[0], None
    language = _LANGUAGE_BY_CODE.get(parts[1])
    return (parts[0], language) if language is not None else None


def search_filter_action(session_id: str, action: str) -> str:
    _require_session_id(session_id)
    if action not in {"stars", "owner", "topic", "arch", "clear", "apply"}:
        raise ValueError("search filter action is invalid")
    return f"{PREFIX}:search:flt:{session_id}:{action}"


def parse_search_filter_action(data: str) -> tuple[str, str] | None:
    prefix = f"{PREFIX}:search:flt:"
    if not data.startswith(prefix):
        return None
    parts = data[len(prefix) :].split(":")
    if len(parts) != 2 or not _is_session_id(parts[0]):
        return None
    if parts[1] not in {"stars", "owner", "topic", "arch", "clear", "apply"}:
        return None
    return parts[0], parts[1]


def placeholder(area: str) -> str:
    normalized = area.strip().lower().replace(":", "-")
    if not normalized or len(normalized) > 20:
        raise ValueError("placeholder area is invalid")
    return f"{PLACEHOLDER_PREFIX}{normalized}"


def _parse_confirmation_callback(data: str, action: str) -> str | None:
    return _parse_token_suffix(data, f"{PREFIX}:account:disconnect:{action}:")


def _parse_token_suffix(data: str, prefix: str) -> str | None:
    if not data.startswith(prefix):
        return None
    token = data[len(prefix) :]
    return token if _CONFIRMATION_TOKEN_RE.fullmatch(token) is not None else None


def _require_confirmation_token(value: str) -> None:
    if _CONFIRMATION_TOKEN_RE.fullmatch(value) is None:
        raise ValueError("confirmation token is invalid")


def _require_session_id(value: str) -> None:
    if not _is_session_id(value):
        raise ValueError("search session ID is invalid")


def _is_session_id(value: str) -> bool:
    return _SESSION_RE.fullmatch(value) is not None


def _base36(value: int) -> str:
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    encoded = ""
    while value:
        value, remainder = divmod(value, 36)
        encoded = alphabet[remainder] + encoded
    return encoded