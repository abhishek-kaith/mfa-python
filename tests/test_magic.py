"""Phase 3 tests covering magic-link login (TC-07..10)."""

from __future__ import annotations

import re
from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.common.tokens import hash_token
from apps.magic.models import MagicLinkToken

pytestmark = pytest.mark.django_db


# ---------- TC-07: request issues link to known email ----------
def test_tc07_magic_link_request_for_known_email_sends_mail(client, make_user):
    user = make_user(email="known@example.com")
    response = client.post(reverse("magic:request"), {"email": user.email})
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to

    record = MagicLinkToken.objects.filter(email=user.email).first()
    assert record is not None
    assert record.user_id == user.id
    assert record.used_at is None


def test_request_for_unknown_email_is_silent(client):
    response = client.post(reverse("magic:request"), {"email": "ghost@example.com"})
    assert response.status_code == 200
    # No mail sent, but a token row is created so timing/DB-write counts match.
    assert len(mail.outbox) == 0
    assert MagicLinkToken.objects.filter(email="ghost@example.com").exists()


def _extract_token_from_mail(body: str) -> str:
    match = re.search(r"/magic/consume/(?P<t>[^/\s]+)/", body)
    assert match is not None, body
    return match.group("t")


# ---------- TC-08: consume within TTL logs in ----------
def test_tc08_magic_link_consumed_within_ttl_logs_in(client, make_user):
    user = make_user(email="cons@example.com")
    client.post(reverse("magic:request"), {"email": user.email})
    token = _extract_token_from_mail(mail.outbox[0].body)

    response = client.get(reverse("magic:consume", args=[token]))
    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")
    assert int(client.session.get("_auth_user_id", 0)) == user.id


# ---------- TC-09: reuse rejected ----------
def test_tc09_magic_link_reuse_rejected(client, make_user):
    user = make_user(email="reuse@example.com")
    client.post(reverse("magic:request"), {"email": user.email})
    token = _extract_token_from_mail(mail.outbox[0].body)

    first = client.get(reverse("magic:consume", args=[token]))
    assert first.status_code == 302

    # New client to drop the session, then reuse the same token.
    client.logout()
    second = client.get(reverse("magic:consume", args=[token]))
    assert second.status_code == 400
    assert "_auth_user_id" not in client.session


# ---------- TC-10: consume after TTL rejected ----------
def test_tc10_magic_link_consumed_after_ttl_rejected(client, make_user):
    user = make_user(email="late@example.com")
    client.post(reverse("magic:request"), {"email": user.email})
    token = _extract_token_from_mail(mail.outbox[0].body)

    # Backdate the token row so it's expired.
    record = MagicLinkToken.objects.get(token_hash=hash_token(token))
    record.expires_at = timezone.now() - timedelta(minutes=1)
    record.save(update_fields=["expires_at"])

    response = client.get(reverse("magic:consume", args=[token]))
    assert response.status_code == 400
    assert "_auth_user_id" not in client.session


def test_consume_random_garbage_returns_400(client):
    response = client.get(reverse("magic:consume", args=["totally-not-a-real-token"]))
    assert response.status_code == 400
