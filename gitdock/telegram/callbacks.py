"""Compact versioned Telegram callback helpers for P2.3."""

from __future__ import annotations

from gitdock.core.constants import CALLBACK_SCHEMA_VERSION, TELEGRAM_CALLBACK_PREFIX
from gitdock.services.repositories import RepositoryFilter

PREFIX = f"{TELEGRAM_CALLBACK_PREFIX}:{CALLBACK_SCHEMA_VERSION}"
HOME_OPEN = f"{PREFIX}:home:open"
HOME_REFRESH = f"{PREFIX}:home:refresh"
CONNECT_BEGIN = f"{PREFIX}:connect:begin"
CONNECT_INFO = f"{PREFIX}:connect:info"
PLACEHOLDER_PREFIX = f"{PREFIX}:later:"


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


def placeholder(area: str) -> str:
    normalized = area.strip().lower().replace(":", "-")
    if not normalized or len(normalized) > 20:
        raise ValueError("placeholder area is invalid")
    return f"{PLACEHOLDER_PREFIX}{normalized}"


def _base36(value: int) -> str:
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    encoded = ""
    while value:
        value, remainder = divmod(value, 36)
        encoded = alphabet[remainder] + encoded
    return encoded
