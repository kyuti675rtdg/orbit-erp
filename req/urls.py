"""Requests module URLs."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="req_dashboard"),
    path("requests/", views.request_list, name="req_list"),
    path("requests/new/", views.request_create, name="req_create"),
    path("requests/history/", views.request_history, name="req_history"),
    path("requests/<int:pk>/", views.request_detail, name="req_detail"),
    path("requests/<int:pk>/edit/", views.request_update, name="req_update"),
    path("requests/<int:pk>/delete/", views.request_delete, name="req_delete"),
    path("requests/<int:pk>/<str:action>/", views.request_action, name="req_action"),
]
