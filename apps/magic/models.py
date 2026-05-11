"""Magic-link token model."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class MagicLinkToken(models.Model):
    """One-time, hashed, time-bound login token sent over email.

    The plain token is never stored. Only its SHA-256 hash sits in the database,
    so a leaked dump cannot be replayed. ``user`` is nullable because we issue
    a row even for unknown emails to keep the response time identical and
    avoid enumeration via timing.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="magic_links",
    )
    email = models.EmailField()
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip_created = models.GenericIPAddressField(null=True, blank=True)
    ip_used = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token_hash"]),
            models.Index(fields=["email", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"MagicLinkToken(email={self.email}, used={self.used_at is not None})"
