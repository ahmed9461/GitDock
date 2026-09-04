"""Pure repository-file validation and preview helpers for P4.1."""

from __future__ import annotations

import difflib
import hashlib
import re
from dataclasses import dataclass

from gitdock.core.constants import FILE_PATH_MAX_CHARS, FILE_PREVIEW_PAGE_CHARS, FILE_REF_MAX_CHARS

_DRIVE_PREFIX_RE = re.compile(r"^[A-Za-z]:")
_FORBIDDEN_REF_CHARS = frozenset(" ~^:?*[\\")


class RepositoryPathError(ValueError):
    """Raised when a user-controlled repository path is unsafe or malformed."""


class RepositoryRefError(ValueError):
    """Raised when a user-controlled Git ref is malformed."""


@dataclass(frozen=True, slots=True)
class TextDiffPreview:
    additions: int
    deletions: int
    preview: str


def normalize_repository_path(value: str, *, allow_root: bool = True) -> str:
    if not isinstance(value, str):
        raise RepositoryPathError("repository path must be text")
    if "\x00" in value or "\\" in value:
        raise RepositoryPathError("repository path contains an unsafe character")
    if len(value) > FILE_PATH_MAX_CHARS:
        raise RepositoryPathError("repository path is too long")
    if value == "":
        if allow_root:
            return ""
        raise RepositoryPathError("repository file path is required")
    if value.startswith("/") or _DRIVE_PREFIX_RE.match(value):
        raise RepositoryPathError("repository path must be relative")

    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise RepositoryPathError("repository path contains an unsafe segment")
    return "/".join(parts)


def normalize_repository_ref(value: str) -> str:
    if not isinstance(value, str):
        raise RepositoryRefError("repository ref must be text")
    if not value or value != value.strip() or len(value) > FILE_REF_MAX_CHARS:
        raise RepositoryRefError("repository ref is invalid")
    if any(ord(char) < 32 or ord(char) == 127 or char in _FORBIDDEN_REF_CHARS for char in value):
        raise RepositoryRefError("repository ref contains an unsafe character")
    if (
        value.startswith("/")
        or value.endswith("/")
        or value.endswith(".")
        or "//" in value
        or ".." in value
        or "@{" in value
    ):
        raise RepositoryRefError("repository ref is invalid")
    for part in value.split("/"):
        if not part or part.startswith(".") or part.endswith(".lock"):
            raise RepositoryRefError("repository ref is invalid")
    return value


def join_repository_path(parent: str, name: str) -> str:
    parent = normalize_repository_path(parent, allow_root=True)
    child = normalize_repository_path(name, allow_root=False)
    if "/" in child:
        raise RepositoryPathError("child path must contain one segment")
    return child if not parent else f"{parent}/{child}"


def parent_repository_path(path: str) -> str:
    normalized = normalize_repository_path(path, allow_root=True)
    if not normalized or "/" not in normalized:
        return ""
    return normalized.rsplit("/", 1)[0]


def is_workflow_path(path: str) -> bool:
    normalized = normalize_repository_path(path, allow_root=False)
    return normalized.startswith(".github/workflows/")


def git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def content_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def decode_utf8_text(content: bytes) -> str | None:
    if b"\x00" in content:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def paginate_text(text: str, *, page_chars: int = FILE_PREVIEW_PAGE_CHARS) -> tuple[str, ...]:
    if page_chars <= 0:
        raise ValueError("page size must be positive")
    if text == "":
        return ("",)
    return tuple(text[index : index + page_chars] for index in range(0, len(text), page_chars))


def build_text_diff(before: bytes | None, after: bytes | None, *, max_chars: int = 2400) -> TextDiffPreview | None:
    before_text = "" if before is None else decode_utf8_text(before)
    after_text = "" if after is None else decode_utf8_text(after)
    if before_text is None or after_text is None:
        return None

    before_lines = before_text.splitlines(keepends=True)
    after_lines = after_text.splitlines(keepends=True)
    additions = 0
    deletions = 0
    diff_lines = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )
    for line in diff_lines:
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            additions += 1
        elif line.startswith("-"):
            deletions += 1
    preview = "".join(diff_lines)
    if len(preview) > max_chars:
        preview = f"{preview[: max_chars - 1]}…"
    return TextDiffPreview(additions=additions, deletions=deletions, preview=preview)
