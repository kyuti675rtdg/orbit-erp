from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from core.views import LoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(template_name="auth/password_reset.html"),
        name="password_reset",
    ),
    path("", include("core.urls")),
]
