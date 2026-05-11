"""Phase 1 tests covering registration, login, logout (TC-01..05, TC-20)."""

from __future__ import annotations

import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts.models import User
from apps.common.models import LoginAttempt

pytestmark = pytest.mark.django_db


# ---------- TC-01: register valid ----------
def test_tc01_register_valid_creates_user_and_sends_email(client):
    response = client.post(
        reverse("accounts:register"),
        {
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "Strong-Pass-2026!",
            "password_confirm": "Strong-Pass-2026!",
        },
    )
    assert response.status_code == 302  # redirect to login
    assert User.objects.filter(email="newuser@example.com").exists()
    assert len(mail.outbox) == 1
    assert "newuser@example.com" in mail.outbox[0].to
    body = mail.outbox[0].body
    assert "verify-email" in body or "/verify-email/" in body


# ---------- TC-02: register duplicate ----------
def test_tc02_register_duplicate_email_fails(client, make_user):
    existing = make_user(email="dup@example.com")
    response = client.post(
        reverse("accounts:register"),
        {
            "email": existing.email,
            "full_name": "Dup",
            "password": "Strong-Pass-2026!",
            "password_confirm": "Strong-Pass-2026!",
        },
    )
    assert response.status_code == 200
    form = response.context["form"]
    assert form.errors.get("email")
    assert User.objects.filter(email__iexact="dup@example.com").count() == 1


# ---------- TC-03: register weak password ----------
@pytest.mark.parametrize(
    "weak_password",
    [
        "short!1",  # too short (< 10 chars)
        "alllowercase",  # no digit, no symbol
        "NoSymbols2026",  # no symbol
        "NoDigits!@#$%",  # no digit
    ],
)
def test_tc03_register_weak_password_fails(client, weak_password):
    response = client.post(
        reverse("accounts:register"),
        {
            "email": "weak@example.com",
            "full_name": "Weak",
            "password": weak_password,
            "password_confirm": weak_password,
        },
    )
    assert response.status_code == 200
    form = response.context["form"]
    assert form.errors.get("password"), f"Expected password error for {weak_password!r}"
    assert not User.objects.filter(email="weak@example.com").exists()


# ---------- TC-04: login correct password ----------
def test_tc04_login_correct_password_creates_session(client, make_user, password):
    user = make_user(email="alice@example.com")
    response = client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": password},
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")
    # session has user id
    assert int(client.session.get("_auth_user_id", 0)) == user.id

    attempt = (
        LoginAttempt.objects.filter(email_attempted=user.email).order_by("-created_at").first()
    )
    assert attempt is not None
    assert attempt.outcome == LoginAttempt.OUTCOME_SUCCESS


# ---------- TC-05: login wrong password ----------
def test_tc05_login_wrong_password_logs_attempt(client, make_user):
    user = make_user(email="bob@example.com")
    response = client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": "obviously-wrong-1!"},
    )
    assert response.status_code == 401
    assert "_auth_user_id" not in client.session

    attempt = (
        LoginAttempt.objects.filter(email_attempted=user.email).order_by("-created_at").first()
    )
    assert attempt is not None
    assert attempt.outcome == LoginAttempt.OUTCOME_WRONG_PASSWORD
    assert attempt.user_id == user.id


def test_login_unknown_email_logs_unknown_user(client):
    response = client.post(
        reverse("accounts:login"),
        {"email": "nobody@example.com", "password": "whatever-1!"},
    )
    assert response.status_code == 401
    attempt = LoginAttempt.objects.filter(email_attempted="nobody@example.com").first()
    assert attempt is not None
    assert attempt.outcome == LoginAttempt.OUTCOME_UNKNOWN_USER
    assert attempt.user is None


# ---------- TC-20: logout ----------
def test_tc20_logout_destroys_session(client, make_user, password):
    user = make_user()
    client.post(reverse("accounts:login"), {"email": user.email, "password": password})
    assert "_auth_user_id" in client.session

    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302
    assert "_auth_user_id" not in client.session


def test_logout_get_is_rejected(client):
    response = client.get(reverse("accounts:logout"))
    assert response.status_code == 405


def test_email_verification_consumes_token(client, make_user):
    from apps.accounts.services import issue_email_verification_token

    user = make_user(is_email_verified=False)
    token = issue_email_verification_token(user)

    response = client.get(reverse("accounts:verify_email", args=[token]))
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.is_email_verified is True

    # Reuse rejected
    response = client.get(reverse("accounts:verify_email", args=[token]))
    assert response.status_code == 400


def test_password_reset_flow_changes_password(client, make_user):
    user = make_user(email="reset@example.com")

    response = client.post(
        reverse("accounts:password_reset"),
        {"email": user.email},
    )
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    body = mail.outbox[0].body
    # Pull the token out of the URL in the email body.
    import re

    m = re.search(r"/password-reset/confirm/(?P<t>[^/\s]+)/", body)
    assert m is not None
    token = m.group("t")

    # Open the form
    response = client.get(reverse("accounts:password_reset_confirm", args=[token]))
    assert response.status_code == 200

    # Submit new password
    response = client.post(
        reverse("accounts:password_reset_confirm", args=[token]),
        {"password": "Brand-New-Pass-2026!", "password_confirm": "Brand-New-Pass-2026!"},
    )
    assert response.status_code == 302

    user.refresh_from_db()
    assert user.check_password("Brand-New-Pass-2026!")


def test_password_reset_for_unknown_email_does_not_send(client):
    response = client.post(
        reverse("accounts:password_reset"),
        {"email": "ghost@example.com"},
    )
    assert response.status_code == 200
    # generic response, no email sent
    assert len(mail.outbox) == 0


# ---------- profile editing ----------
def test_profile_edit_requires_login(client):
    response = client.get(reverse("accounts:profile_edit"))
    assert response.status_code == 302
    assert "/login/" in response.url


def test_profile_edit_updates_full_name(client, make_user, password):
    user = make_user(full_name="Old Name")
    client.post(reverse("accounts:login"), {"email": user.email, "password": password})
    response = client.post(
        reverse("accounts:profile_edit"),
        {"full_name": "New Name"},
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.full_name == "New Name"


def test_password_change_requires_correct_current_password(client, make_user, password):
    user = make_user()
    client.post(reverse("accounts:login"), {"email": user.email, "password": password})
    response = client.post(
        reverse("accounts:password_change"),
        {
            "old_password": "obviously-wrong-1!",
            "new_password": "Brand-New-Pass-2026!",
            "new_password_confirm": "Brand-New-Pass-2026!",
        },
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password(password)


def test_password_change_updates_password_and_keeps_session(client, make_user, password):
    user = make_user()
    client.post(reverse("accounts:login"), {"email": user.email, "password": password})
    response = client.post(
        reverse("accounts:password_change"),
        {
            "old_password": password,
            "new_password": "Brand-New-Pass-2026!",
            "new_password_confirm": "Brand-New-Pass-2026!",
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password("Brand-New-Pass-2026!")
    # Session should survive a password change.
    assert int(client.session.get("_auth_user_id", 0)) == user.id


def test_resend_verification_sends_fresh_link(client, make_user, password):
    user = make_user(is_email_verified=False)
    client.post(reverse("accounts:login"), {"email": user.email, "password": password})
    response = client.post(reverse("accounts:resend_verification"))
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to


def test_resend_verification_noop_for_already_verified(client, make_user, password):
    user = make_user(is_email_verified=True)
    client.post(reverse("accounts:login"), {"email": user.email, "password": password})
    response = client.post(reverse("accounts:resend_verification"))
    assert response.status_code == 302
    assert len(mail.outbox) == 0
