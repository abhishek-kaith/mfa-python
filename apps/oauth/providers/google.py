"""Google OAuth 2.0 provider."""

from __future__ import annotations

from urllib.parse import urlencode

import requests
from django.conf import settings

from .base import OAuthUser, Provider

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - public OAuth endpoint URL
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
SCOPES = "openid email profile"


class GoogleProvider(Provider):
    name = "google"

    @property
    def client_id(self) -> str:
        return settings.GOOGLE_OAUTH_CLIENT_ID

    @property
    def client_secret(self) -> str:
        return settings.GOOGLE_OAUTH_CLIENT_SECRET

    @property
    def redirect_uri(self) -> str:
        return settings.GOOGLE_OAUTH_REDIRECT_URI

    def authorize_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> str:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": redirect_uri,
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def fetch_user(self, access_token: str) -> OAuthUser:
        response = requests.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return OAuthUser(
            provider_user_id=str(data["sub"]),
            email=data.get("email", "").lower(),
            full_name=data.get("name", ""),
        )
