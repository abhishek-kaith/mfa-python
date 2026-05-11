"""Dashboard views."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import redirect, render

from apps.common.models import LoginAttempt


def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    return render(request, "dashboard/landing.html")


@login_required
def home(request):
    user = request.user
    has_totp = bool(getattr(getattr(user, "totp_device", None), "confirmed", False))
    backup_codes_remaining = user.backup_codes.filter(used_at__isnull=True).count()
    social_accounts = list(user.social_accounts.all())
    recent_attempts = list(LoginAttempt.objects.filter(user=user).order_by("-created_at")[:10])
    return render(
        request,
        "dashboard/home.html",
        {
            "has_totp": has_totp,
            "backup_codes_remaining": backup_codes_remaining,
            "social_accounts": social_accounts,
            "recent_attempts": recent_attempts,
        },
    )


@login_required
def security(request):
    user = request.user
    has_totp = bool(getattr(getattr(user, "totp_device", None), "confirmed", False))
    return render(
        request,
        "dashboard/security.html",
        {
            "has_totp": has_totp,
            "social_accounts": list(user.social_accounts.all()),
        },
    )


def healthz(request):
    """Liveness + readiness probe.

    Returns 200 if the process is up and the database accepts a trivial query.
    Used by Docker healthcheck and any external uptime monitor.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # noqa: BLE001 - any failure means not ready
        return HttpResponse("db unreachable", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")
