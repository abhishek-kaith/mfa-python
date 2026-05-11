"""Seed three demo users for graders.

Usage::

    docker compose exec web python manage.py create_demo_users

The command is idempotent. It re-runs cleanly without raising on duplicates.
"""

from __future__ import annotations

import pyotp
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.mfa.services import (
    confirm_device,
    generate_backup_codes,
    get_or_start_device,
)
from apps.oauth.models import SocialAccount

DEFAULT_PASSWORD = "Demo-Pass-2026!"  # noqa: S105 - documented seed credential


class Command(BaseCommand):
    help = "Create three demo users (plain, TOTP-enabled, Google-linked) for graders."

    def handle(self, *args, **options):
        plain = self._get_or_make("alice@demo.local", "Alice Demo")
        with_totp = self._get_or_make("bob@demo.local", "Bob Demo")
        with_google = self._get_or_make("carol@demo.local", "Carol Demo")

        device, secret = get_or_start_device(with_totp)
        if not device.confirmed:
            confirm_device(device, pyotp.TOTP(secret).now())
            generate_backup_codes(with_totp)

        SocialAccount.objects.update_or_create(
            provider="google",
            provider_user_id="demo-google-user-id",
            defaults={"user": with_google, "email": with_google.email},
        )

        self.stdout.write(self.style.SUCCESS("Demo users ready:"))
        self.stdout.write(f"  - {plain.email}    (password: {DEFAULT_PASSWORD})")
        self.stdout.write(
            f"  - {with_totp.email}   (password: {DEFAULT_PASSWORD}, TOTP secret: {secret})"
        )
        self.stdout.write(
            f"  - {with_google.email} (password: {DEFAULT_PASSWORD}, also linked to Google)"
        )

    @staticmethod
    def _get_or_make(email: str, full_name: str) -> User:
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(
                email=email,
                password=DEFAULT_PASSWORD,
                full_name=full_name,
                is_active=True,
                is_email_verified=True,
            )
        else:
            user.set_password(DEFAULT_PASSWORD)
            user.save(update_fields=["password"])
        return user
