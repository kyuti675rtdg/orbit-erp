from django.urls import path

from core import crud
from shared import views

from .entities import ENTITIES
from .sidebar import get_modules  # noqa: F401  (used by core.modules)


def _sidebar(request):
    from core.modules import build_sidebar
    return build_sidebar(request)


urlpatterns = [
    path("notifications/feed/", views.notifications_feed, name="shared_notifications_feed"),
    path("notifications/read/", views.notifications_read, name="shared_notifications_read"),
    path("notifications/<int:pk>/open/", views.notification_open, name="shared_notification_open"),
    *crud.crud_urls("shared", ENTITIES, _sidebar, module_name="Shared Modules"),
]
