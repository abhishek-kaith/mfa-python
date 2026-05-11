"""Account linking decisions for OAuth callbacks."""

from __future__ import annotations

from dataclasses import dataclass

from apps.accounts.models import User

from .models import SocialAccount
from .providers import OAuthUser


@dataclass
class LinkResult:
    user: User
    created: bool


def link_or_create(provider: str, profile: OAuthUser) -> LinkResult:
    """Resolve an OAuth identity to a Django user.

    Strategy, in order:

    1. If a SocialAccount already exists for (provider, provider_user_id),
       return its user.
    2. Otherwise, look up a user by email. If one exists, link the social
       account to that user.
    3. Otherwise, create a new user. Mark the account email-verified because
       receipt of the OAuth callback proves control of the email at the
       provider level.
    """
    existing = (
        SocialAccount.objects.select_related("user")
        .filter(provider=provider, provider_user_id=profile.provider_user_id)
        .first()
    )
    if existing is not None and existing.user is not None:
        return LinkResult(user=existing.user, created=False)

    user = User.objects.filter(email__iexact=profile.email).first() if profile.email else None
    created = False
    if user is None:
        user = User.objects.create_user(
            email=profile.email or f"{profile.provider_user_id}@{provider}.local",
            full_name=profile.full_name or "",
        )
        user.is_active = True
        user.is_email_verified = bool(profile.email)
        user.set_unusable_password()
        user.save()
        created = True

    SocialAccount.objects.update_or_create(
        provider=provider,
        provider_user_id=profile.provider_user_id,
        defaults={"user": user, "email": profile.email or ""},
    )
    return LinkResult(user=user, created=created)
