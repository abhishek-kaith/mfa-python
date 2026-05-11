from django.apps import AppConfig


class MFAConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mfa"
    label = "mfa"
    verbose_name = "MFA"
