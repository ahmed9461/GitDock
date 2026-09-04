"""Shared typed contracts and result models for P4.1 file operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import SecretStr

from gitdock.domain.files import TextDiffPreview
from gitdock.github.contents import ContentEntry, FileContent, FileWriteResult, RefSnapshot
from gitdock.github.models import GitHubResponse
from gitdock.github.repositories import RepositorySnapshot

FILE_CREATE_OPERATION = "file.create"
FILE_UPDATE_OPERATION = "file.update"
FILE_DELETE_OPERATION = "file.delete"


class FileDisplayKind(StrEnum):
    TEXT = "text"
    BINARY = "binary"
    LARGE = "large"
    UNAVAILABLE = "unavailable"


class FileWriteState(StrEnum):
    APPLIED = "applied"
    STALE = "stale"
    INVALID = "invalid"
    UNCERTAIN = "uncertain"


class FileBrowserError(RuntimeError):
    """Safe local file-browser failure."""


class FileSelectionError(FileBrowserError):
    """Raised when repository callback context is no longer current."""


class FileWriteValidationError(FileBrowserError, ValueError):
    """Raised when a requested file write is not safe to stage."""


class ContentsGateway(Protocol):
    async def list_directory(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        ref: str,
    ) -> tuple[ContentEntry, ...]: ...

    async def get_file(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        ref: str,
    ) -> FileContent: ...

    async def resolve_ref(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        ref: str,
    ) -> RefSnapshot: ...

    async def get_branch(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        repository_name: str,
        branch: str,
    ) -> RefSnapshot: ...

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
    ) -> GitHubResponse[FileWriteResult]: ...

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
    ) -> GitHubResponse[FileWriteResult]: ...


class RepositoryReadGateway(Protocol):
    async def get_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ) -> RepositorySnapshot: ...


@dataclass(frozen=True, slots=True)
class InstalledRepositoryContext:
    installation_id: int
    github_repository_id: int
    owner_login: str
    repository_name: str


@dataclass(frozen=True, slots=True)
class CurrentRepository:
    context: InstalledRepositoryContext
    repository: RepositorySnapshot
    read_token: SecretStr


@dataclass(frozen=True, slots=True)
class DirectoryView:
    repository: RepositorySnapshot
    ref: str
    ref_commit_sha: str
    path: str
    entries: tuple[ContentEntry, ...]


@dataclass(frozen=True, slots=True)
class FileView:
    repository: RepositorySnapshot
    ref: str
    ref_commit_sha: str
    file: FileContent
    display_kind: FileDisplayKind
    preview_pages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FileWritePlan:
    token: str
    operation: str
    repository: RepositorySnapshot
    branch: str
    path: str
    risk_tier: int
    diff: TextDiffPreview | None


@dataclass(frozen=True, slots=True)
class FileWriteOutcome:
    state: FileWriteState
    operation: str
    repository: RepositorySnapshot | None
    branch: str | None
    path: str | None
    commit_sha: str | None = None


@dataclass(frozen=True, slots=True)
class StagedWrite:
    session_id: int
    user_id: int
    operation: str
    github_repository_id: int
    installation_id: int
    repository_full_name: str
    repository_default_branch: str
    branch: str
    path: str
    branch_head_sha: str
    expected_file_sha: str | None
    desired_blob_sha: str | None
    content_digest: str | None
    content: bytes | None
    commit_message: str
    risk_tier: int
