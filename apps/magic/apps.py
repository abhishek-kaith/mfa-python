from django.apps import AppConfig


class MagicConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.magic"
    label = "magic"
    verbose_name = "Magic Link"
