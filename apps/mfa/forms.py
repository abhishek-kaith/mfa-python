"""MFA forms."""

from __future__ import annotations

from django import forms


class TOTPCodeForm(forms.Form):
    code = forms.CharField(
        label="Authenticator code",
        max_length=12,
        min_length=6,
    )

    def clean_code(self) -> str:
        return self.cleaned_data["code"].strip().replace(" ", "").replace("-", "")


class PasswordConfirmForm(forms.Form):
    """Used before destructive MFA operations (disable, regenerate)."""

    password = forms.CharField(
        label="Confirm your password",
        widget=forms.PasswordInput,
        strip=False,
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self) -> str:
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password.")
        return password
