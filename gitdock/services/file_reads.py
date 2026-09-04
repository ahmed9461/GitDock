"""Tier 0 repository directory and file reading for P4.1."""

from __future__ import annotations

from gitdock.core.constants import FILE_TEXT_PREVIEW_MAX_BYTES
from gitdock.domain.files import (
    decode_utf8_text,
    normalize_repository_path,
    normalize_repository_ref,
    paginate_text,
    parent_repository_path,
)
from gitdock.github.contents import ContentKind, FileContent
from gitdock.services.file_context import FileRepositoryContextResolver
from gitdock.services.file_types import (
    ContentsGateway,
    DirectoryView,
    FileBrowserError,
    FileDisplayKind,
    FileView,
)


class FileReadService:
    def __init__(
        self,
        resolver: FileRepositoryContextResolver,
        contents_gateway: ContentsGateway,
    ) -> None:
        self._resolver = resolver
        self._contents_gateway = contents_gateway

    async def browse_directory(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        path: str = "",
        ref: str | None = None,
    ) -> DirectoryView:
        normalized_path = normalize_repository_path(path, allow_root=True)
        current = await self._resolver.resolve(
            user_id=user_id,
            github_repository_id=github_repository_id,
        )
        repository = current.repository
        normalized_ref = normalize_repository_ref(ref or repository.default_branch)
        resolved = await self._contents_gateway.resolve_ref(
            current.read_token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            ref=normalized_ref,
        )
        entries = await self._contents_gateway.list_directory(
            current.read_token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            path=normalized_path,
            ref=resolved.commit_sha,
        )
        for entry in entries:
            try:
                entry_path = normalize_repository_path(entry.path, allow_root=False)
            except ValueError as exc:
                raise FileBrowserError("GitHub returned an unsafe repository path") from exc
            if parent_repository_path(entry_path) != normalized_path:
                raise FileBrowserError("GitHub returned content outside the requested directory")
        ordered = tuple(
            sorted(
                entries,
                key=lambda item: (
                    item.kind is not ContentKind.DIRECTORY,
                    item.name.casefold(),
                ),
            )
        )
        return DirectoryView(
            repository=repository,
            ref=normalized_ref,
            ref_commit_sha=resolved.commit_sha,
            path=normalized_path,
            entries=ordered,
        )

    async def view_file(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        path: str,
        ref: str | None = None,
    ) -> FileView:
        normalized_path = normalize_repository_path(path, allow_root=False)
        current = await self._resolver.resolve(
            user_id=user_id,
            github_repository_id=github_repository_id,
        )
        repository = current.repository
        normalized_ref = normalize_repository_ref(ref or repository.default_branch)
        resolved = await self._contents_gateway.resolve_ref(
            current.read_token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            ref=normalized_ref,
        )
        file = await self._contents_gateway.get_file(
            current.read_token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            path=normalized_path,
            ref=resolved.commit_sha,
        )
        if normalize_repository_path(file.path, allow_root=False) != normalized_path:
            raise FileBrowserError("GitHub returned a different file path")
        display_kind, pages = _preview(file)
        return FileView(
            repository=repository,
            ref=normalized_ref,
            ref_commit_sha=resolved.commit_sha,
            file=file,
            display_kind=display_kind,
            preview_pages=pages,
        )


def _preview(file: FileContent) -> tuple[FileDisplayKind, tuple[str, ...]]:
    if file.content is None:
        kind = (
            FileDisplayKind.LARGE
            if file.size > FILE_TEXT_PREVIEW_MAX_BYTES
            else FileDisplayKind.UNAVAILABLE
        )
        return kind, ()
    if len(file.content) > FILE_TEXT_PREVIEW_MAX_BYTES:
        return FileDisplayKind.LARGE, ()
    text = decode_utf8_text(file.content)
    if text is None:
        return FileDisplayKind.BINARY, ()
    return FileDisplayKind.TEXT, paginate_text(text)
