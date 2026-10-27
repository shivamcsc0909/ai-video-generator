"""Tests for Credential Encryption Service and security requirements."""

from backend.services.credentials.encryption import CredentialEncryptionService


def test_encryption_decryption_cycle():
    key = CredentialEncryptionService.generate_key()
    service = CredentialEncryptionService(key=key)

    secret_api_key = "AIzaSyD-TEST-GEMINI-SECRET-KEY-12345"
    encrypted = service.encrypt(secret_api_key)

    # Must be encrypted (not plaintext)
    assert encrypted != secret_api_key
    assert "AIzaSyD" not in encrypted

    # Must cleanly decrypt back
    decrypted = service.decrypt(encrypted)
    assert decrypted == secret_api_key


def test_key_hint_masking():
    # Never expose more than the last 4 characters
    hint1 = CredentialEncryptionService.get_key_hint("gsk_1234567890abcdefABCD")
    assert hint1.endswith("ABCD")
    assert "1234567890" not in hint1
    assert hint1.startswith("************")

    # Short key fallback
    hint2 = CredentialEncryptionService.get_key_hint("abc")
    assert hint2 == "****"


def test_cannot_encrypt_empty():
    key = CredentialEncryptionService.generate_key()
    service = CredentialEncryptionService(key=key)

    failed = False
    try:
        service.encrypt("")
    except ValueError:
        failed = True
    assert failed, "Should raise ValueError on empty encryption"

    failed = False
    try:
        service.decrypt("")
    except ValueError:
        failed = True
    assert failed, "Should raise ValueError on empty decryption"
