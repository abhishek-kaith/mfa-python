"""Dashboard URL routes."""

from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("dashboard/", views.home, name="home"),
    path("dashboard/security/", views.security, name="security"),
    path("healthz/", views.healthz, name="healthz"),
]
