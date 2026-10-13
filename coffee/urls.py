"""Bean Power Coffee URLs."""
from django.urls import path

from core import crud

from . import views
from .entities import ENTITIES


def _sidebar(request):
    from core.modules import build_sidebar
    return build_sidebar(request)


urlpatterns = [
    path("", views.dashboard, name="coffee_dashboard"),
    path("traceability/", views.traceability, name="coffee_traceability"),
    *crud.crud_urls("coffee", ENTITIES, _sidebar, module_name="Coffee Operations"),
]
