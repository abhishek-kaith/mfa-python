"""OAuth start and callback views."""

from __future__ import annotations

import logging
import secrets

from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.common import audit
from apps.common.models import LoginAttempt

from .providers import get_provider
from .services import link_or_create

logger = logging.getLogger(__name__)


SESSION_STATE_KEY = "oauth_state"
SESSION_PROVIDER_KEY = "oauth_provider"


@require_http_methods(["GET"])
def start(request: HttpRequest, provider: str) -> HttpResponse:
    try:
        oauth = get_provider(provider)
    except KeyError:
        return render(request, "oauth/error.html", {"reason": "unknown provider"}, status=404)

    state = secrets.token_urlsafe(32)
    request.session[SESSION_STATE_KEY] = state
    request.session[SESSION_PROVIDER_KEY] = provider
    return redirect(oauth.authorize_url(state))


@require_http_methods(["GET"])
def callback(request: HttpRequest, provider: str) -> HttpResponse:
    expected_state = request.session.pop(SESSION_STATE_KEY, None)
    expected_provider = request.session.pop(SESSION_PROVIDER_KEY, None)

    received_state = request.GET.get("state", "")
    code = request.GET.get("code", "")
    error = request.GET.get("error")

    if error:
        return render(
            request,
            "oauth/error.html",
            {"reason": f"Provider returned an error: {error}"},
            status=400,
        )

    if not expected_state or not received_state:
        return render(request, "oauth/error.html", {"reason": "missing state"}, status=400)
    if not secrets.compare_digest(expected_state, received_state):
        return render(request, "oauth/error.html", {"reason": "state mismatch"}, status=400)
    if expected_provider != provider:
        return render(request, "oauth/error.html", {"reason": "provider mismatch"}, status=400)
    if not code:
        return render(request, "oauth/error.html", {"reason": "missing code"}, status=400)

    try:
        oauth = get_provider(provider)
    except KeyError:
        return render(request, "oauth/error.html", {"reason": "unknown provider"}, status=404)

    try:
        access_token = oauth.exchange_code(code, oauth.redirect_uri)
        profile = oauth.fetch_user(access_token)
    except Exception as exc:  # noqa: BLE001 - we fail closed on any provider error
        logger.warning("OAuth exchange failed for provider=%s: %s", provider, exc)
        return render(
            request,
            "oauth/error.html",
            {"reason": "could not complete sign-in with provider"},
            status=502,
        )
    finally:
        # Token is discarded as soon as we fall out of this scope.
        access_token = None  # noqa: F841

    if not profile.email:
        return render(
            request,
            "oauth/error.html",
            {"reason": "provider did not supply a verified email"},
            status=400,
        )

    result = link_or_create(provider, profile)
    user = result.user

    # If TOTP is enabled on this account, route through MFA challenge.
    if _user_has_totp(user):
        request.session["pre_auth_user_id"] = user.id
        request.session["pre_auth_method"] = f"oauth_{provider}"
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
    except Exception:  # noqa: BLE001
        return False
    return bool(getattr(device, "confirmed", False))
