"""Models for the OAuth app."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class SocialAccount(models.Model):
    """A link between a Django user and an external identity at a provider.

    Access tokens are intentionally not stored. After we fetch the user's
    profile during the OAuth callback, the token is discarded. The only
    long-lived state is the (provider, provider_user_id, email, user) row.
    """

    PROVIDER_GOOGLE = "google"
    PROVIDER_GITHUB = "github"

    PROVIDER_CHOICES = [
        (PROVIDER_GOOGLE, "Google"),
        (PROVIDER_GITHUB, "GitHub"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_accounts",
        null=True,
        blank=True,
    )
    provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=191)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("provider", "provider_user_id")]
        indexes = [models.Index(fields=["email"])]

    def __str__(self) -> str:
        return f"{self.provider}:{self.provider_user_id} ({self.email})"
