"""Inbox URLs."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="inbox_dashboard"),
    path("pending/", views.pending, name="inbox_pending"),
    path("pending/<int:pk>/", views.item_detail, name="inbox_detail"),
    path("mine/", views.mine, name="inbox_mine"),
    path("history/", views.history, name="inbox_history"),
]
