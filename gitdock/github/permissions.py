"""Central GitDock capability to GitHub permission/token-context mapping."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final


class TokenContext(StrEnum):
    INSTALLATION = "installation"
    USER = "user"


class PermissionLevel(StrEnum):
    READ = "read"
    WRITE = "write"


class GitHubCapability(StrEnum):
    REPOSITORY_METADATA_READ = "repository.metadata.read"
    CONTENTS_READ = "contents.read"
    ISSUES_READ = "issues.read"
    PULL_REQUESTS_READ = "pull_requests.read"
    ACTIONS_READ = "actions.read"
    CONTENTS_WRITE = "contents.write"
    ISSUES_WRITE = "issues.write"
    PULL_REQUESTS_WRITE = "pull_requests.write"
    ACTIONS_WRITE = "actions.write"
    WORKFLOWS_WRITE = "workflows.write"
    REPOSITORY_ADMIN = "repository.admin"


@dataclass(frozen=True, slots=True)
class CapabilityRequirement:
    token_context: TokenContext
    permissions: MappingProxyType[str, PermissionLevel]


def _requirement(
    token_context: TokenContext,
    **permissions: PermissionLevel,
) -> CapabilityRequirement:
    return CapabilityRequirement(token_context, MappingProxyType(dict(permissions)))


CAPABILITY_REQUIREMENTS: Final[MappingProxyType[GitHubCapability, CapabilityRequirement]] = (
    MappingProxyType(
        {
            GitHubCapability.REPOSITORY_METADATA_READ: _requirement(
                TokenContext.INSTALLATION, metadata=PermissionLevel.READ
            ),
            GitHubCapability.CONTENTS_READ: _requirement(
                TokenContext.INSTALLATION, contents=PermissionLevel.READ
            ),
            GitHubCapability.ISSUES_READ: _requirement(
                TokenContext.INSTALLATION, issues=PermissionLevel.READ
            ),
            GitHubCapability.PULL_REQUESTS_READ: _requirement(
                TokenContext.INSTALLATION, pull_requests=PermissionLevel.READ
            ),
            GitHubCapability.ACTIONS_READ: _requirement(
                TokenContext.INSTALLATION, actions=PermissionLevel.READ
            ),
            GitHubCapability.CONTENTS_WRITE: _requirement(
                TokenContext.INSTALLATION, contents=PermissionLevel.WRITE
            ),
            GitHubCapability.ISSUES_WRITE: _requirement(
                TokenContext.INSTALLATION, issues=PermissionLevel.WRITE
            ),
            GitHubCapability.PULL_REQUESTS_WRITE: _requirement(
                TokenContext.INSTALLATION, pull_requests=PermissionLevel.WRITE
            ),
            GitHubCapability.ACTIONS_WRITE: _requirement(
                TokenContext.INSTALLATION, actions=PermissionLevel.WRITE
            ),
            GitHubCapability.WORKFLOWS_WRITE: _requirement(
                TokenContext.INSTALLATION, workflows=PermissionLevel.WRITE
            ),
            GitHubCapability.REPOSITORY_ADMIN: _requirement(
                TokenContext.INSTALLATION, administration=PermissionLevel.WRITE
            ),
        }
    )
)


def requirement_for(capability: GitHubCapability) -> CapabilityRequirement:
    return CAPABILITY_REQUIREMENTS[capability]


def combine_installation_permissions(
    capabilities: set[GitHubCapability],
) -> dict[str, PermissionLevel]:
    """Combine compatible capabilities using write-over-read semantics."""

    merged: dict[str, PermissionLevel] = {}
    for capability in capabilities:
        requirement = requirement_for(capability)
        if requirement.token_context is not TokenContext.INSTALLATION:
            raise ValueError(f"capability requires {requirement.token_context.value} token context")
        for permission, level in requirement.permissions.items():
            current = merged.get(permission)
            if current is None or level is PermissionLevel.WRITE:
                merged[permission] = level
    return merged
