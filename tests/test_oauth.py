"""Phase 4 tests covering Google + GitHub OAuth (TC-11, TC-12)."""

from __future__ import annotations

import pytest
import responses
from django.urls import reverse

from apps.accounts.models import User
from apps.oauth.models import SocialAccount
from apps.oauth.providers import google as google_provider

pytestmark = pytest.mark.django_db


# ---------- TC-11: valid Google callback creates user ----------
@responses.activate
def test_tc11_google_callback_creates_user(client, settings):
    settings.GOOGLE_OAUTH_CLIENT_ID = "client-id"
    settings.GOOGLE_OAUTH_CLIENT_SECRET = "client-secret"

    # Step 1: start sets the state in session.
    start_response = client.get(reverse("oauth:start", args=["google"]))
    assert start_response.status_code == 302
    state = client.session["oauth_state"]
    assert state

    # Mock provider HTTP.
    responses.add(
        responses.POST,
        google_provider.TOKEN_URL,
        json={"access_token": "abc-token", "token_type": "Bearer"},
        status=200,
    )
    responses.add(
        responses.GET,
        google_provider.USERINFO_URL,
        json={
            "sub": "1234567890",
            "email": "alice.google@example.com",
            "name": "Alice Google",
        },
        status=200,
    )

    callback_response = client.get(
        reverse("oauth:callback", args=["google"]),
        {"code": "auth-code", "state": state},
    )
    assert callback_response.status_code == 302
    assert callback_response.url == reverse("dashboard:home")

    user = User.objects.get(email="alice.google@example.com")
    assert user.is_email_verified is True
    assert SocialAccount.objects.filter(
        provider="google", provider_user_id="1234567890", user=user
    ).exists()
    assert int(client.session.get("_auth_user_id", 0)) == user.id


# ---------- TC-12: state mismatch is rejected ----------
def test_tc12_google_callback_state_mismatch_rejected(client, settings):
    settings.GOOGLE_OAUTH_CLIENT_ID = "client-id"
    settings.GOOGLE_OAUTH_CLIENT_SECRET = "client-secret"

    start_response = client.get(reverse("oauth:start", args=["google"]))
    assert start_response.status_code == 302

    response = client.get(
        reverse("oauth:callback", args=["google"]),
        {"code": "auth-code", "state": "totally-different-state"},
    )
    assert response.status_code == 400
    assert not User.objects.exists()
    assert "_auth_user_id" not in client.session


def test_callback_without_session_state_rejected(client, settings):
    response = client.get(
        reverse("oauth:callback", args=["google"]),
        {"code": "auth-code", "state": "anything"},
    )
    assert response.status_code == 400


@responses.activate
def test_oauth_links_existing_user_by_email(client, settings, make_user):
    """A user with a matching local email should be linked, not duplicated."""
    settings.GOOGLE_OAUTH_CLIENT_ID = "client-id"
    settings.GOOGLE_OAUTH_CLIENT_SECRET = "client-secret"

    existing = make_user(email="bob@example.com")

    client.get(reverse("oauth:start", args=["google"]))
    state = client.session["oauth_state"]

    responses.add(
        responses.POST,
        google_provider.TOKEN_URL,
        json={"access_token": "tok"},
        status=200,
    )
    responses.add(
        responses.GET,
        google_provider.USERINFO_URL,
        json={"sub": "999", "email": "bob@example.com", "name": "Bob"},
        status=200,
    )

    client.get(reverse("oauth:callback", args=["google"]), {"code": "c", "state": state})

    assert User.objects.filter(email="bob@example.com").count() == 1
    link = SocialAccount.objects.get(provider="google", provider_user_id="999")
    assert link.user_id == existing.id


def test_oauth_unknown_provider_returns_404(client):
    response = client.get(reverse("oauth:start", args=["facebook"]))
    assert response.status_code == 404
