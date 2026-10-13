"""Executive Management & BI sidebar."""
from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "exec_entity_list", company, {"entity": entity}, entity=entity)


def get_section(company, counts=None):
    from django.urls import reverse
    dash = {"type": "link", "label": "Executive Dashboard", "icon": "dashboard",
            "url": reverse("exec_dashboard", kwargs={"company_slug": company.slug}),
            "url_name": "exec_dashboard"}
    return [
        {"type": "section", "label": "EXECUTIVE"},
        dash,
        {"type": "group", "name": "Analytics", "icon": "chart", "pages": [
            {"label": "Performance Overview", "icon": "chart",
             "url": reverse("exec_dashboard", kwargs={"company_slug": company.slug}),
             "url_name": "exec_dashboard", "entity": None},
            {"label": "Budget vs Actual", "icon": "file",
             "url": reverse("exec_budget", kwargs={"company_slug": company.slug}),
             "url_name": "exec_budget", "entity": None},
        ]},
        {"type": "group", "name": "Reports", "icon": "file", "pages": [
            _ent(company, "Custom Reports", "chart", "report-definitions"),
            _ent(company, "Scheduled Reports", "clock", "scheduled-reports"),
        ]},
    ]
