from django.urls import path

from core import crud

from . import views
from .entities import ENTITIES


def _sidebar(request):
    from core.modules import build_sidebar
    return build_sidebar(request)


urlpatterns = [
    path("", views.dashboard, name="finance_dashboard"),
    path("statements/", views.statements, name="finance_statements"),
    *crud.crud_urls("finance", ENTITIES, _sidebar, module_name="Finance & Accounting"),
]
