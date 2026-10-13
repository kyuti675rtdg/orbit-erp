"""Business Monitoring URLs (global, outside the company workspace)."""
from django.urls import path

from . import views

urlpatterns = [
    path("monitoring/", views.overview, name="monitoring_overview"),
    path("monitoring/<slug:company_slug>/", views.company_view, name="monitoring_company"),
]
