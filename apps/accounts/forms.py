"""Forms for the accounts app."""

from __future__ import annotations

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class RegistrationForm(forms.Form):
    email = forms.EmailField(label="Email")
    full_name = forms.CharField(label="Full name", max_length=150, required=False)
    password = forms.CharField(label="Password", widget=forms.PasswordInput, strip=False)
    password_confirm = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
        strip=False,
    )

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self) -> dict:
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("password_confirm")
        if password and confirm and password != confirm:
            self.add_error("password_confirm", "Passwords do not match.")
        if password:
            tentative = User(email=cleaned.get("email", ""), full_name=cleaned.get("full_name", ""))
            try:
                validate_password(password, tentative)
            except ValidationError as exc:
                self.add_error("password", exc)
        return cleaned

    def save(self) -> User:
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            full_name=self.cleaned_data.get("full_name", ""),
        )
        user.is_active = True
        user.save(update_fields=["is_active"])
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput, strip=False)

    def clean_email(self) -> str:
        return self.cleaned_data["email"].strip().lower()


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label="Email")

    def clean_email(self) -> str:
        return self.cleaned_data["email"].strip().lower()


class SetPasswordForm(forms.Form):
    """New-password form used both at first verification and at reset confirm."""

    password = forms.CharField(label="New password", widget=forms.PasswordInput, strip=False)
    password_confirm = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
        strip=False,
    )

    def __init__(self, *args, user: User | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self) -> dict:
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("password_confirm")
        if password and confirm and password != confirm:
            self.add_error("password_confirm", "Passwords do not match.")
        if password:
            try:
                validate_password(password, self.user)
            except ValidationError as exc:
                self.add_error("password", exc)
        return cleaned


class ProfileForm(forms.ModelForm):
    """Edit the parts of the profile a user is allowed to change themselves."""

    class Meta:
        model = User
        fields = ["full_name"]
        labels = {"full_name": "Full name"}


class ChangePasswordForm(forms.Form):
    """Change password while logged in.

    Requires the current password before accepting the new one, so a stolen
    session cannot quietly rotate credentials.
    """

    old_password = forms.CharField(
        label="Current password", widget=forms.PasswordInput, strip=False
    )
    new_password = forms.CharField(label="New password", widget=forms.PasswordInput, strip=False)
    new_password_confirm = forms.CharField(
        label="Confirm new password", widget=forms.PasswordInput, strip=False
    )

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_old_password(self) -> str:
        old = self.cleaned_data["old_password"]
        if not self.user.check_password(old):
            raise ValidationError("Your current password is incorrect.")
        return old

    def clean(self) -> dict:
        cleaned = super().clean()
        new = cleaned.get("new_password")
        confirm = cleaned.get("new_password_confirm")
        if new and confirm and new != confirm:
            self.add_error("new_password_confirm", "Passwords do not match.")
        if new:
            try:
                validate_password(new, self.user)
            except ValidationError as exc:
                self.add_error("new_password", exc)
        return cleaned

    def save(self) -> User:
        self.user.set_password(self.cleaned_data["new_password"])
        self.user.save(update_fields=["password"])
        return self.user
