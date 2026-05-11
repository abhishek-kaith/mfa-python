"""Fernet helpers for symmetric encryption of secrets at rest.

The TOTP secret in the database is encrypted with a Fernet key supplied via the
``FERNET_KEY`` environment variable. The plaintext appears only in process
memory at the moment a code is verified.
"""

from __future__ import annotations

from cryptography.fernet import Fernet
from django.conf import settings


def _fernet() -> Fernet:
    key = settings.FERNET_KEY
    if not key:
        raise RuntimeError(
            "FERNET_KEY is not set. Run `make keys` and paste the value into your .env."
        )
    return Fernet(key.encode("utf-8") if isinstance(key, str) else key)


def encrypt(plaintext: bytes) -> str:
    """Encrypt ``plaintext`` and return the ciphertext as a UTF-8 string."""
    return _fernet().encrypt(plaintext).decode("utf-8")


def decrypt(ciphertext: str) -> bytes:
    """Decrypt ``ciphertext`` produced by :func:`encrypt`."""
    return _fernet().decrypt(ciphertext.encode("utf-8"))
