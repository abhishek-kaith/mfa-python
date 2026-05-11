"""Account URL routes."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("verify-email/resend/", views.resend_verification, name="resend_verification"),
    path("verify-email/<str:token>/", views.verify_email, name="verify_email"),
    path("password-reset/", views.password_reset_request, name="password_reset"),
    path(
        "password-reset/confirm/<str:token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    path("profile/", views.profile_edit, name="profile_edit"),
    path("password/change/", views.password_change, name="password_change"),
]
