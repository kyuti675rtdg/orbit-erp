from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.static import serve as static_serve
from core.views import LoginView
from core.views_app import flutter_app

urlpatterns = [
    path("admin/", admin.site.urls),
    path("app/", flutter_app, name="flutter_app"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(template_name="auth/password_reset.html"),
        name="password_reset",
    ),
    path("", include("core.urls")),
    # serve uploaded media (avatars, chat attachments) in all environments
    path("media/<path:path>", static_serve, {"document_root": settings.MEDIA_ROOT}),
]
