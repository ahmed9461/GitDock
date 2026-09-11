"""P4.2 branch/commit application service."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.db.models import AuditLog
from gitdock.github.errors import GitHubErrorKind, GitHubGatewayError
from gitdock.github.git_tools import (
    BranchSnapshot,
    CommitDetail,
    CommitSummary,
    CompareSnapshot,
    GitHubGitToolsGateway,
    validate_branch_name,
    validate_ref,
)
from gitdock.github.permissions import GitHubCapability, combine_installation_permissions
from gitdock.github.token_provider import InstallationTokenProvider
from gitdock.services.confirmations import ConfirmationService
from gitdock.services.file_context import FileRepositoryContextResolver
from gitdock.services.file_types import CurrentRepository, RepositoryReadGateway

_CREATE_BRANCH_OPERATION = "git.branch.create"


@dataclass(frozen=True, slots=True)
class BranchListView:
    repository_full_name: str
    default_branch: str
    branches: tuple[BranchSnapshot, ...]


@dataclass(frozen=True, slots=True)
class CommitListView:
    repository_full_name: str
    ref: str
    commits: tuple[CommitSummary, ...]


@dataclass(frozen=True, slots=True)
class CommitDetailView:
    repository_full_name: str
    commit: CommitDetail


@dataclass(frozen=True, slots=True)
class CompareView:
    repository_full_name: str
    base: str
    head: str
    comparison: CompareSnapshot


@dataclass(frozen=True, slots=True)
class BranchCreatePlan:
    repository_full_name: str
    branch: str
    base_ref: str
    base_sha: str
    confirmation_token: str


class BranchCreateState(StrEnum):
    APPLIED = "applied"
    INVALID = "invalid"
    STALE = "stale"
    EXISTS = "exists"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class BranchCreateOutcome:
    state: BranchCreateState
    branch: str | None = None
    sha: str | None = None


class GitToolsService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        token_provider: InstallationTokenProvider,
        repository_gateway: RepositoryReadGateway,
        gateway: GitHubGitToolsGateway,
        confirmations: ConfirmationService,
    ) -> None:
        self._session_factory = session_factory
        self._token_provider = token_provider
        self._gateway = gateway
        self._confirmations = confirmations
        self._resolver = FileRepositoryContextResolver(
            session_factory, token_provider, repository_gateway
        )
        levels = combine_installation_permissions(
            {GitHubCapability.REPOSITORY_METADATA_READ, GitHubCapability.CONTENTS_WRITE}
        )
        self._write_permissions = {name: level.value for name, level in levels.items()}

    async def list_branches(
        self, *, user_id: int, github_repository_id: int, query: str | None = None
    ) -> BranchListView:
        current = await self._resolver.resolve(
            user_id=user_id, github_repository_id=github_repository_id
        )
        branches = await self._gateway.list_branches(
            current.read_token,
            owner_login=current.repository.owner_login,
            name=current.repository.name,
        )
        if query:
            needle = query.casefold().strip()
            branches = tuple(branch for branch in branches if needle in branch.name.casefold())
        return BranchListView(
            current.repository.full_name, current.repository.default_branch, branches
        )

    async def recent_commits(
        self, *, user_id: int, github_repository_id: int, ref: str | None = None
    ) -> CommitListView:
        current = await self._resolver.resolve(
            user_id=user_id, github_repository_id=github_repository_id
        )
        selected_ref = (ref or current.repository.default_branch).strip()
        commits = await self._gateway.recent_commits(
            current.read_token,
            owner_login=current.repository.owner_login,
            name=current.repository.name,
            ref=selected_ref,
            limit=30,
        )
        return CommitListView(current.repository.full_name, selected_ref, commits)

    async def commit_detail(
        self, *, user_id: int, github_repository_id: int, ref: str
    ) -> CommitDetailView:
        current = await self._resolver.resolve(
            user_id=user_id, github_repository_id=github_repository_id
        )
        commit = await self._gateway.get_commit(
            current.read_token,
            owner_login=current.repository.owner_login,
            name=current.repository.name,
            ref=ref,
        )
        return CommitDetailView(current.repository.full_name, commit)

    async def compare(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        base: str,
        head: str,
    ) -> CompareView:
        current = await self._resolver.resolve(
            user_id=user_id, github_repository_id=github_repository_id
        )
        comparison = await self._gateway.compare(
            current.read_token,
            owner_login=current.repository.owner_login,
            name=current.repository.name,
            base=base,
            head=head,
        )
        return CompareView(current.repository.full_name, base, head, comparison)

    async def begin_create_branch(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        branch: str,
        base_ref: str,
    ) -> BranchCreatePlan:
        branch = validate_branch_name(branch)
        base_ref = validate_ref(base_ref)
        current = await self._resolver.resolve(
            user_id=user_id, github_repository_id=github_repository_id
        )
        base_commit = await self._gateway.get_commit(
            current.read_token,
            owner_login=current.repository.owner_login,
            name=current.repository.name,
            ref=base_ref,
        )
        try:
            await self._gateway.get_branch(
                current.read_token,
                owner_login=current.repository.owner_login,
                name=current.repository.name,
                branch=branch,
            )
        except GitHubGatewayError as exc:
            if exc.kind is not GitHubErrorKind.NOT_FOUND:
                raise
        else:
            raise ValueError("branch already exists")

        fingerprint = _fingerprint(github_repository_id, branch, base_ref, base_commit.sha)
        async with self._session_factory() as session:
            async with session.begin():
                issued = await self._confirmations.create(
                    session,
                    user_id=user_id,
                    operation_type=_CREATE_BRANCH_OPERATION,
                    target_fingerprint=fingerprint,
                    payload={
                        "repository_id": github_repository_id,
                        "branch": branch,
                        "base_ref": base_ref,
                        "base_sha": base_commit.sha,
                    },
                    risk_tier=1,
                )
        return BranchCreatePlan(
            current.repository.full_name,
            branch,
            base_ref,
            base_commit.sha,
            issued.token,
        )

    async def cancel_create_branch(self, *, user_id: int, token: str) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                return await self._confirmations.cancel(
                    session,
                    user_id=user_id,
                    token=token,
                    expected_operation=_CREATE_BRANCH_OPERATION,
                )

    async def confirm_create_branch(
        self, *, user_id: int, token: str
    ) -> BranchCreateOutcome:
        async with self._session_factory() as session:
            async with session.begin():
                consumed = await self._confirmations.consume(
                    session,
                    user_id=user_id,
                    token=token,
                    expected_operation=_CREATE_BRANCH_OPERATION,
                )
        if consumed is None:
            return BranchCreateOutcome(BranchCreateState.INVALID)
        payload = consumed.payload
        try:
            repository_id = int(payload["repository_id"])
            branch = str(payload["branch"])
            base_ref = str(payload["base_ref"])
            expected_sha = str(payload["base_sha"])
        except (KeyError, TypeError, ValueError):
            return BranchCreateOutcome(BranchCreateState.INVALID)
        if consumed.target_fingerprint != _fingerprint(
            repository_id, branch, base_ref, expected_sha
        ):
            return BranchCreateOutcome(BranchCreateState.INVALID)

        current = await self._resolver.resolve(
            user_id=user_id, github_repository_id=repository_id
        )
        latest_base = await self._gateway.get_commit(
            current.read_token,
            owner_login=current.repository.owner_login,
            name=current.repository.name,
            ref=base_ref,
        )
        if latest_base.sha != expected_sha:
            await self._audit(
                user_id=user_id,
                current=current,
                branch=branch,
                base_ref=base_ref,
                base_sha=expected_sha,
                status="stale",
            )
            return BranchCreateOutcome(BranchCreateState.STALE, branch, expected_sha)
        try:
            existing = await self._gateway.get_branch(
                current.read_token,
                owner_login=current.repository.owner_login,
                name=current.repository.name,
                branch=branch,
            )
        except GitHubGatewayError as exc:
            if exc.kind is not GitHubErrorKind.NOT_FOUND:
                raise
        else:
            await self._audit(
                user_id=user_id,
                current=current,
                branch=branch,
                base_ref=base_ref,
                base_sha=expected_sha,
                status="exists",
            )
            return BranchCreateOutcome(BranchCreateState.EXISTS, branch, existing.sha)

        write_token = await self._token_provider.get_token(
            current.context.installation_id,
            permissions=self._write_permissions,
            repository_ids=[repository_id],
        )
        try:
            created = await self._gateway.create_branch(
                write_token.token,
                owner_login=current.repository.owner_login,
                name=current.repository.name,
                branch=branch,
                sha=expected_sha,
            )
        except GitHubGatewayError as exc:
            try:
                reconciled = await self._gateway.get_branch(
                    current.read_token,
                    owner_login=current.repository.owner_login,
                    name=current.repository.name,
                    branch=branch,
                )
            except GitHubGatewayError:
                await self._audit(
                    user_id=user_id,
                    current=current,
                    branch=branch,
                    base_ref=base_ref,
                    base_sha=expected_sha,
                    status="uncertain",
                    request_id=exc.context.request_id,
                )
                return BranchCreateOutcome(BranchCreateState.UNCERTAIN, branch)
            if reconciled.sha == expected_sha:
                await self._audit(
                    user_id=user_id,
                    current=current,
                    branch=branch,
                    base_ref=base_ref,
                    base_sha=expected_sha,
                    status="success",
                    request_id=exc.context.request_id,
                )
                return BranchCreateOutcome(BranchCreateState.APPLIED, branch, expected_sha)
            await self._audit(
                user_id=user_id,
                current=current,
                branch=branch,
                base_ref=base_ref,
                base_sha=expected_sha,
                status="uncertain",
                request_id=exc.context.request_id,
            )
            return BranchCreateOutcome(BranchCreateState.UNCERTAIN, branch, reconciled.sha)

        await self._audit(
            user_id=user_id,
            current=current,
            branch=branch,
            base_ref=base_ref,
            base_sha=expected_sha,
            status="success",
            request_id=created.request_id,
        )
        return BranchCreateOutcome(BranchCreateState.APPLIED, branch, created.sha)

    async def _audit(
        self,
        *,
        user_id: int,
        current: CurrentRepository,
        branch: str,
        base_ref: str,
        base_sha: str,
        status: str,
        request_id: str | None = None,
    ) -> None:
        repository = current.repository
        context = current.context
        async with self._session_factory() as session:
            async with session.begin():
                session.add(
                    AuditLog(
                        user_id=user_id,
                        operation=_CREATE_BRANCH_OPERATION,
                        status=status,
                        installation_id=context.installation_id,
                        github_repository_id=repository.github_repository_id,
                        repository_full_name=repository.full_name,
                        github_request_id=request_id,
                        details_json={
                            "branch": branch,
                            "base_ref": base_ref,
                            "base_sha": base_sha,
                            "risk_tier": 1,
                        },
                    )
                )


def _fingerprint(repository_id: int, branch: str, base_ref: str, base_sha: str) -> str:
    material = f"{repository_id}\0{branch}\0{base_ref}\0{base_sha}".encode()
    return hashlib.sha256(material).hexdigest()
