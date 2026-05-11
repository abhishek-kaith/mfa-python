"""Shared models used across apps."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class LoginAttempt(models.Model):
    """Audit row for every login attempt, success or failure."""

    OUTCOME_SUCCESS = "success"
    OUTCOME_WRONG_PASSWORD = "wrong_password"  # noqa: S105 - enum identifier, not a credential
    OUTCOME_MFA_FAILED = "mfa_failed"
    OUTCOME_LOCKED = "locked"
    OUTCOME_UNKNOWN_USER = "unknown_user"
    OUTCOME_INACTIVE = "inactive"

    OUTCOME_CHOICES = [
        (OUTCOME_SUCCESS, "Success"),
        (OUTCOME_WRONG_PASSWORD, "Wrong password"),
        (OUTCOME_MFA_FAILED, "MFA failed"),
        (OUTCOME_LOCKED, "Locked"),
        (OUTCOME_UNKNOWN_USER, "Unknown user"),
        (OUTCOME_INACTIVE, "Inactive account"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_attempts",
    )
    email_attempted = models.EmailField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    outcome = models.CharField(max_length=32, choices=OUTCOME_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email_attempted", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.email_attempted} {self.outcome} @ {self.created_at:%Y-%m-%d %H:%M}"
