"""Magic-link views."""

from __future__ import annotations

from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.common import audit
from apps.common.lockout import is_locked
from apps.common.models import LoginAttempt

from .forms import MagicLinkRequestForm
from .services import consume, issue_link


@require_http_methods(["GET", "POST"])
def request_link(request: HttpRequest) -> HttpResponse:
    form = MagicLinkRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        # Lockout still applies to magic link requests for a given email,
        # to slow down enumeration attempts that target one address.
        if not is_locked(email):
            issue_link(email=email, ip=audit.client_ip(request), request=request)
        return render(request, "magic/request_done.html", {"email": email})
    return render(request, "magic/request.html", {"form": form})


@require_http_methods(["GET"])
def consume_link(request: HttpRequest, token: str) -> HttpResponse:
    user = consume(token=token, ip=audit.client_ip(request))
    if user is None:
        audit.record_attempt(
            request=request,
            email="",
            outcome=LoginAttempt.OUTCOME_WRONG_PASSWORD,
        )
        return render(request, "magic/invalid.html", status=400)

    # Mid-login MFA branch. If the user has a confirmed TOTP device,
    # stash the user id and route to the challenge instead of fully logging in.
    if _user_has_totp(user):
        request.session["pre_auth_user_id"] = user.id
        request.session["pre_auth_method"] = "magic"
        return redirect("mfa:challenge")

    login(request, user, backend="apps.accounts.backends.EmailBackend")
    audit.record_attempt(
        request=request,
        email=user.email,
        outcome=LoginAttempt.OUTCOME_SUCCESS,
        user=user,
    )
    return redirect("dashboard:home")


def _user_has_totp(user) -> bool:
    try:
        device = user.totp_device
    except Exception:  # noqa: BLE001 - related accessor raises DoesNotExist
        return False
    return bool(getattr(device, "confirmed", False))
