"""MFA URL routes."""

from django.urls import path

from . import views

app_name = "mfa"

urlpatterns = [
    path("setup/", views.setup, name="setup"),
    path("setup/qr/", views.qr, name="qr"),
    path("challenge/", views.challenge, name="challenge"),
    path("disable/", views.disable, name="disable"),
    path("backup-codes/regenerate/", views.regenerate_backup_codes, name="regenerate_codes"),
]
