"""Per-email lockout helpers, called from login views."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import LoginAttempt

FAILURE_OUTCOMES = (
    LoginAttempt.OUTCOME_WRONG_PASSWORD,
    LoginAttempt.OUTCOME_MFA_FAILED,
    LoginAttempt.OUTCOME_UNKNOWN_USER,
)


def _window_start(now=None):
    now = now or timezone.now()
    return now - timedelta(minutes=int(settings.LOGIN_LOCKOUT_WINDOW_MINUTES))


def _lockout_horizon(now=None):
    now = now or timezone.now()
    return now - timedelta(minutes=int(settings.LOGIN_LOCKOUT_DURATION_MINUTES))


def is_locked(email: str) -> bool:
    """Return True when the email has hit the failure threshold within the window
    and the lockout duration has not yet elapsed.

    Implementation: count failures in the lockout window. Once the threshold is
    reached, the lockout persists for LOGIN_LOCKOUT_DURATION_MINUTES from the most
    recent failure.
    """
    if not email:
        return False

    threshold = int(settings.LOGIN_MAX_ATTEMPTS)
    duration_horizon = _lockout_horizon()
    window_start = _window_start()

    qs = LoginAttempt.objects.filter(
        email_attempted__iexact=email,
        outcome__in=FAILURE_OUTCOMES,
        created_at__gte=min(duration_horizon, window_start),
    ).order_by("-created_at")

    recent = list(qs[: threshold + 5])
    if len(recent) < threshold:
        return False

    last_failure = recent[0].created_at
    if last_failure < duration_horizon:
        return False

    in_window = [a for a in recent if a.created_at >= window_start]
    return len(in_window) >= threshold
