"""Provider abstraction for OAuth 2.0 social login.

Each concrete provider implements three operations:

- ``authorize_url(state)``  – return the URL we should redirect the browser to
  with the given anti-forgery state token.
- ``exchange_code(code, redirect_uri)`` – exchange the authorization code at
  the provider for an access token.
- ``fetch_user(access_token)`` – use the access token to fetch enough profile
  to identify or create a local account.

The token never leaves this layer; views see only an :class:`OAuthUser`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OAuthUser:
    """Minimal profile returned by a provider after a successful callback."""

    provider_user_id: str
    email: str
    full_name: str = ""


class Provider:
    """Abstract OAuth provider."""

    name: str = ""

    def authorize_url(self, state: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def exchange_code(self, code: str, redirect_uri: str) -> str:  # pragma: no cover
        raise NotImplementedError

    def fetch_user(self, access_token: str) -> OAuthUser:  # pragma: no cover
        raise NotImplementedError
