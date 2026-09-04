"""Typed repository administration endpoints built on the canonical REST gateway."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from pydantic import SecretStr

from gitdock.github.client import GitHubRestClient
from gitdock.github.models import GitHubResponse
from gitdock.github.repositories import RepositorySnapshot, parse_repository


@dataclass(frozen=True, slots=True)
class RepositoryCreateRequest:
    name: str
    description: str | None = None
    private: bool = True


@dataclass(frozen=True, slots=True)
class RepositoryUpdateRequest:
    name: str | None = None
    description: str | None = None
    private: bool | None = None
    visibility: str | None = None
    archived: bool | None = None
    default_branch: str | None = None

    def payload(self) -> dict[str, object]:
        values: dict[str, object] = {}
        if self.name is not None:
            values["name"] = self.name
        if self.description is not None:
            values["description"] = self.description
        if self.private is not None:
            values["private"] = self.private
        if self.visibility is not None:
            values["visibility"] = self.visibility
        if self.archived is not None:
            values["archived"] = self.archived
        if self.default_branch is not None:
            values["default_branch"] = self.default_branch
        if not values:
            raise ValueError("repository update must contain at least one field")
        return values


class GitHubRepositoryAdminGateway:
    """Repository write endpoints. Higher-level services own authorization and confirmation."""

    def __init__(self, client: GitHubRestClient) -> None:
        self._client = client

    async def create_personal_repository(
        self,
        token: SecretStr,
        request: RepositoryCreateRequest,
    ) -> GitHubResponse[RepositorySnapshot]:
        return await self._client.request_json(
            "POST",
            "/user/repos",
            parser=parse_repository,
            token=token,
            json_body=_create_payload(request),
        )

    async def create_organization_repository(
        self,
        token: SecretStr,
        *,
        organization: str,
        request: RepositoryCreateRequest,
    ) -> GitHubResponse[RepositorySnapshot]:
        organization_path = quote(_path_segment(organization, "organization"), safe="")
        return await self._client.request_json(
            "POST",
            f"/orgs/{organization_path}/repos",
            parser=parse_repository,
            token=token,
            json_body=_create_payload(request),
        )

    async def update_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
        request: RepositoryUpdateRequest,
    ) -> GitHubResponse[RepositorySnapshot]:
        owner = quote(_path_segment(owner_login, "owner"), safe="")
        repository = quote(_path_segment(name, "repository"), safe="")
        return await self._client.request_json(
            "PATCH",
            f"/repos/{owner}/{repository}",
            parser=parse_repository,
            token=token,
            json_body=request.payload(),
        )

    async def delete_repository(
        self,
        token: SecretStr,
        *,
        owner_login: str,
        name: str,
    ) -> GitHubResponse[None]:
        owner = quote(_path_segment(owner_login, "owner"), safe="")
        repository = quote(_path_segment(name, "repository"), safe="")
        return await self._client.request_empty(
            "DELETE",
            f"/repos/{owner}/{repository}",
            token=token,
        )


def _create_payload(request: RepositoryCreateRequest) -> dict[str, object]:
    name = _path_segment(request.name, "repository")
    payload: dict[str, object] = {"name": name, "private": request.private}
    if request.description is not None:
        payload["description"] = request.description.strip()
    return payload


def _path_segment(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized or "/" in normalized or "\\" in normalized or "\x00" in normalized:
        raise ValueError(f"{label} is not a valid path segment")
    if len(normalized) > 255:
        raise ValueError(f"{label} is too long")
    return normalized
