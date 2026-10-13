"""Sidebar sections for shared modules. Included for every company;
transport companies use fleet's own HR/Finance, so those can be excluded."""
from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "shared_entity_list", company,
                 {"entity": entity}, entity=entity)


def get_modules(company, include_hr=True, include_finance=True):
    modules = []
    if include_hr:
        modules.append({
            "module": "HR & Payroll", "icon": "users",
            "submodules": [
                {"name": "Organization", "pages": [
                    _ent(company, "Departments", "building", "departments"),
                    _ent(company, "Employees", "users", "employees"),
                ]},
                {"name": "Time & Leave", "pages": [
                    _ent(company, "Attendance", "clock", "attendance"),
                    _ent(company, "Leave Requests", "calendar", "leave-requests"),
                ]},
                {"name": "Payroll", "pages": [
                    _ent(company, "Payroll Runs", "card", "payroll-runs"),
                ]},
            ],
        })
    if include_finance:
        modules.append({
            "module": "Finance & Accounting", "icon": "receipt",
            "submodules": [
                {"name": "General Ledger", "pages": [
                    _ent(company, "Chart of Accounts", "file", "gl-accounts"),
                    _ent(company, "Journal Entries", "pencil", "journal"),
                ]},
                {"name": "Payables & Assets", "pages": [
                    _ent(company, "Bills (AP)", "receipt", "bills"),
                    _ent(company, "Fixed Assets", "box", "assets"),
                ]},
            ],
        })
    modules.append({
        "module": "Communication", "icon": "bell",
        "submodules": [{
            "name": "Announcements", "pages": [
                _ent(company, "Announcements", "bell", "announcements"),
            ],
        }],
    })
    modules.append({
        "module": "Documents", "icon": "file",
        "submodules": [{
            "name": "Library", "pages": [
                _ent(company, "Documents", "file", "documents"),
            ],
        }],
    })
    modules.append({
        "module": "Administration", "icon": "gear",
        "submodules": [
            {"name": "Access", "pages": [
                _ent(company, "Users & Roles", "users", "members"),
            ]},
            {"name": "System", "pages": [
                _ent(company, "Audit Logs", "shield", "audit-logs"),
                _ent(company, "Company Settings", "gear", "settings"),
            ]},
        ],
    })
    return modules
