from django.urls import path

from core import crud

from . import views
from .entities import ENTITIES


def _sidebar(request):
    from core.modules import build_sidebar
    return build_sidebar(request)


urlpatterns = [
    path("", views.dashboard, name="exec_dashboard"),
    path("budget/", views.budget_vs_actual, name="exec_budget"),
    path("reports/<int:pk>/run/", views.run_report, name="exec_report_run"),
    path("reports/<int:pk>/csv/", views.report_csv, name="exec_report_csv"),
    *crud.crud_urls("exec", ENTITIES, _sidebar, module_name="Executive"),
]
