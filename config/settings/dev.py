"""Development settings."""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

INTERNAL_IPS = ["127.0.0.1"]

# Plain HTTP in dev: never set Secure cookies here.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Surface email in MailHog by default; allow override to console for tests.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
