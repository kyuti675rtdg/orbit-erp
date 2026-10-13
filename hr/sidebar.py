"""HR Management sidebar: Workforce, Recruitment, Time, Payroll, Performance."""
from django.urls import reverse

from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "hr_entity_list", company, {"entity": entity}, entity=entity)


def _dash(company):
    from django.urls import reverse
    return {"type": "link", "label": "HR Dashboard", "icon": "dashboard",
            "url": reverse("hr_dashboard", kwargs={"company_slug": company.slug}),
            "url_name": "hr_dashboard"}


def get_section(company, counts=None):
    _b = lambda k: (counts or {}).get(k) or None
    items = [
        {"type": "section", "label": "HR MANAGEMENT"},
        _dash(company),
        {"type": "group", "name": "Workforce", "icon": "users", "pages": [
            _ent(company, "Departments", "building", "departments"),
            _ent(company, "Positions", "layers", "positions"),
            _ent(company, "Employees", "users", "employees"),
            _ent(company, "Promotions & Transfers", "clipboard", "employment-events"),
        ]},
        {"type": "group", "name": "Recruitment", "icon": "search",
         "badge": _b("vacancies"), "pages": [
            _ent(company, "Job Vacancies", "search", "vacancies"),
            _ent(company, "Applicants", "users", "applicants"),
            _ent(company, "Onboarding", "clipboard", "onboarding"),
        ]},
        {"type": "group", "name": "Time & Attendance", "icon": "clock",
         "badge": _b("leave"), "pages": [
            _ent(company, "Shifts", "clock", "shifts"),
            _ent(company, "Attendance", "clock", "attendance"),
            _ent(company, "Timesheets", "file", "timesheets"),
            _ent(company, "Leave Requests", "calendar", "leave-requests"),
        ]},
        {"type": "group", "name": "Payroll", "icon": "card", "pages": [
            _ent(company, "Salary Structures", "layers", "salary-structures"),
            _ent(company, "Allowances & Deductions", "wallet", "salary-components"),
            _ent(company, "Payroll Runs", "card", "payroll-runs"),
            _ent(company, "Payslips", "receipt", "payslips"),
            _ent(company, "Benefits", "gift", "benefits"),
            _ent(company, "Employee Benefits", "gift", "employee-benefits"),
            _ent(company, "Loans & Advances", "bank", "loans"),
        ]},
        {"type": "group", "name": "Performance", "icon": "chart", "pages": [
            _ent(company, "Reviews", "chart", "reviews"),
            _ent(company, "Objectives & KPIs", "target", "objectives"),
            _ent(company, "Trainings", "book", "trainings"),
            _ent(company, "Enrollments", "users", "training-enrollments"),
            _ent(company, "Certifications", "shield", "certifications"),
        ]},
        {"type": "group", "name": "HR Library", "icon": "file", "pages": [
            _ent(company, "Documents & Policies", "file", "hr-documents"),
        ]},
    ]
    portal = {"type": "link", "label": "Self-Service Portal", "icon": "users",
              "url": reverse("hr_portal", kwargs={"company_slug": company.slug}),
              "url_name": "hr_portal"}
    items.append(portal)
    return items
