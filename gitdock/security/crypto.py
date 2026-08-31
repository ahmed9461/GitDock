"""Authenticated encryption for persisted credential material."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken


class CredentialEncryptionError(RuntimeError):
    """Raised when credential material cannot be encrypted or decrypted safely."""


@dataclass(frozen=True, slots=True)
class EncryptedSecret:
    ciphertext: bytes
    key_version: int


class CredentialCipher:
    """Version-aware Fernet encryption without storing master keys in the database."""

    def __init__(self, keys: Mapping[int, str | bytes], active_version: int) -> None:
        if active_version <= 0:
            raise ValueError("active key version must be positive")
        if active_version not in keys:
            raise ValueError("active credential encryption key version is not configured")

        ciphers: dict[int, Fernet] = {}
        try:
            for version, raw_key in keys.items():
                if version <= 0:
                    raise ValueError("credential encryption key versions must be positive")
                key = raw_key.encode("ascii") if isinstance(raw_key, str) else raw_key
                ciphers[version] = Fernet(key)
        except (ValueError, TypeError) as exc:
            raise CredentialEncryptionError("credential encryption key is invalid") from exc

        self._ciphers = ciphers
        self._active_version = active_version

    @property
    def active_version(self) -> int:
        return self._active_version

    def encrypt(self, plaintext: str) -> EncryptedSecret:
        if not plaintext:
            raise ValueError("credential plaintext must not be empty")
        ciphertext = self._ciphers[self._active_version].encrypt(plaintext.encode("utf-8"))
        return EncryptedSecret(ciphertext=ciphertext, key_version=self._active_version)

    def decrypt(self, ciphertext: bytes, key_version: int) -> str:
        cipher = self._ciphers.get(key_version)
        if cipher is None:
            raise CredentialEncryptionError("credential encryption key version is unavailable")
        try:
            plaintext = cipher.decrypt(ciphertext)
        except InvalidToken as exc:
            raise CredentialEncryptionError(
                "credential ciphertext could not be authenticated"
            ) from exc
        try:
            return plaintext.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CredentialEncryptionError("credential plaintext encoding is invalid") from exc
