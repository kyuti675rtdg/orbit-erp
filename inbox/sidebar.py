"""Inbox sidebar."""
from django.urls import reverse

from core.modules import _page


def get_section(company, counts=None):
    _b = lambda k: (counts or {}).get(k) or None
    dash = {"type": "link", "label": "Inbox Dashboard", "icon": "dashboard",
            "url": reverse("inbox_dashboard", kwargs={"company_slug": company.slug}),
            "url_name": "inbox_dashboard"}
    return [
        {"type": "section", "label": "INBOX"},
        dash,
        {"type": "group", "name": "Review", "icon": "inbox",
         "badge": _b("inbox_pending"),
         "pages": [
            _page("Pending Approval", "inbox", "inbox_pending", company),
            _page("My Submissions", "file", "inbox_mine", company),
            _page("Decision History", "clock", "inbox_history", company),
        ]},
    ]
