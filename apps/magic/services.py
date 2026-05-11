"""Magic-link issue and consume services.

Both functions are pure with respect to side effects beyond the ORM and email
backend, so they are easy to test in isolation.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.common.emails import send_template_email
from apps.common.tokens import hash_token, new_token

from .models import MagicLinkToken


def _ttl() -> timedelta:
    return timedelta(minutes=int(settings.MAGIC_LINK_TTL_MINUTES))


def issue_link(*, email: str, ip: str | None, request=None) -> None:
    """Issue a magic link for ``email``.

    Always behaves identically (same response time, same DB write count) whether
    the email belongs to a registered user or not. The plain token is included
    in the outbound email only.
    """
    email = (email or "").strip().lower()
    if not email:
        return
    user = User.objects.filter(email__iexact=email).first()
    plain = new_token()
    record = MagicLinkToken.objects.create(
        user=user,
        email=email,
        token_hash=hash_token(plain),
        expires_at=timezone.now() + _ttl(),
        ip_created=ip,
    )

    if user is None or not user.is_active:
        # Generate the row but skip sending. Caller must still respond
        # generically — that is enforced at the view layer.
        return

    consume_path = reverse("magic:consume", args=[plain])
    if request is not None:
        consume_url = request.build_absolute_uri(consume_path)
    else:
        consume_url = consume_path

    send_template_email(
        to=email,
        subject="Your sign-in link",
        template="emails/magic_link.txt",
        context={"user": user, "consume_url": consume_url, "ttl": _ttl()},
    )

    # Mark the row as the most recent for that email; nothing else needed.
    _ = record


def consume(*, token: str, ip: str | None) -> User | None:
    """Verify a magic-link token and return the associated user, or None.

    Marks the token as used on success so that replay is rejected.
    """
    if not token:
        return None
    try:
        record = MagicLinkToken.objects.select_related("user").get(token_hash=hash_token(token))
    except MagicLinkToken.DoesNotExist:
        return None
    if record.used_at is not None:
        return None
    if record.expires_at < timezone.now():
        return None
    if record.user is None or not record.user.is_active:
        return None

    now = timezone.now()
    record.used_at = now
    record.ip_used = ip
    record.save(update_fields=["used_at", "ip_used"])

    user = record.user
    if not user.is_email_verified:
        # Receiving the email proves control of the inbox, so mark verified.
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
    return user
