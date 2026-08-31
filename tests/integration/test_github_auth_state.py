import base64
import hashlib
from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import select

from gitdock.db.base import Base
from gitdock.db.models import GitHubAuthorizationState, User
from gitdock.db.session import create_engine, create_session_factory
from gitdock.github.auth_state import (
    AuthorizationFlow,
    GitHubAuthorizationStateService,
    InvalidAuthorizationState,
)
from gitdock.security.crypto import CredentialCipher


@pytest.mark.integration
@pytest.mark.asyncio
async def test_authorization_state_is_hashed_encrypted_user_bound_and_one_time() -> None:
    now = [datetime(2026, 8, 31, 1, 0, tzinfo=UTC)]
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    cipher = CredentialCipher({1: Fernet.generate_key()}, active_version=1)
    service = GitHubAuthorizationStateService(cipher, clock=lambda: now[0])

    async with sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        request = await service.create(
            session,
            user_id=user.id,
            flow=AuthorizationFlow.USER_AUTHORIZATION,
            candidate_installation_id=987,
        )
        await session.commit()

        stored = await session.scalar(select(GitHubAuthorizationState))
        assert stored is not None
        assert stored.state_digest != request.state
        assert stored.state_digest == hashlib.sha256(request.state.encode()).hexdigest()
        assert request.state.encode() not in stored.encrypted_code_verifier

        consumed = await service.consume(
            session,
            state=request.state,
            expected_flow=AuthorizationFlow.USER_AUTHORIZATION,
        )
        await session.commit()

        assert consumed.user_id == user.id
        assert consumed.candidate_installation_id == 987
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(consumed.code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        assert challenge == request.code_challenge

        with pytest.raises(InvalidAuthorizationState):
            await service.consume(
                session,
                state=request.state,
                expected_flow=AuthorizationFlow.USER_AUTHORIZATION,
            )

    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_wrong_flow_does_not_consume_state_and_expired_state_is_rejected() -> None:
    now = [datetime(2026, 8, 31, 1, 0, tzinfo=UTC)]
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    service = GitHubAuthorizationStateService(
        CredentialCipher({1: Fernet.generate_key()}, active_version=1),
        ttl=timedelta(minutes=10),
        clock=lambda: now[0],
    )

    async with sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        request = await service.create(
            session,
            user_id=user.id,
            flow=AuthorizationFlow.INSTALLATION_BINDING,
        )
        await session.commit()

        with pytest.raises(InvalidAuthorizationState):
            await service.consume(
                session,
                state=request.state,
                expected_flow=AuthorizationFlow.USER_AUTHORIZATION,
            )
        await session.rollback()

        consumed = await service.consume(
            session,
            state=request.state,
            expected_flow=AuthorizationFlow.INSTALLATION_BINDING,
        )
        await session.commit()
        assert consumed.user_id == user.id

        another = await service.create(
            session,
            user_id=user.id,
            flow=AuthorizationFlow.INSTALLATION_BINDING,
        )
        await session.commit()
        now[0] += timedelta(minutes=11)
        with pytest.raises(InvalidAuthorizationState):
            await service.consume(
                session,
                state=another.state,
                expected_flow=AuthorizationFlow.INSTALLATION_BINDING,
            )

    await engine.dispose()
