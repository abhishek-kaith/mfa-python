"""OAuth URL routes."""

from django.urls import path

from . import views

app_name = "oauth"

urlpatterns = [
    path("<str:provider>/start/", views.start, name="start"),
    path("<str:provider>/callback/", views.callback, name="callback"),
]
