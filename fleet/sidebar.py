"""Hierarchical sidebar for Transportation & Fleet (Module -> Submodule -> Page)."""
from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "fleet_entity_list", company, {"entity": entity}, entity=entity)


def get_modules(company, counts=None):
    _b = lambda k: (counts or {}).get(k) or None
    return [
        {"module": "Transport Operations", "icon": "truck", "submodules": [
            {"name": "Overview", "icon": "dashboard", "badge": _b("alerts"), "pages": [
                _page("Dashboard", "dashboard", "fleet_dashboard", company),
                _page("Live Tracking", "tracking", "fleet_tracking", company),
                _page("Reports & BI", "chart", "fleet_reports", company),
                _ent(company, "Alerts", "bell", "alerts"),
            ]},
            {"name": "Trips & Dispatch", "icon": "trips", "badge": _b("trips"), "pages": [
                _ent(company, "Trips", "trips", "trips"),
                _ent(company, "Dispatch Orders", "clipboard", "dispatches"),
                _ent(company, "Deliveries & POD", "package", "deliveries"),
            ]},
            {"name": "Fleet", "icon": "truck", "pages": [
                _ent(company, "Vehicles", "truck", "vehicles"),
                _ent(company, "Vehicle Documents", "file", "vehicle-documents"),
                _ent(company, "Routes", "map", "routes"),
                _ent(company, "Geofences", "pin", "geofences"),
            ]},
            {"name": "Drivers", "icon": "users", "pages": [
                _ent(company, "Drivers", "user", "drivers"),
                _ent(company, "Driver Documents", "idcard", "driver-documents"),
            ]},
            {"name": "Fuel & Maintenance", "icon": "fuel", "pages": [
                _ent(company, "Fuel Logs", "fuel", "fuel"),
                _ent(company, "Maintenance", "wrench", "services"),
                _ent(company, "Inspections", "shield", "inspections"),
                _ent(company, "Spare Parts", "gear", "parts"),
                _ent(company, "Workshop Jobs", "warehouse", "workshop-jobs"),
                _ent(company, "Part Issues", "box", "part-issues"),
            ]},
        ]},
        {"module": "Billing & Expenses", "icon": "receipt", "submodules": [
            {"name": "Billing", "icon": "receipt", "pages": [
                _ent(company, "Trip Expenses", "wallet", "expenses"),
                _ent(company, "Driver Advances", "cash", "advances"),
                _ent(company, "Invoices", "receipt", "invoices"),
                _ent(company, "Payments", "bank", "payments"),
            ]},
        ]},
    ]
