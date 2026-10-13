"""Collaboration sidebar (legacy comms app): tasks, meetings, documents.

Team messaging now lives in the dedicated COMMUNICATION module
(messaging permissions follow organizational roles). The legacy
conversation URLs still work but are no longer linked here.
"""
from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "comms_entity_list", company, {"entity": entity}, entity=entity)


def get_section(company, counts=None):
    from django.urls import reverse
    _b = lambda k: (counts or {}).get(k) or None
    dash = {"type": "link", "label": "Collaboration Hub", "icon": "dashboard",
            "url": reverse("comms_dashboard", kwargs={"company_slug": company.slug}),
            "url_name": "comms_dashboard"}
    return [
        {"type": "section", "label": "COLLABORATION"},
        dash,
        {"type": "group", "name": "Collaboration", "icon": "users",
         "badge": _b("tasks"), "pages": [
            _ent(company, "Tasks & Assignments", "clipboard", "tasks"),
            _ent(company, "Meetings & Events", "calendar", "meetings"),
            _ent(company, "Document Library", "file", "documents"),
        ]},
        {"type": "group", "name": "Updates", "icon": "bell",
         "pages": [
            _ent(company, "Announcements", "bell", "announcements"),
            _ent(company, "Notifications", "bell", "notifications"),
        ]},
    ]
