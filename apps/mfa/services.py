"""TOTP and backup-code services."""

from __future__ import annotations

import hashlib
import io
import secrets
from urllib.parse import quote

import pyotp
import qrcode
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import User
from apps.common.crypto import decrypt, encrypt

from .models import BackupCode, TOTPDevice

BACKUP_CODE_COUNT = 8
BACKUP_CODE_BYTES = 5  # 5 bytes -> 10 hex chars


# ---------- TOTP secret ----------
def generate_secret() -> str:
    """Return a new base32 TOTP secret."""
    return pyotp.random_base32()


def encrypt_secret(secret: str) -> str:
    return encrypt(secret.encode("utf-8"))


def decrypt_secret(secret_encrypted: str) -> str:
    return decrypt(secret_encrypted).decode("utf-8")


def otpauth_uri(user: User, secret: str) -> str:
    """Build an otpauth:// URI compatible with Google Authenticator and friends."""
    issuer = settings.TOTP_ISSUER_NAME
    label = f"{issuer}:{user.email}"
    return (
        f"otpauth://totp/{quote(label)}?secret={secret}&issuer={quote(issuer)}&digits=6&period=30"
    )


def qr_png_bytes(otpauth: str) -> bytes:
    img = qrcode.make(otpauth)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


# ---------- TOTP device lifecycle ----------
def get_or_start_device(user: User) -> tuple[TOTPDevice, str]:
    """Return the user's device, creating an unconfirmed one with a fresh secret if absent.

    Returns ``(device, plain_secret)``. Once the device exists, repeat calls
    return the same secret so that the QR shown on GET and the code verified
    on POST line up.
    """
    device = TOTPDevice.objects.filter(user=user).first()
    if device is None:
        secret = generate_secret()
        device = TOTPDevice.objects.create(
            user=user,
            secret_encrypted=encrypt_secret(secret),
            confirmed=False,
        )
        return device, secret
    if not device.secret_encrypted:
        secret = generate_secret()
        device.secret_encrypted = encrypt_secret(secret)
        device.save(update_fields=["secret_encrypted"])
        return device, secret
    return device, decrypt_secret(device.secret_encrypted)


def confirm_device(device: TOTPDevice, code: str) -> bool:
    """Verify the provided code against the device's secret and confirm on success."""
    if device.confirmed:
        return verify_totp(device, code)
    secret = decrypt_secret(device.secret_encrypted)
    if not pyotp.TOTP(secret).verify(code, valid_window=1):
        return False
    device.confirmed = True
    device.last_used_at = timezone.now()
    device.save(update_fields=["confirmed", "last_used_at"])
    return True


def verify_totp(device: TOTPDevice, code: str) -> bool:
    """Verify a TOTP code against a confirmed device."""
    if not device.confirmed:
        return False
    secret = decrypt_secret(device.secret_encrypted)
    if not pyotp.TOTP(secret).verify(code, valid_window=1):
        return False
    device.last_used_at = timezone.now()
    device.save(update_fields=["last_used_at"])
    return True


def disable_device(user: User) -> None:
    """Remove the device and all backup codes."""
    TOTPDevice.objects.filter(user=user).delete()
    BackupCode.objects.filter(user=user).delete()


# ---------- backup codes ----------
def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def generate_backup_codes(user: User, count: int = BACKUP_CODE_COUNT) -> list[str]:
    """Replace any existing backup codes for the user and return the new plain codes."""
    BackupCode.objects.filter(user=user).delete()
    plain_codes: list[str] = []
    for _ in range(count):
        plain = secrets.token_hex(BACKUP_CODE_BYTES)
        plain_codes.append(plain)
        BackupCode.objects.create(user=user, code_hash=_hash_code(plain))
    return plain_codes


def consume_backup_code(user: User, code: str) -> bool:
    """Mark a backup code as used. Returns True if the code was valid and unused."""
    if not code:
        return False
    normalised = code.strip().lower().replace(" ", "").replace("-", "")
    candidate = (
        BackupCode.objects.filter(user=user, code_hash=_hash_code(normalised))
        .filter(used_at__isnull=True)
        .first()
    )
    if candidate is None:
        return False
    candidate.used_at = timezone.now()
    candidate.save(update_fields=["used_at"])
    return True
