from django.contrib import admin

from .models import MagicLinkToken


@admin.register(MagicLinkToken)
class MagicLinkTokenAdmin(admin.ModelAdmin):
    list_display = ("created_at", "email", "user", "expires_at", "used_at")
    list_filter = ("used_at",)
    search_fields = ("email",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "user",
        "email",
        "token_hash",
        "expires_at",
        "used_at",
        "ip_created",
        "ip_used",
        "created_at",
    )
