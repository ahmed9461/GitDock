"""Encrypted persistence helpers for GitHub user credential material."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import SecretStr

from gitdock.db.models.identity import GitHubAccount
from gitdock.github.auth import UserAccessToken
from gitdock.security.crypto import CredentialCipher


@dataclass(frozen=True, slots=True)
class DecryptedUserCredentials:
    access_token: SecretStr
    refresh_token: SecretStr | None
    expires_at: datetime | None
    refresh_expires_at: datetime | None


class GitHubUserCredentialStore:
    """Seal/unseal user tokens while keeping encryption keys outside database rows."""

    def __init__(self, cipher: CredentialCipher) -> None:
        self._cipher = cipher

    def persist(self, account: GitHubAccount, token: UserAccessToken) -> None:
        access = self._cipher.encrypt(token.token.get_secret_value())
        refresh = (
            self._cipher.encrypt(token.refresh_token.get_secret_value())
            if token.refresh_token is not None
            else None
        )
        if refresh is not None and refresh.key_version != access.key_version:
            raise RuntimeError(
                "credential encryption key version changed during one persistence call"
            )

        account.encrypted_access_token = access.ciphertext
        account.encrypted_refresh_token = refresh.ciphertext if refresh is not None else None
        account.token_expires_at = token.expires_at
        account.refresh_token_expires_at = token.refresh_expires_at
        account.token_key_version = access.key_version

    def load(self, account: GitHubAccount) -> DecryptedUserCredentials | None:
        if account.encrypted_access_token is None:
            return None
        if account.token_key_version is None:
            raise RuntimeError("stored GitHub credential is missing its encryption key version")

        access_token = SecretStr(
            self._cipher.decrypt(account.encrypted_access_token, account.token_key_version)
        )
        refresh_token = None
        if account.encrypted_refresh_token is not None:
            refresh_token = SecretStr(
                self._cipher.decrypt(account.encrypted_refresh_token, account.token_key_version)
            )
        return DecryptedUserCredentials(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=account.token_expires_at,
            refresh_expires_at=account.refresh_token_expires_at,
        )

    @staticmethod
    def clear(account: GitHubAccount) -> None:
        account.encrypted_access_token = None
        account.encrypted_refresh_token = None
        account.token_expires_at = None
        account.refresh_token_expires_at = None
        account.token_key_version = None
