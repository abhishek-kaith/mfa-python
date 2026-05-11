"""TOTP device and backup-code models."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class TOTPDevice(models.Model):
    """A single user's TOTP device.

    The base32 secret is encrypted at rest with a Fernet key from settings.
    A device only counts toward MFA gating once :attr:`confirmed` is True,
    which is set after the user's authenticator app produces a valid code.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="totp_device",
    )
    secret_encrypted = models.TextField()
    confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "TOTP device"
        verbose_name_plural = "TOTP devices"

    def __str__(self) -> str:
        state = "confirmed" if self.confirmed else "pending"
        return f"TOTPDevice(user={self.user_id}, {state})"


class BackupCode(models.Model):
    """One-time recovery code that substitutes for a TOTP code.

    Only the SHA-256 hash is stored; the plain codes are shown to the user
    exactly once at generation time.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="backup_codes",
    )
    code_hash = models.CharField(max_length=64, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        unique_together = [("user", "code_hash")]

    def __str__(self) -> str:
        return f"BackupCode(user={self.user_id}, used={self.is_used})"

    @property
    def is_used(self) -> bool:
        return self.used_at is not None
