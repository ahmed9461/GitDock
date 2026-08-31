from gitdock.github.permissions import (
    GitHubCapability,
    PermissionLevel,
    TokenContext,
    combine_installation_permissions,
    requirement_for,
)


def test_read_capability_uses_installation_context_and_minimum_permission() -> None:
    requirement = requirement_for(GitHubCapability.CONTENTS_READ)

    assert requirement.token_context is TokenContext.INSTALLATION
    assert dict(requirement.permissions) == {"contents": PermissionLevel.READ}


def test_combined_permissions_promote_write_over_read() -> None:
    permissions = combine_installation_permissions(
        {GitHubCapability.CONTENTS_READ, GitHubCapability.CONTENTS_WRITE}
    )

    assert permissions == {"contents": PermissionLevel.WRITE}


def test_read_only_p2_capabilities_do_not_request_write_permissions() -> None:
    permissions = combine_installation_permissions(
        {
            GitHubCapability.REPOSITORY_METADATA_READ,
            GitHubCapability.CONTENTS_READ,
            GitHubCapability.ISSUES_READ,
            GitHubCapability.PULL_REQUESTS_READ,
            GitHubCapability.ACTIONS_READ,
        }
    )

    assert set(permissions.values()) == {PermissionLevel.READ}
