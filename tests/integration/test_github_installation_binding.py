from pydantic import SecretStr
import pytest
from sqlalchemy import select

from gitdock.db.base import Base
from gitdock.db.models import GitHubInstallation, User
from gitdock.db.session import create_engine, create_session_factory
from gitdock.github.auth import InstallationIdentity
from gitdock.github.binding import InstallationBindingError, InstallationBindingService


class FakeAuthClient:
    def __init__(
        self,
        app_installation: InstallationIdentity,
        user_installation: InstallationIdentity,
    ) -> None:
        self.app_installation = app_installation
        self.user_installation = user_installation

    async def get_app_installation(self, installation_id: int) -> InstallationIdentity:
        assert installation_id == self.app_installation.installation_id
        return self.app_installation

    async def get_user_installation(
        self,
        user_token: SecretStr,
        installation_id: int,
    ) -> InstallationIdentity:
        assert user_token.get_secret_value() == "ghu_test"
        assert installation_id == self.user_installation.installation_id
        return self.user_installation


def installation(account_id: int = 10, login: str = "octocat") -> InstallationIdentity:
    return InstallationIdentity(
        installation_id=99,
        account_id=account_id,
        account_login=login,
        account_type="User",
        suspended=False,
        permissions={"metadata": "read", "contents": "read"},
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_binding_persists_only_after_app_and_user_installation_identity_match() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)

    async with sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = InstallationBindingService(FakeAuthClient(installation(), installation()))  # type: ignore[arg-type]
        bound = await service.bind(
            session,
            user_id=user.id,
            user_access_token=SecretStr("ghu_test"),
            installation_id=99,
        )
        await session.commit()

        assert bound.user_id == user.id
        stored = await session.scalar(
            select(GitHubInstallation).where(GitHubInstallation.installation_id == 99)
        )
        assert stored is not None
        assert stored.account_login == "octocat"

    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_binding_rejects_spoofed_candidate_identity_before_database_write() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)

    async with sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = InstallationBindingService(
            FakeAuthClient(installation(account_id=10), installation(account_id=999))  # type: ignore[arg-type]
        )
        with pytest.raises(InstallationBindingError, match="did not match"):
            await service.bind(
                session,
                user_id=user.id,
                user_access_token=SecretStr("ghu_test"),
                installation_id=99,
            )
        await session.rollback()

        stored = await session.scalar(select(GitHubInstallation))
        assert stored is None

    await engine.dispose()
