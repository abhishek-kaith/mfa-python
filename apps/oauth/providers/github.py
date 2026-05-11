"""GitHub OAuth 2.0 provider."""

from __future__ import annotations

from urllib.parse import urlencode

import requests
from django.conf import settings

from .base import OAuthUser, Provider

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"  # noqa: S105 - public OAuth endpoint URL
USER_URL = "https://api.github.com/user"
EMAILS_URL = "https://api.github.com/user/emails"
SCOPES = "user:email"


class GitHubProvider(Provider):
    name = "github"

    @property
    def client_id(self) -> str:
        return settings.GITHUB_OAUTH_CLIENT_ID

    @property
    def client_secret(self) -> str:
        return settings.GITHUB_OAUTH_CLIENT_SECRET

    @property
    def redirect_uri(self) -> str:
        return settings.GITHUB_OAUTH_REDIRECT_URI

    def authorize_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": SCOPES,
            "state": state,
            "allow_signup": "true",
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> str:
        response = requests.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if "access_token" not in payload:
            raise RuntimeError(f"GitHub token exchange failed: {payload!r}")
        return payload["access_token"]

    def fetch_user(self, access_token: str) -> OAuthUser:
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        user_resp = requests.get(USER_URL, headers=headers, timeout=10)
        user_resp.raise_for_status()
        user = user_resp.json()
        email = (user.get("email") or "").lower()
        if not email:
            emails_resp = requests.get(EMAILS_URL, headers=headers, timeout=10)
            emails_resp.raise_for_status()
            for entry in emails_resp.json():
                if entry.get("primary") and entry.get("verified"):
                    email = entry["email"].lower()
                    break
        return OAuthUser(
            provider_user_id=str(user["id"]),
            email=email,
            full_name=user.get("name") or user.get("login", ""),
        )
