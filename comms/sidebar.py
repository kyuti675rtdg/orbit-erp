"""Communication & Collaboration sidebar."""
from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "comms_entity_list", company, {"entity": entity}, entity=entity)


def get_section(company, counts=None):
    from django.urls import reverse
    _b = lambda k: (counts or {}).get(k) or None
    dash = {"type": "link", "label": "Communication Hub", "icon": "dashboard",
            "url": reverse("comms_dashboard", kwargs={"company_slug": company.slug}),
            "url_name": "comms_dashboard"}
    return [
        {"type": "section", "label": "COMMUNICATION"},
        dash,
        {"type": "group", "name": "Messaging", "icon": "chat",
         "badge": _b("unread"), "pages": [
            _ent(company, "Conversations", "chat", "conversations"),
            _ent(company, "Messages", "chat", "messages"),
            _ent(company, "Announcements", "bell", "announcements"),
            _ent(company, "Notifications", "bell", "notifications"),
        ]},
        {"type": "group", "name": "Collaboration", "icon": "users",
         "badge": _b("tasks"), "pages": [
            _ent(company, "Tasks & Assignments", "clipboard", "tasks"),
            _ent(company, "Meetings & Events", "calendar", "meetings"),
            _ent(company, "Document Library", "file", "documents"),
        ]},
    ]
