from django.contrib import admin

from .models import LoginAttempt


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("created_at", "email_attempted", "outcome", "ip_address", "user")
    list_filter = ("outcome",)
    search_fields = ("email_attempted", "ip_address")
    date_hierarchy = "created_at"
    readonly_fields = (
        "user",
        "email_attempted",
        "ip_address",
        "user_agent",
        "outcome",
        "created_at",
    )
