"""Helpers for issuing and verifying single-use tokens.

Plain tokens are returned to the caller (so they can be put in an email URL).
Only the SHA-256 of the token is stored — the database never sees the
plaintext, so a leaked dump cannot be replayed.
"""

from __future__ import annotations

import hashlib
import secrets


def new_token() -> str:
    """Return a URL-safe random token (43 chars, ~256 bits of entropy)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Return the hex SHA-256 of a token, suitable for storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
