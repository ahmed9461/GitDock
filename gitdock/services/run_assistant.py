"""P4.3 read-only repository evidence collection and command planning."""

from __future__ import annotations

from pydantic import SecretStr

from gitdock.core.constants import RUN_EVIDENCE_FILE_MAX_BYTES, RUN_EVIDENCE_MAX_FILES
from gitdock.domain.run_assistant import CommandPlan, EvidenceFile, TargetOS, build_command_plan
from gitdock.github.contents import ContentKind, GitHubContentsGateway
from gitdock.github.errors import GitHubErrorKind, GitHubGatewayError
from gitdock.github.search import RepositorySearchResult
from gitdock.services.file_context import FileRepositoryContextResolver

_CONTENT_EVIDENCE_NAMES = frozenset(
    {
        "package.json",
        "pyproject.toml",
        "build.gradle",
        "build.gradle.kts",
        "pom.xml",
    }
)


class RunAssistantUnavailable(RuntimeError):
    """Raised when an installed-repository plan is unavailable in this runtime."""


class RunAssistantService:
    """Collect bounded read-only evidence, then delegate to pure command inference."""

    def __init__(
        self,
        contents_gateway: GitHubContentsGateway,
        installed_resolver: FileRepositoryContextResolver | None = None,
    ) -> None:
        self._contents = contents_gateway
        self._installed_resolver = installed_resolver

    async def plan_installed(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        target_os: TargetOS,
    ) -> CommandPlan:
        if self._installed_resolver is None:
            raise RunAssistantUnavailable("installed repository context is unavailable")
        current = await self._installed_resolver.resolve(
            user_id=user_id,
            github_repository_id=github_repository_id,
        )
        repository = current.repository
        evidence = await self._load_evidence(
            token=current.read_token,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            ref=repository.default_branch,
        )
        return build_command_plan(
            owner_login=repository.owner_login,
            repository_name=repository.name,
            default_branch=repository.default_branch,
            target_os=target_os,
            evidence=evidence,
        )

    async def plan_public(
        self,
        *,
        repository: RepositorySearchResult,
        target_os: TargetOS,
    ) -> CommandPlan:
        evidence = await self._load_evidence(
            token=None,
            owner_login=repository.owner_login,
            repository_name=repository.name,
            ref=repository.default_branch,
        )
        return build_command_plan(
            owner_login=repository.owner_login,
            repository_name=repository.name,
            default_branch=repository.default_branch,
            target_os=target_os,
            evidence=evidence,
        )

    async def _load_evidence(
        self,
        *,
        token: SecretStr | None,
        owner_login: str,
        repository_name: str,
        ref: str,
    ) -> tuple[EvidenceFile, ...]:
        try:
            entries = await self._contents.list_directory(
                token,
                owner_login=owner_login,
                repository_name=repository_name,
                path="",
                ref=ref,
            )
        except GitHubGatewayError as exc:
            if exc.kind is GitHubErrorKind.NOT_FOUND:
                return ()
            raise

        files = tuple(entry for entry in entries if entry.kind is ContentKind.FILE)
        contents: dict[str, bytes] = {}
        reads = 0
        for entry in files:
            if reads >= RUN_EVIDENCE_MAX_FILES:
                break
            if entry.name.casefold() not in _CONTENT_EVIDENCE_NAMES:
                continue
            if entry.size > RUN_EVIDENCE_FILE_MAX_BYTES:
                continue
            reads += 1
            try:
                result = await self._contents.get_file(
                    token,
                    owner_login=owner_login,
                    repository_name=repository_name,
                    path=entry.path,
                    ref=ref,
                )
            except GitHubGatewayError as exc:
                if exc.kind is GitHubErrorKind.NOT_FOUND:
                    continue
                raise
            if result.content is not None and len(result.content) <= RUN_EVIDENCE_FILE_MAX_BYTES:
                contents[entry.path] = result.content

        return tuple(
            EvidenceFile(path=entry.path, content=contents.get(entry.path)) for entry in files
        )
