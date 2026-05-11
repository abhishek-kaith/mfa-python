from django.contrib import admin

from .models import BackupCode, TOTPDevice


@admin.register(TOTPDevice)
class TOTPDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "confirmed", "created_at", "last_used_at")
    list_filter = ("confirmed",)
    search_fields = ("user__email",)
    readonly_fields = ("secret_encrypted", "created_at", "last_used_at")


@admin.register(BackupCode)
class BackupCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "used_at")
    list_filter = ("used_at",)
    search_fields = ("user__email",)
    readonly_fields = ("code_hash", "created_at", "used_at")
