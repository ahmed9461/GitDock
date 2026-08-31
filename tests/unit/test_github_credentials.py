from datetime import UTC, datetime

from cryptography.fernet import Fernet
from pydantic import SecretStr

from gitdock.db.models.identity import GitHubAccount
from gitdock.github.auth import UserAccessToken
from gitdock.github.credentials import GitHubUserCredentialStore
from gitdock.security.crypto import CredentialCipher


def test_user_credentials_are_encrypted_before_model_persistence_and_can_be_cleared() -> None:
    cipher = CredentialCipher({7: Fernet.generate_key()}, active_version=7)
    store = GitHubUserCredentialStore(cipher)
    account = GitHubAccount(user_id=1, github_user_id=55, login="octocat")
    token = UserAccessToken(
        token=SecretStr("ghu_access_secret"),
        expires_at=datetime(2026, 9, 1, tzinfo=UTC),
        refresh_token=SecretStr("ghr_refresh_secret"),
        refresh_expires_at=datetime(2027, 1, 1, tzinfo=UTC),
    )

    store.persist(account, token)

    assert account.token_key_version == 7
    assert account.encrypted_access_token is not None
    assert account.encrypted_refresh_token is not None
    assert b"ghu_access_secret" not in account.encrypted_access_token
    assert b"ghr_refresh_secret" not in account.encrypted_refresh_token

    loaded = store.load(account)
    assert loaded is not None
    assert loaded.access_token.get_secret_value() == "ghu_access_secret"
    assert loaded.refresh_token is not None
    assert loaded.refresh_token.get_secret_value() == "ghr_refresh_secret"

    store.clear(account)
    assert store.load(account) is None
