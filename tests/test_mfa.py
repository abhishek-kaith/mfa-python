"""Phase 5 tests covering TOTP and backup codes (TC-13..TC-17)."""

from __future__ import annotations

import pyotp
import pytest
from django.urls import reverse

from apps.common.crypto import decrypt
from apps.common.models import LoginAttempt
from apps.mfa.models import BackupCode, TOTPDevice
from apps.mfa.services import (
    confirm_device,
    generate_backup_codes,
    get_or_start_device,
)

pytestmark = pytest.mark.django_db


def _login(client, user, password):
    response = client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": password},
    )
    return response


def _enable_totp_for(user) -> str:
    """Helper that enables TOTP and returns the plaintext secret."""
    device, secret = get_or_start_device(user)
    code = pyotp.TOTP(secret).now()
    assert confirm_device(device, code)
    return secret


# ---------- TC-13: enable + confirm ----------
def test_tc13_enable_totp_and_confirm(client, make_user, password):
    user = make_user()
    _login(client, user, password)
    assert "_auth_user_id" in client.session

    setup_url = reverse("mfa:setup")
    get_response = client.get(setup_url)
    assert get_response.status_code == 200
    secret = get_response.context["secret"]
    assert secret

    code = pyotp.TOTP(secret).now()
    response = client.post(setup_url, {"code": code})
    assert response.status_code == 200

    device = TOTPDevice.objects.get(user=user)
    assert device.confirmed is True
    # Secret is encrypted at rest; decrypt round-trips to the same value.
    assert decrypt(device.secret_encrypted).decode() == secret
    # 8 backup codes were generated.
    assert BackupCode.objects.filter(user=user).count() == 8


# ---------- TC-14: login + valid TOTP -> full session ----------
def test_tc14_login_then_valid_totp_creates_full_session(client, make_user, password):
    user = make_user()
    secret = _enable_totp_for(user)
    client.logout()

    response = _login(client, user, password)
    assert response.status_code == 302
    assert response.url == reverse("mfa:challenge")
    # Pre-auth state, not full login yet.
    assert "_auth_user_id" not in client.session
    assert client.session.get("pre_auth_user_id") == user.id

    code = pyotp.TOTP(secret).now()
    response = client.post(reverse("mfa:challenge"), {"code": code})
    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")
    assert int(client.session.get("_auth_user_id", 0)) == user.id
    assert "pre_auth_user_id" not in client.session


# ---------- TC-15: wrong TOTP -> rejected, audited ----------
def test_tc15_login_then_wrong_totp_rejected(client, make_user, password):
    user = make_user()
    _enable_totp_for(user)
    client.logout()

    _login(client, user, password)
    response = client.post(reverse("mfa:challenge"), {"code": "000000"})
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session

    failed = LoginAttempt.objects.filter(
        email_attempted=user.email,
        outcome=LoginAttempt.OUTCOME_MFA_FAILED,
    )
    assert failed.exists()


# ---------- TC-16: backup code accepted ----------
def test_tc16_backup_code_accepted_and_marked_used(client, make_user, password):
    user = make_user()
    _enable_totp_for(user)
    backup_codes = generate_backup_codes(user)
    client.logout()

    _login(client, user, password)
    one_code = backup_codes[0]
    response = client.post(reverse("mfa:challenge"), {"code": one_code})
    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")
    assert int(client.session.get("_auth_user_id", 0)) == user.id

    used = BackupCode.objects.filter(user=user, used_at__isnull=False)
    assert used.count() == 1


# ---------- TC-17: backup code reuse rejected ----------
def test_tc17_reused_backup_code_rejected(client, make_user, password):
    user = make_user()
    _enable_totp_for(user)
    backup_codes = generate_backup_codes(user)
    client.logout()

    # First use succeeds.
    _login(client, user, password)
    response = client.post(reverse("mfa:challenge"), {"code": backup_codes[0]})
    assert response.status_code == 302
    client.logout()

    # Second use of the same code fails.
    _login(client, user, password)
    response = client.post(reverse("mfa:challenge"), {"code": backup_codes[0]})
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


def test_disable_requires_password(client, make_user, password):
    user = make_user()
    _enable_totp_for(user)
    _login(client, user, password)
    client.post(reverse("mfa:challenge"), {"code": pyotp.TOTP(_get_secret(user)).now()})

    # Wrong password leaves the device intact.
    response = client.post(reverse("mfa:disable"), {"password": "obviously-wrong-1!"})
    assert response.status_code == 200
    assert TOTPDevice.objects.filter(user=user).exists()

    # Correct password destroys the device + backup codes.
    response = client.post(reverse("mfa:disable"), {"password": password})
    assert response.status_code == 302
    assert not TOTPDevice.objects.filter(user=user).exists()
    assert not BackupCode.objects.filter(user=user).exists()


def _get_secret(user) -> str:
    device = TOTPDevice.objects.get(user=user)
    return decrypt(device.secret_encrypted).decode()


def test_qr_endpoint_returns_png(client, make_user, password):
    user = make_user()
    _login(client, user, password)
    response = client.get(reverse("mfa:qr"))
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"
