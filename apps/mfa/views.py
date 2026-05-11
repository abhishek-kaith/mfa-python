"""MFA views: setup, challenge, disable, backup-code regeneration."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.common import audit
from apps.common.lockout import is_locked
from apps.common.models import LoginAttempt

from .forms import PasswordConfirmForm, TOTPCodeForm
from .services import (
    confirm_device,
    consume_backup_code,
    disable_device,
    generate_backup_codes,
    get_or_start_device,
    otpauth_uri,
    qr_png_bytes,
    verify_totp,
)

logger = logging.getLogger(__name__)


# ---------- enrolment ----------
@login_required
@require_http_methods(["GET", "POST"])
def setup(request: HttpRequest) -> HttpResponse:
    user = request.user
    device, secret = get_or_start_device(user)

    if request.method == "POST":
        form = TOTPCodeForm(request.POST)
        if form.is_valid() and confirm_device(device, form.cleaned_data["code"]):
            backup_codes = generate_backup_codes(user)
            messages.success(request, "Two-factor authentication is now enabled.")
            return render(
                request,
                "mfa/setup_done.html",
                {"backup_codes": backup_codes},
            )
        if not form.errors:
            form.add_error("code", "That code is not valid. Kindly try again.")
    else:
        form = TOTPCodeForm()

    uri = otpauth_uri(user, secret)
    return render(
        request,
        "mfa/setup.html",
        {"form": form, "secret": secret, "otpauth": uri},
    )


@login_required
@require_http_methods(["GET"])
def qr(request: HttpRequest) -> HttpResponse:
    """Render the otpauth URI as an inline PNG."""
    user = request.user
    device, secret = get_or_start_device(user)
    _ = device  # ensure row exists
    png = qr_png_bytes(otpauth_uri(user, secret))
    response = HttpResponse(png, content_type="image/png")
    response["Cache-Control"] = "no-store"
    return response


# ---------- mid-login challenge ----------
@require_http_methods(["GET", "POST"])
def challenge(request: HttpRequest) -> HttpResponse:
    user_id = request.session.get("pre_auth_user_id")
    if not user_id:
        return redirect("accounts:login")
    user = User.objects.filter(pk=user_id).first()
    if user is None or not user.is_active:
        request.session.pop("pre_auth_user_id", None)
        return redirect("accounts:login")

    if is_locked(user.email):
        audit.record_attempt(
            request=request, email=user.email, outcome=LoginAttempt.OUTCOME_LOCKED, user=user
        )
        return render(
            request,
            "mfa/challenge.html",
            {
                "form": TOTPCodeForm(),
                "error": "Too many failed attempts. Kindly try again later.",
            },
            status=429,
        )

    form = TOTPCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["code"]
        device = getattr(user, "totp_device", None)

        if device is not None and device.confirmed and verify_totp(device, code):
            return _complete_login(request, user)

        if consume_backup_code(user, code):
            return _complete_login(request, user)

        audit.record_attempt(
            request=request,
            email=user.email,
            outcome=LoginAttempt.OUTCOME_MFA_FAILED,
            user=user,
        )
        form.add_error("code", "That code is not valid.")

    return render(request, "mfa/challenge.html", {"form": form})


def _complete_login(request: HttpRequest, user: User) -> HttpResponse:
    request.session.pop("pre_auth_user_id", None)
    request.session.pop("pre_auth_method", None)
    login(request, user, backend="apps.accounts.backends.EmailBackend")
    audit.record_attempt(
        request=request, email=user.email, outcome=LoginAttempt.OUTCOME_SUCCESS, user=user
    )
    return redirect("dashboard:home")


# ---------- disable / regenerate ----------
@login_required
@require_http_methods(["GET", "POST"])
def disable(request: HttpRequest) -> HttpResponse:
    user = request.user
    form = PasswordConfirmForm(request.POST or None, user=user)
    if request.method == "POST" and form.is_valid():
        disable_device(user)
        messages.success(request, "Two-factor authentication has been disabled.")
        return redirect("dashboard:home")
    return render(request, "mfa/disable.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def regenerate_backup_codes(request: HttpRequest) -> HttpResponse:
    user = request.user
    form = PasswordConfirmForm(request.POST or None, user=user)
    if request.method == "POST" and form.is_valid():
        codes = generate_backup_codes(user)
        return render(request, "mfa/setup_done.html", {"backup_codes": codes, "regenerated": True})
    return render(request, "mfa/regenerate.html", {"form": form})
