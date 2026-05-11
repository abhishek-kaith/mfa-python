"""Custom authentication backend keyed on email."""

from __future__ import annotations

from django.contrib.auth.backends import ModelBackend

from .models import User


class EmailBackend(ModelBackend):
    """Authenticate against the email field, case-insensitive."""

    def authenticate(
        self, request, email: str | None = None, password: str | None = None, **kwargs
    ):
        if email is None or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            User().set_password(password)  # mitigate timing-based enumeration
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
