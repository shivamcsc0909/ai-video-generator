"""Secure Credential Encryption Service.

Uses Fernet symmetric encryption to encrypt API keys at rest in PostgreSQL.
Never logs credentials or exposes raw keys to the frontend.
"""

from __future__ import annotations

import base64
import os
from typing import Optional
from cryptography.fernet import Fernet
try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class CredentialEncryptionService:
    """Encrypts and decrypts provider API keys using Fernet symmetric encryption.

    The encryption key is loaded from the ENCRYPTION_KEY environment variable.
    Raw keys are never stored in PostgreSQL or logged.
    """

    def __init__(self, key: Optional[str] = None):
        if not key:
            from backend.core.config import get_settings

            settings = get_settings()
            key = settings.ENCRYPTION_KEY

        if not key:
            # Fallback to key file if present, or generate a deterministic development key
            key_file = os.path.expanduser("~/.videostudio_key")
            if os.path.exists(key_file):
                with open(key_file, "r") as f:
                    key = f.read().strip()
            else:
                # Generate new key and persist to ~/.videostudio_key for seamless local development
                new_key = Fernet.generate_key().decode()
                try:
                    with open(key_file, "w") as f:
                        f.write(new_key)
                    key = new_key
                    logger.info("credential_encryption_key_auto_generated", path=key_file)
                except Exception as e:
                    key = new_key
                    logger.warning("credential_key_file_write_failed", error=str(e))

        # Format key as valid 32-byte urlsafe base64 if needed
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception:
            # Hash to standard 32 bytes and urlsafe base64 encode
            import hashlib

            digest = hashlib.sha256(key.encode()).digest()
            b64_key = base64.urlsafe_b64encode(digest)
            self._fernet = Fernet(b64_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt an API key into a base64 ciphertext string."""
        if not plaintext or not plaintext.strip():
            raise ValueError("Cannot encrypt an empty credential.")
        encrypted_bytes = self._fernet.encrypt(plaintext.strip().encode("utf-8"))
        return encrypted_bytes.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext back to the plaintext API key. Only invoked server-side."""
        if not ciphertext or not ciphertext.strip():
            raise ValueError("No encrypted credential provided.")
        decrypted_bytes = self._fernet.decrypt(ciphertext.strip().encode("utf-8"))
        return decrypted_bytes.decode("utf-8")

    @staticmethod
    def get_key_hint(plaintext: str) -> str:
        """Return a safe masked representation showing only the last 4 characters.

        Example: ************abcd
        Never displays the full key.
        """
        clean = plaintext.strip() if plaintext else ""
        if len(clean) <= 4:
            return "****"
        return "************" + clean[-4:]

    @staticmethod
    def generate_key() -> str:
        """Generate a cryptographically secure 256-bit Fernet key."""
        return Fernet.generate_key().decode("utf-8")


# Module-level singleton
_instance: Optional[CredentialEncryptionService] = None


def get_encryption_service() -> CredentialEncryptionService:
    global _instance
    if _instance is None:
        _instance = CredentialEncryptionService()
    return _instance
