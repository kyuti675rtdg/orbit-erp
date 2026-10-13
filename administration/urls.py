from django.urls import path

from core import crud

from . import views
from .entities import ENTITIES


def _sidebar(request):
    from core.modules import build_sidebar
    return build_sidebar(request)


urlpatterns = [
    path("", views.dashboard, name="admin_dashboard"),
    
    *crud.crud_urls("admin", ENTITIES, _sidebar, module_name="Administration"),
]
