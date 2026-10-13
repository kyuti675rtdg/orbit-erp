"""Hierarchical sidebar for Building & Property Rental."""
from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "rentals_entity_list", company, {"entity": entity}, entity=entity)


def get_modules(company):
    return [
        {"module": "Property Rental", "icon": "building", "submodules": [
            {"name": "Overview", "pages": [
                _page("Rental Dashboard", "dashboard", "rentals_dashboard", company),
            ]},
            {"name": "Properties", "pages": [
                _ent(company, "Properties", "building", "properties"),
                _ent(company, "Buildings", "building", "buildings"),
                _ent(company, "Units", "home", "units"),
            ]},
            {"name": "Tenants & Leases", "pages": [
                _ent(company, "Tenants", "users", "tenants"),
                _ent(company, "Leases", "clipboard", "leases"),
                _ent(company, "Rent Schedule", "calendar", "rent-schedule"),
            ]},
            {"name": "Billing & Collection", "pages": [
                _ent(company, "Rent Invoices", "receipt", "rent-invoices"),
                _ent(company, "Rent Payments", "bank", "rent-payments"),
                _ent(company, "Deposits", "wallet", "deposits"),
            ]},
            {"name": "Operations", "pages": [
                _ent(company, "Maintenance Requests", "wrench", "maintenance-requests"),
                _ent(company, "Work Orders", "gear", "work-orders"),
                _ent(company, "Utilities", "file", "utilities"),
                _ent(company, "Property Expenses", "wallet", "property-expenses"),
            ]},
        ]},
    ]
