"""Account services: token issuing and consuming.

The view layer should call these. Returning ``None`` on a failed consume keeps
error messages generic and prevents account enumeration.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.common.tokens import hash_token, new_token

from .models import EmailVerificationToken, PasswordResetToken, User


def issue_email_verification_token(user: User, ttl_hours: int = 24) -> str:
    token = new_token()
    EmailVerificationToken.objects.create(
        user=user,
        token_hash=hash_token(token),
        expires_at=timezone.now() + timedelta(hours=ttl_hours),
    )
    return token


def consume_email_verification_token(token: str) -> User | None:
    if not token:
        return None
    try:
        record = EmailVerificationToken.objects.select_related("user").get(
            token_hash=hash_token(token)
        )
    except EmailVerificationToken.DoesNotExist:
        return None
    if record.used_at is not None:
        return None
    if record.expires_at < timezone.now():
        return None
    now = timezone.now()
    record.used_at = now
    record.save(update_fields=["used_at"])
    user = record.user
    if not user.is_email_verified:
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
    return user


def issue_password_reset_token(user: User, ttl_hours: int = 1) -> str:
    token = new_token()
    PasswordResetToken.objects.create(
        user=user,
        token_hash=hash_token(token),
        expires_at=timezone.now() + timedelta(hours=ttl_hours),
    )
    return token


def consume_password_reset_token(token: str) -> User | None:
    if not token:
        return None
    try:
        record = PasswordResetToken.objects.select_related("user").get(token_hash=hash_token(token))
    except PasswordResetToken.DoesNotExist:
        return None
    if record.used_at is not None:
        return None
    if record.expires_at < timezone.now():
        return None
    record.used_at = timezone.now()
    record.save(update_fields=["used_at"])
    return record.user
