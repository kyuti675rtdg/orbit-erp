"""Hierarchical sidebar for Building & Property Rental."""
from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "rentals_entity_list", company, {"entity": entity}, entity=entity)


def get_modules(company, counts=None):
    _b = lambda k: (counts or {}).get(k) or None
    return [
        {"module": "Property Rental", "icon": "building", "submodules": [
            {"name": "Overview", "icon": "dashboard", "pages": [
                _page("Rental Dashboard", "dashboard", "rentals_dashboard", company),
            ]},
            {"name": "Properties", "icon": "building", "pages": [
                _ent(company, "Properties", "building", "properties"),
                _ent(company, "Buildings", "building", "buildings"),
                _ent(company, "Units", "home", "units"),
            ]},
            {"name": "Tenants & Leases", "icon": "users", "pages": [
                _ent(company, "Tenants", "users", "tenants"),
                _ent(company, "Leases", "clipboard", "leases"),
                _ent(company, "Rent Schedule", "calendar", "rent-schedule"),
            ]},
            {"name": "Billing & Collection", "icon": "receipt", "badge": _b("overdue"), "pages": [
                _ent(company, "Rent Invoices", "receipt", "rent-invoices"),
                _ent(company, "Rent Payments", "bank", "rent-payments"),
                _ent(company, "Deposits", "wallet", "deposits"),
            ]},
            {"name": "Operations", "icon": "wrench", "badge": _b("maint"), "pages": [
                _ent(company, "Maintenance Requests", "wrench", "maintenance-requests"),
                _ent(company, "Work Orders", "gear", "work-orders"),
                _ent(company, "Utilities", "file", "utilities"),
                _ent(company, "Property Expenses", "wallet", "property-expenses"),
            ]},
        ]},
    ]
