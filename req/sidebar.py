"""Requests sidebar: submit, track, decide."""
from django.urls import reverse

from core.modules import _page


def _dash(company):
    return {"type": "link", "label": "Requests Dashboard", "icon": "dashboard",
            "url": reverse("req_dashboard", kwargs={"company_slug": company.slug}),
            "url_name": "req_dashboard"}


def get_section(company, counts=None):
    _b = lambda k: (counts or {}).get(k) or None
    return [
        {"type": "section", "label": "REQUESTS"},
        _dash(company),
        {"type": "group", "name": "My Requests", "icon": "inbox",
         "pages": [
            _page("New Request", "plus", "req_create", company),
            _page("My Requests", "inbox", "req_list", company),
            _page("Activity History", "clock", "req_history", company),
        ]},
        {"type": "group", "name": "Approvals", "icon": "check",
         "badge": _b("req_pending"),
         "pages": [
            _page("All Requests", "layers", "req_list", company),
            _page("Approval Inbox", "inbox", "inbox_pending", company),
        ]},
    ]
