"""Shared pytest fixtures.

Tests run with ``DJANGO_SETTINGS_MODULE = config.settings.dev`` (set via pytest-django).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _email_locmem(settings):
    """Use Django's locmem email backend so tests can introspect outbox."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture
def password() -> str:
    return "Strong-Pass-2026!"


@pytest.fixture
def make_user(db, password):
    """Factory that creates an active, verified user."""
    from apps.accounts.models import User

    counter = {"i": 0}

    def _make(email: str | None = None, **extras) -> User:
        if email is None:
            counter["i"] += 1
            email = f"user{counter['i']}@example.com"
        defaults = {
            "is_active": True,
            "is_email_verified": True,
            "full_name": "Test User",
        }
        defaults.update(extras)
        user = User.objects.create_user(email=email, password=password, **defaults)
        return user

    return _make


@pytest.fixture
def lockout_settings(settings):
    settings.LOGIN_MAX_ATTEMPTS = 5
    settings.LOGIN_LOCKOUT_WINDOW_MINUTES = 15
    settings.LOGIN_LOCKOUT_DURATION_MINUTES = 30
    return settings


@pytest.fixture(autouse=True)
def _fernet_key(settings):
    """Provide a stable Fernet key for tests that touch encrypted TOTP secrets."""
    settings.FERNET_KEY = "YOWcD3c-4eOyPesHhzN7rg-suFT6RP_QO8ivJs-bP84="


@pytest.fixture(autouse=True)
def _ensure_settings(settings):
    """Provide default values for env-driven settings in every test."""
    if not hasattr(settings, "MAGIC_LINK_TTL_MINUTES"):
        settings.MAGIC_LINK_TTL_MINUTES = 15
    if not hasattr(settings, "LOGIN_MAX_ATTEMPTS"):
        settings.LOGIN_MAX_ATTEMPTS = 5
    if not hasattr(settings, "LOGIN_LOCKOUT_WINDOW_MINUTES"):
        settings.LOGIN_LOCKOUT_WINDOW_MINUTES = 15
    if not hasattr(settings, "LOGIN_LOCKOUT_DURATION_MINUTES"):
        settings.LOGIN_LOCKOUT_DURATION_MINUTES = 30
