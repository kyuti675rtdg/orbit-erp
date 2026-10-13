"""Communication URLs."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="comm_dashboard"),
    path("channels/", views.channel_list, name="comm_channels"),
    path("channels/new-direct/", views.new_direct, name="comm_new_direct"),
    path("channels/new-group/", views.new_group, name="comm_new_group"),
    path("channel/<int:pk>/", views.channel_detail, name="comm_channel"),
    path("channel/<int:pk>/post/", views.message_post, name="comm_post"),
    path("channel/<int:pk>/members/add/", views.member_add, name="comm_member_add"),
    path("channel/<int:pk>/members/<int:user_id>/remove/", views.member_remove,
         name="comm_member_remove"),
]
