"""Communication sidebar: department channels, group chats, direct messages."""
from django.urls import reverse


def get_section(company, counts=None):
    _b = lambda k: (counts or {}).get(k) or None
    dash = {"type": "link", "label": "Communication Hub", "icon": "dashboard",
            "url": reverse("comm_dashboard", kwargs={"company_slug": company.slug}),
            "url_name": "comm_dashboard"}

    def page(label, icon, url_name, badge=None):
        return {"label": label, "icon": icon, "url_name": url_name, "entity": None,
                "url": reverse(url_name, kwargs={"company_slug": company.slug})}

    return [
        {"type": "section", "label": "COMMUNICATION"},
        dash,
        {"type": "group", "name": "Messaging", "icon": "chat",
         "badge": _b("comm_unread"),
         "pages": [
            page("All Channels", "chat", "comm_channels"),
            page("New Direct Message", "user", "comm_new_direct"),
            page("New Group Chat", "users", "comm_new_group"),
        ]},
    ]
