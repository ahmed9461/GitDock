from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import SecretStr

from gitdock.core.constants import RUN_EVIDENCE_FILE_MAX_BYTES
from gitdock.domain.run_assistant import PlanNote, StackKind, TargetOS
from gitdock.github.contents import ContentEntry, ContentKind, FileContent
from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.search import RepositorySearchResult
from gitdock.services.file_types import CurrentRepository, InstalledRepositoryContext
from gitdock.services.run_assistant import RunAssistantService


class FakeContentsGateway:
    def __init__(self, entries: tuple[ContentEntry, ...], files: dict[str, bytes]) -> None:
        self.entries = entries
        self.files = files
        self.list_tokens: list[str | None] = []
        self.file_tokens: list[str | None] = []
        self.file_reads: list[str] = []

    async def list_directory(
        self,
        token: SecretStr | None,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        ref: str,
    ) -> tuple[ContentEntry, ...]:
        self.list_tokens.append(token.get_secret_value() if token is not None else None)
        assert path == ""
        assert ref == "main"
        return self.entries

    async def get_file(
        self,
        token: SecretStr | None,
        *,
        owner_login: str,
        repository_name: str,
        path: str,
        ref: str,
    ) -> FileContent:
        self.file_tokens.append(token.get_secret_value() if token is not None else None)
        self.file_reads.append(path)
        body = self.files[path]
        return FileContent(
            name=path,
            path=path,
            sha="a" * 40,
            size=len(body),
            content=body,
            html_url=f"https://github.com/{owner_login}/{repository_name}/blob/{ref}/{path}",
        )


class FakeResolver:
    def __init__(self, current: CurrentRepository) -> None:
        self.current = current

    async def resolve(self, *, user_id: int, github_repository_id: int) -> CurrentRepository:
        assert user_id == 7
        assert github_repository_id == self.current.repository.github_repository_id
        return self.current


def _entry(name: str, *, size: int = 1) -> ContentEntry:
    return ContentEntry(
        name=name,
        path=name,
        sha="b" * 40,
        size=size,
        kind=ContentKind.FILE,
        html_url=f"https://github.com/ahmed9461/GitDock/blob/main/{name}",
    )


def _snapshot() -> RepositorySnapshot:
    now = datetime.now(UTC)
    return RepositorySnapshot(
        github_repository_id=1351822221,
        owner_login="ahmed9461",
        name="GitDock",
        full_name="ahmed9461/GitDock",
        html_url="https://github.com/ahmed9461/GitDock",
        private=True,
        archived=False,
        fork=False,
        default_branch="main",
        language="Python",
        description=None,
        stars=0,
        forks=0,
        updated_at=now,
        pushed_at=now,
    )


def _public() -> RepositorySearchResult:
    now = datetime.now(UTC)
    return RepositorySearchResult(
        github_repository_id=1296269,
        owner_login="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        html_url="https://github.com/octocat/Hello-World",
        archived=False,
        fork=False,
        default_branch="main",
        language="JavaScript",
        description=None,
        stars=1,
        forks=1,
        license_spdx=None,
        topics=(),
        updated_at=now,
        pushed_at=now,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_public_plan_uses_unauthenticated_bounded_contents_reads() -> None:
    package = b'{"scripts":{"start":"node server.js"}}'
    entries = (
        _entry("package.json", size=len(package)),
        _entry("package-lock.json"),
        _entry("README.md", size=100),
    )
    gateway = FakeContentsGateway(entries, {"package.json": package})
    service = RunAssistantService(gateway)  # type: ignore[arg-type]

    plan = await service.plan_public(repository=_public(), target_os=TargetOS.LINUX)

    assert gateway.list_tokens == [None]
    assert gateway.file_tokens == [None]
    assert gateway.file_reads == ["package.json"]
    assert StackKind.NODE in {item.stack for item in plan.stacks}
    assert PlanNote.README_PRESENT in plan.notes
    assert "npm run start" in plan.run[0].commands


@pytest.mark.integration
@pytest.mark.asyncio
async def test_installed_plan_reuses_repository_read_token() -> None:
    pyproject = b'[project]\nname="gitdock"\nversion="0.1"\n'
    gateway = FakeContentsGateway(
        (_entry("pyproject.toml", size=len(pyproject)),),
        {"pyproject.toml": pyproject},
    )
    repository = _snapshot()
    current = CurrentRepository(
        context=InstalledRepositoryContext(
            installation_id=99,
            github_repository_id=repository.github_repository_id,
            owner_login=repository.owner_login,
            repository_name=repository.name,
        ),
        repository=repository,
        read_token=SecretStr("test-read-context"),
    )
    service = RunAssistantService(
        gateway,  # type: ignore[arg-type]
        FakeResolver(current),  # type: ignore[arg-type]
    )

    plan = await service.plan_installed(
        user_id=7,
        github_repository_id=repository.github_repository_id,
        target_os=TargetOS.WINDOWS,
    )

    assert gateway.list_tokens == ["test-read-context"]
    assert gateway.file_tokens == ["test-read-context"]
    assert StackKind.PYTHON in {item.stack for item in plan.stacks}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_evidence_loader_never_reads_readme_body_or_oversized_known_file() -> None:
    entries = (
        _entry("README.md", size=20),
        _entry("package.json", size=RUN_EVIDENCE_FILE_MAX_BYTES + 1),
        _entry("requirements.txt", size=10),
    )
    gateway = FakeContentsGateway(entries, {})
    service = RunAssistantService(gateway)  # type: ignore[arg-type]

    plan = await service.plan_public(repository=_public(), target_os=TargetOS.MACOS)

    assert gateway.file_reads == []
    assert StackKind.NODE in {item.stack for item in plan.stacks}
    assert StackKind.PYTHON in {item.stack for item in plan.stacks}
    assert PlanNote.README_PRESENT in plan.notes
