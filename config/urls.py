"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.accounts.urls")),
    path("magic/", include("apps.magic.urls")),
    path("oauth/", include("apps.oauth.urls")),
    path("mfa/", include("apps.mfa.urls")),
]
