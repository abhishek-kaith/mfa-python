"""Phase 2 and Phase 6 security tests."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.common.models import LoginAttempt

pytestmark = pytest.mark.django_db


# ---------- TC-06: lockout after threshold ----------
def test_tc06_account_locks_after_threshold(client, make_user, lockout_settings):
    user = make_user(email="locked@example.com")
    url = reverse("accounts:login")

    # Five failures within the window.
    for _ in range(int(lockout_settings.LOGIN_MAX_ATTEMPTS)):
        response = client.post(url, {"email": user.email, "password": "wrong-pass-1!"})
        assert response.status_code == 401

    # Sixth attempt is locked even though the password might be correct.
    response = client.post(url, {"email": user.email, "password": "wrong-pass-1!"})
    assert response.status_code == 429

    locked_attempts = LoginAttempt.objects.filter(
        email_attempted=user.email,
        outcome=LoginAttempt.OUTCOME_LOCKED,
    )
    assert locked_attempts.exists()


# ---------- TC-18: form POST without CSRF -> 403 ----------
def test_tc18_form_post_without_csrf_token_is_forbidden():
    """A client that does not bypass CSRF protection must receive a 403."""
    enforcing_client = Client(enforce_csrf_checks=True)
    response = enforcing_client.post(
        reverse("accounts:login"),
        {"email": "anyone@example.com", "password": "anything-1!"},
    )
    assert response.status_code == 403


# ---------- TC-19: protected page without login -> redirect ----------
def test_tc19_protected_page_without_login_redirects(client, settings):
    response = client.get(reverse("dashboard:home"))
    assert response.status_code == 302
    # Redirect to LOGIN_URL with ?next=...
    assert "/login/" in response.url
    assert "next=" in response.url


def test_mfa_setup_requires_login(client):
    response = client.get(reverse("mfa:setup"))
    assert response.status_code == 302
    assert "/login/" in response.url


def test_prod_settings_have_security_headers():
    """Sanity check that production settings define the headers from spec section 9."""
    import importlib

    prod = importlib.import_module("config.settings.prod")
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
    assert prod.SECURE_HSTS_SECONDS >= 31_536_000
    assert prod.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert prod.X_FRAME_OPTIONS == "DENY"
    assert prod.SECURE_REFERRER_POLICY == "same-origin"
    assert prod.SECURE_CONTENT_TYPE_NOSNIFF is True
