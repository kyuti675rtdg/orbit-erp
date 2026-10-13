"""Administration & System Management sidebar."""
from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "admin_entity_list", company, {"entity": entity}, entity=entity)


def get_section(company, counts=None):
    from django.urls import reverse
    dash = {"type": "link", "label": "Admin Dashboard", "icon": "dashboard",
            "url": reverse("admin_dashboard", kwargs={"company_slug": company.slug}),
            "url_name": "admin_dashboard"}
    return [
        {"type": "section", "label": "ADMINISTRATION"},
        dash,
        {"type": "group", "name": "Organization", "icon": "building", "pages": [
            _ent(company, "Branches", "building", "branches"),
            _ent(company, "Company Settings", "gear", "settings"),
        ]},
        {"type": "group", "name": "Users & Access", "icon": "users", "pages": [
            _ent(company, "Users & Roles", "users", "members"),
            _ent(company, "Custom Roles", "shield", "roles"),
            _ent(company, "Approval Rules", "clipboard", "approval-rules"),
        ]},
        {"type": "group", "name": "Master Data", "icon": "layers", "pages": [
            _ent(company, "Currencies", "bank", "currencies"),
            _ent(company, "Numbering", "file", "numbering"),
            _ent(company, "Fiscal Calendars", "calendar", "fiscal-calendars"),
        ]},
        {"type": "group", "name": "Security", "icon": "shield", "pages": [
            _ent(company, "Audit Logs", "shield", "audit-logs"),
            _ent(company, "Login Sessions", "clock", "sessions"),
            _ent(company, "Notification Settings", "bell", "notification-settings"),
        ]},
        {"type": "group", "name": "Data & Integrations", "icon": "box", "pages": [
            _ent(company, "Backups", "box", "backups"),
            _ent(company, "API Integrations", "layers", "integrations"),
        ]},
    ]
