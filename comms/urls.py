from django.urls import path

from core import crud

from . import views
from .entities import ENTITIES


def _sidebar(request):
    from core.modules import build_sidebar
    return build_sidebar(request)


urlpatterns = [
    path("", views.dashboard, name="comms_dashboard"),
    path("notifications/feed/", views.notifications_feed, name="comms_notifications_feed"),
    path("notifications/read/", views.notifications_read, name="comms_notifications_read"),
    path("notifications/<int:pk>/open/", views.notification_open, name="comms_notification_open"),
    *crud.crud_urls("comms", ENTITIES, _sidebar, module_name="Communication"),
]
