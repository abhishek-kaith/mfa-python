"""Print a fresh DJANGO_SECRET_KEY and FERNET_KEY.

Run on first setup, then paste the values into your .env file.
"""

from __future__ import annotations

import secrets
import string

from cryptography.fernet import Fernet


def generate_django_secret_key(length: int = 64) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> None:
    print("# Paste these into your .env file:")
    print()
    print(f"DJANGO_SECRET_KEY={generate_django_secret_key()}")
    print(f"FERNET_KEY={Fernet.generate_key().decode()}")


if __name__ == "__main__":
    main()
