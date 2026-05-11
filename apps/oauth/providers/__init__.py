"""Provider registry."""

from __future__ import annotations

from .base import OAuthUser, Provider
from .github import GitHubProvider
from .google import GoogleProvider

PROVIDERS: dict[str, type[Provider]] = {
    "google": GoogleProvider,
    "github": GitHubProvider,
}


def get_provider(name: str) -> Provider:
    if name not in PROVIDERS:
        raise KeyError(f"Unknown OAuth provider: {name!r}")
    return PROVIDERS[name]()


__all__ = ["OAuthUser", "Provider", "GoogleProvider", "GitHubProvider", "get_provider"]
