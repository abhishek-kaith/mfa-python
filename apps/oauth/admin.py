from django.contrib import admin

from .models import SocialAccount


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("created_at", "provider", "email", "user", "provider_user_id")
    list_filter = ("provider",)
    search_fields = ("email", "provider_user_id")
    readonly_fields = ("created_at",)
