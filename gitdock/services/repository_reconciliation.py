"""Safe read-back reconciliation helpers for uncertain repository writes."""

from __future__ import annotations

from gitdock.github.errors import GitHubErrorKind, GitHubGatewayError
from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.repository_admin import RepositoryCreateRequest, RepositoryUpdateRequest

_RECONCILABLE_WRITE_ERRORS = {
    GitHubErrorKind.TRANSIENT,
    GitHubErrorKind.UNEXPECTED,
}


def should_reconcile_write_error(error: GitHubGatewayError) -> bool:
    """Return whether a write may have reached GitHub despite the observed error."""

    return error.kind in _RECONCILABLE_WRITE_ERRORS


def create_matches_remote(
    snapshot: RepositorySnapshot,
    *,
    owner_login: str,
    request: RepositoryCreateRequest,
) -> bool:
    """Check whether remote state proves the requested repository creation exists."""

    return (
        snapshot.owner_login == owner_login
        and snapshot.name == request.name.strip()
        and snapshot.private is request.private
        and _normalized_description(snapshot.description)
        == _normalized_description(request.description)
    )


def update_matches_remote(
    snapshot: RepositorySnapshot,
    *,
    repository_id: int,
    request: RepositoryUpdateRequest,
) -> bool:
    """Check whether remote state proves all requested mutable fields were applied."""

    if snapshot.github_repository_id != repository_id:
        return False
    if request.name is not None and snapshot.name != request.name.strip():
        return False
    if request.description is not None and _normalized_description(
        snapshot.description
    ) != _normalized_description(request.description):
        return False
    if request.private is not None and snapshot.private is not request.private:
        return False
    if request.visibility is not None:
        visibility = request.visibility.strip().lower()
        if visibility == "private" and not snapshot.private:
            return False
        if visibility == "public" and snapshot.private:
            return False
        if visibility not in {"private", "public"}:
            return False
    if request.archived is not None and snapshot.archived is not request.archived:
        return False
    if request.default_branch is not None and snapshot.default_branch != request.default_branch.strip():
        return False
    return True


def _normalized_description(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
