"""Safe repository creation and administration use cases for P3.3."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Protocol

from pydantic import SecretStr
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gitdock.db.models import AuditLog, GitHubAccount, GitHubInstallation, RepositoryCache
from gitdock.github.errors import GitHubGatewayError
from gitdock.github.permissions import GitHubCapability, combine_installation_permissions
from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.repository_admin import RepositoryCreateRequest, RepositoryUpdateRequest
from gitdock.github.token_provider import InstallationTokenProvider
from gitdock.services.confirmations import ConfirmationService
from gitdock.services.user_authorization import (
    GitHubUserAuthorizationService,
    ReauthorizationRequired,
)

CREATE_OPERATION = "repository.create"
UPDATE_OPERATION = "repository.update"
DELETE_OPERATION = "repository.delete"


class RepositoryAdminState(StrEnum):
    APPLIED = "applied"
    STALE = "stale"
    INVALID = "invalid"


class RepositoryAdminError(RuntimeError):
    """Safe local repository-administration failure."""


class RepositoryAdminSelectionError(RepositoryAdminError):
    """Repository callback/cache selection is missing or no longer valid."""


class RepositoryAdminGateway(Protocol):
    async def create_personal_repository(
        self,
        token: SecretStr,
        request: RepositoryCreateRequest,
    ): ...

    async def create_organization_repository(
        self,
        token: SecretStr,
        *,
        organization: str,
        request: RepositoryCreateRequest,
    ): ...

    async def update_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        request: RepositoryUpdateRequest,
    ): ...

    async def delete_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ): ...


class RepositoryReadGateway(Protocol):
    async def get_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ) -> RepositorySnapshot: ...


@dataclass(frozen=True, slots=True)
class RepositoryCreatePlan:
    token: str
    owner_label: str
    request: RepositoryCreateRequest
    organization: str | None


@dataclass(frozen=True, slots=True)
class RepositoryUpdatePlan:
    token: str
    repository: RepositorySnapshot
    request: RepositoryUpdateRequest


@dataclass(frozen=True, slots=True)
class RepositoryDeletePlan:
    token: str
    repository: RepositorySnapshot


@dataclass(frozen=True, slots=True)
class RepositoryAdminResult:
    state: RepositoryAdminState
    repository: RepositorySnapshot | None = None


@dataclass(frozen=True, slots=True)
class _InstalledRepositoryContext:
    user_id: int
    installation_id: int
    github_repository_id: int
    owner_login: str
    name: str


class RepositoryAdminService:
    """Execute repository writes only through durable confirmations and scoped tokens."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        user_authorization: GitHubUserAuthorizationService,
        token_provider: InstallationTokenProvider,
        read_gateway: RepositoryReadGateway,
        admin_gateway: RepositoryAdminGateway,
        confirmations: ConfirmationService,
    ) -> None:
        self._session_factory = session_factory
        self._user_authorization = user_authorization
        self._token_provider = token_provider
        self._read_gateway = read_gateway
        self._admin_gateway = admin_gateway
        self._confirmations = confirmations
        permission_levels = combine_installation_permissions({GitHubCapability.REPOSITORY_ADMIN})
        self._admin_permissions = {name: level.value for name, level in permission_levels.items()}

    async def begin_create(
        self,
        *,
        user_id: int,
        request: RepositoryCreateRequest,
        organization: str | None = None,
    ) -> RepositoryCreatePlan:
        _validate_create_request(request)
        async with self._session_factory() as session:
            async with session.begin():
                account = await self._active_account(session, user_id)
                payload = {
                    "name": request.name.strip(),
                    "description": request.description,
                    "private": request.private,
                    "organization": organization.strip() if organization else None,
                    "account_id": account.id,
                    "github_user_id": account.github_user_id,
                    "credential_generation": account.credential_generation,
                }
                fingerprint = _fingerprint(payload)
                issued = await self._confirmations.create(
                    session,
                    user_id=user_id,
                    operation_type=CREATE_OPERATION,
                    target_fingerprint=fingerprint,
                    payload=payload,
                    risk_tier=1,
                )
                return RepositoryCreatePlan(
                    issued.token,
                    organization.strip() if organization else account.login,
                    request,
                    organization.strip() if organization else None,
                )

    async def confirm_create(self, *, user_id: int, token: str) -> RepositoryAdminResult:
        async with self._session_factory() as session:
            async with session.begin():
                consumed = await self._confirmations.consume(
                    session,
                    user_id=user_id,
                    token=token,
                    expected_operation=CREATE_OPERATION,
                )
                if consumed is None:
                    return RepositoryAdminResult(RepositoryAdminState.INVALID)
                payload = consumed.payload
                account = await self._active_account(session, user_id)
                if not _create_preconditions_match(payload, account):
                    return RepositoryAdminResult(RepositoryAdminState.STALE)
                if consumed.target_fingerprint != _fingerprint(payload):
                    return RepositoryAdminResult(RepositoryAdminState.STALE)
                request = _create_request_from_payload(payload)
                organization = _optional_str(payload.get("organization"))
                github_login = account.login

        try:
            user_token = await self._user_authorization.get_valid_token(user_id=user_id)
            if organization is None:
                response = await self._admin_gateway.create_personal_repository(
                    user_token.token,
                    request,
                )
            else:
                response = await self._admin_gateway.create_organization_repository(
                    user_token.token,
                    organization=organization,
                    request=request,
                )
        except (GitHubGatewayError, ReauthorizationRequired) as exc:
            await self._audit_failure(
                user_id=user_id,
                operation=CREATE_OPERATION,
                github_login=github_login,
                repository_full_name=(f"{organization or github_login}/{request.name.strip()}"),
                error=exc,
            )
            raise

        await self._audit_success(
            user_id=user_id,
            operation=CREATE_OPERATION,
            github_login=github_login,
            repository=response.data,
            request_id=response.request_id,
            details={"organization": organization, "private": request.private},
        )
        return RepositoryAdminResult(RepositoryAdminState.APPLIED, response.data)

    async def begin_update(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        request: RepositoryUpdateRequest,
    ) -> RepositoryUpdatePlan:
        request.payload()
        context, snapshot = await self._current_installed_repository(user_id, github_repository_id)
        payload = {
            "repository_id": snapshot.github_repository_id,
            "owner_login": snapshot.owner_login,
            "name": snapshot.name,
            "current": _snapshot_preconditions(snapshot),
            "desired": request.payload(),
            "installation_id": context.installation_id,
        }
        async with self._session_factory() as session:
            async with session.begin():
                issued = await self._confirmations.create(
                    session,
                    user_id=user_id,
                    operation_type=UPDATE_OPERATION,
                    target_fingerprint=_fingerprint(payload),
                    payload=payload,
                    risk_tier=2,
                )
        return RepositoryUpdatePlan(issued.token, snapshot, request)

    async def confirm_update(self, *, user_id: int, token: str) -> RepositoryAdminResult:
        consumed = await self._consume(user_id, token, UPDATE_OPERATION)
        if consumed is None:
            return RepositoryAdminResult(RepositoryAdminState.INVALID)
        payload = consumed.payload
        repository_id = _positive_int(payload.get("repository_id"))
        if repository_id is None or consumed.target_fingerprint != _fingerprint(payload):
            return RepositoryAdminResult(RepositoryAdminState.STALE)
        try:
            context, current = await self._current_installed_repository(user_id, repository_id)
        except RepositoryAdminSelectionError:
            return RepositoryAdminResult(RepositoryAdminState.STALE)
        if context.installation_id != payload.get("installation_id") or _snapshot_preconditions(
            current
        ) != payload.get("current"):
            return RepositoryAdminResult(RepositoryAdminState.STALE)
        desired = payload.get("desired")
        if not isinstance(desired, dict):
            return RepositoryAdminResult(RepositoryAdminState.STALE)
        request = _update_request_from_payload(desired)
        token_value = await self._installation_admin_token(context)
        try:
            response = await self._admin_gateway.update_repository(
                token_value,
                owner_login=current.owner_login,
                name=current.name,
                request=request,
            )
        except GitHubGatewayError as exc:
            await self._audit_failure(
                user_id=user_id,
                operation=UPDATE_OPERATION,
                installation_id=context.installation_id,
                repository_id=current.github_repository_id,
                repository_full_name=current.full_name,
                error=exc,
            )
            raise
        await self._refresh_cache_after_write(user_id, context, response.data)
        await self._audit_success(
            user_id=user_id,
            operation=UPDATE_OPERATION,
            installation_id=context.installation_id,
            repository=response.data,
            request_id=response.request_id,
            details={"desired": desired},
        )
        return RepositoryAdminResult(RepositoryAdminState.APPLIED, response.data)

    async def begin_delete(
        self,
        *,
        user_id: int,
        github_repository_id: int,
        typed_full_name: str,
    ) -> RepositoryDeletePlan | None:
        context, snapshot = await self._current_installed_repository(user_id, github_repository_id)
        if typed_full_name.strip() != snapshot.full_name:
            return None
        payload = {
            "repository_id": snapshot.github_repository_id,
            "owner_login": snapshot.owner_login,
            "name": snapshot.name,
            "full_name": snapshot.full_name,
            "current": _snapshot_preconditions(snapshot),
            "installation_id": context.installation_id,
        }
        async with self._session_factory() as session:
            async with session.begin():
                issued = await self._confirmations.create(
                    session,
                    user_id=user_id,
                    operation_type=DELETE_OPERATION,
                    target_fingerprint=_fingerprint(payload),
                    payload=payload,
                    risk_tier=3,
                )
        return RepositoryDeletePlan(issued.token, snapshot)

    async def confirm_delete(self, *, user_id: int, token: str) -> RepositoryAdminResult:
        consumed = await self._consume(user_id, token, DELETE_OPERATION)
        if consumed is None:
            return RepositoryAdminResult(RepositoryAdminState.INVALID)
        payload = consumed.payload
        repository_id = _positive_int(payload.get("repository_id"))
        if repository_id is None or consumed.target_fingerprint != _fingerprint(payload):
            return RepositoryAdminResult(RepositoryAdminState.STALE)
        try:
            context, current = await self._current_installed_repository(user_id, repository_id)
        except RepositoryAdminSelectionError:
            return RepositoryAdminResult(RepositoryAdminState.STALE)
        if (
            context.installation_id != payload.get("installation_id")
            or current.full_name != payload.get("full_name")
            or _snapshot_preconditions(current) != payload.get("current")
        ):
            return RepositoryAdminResult(RepositoryAdminState.STALE)
        token_value = await self._installation_admin_token(context)
        try:
            response = await self._admin_gateway.delete_repository(
                token_value,
                owner_login=current.owner_login,
                name=current.name,
            )
        except GitHubGatewayError as exc:
            await self._audit_failure(
                user_id=user_id,
                operation=DELETE_OPERATION,
                installation_id=context.installation_id,
                repository_id=current.github_repository_id,
                repository_full_name=current.full_name,
                error=exc,
            )
            raise
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(RepositoryCache).where(
                        RepositoryCache.user_id == user_id,
                        RepositoryCache.github_repository_id == repository_id,
                    )
                )
        await self._audit_success(
            user_id=user_id,
            operation=DELETE_OPERATION,
            installation_id=context.installation_id,
            repository=current,
            request_id=response.request_id,
        )
        return RepositoryAdminResult(RepositoryAdminState.APPLIED, current)

    async def _consume(self, user_id: int, token: str, operation: str):
        async with self._session_factory() as session:
            async with session.begin():
                return await self._confirmations.consume(
                    session,
                    user_id=user_id,
                    token=token,
                    expected_operation=operation,
                )

    async def _current_installed_repository(
        self,
        user_id: int,
        github_repository_id: int,
    ) -> tuple[_InstalledRepositoryContext, RepositorySnapshot]:
        if user_id <= 0 or github_repository_id <= 0:
            raise RepositoryAdminSelectionError("repository selection is invalid")
        async with self._session_factory() as session:
            row = await session.scalar(
                select(RepositoryCache).where(
                    RepositoryCache.user_id == user_id,
                    RepositoryCache.github_repository_id == github_repository_id,
                )
            )
            if row is None:
                raise RepositoryAdminSelectionError("repository selection is stale")
            installation = await session.get(GitHubInstallation, row.installation_db_id)
            if installation is None or installation.user_id != user_id or installation.suspended:
                raise RepositoryAdminSelectionError("repository installation is unavailable")
            context = _InstalledRepositoryContext(
                user_id,
                installation.installation_id,
                github_repository_id,
                row.owner_login,
                row.name,
            )
        token_value = await self._installation_admin_token(context)
        snapshot = await self._read_gateway.get_repository(
            token_value,
            owner_login=context.owner_login,
            name=context.name,
        )
        if snapshot.github_repository_id != github_repository_id:
            raise RepositoryAdminSelectionError("repository identity changed unexpectedly")
        return context, snapshot

    async def _installation_admin_token(self, context: _InstalledRepositoryContext) -> SecretStr:
        token = await self._token_provider.get_token(
            context.installation_id,
            permissions=self._admin_permissions,
            repository_ids=[context.github_repository_id],
        )
        return token.token

    async def _active_account(self, session: AsyncSession, user_id: int) -> GitHubAccount:
        rows = (
            await session.scalars(
                select(GitHubAccount).where(
                    GitHubAccount.user_id == user_id,
                    GitHubAccount.encrypted_access_token.is_not(None),
                )
            )
        ).all()
        if len(rows) != 1:
            raise ReauthorizationRequired("GitHub user authorization is required")
        return rows[0]

    async def _refresh_cache_after_write(
        self,
        user_id: int,
        context: _InstalledRepositoryContext,
        snapshot: RepositorySnapshot,
    ) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.scalar(
                    select(RepositoryCache).where(
                        RepositoryCache.user_id == user_id,
                        RepositoryCache.github_repository_id == snapshot.github_repository_id,
                    )
                )
                if row is None:
                    return
                row.owner_login = snapshot.owner_login
                row.name = snapshot.name
                row.full_name = snapshot.full_name
                row.html_url = snapshot.html_url
                row.private = snapshot.private
                row.archived = snapshot.archived
                row.default_branch = snapshot.default_branch
                row.description = snapshot.description

    async def _audit_success(
        self,
        *,
        user_id: int,
        operation: str,
        repository: RepositorySnapshot,
        request_id: str | None,
        github_login: str | None = None,
        installation_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        await self._write_audit(
            user_id=user_id,
            operation=operation,
            status="success",
            github_login=github_login,
            installation_id=installation_id,
            repository_id=repository.github_repository_id,
            repository_full_name=repository.full_name,
            request_id=request_id,
            details=details,
        )

    async def _audit_failure(
        self,
        *,
        user_id: int,
        operation: str,
        error: Exception,
        github_login: str | None = None,
        installation_id: int | None = None,
        repository_id: int | None = None,
        repository_full_name: str | None = None,
    ) -> None:
        request_id = error.context.request_id if isinstance(error, GitHubGatewayError) else None
        kind = error.kind.value if isinstance(error, GitHubGatewayError) else type(error).__name__
        await self._write_audit(
            user_id=user_id,
            operation=operation,
            status="failure",
            github_login=github_login,
            installation_id=installation_id,
            repository_id=repository_id,
            repository_full_name=repository_full_name,
            request_id=request_id,
            details={"error_kind": kind},
        )

    async def _write_audit(
        self,
        *,
        user_id: int,
        operation: str,
        status: str,
        github_login: str | None,
        installation_id: int | None,
        repository_id: int | None,
        repository_full_name: str | None,
        request_id: str | None,
        details: dict[str, Any] | None,
    ) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                session.add(
                    AuditLog(
                        user_id=user_id,
                        operation=operation,
                        status=status,
                        github_login=github_login,
                        installation_id=installation_id,
                        github_repository_id=repository_id,
                        repository_full_name=repository_full_name,
                        github_request_id=request_id,
                        details_json=details,
                    )
                )


def _validate_create_request(request: RepositoryCreateRequest) -> None:
    name = request.name.strip()
    if not name or "/" in name or "\\" in name or "\x00" in name or len(name) > 100:
        raise ValueError("repository name is invalid")
    if request.description is not None and len(request.description) > 350:
        raise ValueError("repository description is too long")


def _create_preconditions_match(payload: dict[str, Any], account: GitHubAccount) -> bool:
    return (
        payload.get("account_id") == account.id
        and payload.get("github_user_id") == account.github_user_id
        and payload.get("credential_generation") == account.credential_generation
    )


def _create_request_from_payload(payload: dict[str, Any]) -> RepositoryCreateRequest:
    name = payload.get("name")
    private = payload.get("private")
    description = payload.get("description")
    if not isinstance(name, str) or not isinstance(private, bool):
        raise RepositoryAdminError("stored repository creation payload is invalid")
    if description is not None and not isinstance(description, str):
        raise RepositoryAdminError("stored repository creation payload is invalid")
    request = RepositoryCreateRequest(name=name, description=description, private=private)
    _validate_create_request(request)
    return request


def _update_request_from_payload(payload: dict[str, Any]) -> RepositoryUpdateRequest:
    allowed = {"name", "description", "private", "visibility", "archived", "default_branch"}
    if any(key not in allowed for key in payload):
        raise RepositoryAdminError("stored repository update payload is invalid")
    request = RepositoryUpdateRequest(
        name=_optional_str(payload.get("name")),
        description=_optional_str(payload.get("description")),
        private=_optional_bool(payload.get("private")),
        visibility=_optional_str(payload.get("visibility")),
        archived=_optional_bool(payload.get("archived")),
        default_branch=_optional_str(payload.get("default_branch")),
    )
    request.payload()
    return request


def _snapshot_preconditions(snapshot: RepositorySnapshot) -> dict[str, object]:
    return {
        "id": snapshot.github_repository_id,
        "full_name": snapshot.full_name,
        "private": snapshot.private,
        "archived": snapshot.archived,
        "default_branch": snapshot.default_branch,
        "updated_at": snapshot.updated_at.isoformat(),
    }


def _fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _positive_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RepositoryAdminError("stored text payload is invalid")
    return value


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise RepositoryAdminError("stored boolean payload is invalid")
    return value
