"""Audit helpers."""

from __future__ import annotations

import logging

from django.http import HttpRequest

from .models import LoginAttempt

logger = logging.getLogger(__name__)


def client_ip(request: HttpRequest) -> str | None:
    """Best-effort source IP, trusting X-Forwarded-For only behind a proxy."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def user_agent(request: HttpRequest) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:255]


def record_attempt(
    *,
    request: HttpRequest | None,
    email: str,
    outcome: str,
    user=None,
) -> LoginAttempt:
    """Persist a login attempt for later inspection."""
    return LoginAttempt.objects.create(
        user=user,
        email_attempted=email or "",
        ip_address=client_ip(request) if request is not None else None,
        user_agent=user_agent(request) if request is not None else "",
        outcome=outcome,
    )
