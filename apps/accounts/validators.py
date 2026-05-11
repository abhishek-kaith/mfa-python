"""Custom password validators for the accounts app."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class SymbolDigitValidator:
    """Require at least one digit and one symbol in the password.

    Combined with Django's built-in length and similarity checks, this
    fulfils the policy in section 8.1 of the project specification.
    """

    SYMBOL_RE = re.compile(r"[^A-Za-z0-9]")
    DIGIT_RE = re.compile(r"[0-9]")

    def validate(self, password: str, user=None) -> None:
        if not self.DIGIT_RE.search(password):
            raise ValidationError(
                _("Password must contain at least one digit."),
                code="password_no_digit",
            )
        if not self.SYMBOL_RE.search(password):
            raise ValidationError(
                _("Password must contain at least one symbol."),
                code="password_no_symbol",
            )

    def get_help_text(self) -> str:
        return _("Your password must contain at least one digit and one symbol.")
