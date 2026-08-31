import pytest
from cryptography.fernet import Fernet

from gitdock.security.crypto import CredentialCipher, CredentialEncryptionError


def test_credential_cipher_encrypts_and_decrypts_without_plaintext_storage() -> None:
    key = Fernet.generate_key()
    cipher = CredentialCipher({1: key}, active_version=1)

    encrypted = cipher.encrypt("ghu_example_secret")

    assert encrypted.key_version == 1
    assert b"ghu_example_secret" not in encrypted.ciphertext
    assert cipher.decrypt(encrypted.ciphertext, encrypted.key_version) == "ghu_example_secret"


def test_credential_cipher_supports_old_key_versions_for_rotation() -> None:
    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()
    old_cipher = CredentialCipher({1: old_key}, active_version=1)
    encrypted = old_cipher.encrypt("old-secret")

    rotated = CredentialCipher({1: old_key, 2: new_key}, active_version=2)

    assert rotated.decrypt(encrypted.ciphertext, 1) == "old-secret"
    assert rotated.encrypt("new-secret").key_version == 2


def test_credential_cipher_rejects_unknown_or_invalid_keys_without_key_echo() -> None:
    key = Fernet.generate_key()
    cipher = CredentialCipher({1: key}, active_version=1)
    encrypted = cipher.encrypt("secret")

    with pytest.raises(CredentialEncryptionError, match="key version is unavailable"):
        cipher.decrypt(encrypted.ciphertext, 2)

    with pytest.raises(CredentialEncryptionError) as exc_info:
        CredentialCipher({1: b"not-a-valid-fernet-key"}, active_version=1)
    assert "not-a-valid-fernet-key" not in str(exc_info.value)
