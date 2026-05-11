"""Magic-link URL routes."""

from django.urls import path

from . import views

app_name = "magic"

urlpatterns = [
    path("request/", views.request_link, name="request"),
    path("consume/<str:token>/", views.consume_link, name="consume"),
]
