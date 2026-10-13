"""Orbit Chat sidebar section."""
from django.urls import reverse


def get_section(company, counts=None):
    _b = lambda k: (counts or {}).get(k) or None
    return [
        {"type": "section", "label": "ORBIT CHAT"},
        {"type": "link", "label": "Orbit Chat", "icon": "chat",
         "badge": _b("chat_unread"),
         "url": reverse("orbitchat_home", kwargs={"company_slug": company.slug}),
         "url_name": "orbitchat_home"},
    ]


def unread_total(company, user):
    from .models import ChatMember
    total = 0
    for mem in ChatMember.objects.filter(
            user=user, room__company=company, room__is_archived=False):
        total += mem.unread_count()
    return total or None
