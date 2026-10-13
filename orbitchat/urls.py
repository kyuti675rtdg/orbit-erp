"""Orbit Chat URLs."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.chat_home, name="orbitchat_home"),
    path("api/rooms/", views.api_rooms, name="orbitchat_api_rooms"),
    path("api/rooms/dm/", views.api_dm, name="orbitchat_api_dm"),
    path("api/rooms/group/", views.api_group_create, name="orbitchat_api_group"),
    path("api/rooms/<int:room_id>/", views.api_messages, name="orbitchat_api_messages"),
    path("api/rooms/<int:room_id>/send/", views.api_send, name="orbitchat_api_send"),
    path("api/rooms/<int:room_id>/read/", views.api_mark_read, name="orbitchat_api_read"),
    path("api/rooms/<int:room_id>/members/", views.api_room_members,
         name="orbitchat_api_members"),
    path("api/messages/<int:message_id>/react/", views.api_react,
         name="orbitchat_api_react"),
    path("api/messages/<int:message_id>/delete/", views.api_delete_message,
         name="orbitchat_api_delete"),
    path("api/contacts/", views.api_contacts, name="orbitchat_api_contacts"),
    path("api/search/", views.api_search, name="orbitchat_api_search"),
    path("api/updates/", views.api_updates, name="orbitchat_api_updates"),
    path("api/presence/", views.api_heartbeat, name="orbitchat_api_heartbeat"),
]
