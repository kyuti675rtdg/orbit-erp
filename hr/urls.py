from django.urls import path

from core import crud

from . import views
from .entities import ENTITIES


def _sidebar(request):
    from core.modules import build_sidebar
    return build_sidebar(request)


urlpatterns = [
    path("", views.dashboard, name="hr_dashboard"),
    path("portal/", views.portal, name="hr_portal"),
    *crud.crud_urls("hr", ENTITIES, _sidebar, module_name="HR Management"),
]
