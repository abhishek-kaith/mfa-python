"""Magic-link forms."""

from __future__ import annotations

from django import forms


class MagicLinkRequestForm(forms.Form):
    email = forms.EmailField(label="Email")

    def clean_email(self) -> str:
        return self.cleaned_data["email"].strip().lower()
