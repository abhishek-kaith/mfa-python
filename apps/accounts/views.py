"""Account views: register, login, logout, email verification, password reset."""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.common import audit
from apps.common.emails import send_template_email
from apps.common.lockout import is_locked
from apps.common.models import LoginAttempt

from .forms import (
    ChangePasswordForm,
    LoginForm,
    PasswordResetRequestForm,
    ProfileForm,
    RegistrationForm,
    SetPasswordForm,
)
from .models import User
from .services import (
    consume_email_verification_token,
    consume_password_reset_token,
    issue_email_verification_token,
    issue_password_reset_token,
)

logger = logging.getLogger(__name__)


def _build_absolute(request: HttpRequest, name: str, *args) -> str:
    return request.build_absolute_uri(reverse(name, args=args))


# ---------- registration ----------
@require_http_methods(["GET", "POST"])
def register(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        token = issue_email_verification_token(user)
        verify_url = _build_absolute(request, "accounts:verify_email", token)
        send_template_email(
            to=user.email,
            subject="Confirm your email",
            template="emails/email_verification.txt",
            context={"user": user, "verify_url": verify_url},
        )
        messages.success(
            request,
            "Account created. Kindly check your inbox for the verification link.",
        )
        return redirect("accounts:login")
    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET"])
def verify_email(request: HttpRequest, token: str) -> HttpResponse:
    user = consume_email_verification_token(token)
    if user is None:
        return render(request, "accounts/email_verification_invalid.html", status=400)
    return render(request, "accounts/email_verification_done.html", {"user": user})


# ---------- login / logout ----------
@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]

        if is_locked(email):
            audit.record_attempt(request=request, email=email, outcome=LoginAttempt.OUTCOME_LOCKED)
            form.add_error(None, "Too many failed attempts. Please try again later.")
            return render(request, "accounts/login.html", {"form": form}, status=429)

        user = authenticate(request, email=email, password=password)
        if user is None:
            existing = User.objects.filter(email__iexact=email).first()
            outcome = (
                LoginAttempt.OUTCOME_WRONG_PASSWORD
                if existing
                else LoginAttempt.OUTCOME_UNKNOWN_USER
            )
            audit.record_attempt(request=request, email=email, outcome=outcome, user=existing)
            form.add_error(None, "Invalid email or password.")
            return render(request, "accounts/login.html", {"form": form}, status=401)

        if not user.is_active:
            audit.record_attempt(
                request=request, email=email, outcome=LoginAttempt.OUTCOME_INACTIVE, user=user
            )
            form.add_error(None, "This account is inactive.")
            return render(request, "accounts/login.html", {"form": form}, status=403)

        # Branch to TOTP challenge if the user has a confirmed device.
        if _user_has_totp(user):
            request.session["pre_auth_user_id"] = user.id
            request.session["pre_auth_method"] = "password"
            return redirect("mfa:challenge")

        login(request, user)
        audit.record_attempt(
            request=request, email=email, outcome=LoginAttempt.OUTCOME_SUCCESS, user=user
        )
        return redirect("dashboard:home")

    return render(request, "accounts/login.html", {"form": form})


def _user_has_totp(user: User) -> bool:
    """Return True if the user has a confirmed TOTP device.

    Imported lazily so the accounts app does not require the mfa app at import time.
    """
    try:
        device = user.totp_device  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - the related accessor raises DoesNotExist
        return False
    return bool(getattr(device, "confirmed", False))


@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


# ---------- password reset ----------
@require_http_methods(["GET", "POST"])
def password_reset_request(request: HttpRequest) -> HttpResponse:
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if user is not None and user.is_active:
            token = issue_password_reset_token(user)
            reset_url = _build_absolute(request, "accounts:password_reset_confirm", token)
            send_template_email(
                to=user.email,
                subject="Reset your password",
                template="emails/password_reset.txt",
                context={"user": user, "reset_url": reset_url},
            )
        # Generic response either way to avoid enumeration.
        return render(request, "accounts/password_reset_done.html")
    return render(request, "accounts/password_reset_request.html", {"form": form})


@require_http_methods(["GET", "POST"])
def password_reset_confirm(request: HttpRequest, token: str) -> HttpResponse:
    user = consume_password_reset_token(token) if request.method == "GET" else None

    if request.method == "GET":
        if user is None:
            return render(request, "accounts/password_reset_invalid.html", status=400)
        request.session["pwreset_user_id"] = user.id
        form = SetPasswordForm(user=user)
        return render(request, "accounts/password_reset_confirm.html", {"form": form})

    # POST: read the user id stashed at GET time.
    user_id = request.session.get("pwreset_user_id")
    user = User.objects.filter(pk=user_id).first() if user_id else None
    if user is None:
        return render(request, "accounts/password_reset_invalid.html", status=400)
    form = SetPasswordForm(request.POST, user=user)
    if form.is_valid():
        user.set_password(form.cleaned_data["password"])
        user.save(update_fields=["password"])
        request.session.pop("pwreset_user_id", None)
        messages.success(request, "Your password has been updated. Kindly log in.")
        return redirect("accounts:login")
    return render(request, "accounts/password_reset_confirm.html", {"form": form})


# ---------- profile editing (logged-in) ----------
@login_required
@require_http_methods(["GET", "POST"])
def profile_edit(request: HttpRequest) -> HttpResponse:
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile_edit")
    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def password_change(request: HttpRequest) -> HttpResponse:
    form = ChangePasswordForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        # Keep the user logged in after a password change.
        update_session_auth_hash(request, request.user)
        messages.success(request, "Your password has been updated.")
        return redirect("dashboard:security")
    return render(request, "accounts/password_change.html", {"form": form})


@login_required
@require_http_methods(["POST"])
def resend_verification(request: HttpRequest) -> HttpResponse:
    user = request.user
    if user.is_email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect("dashboard:home")
    token = issue_email_verification_token(user)
    verify_url = _build_absolute(request, "accounts:verify_email", token)
    send_template_email(
        to=user.email,
        subject="Confirm your email",
        template="emails/email_verification.txt",
        context={"user": user, "verify_url": verify_url},
    )
    messages.success(request, "We have sent a fresh verification link to your inbox.")
    return redirect("dashboard:home")


# Settings sanity: silence unused-import warnings on settings here for clarity.
_ = settings.LOGIN_MAX_ATTEMPTS
_ = timezone.now
