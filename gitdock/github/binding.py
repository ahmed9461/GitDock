"""Safe GitHub App installation binding primitives."""

from __future__ import annotations

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gitdock.db.models.identity import GitHubInstallation
from gitdock.github.auth import GitHubAuthClient, InstallationIdentity


class InstallationBindingError(RuntimeError):
    """Raised when an installation cannot be safely bound to a GitDock user."""


class InstallationBindingService:
    """Bind only installations verified through both app and user authentication contexts."""

    def __init__(self, auth_client: GitHubAuthClient) -> None:
        self._auth_client = auth_client

    async def bind(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        user_access_token: SecretStr,
        installation_id: int,
    ) -> GitHubInstallation:
        if user_id <= 0:
            raise ValueError("user ID must be positive")
        if installation_id <= 0:
            raise ValueError("installation ID must be positive")

        app_installation = await self._auth_client.get_app_installation(installation_id)
        user_installation = await self._auth_client.get_user_installation(
            user_access_token, installation_id
        )
        self._require_same_installation(app_installation, user_installation)
        if app_installation.suspended:
            raise InstallationBindingError("GitHub App installation is suspended")

        result = await session.execute(
            select(GitHubInstallation).where(
                GitHubInstallation.installation_id == installation_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None and existing.user_id != user_id:
            raise InstallationBindingError("GitHub App installation is already bound")

        if existing is None:
            existing = GitHubInstallation(
                user_id=user_id,
                installation_id=installation_id,
                account_login=app_installation.account_login,
                account_type=app_installation.account_type,
                suspended=app_installation.suspended,
                permissions_json=dict(app_installation.permissions),
            )
            session.add(existing)
        else:
            existing.account_login = app_installation.account_login
            existing.account_type = app_installation.account_type
            existing.suspended = app_installation.suspended
            existing.permissions_json = dict(app_installation.permissions)

        await session.flush()
        return existing

    @staticmethod
    def _require_same_installation(
        app_installation: InstallationIdentity,
        user_installation: InstallationIdentity,
    ) -> None:
        if (
            app_installation.installation_id != user_installation.installation_id
            or app_installation.account_id != user_installation.account_id
            or app_installation.account_login != user_installation.account_login
            or app_installation.account_type != user_installation.account_type
        ):
            raise InstallationBindingError(
                "GitHub installation identity did not match authenticated user access"
            )
