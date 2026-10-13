"""Hierarchical sidebar for Bean Power Coffee ERP."""
from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "coffee_entity_list", company, {"entity": entity}, entity=entity)


def get_modules(company, counts=None):
    _b = lambda k: (counts or {}).get(k) or None
    return [
        {"module": "Coffee Operations", "icon": "coffee", "submodules": [
            {"name": "Overview", "icon": "dashboard", "pages": [
                _page("Coffee Dashboard", "dashboard", "coffee_dashboard", company),
                _page("Traceability", "search", "coffee_traceability", company),
            ]},
            {"name": "Farmers & Suppliers", "icon": "users", "pages": [
                _ent(company, "Farmers", "user", "farmers"),
                _ent(company, "Cooperatives", "users", "cooperatives"),
                _ent(company, "Suppliers", "truck", "suppliers"),
                _ent(company, "Farmer Contracts", "clipboard", "farmer-contracts"),
                _ent(company, "Farmer Payments", "cash", "farmer-payments"),
            ]},
            {"name": "Farms & Plants", "icon": "leaf", "pages": [
                _ent(company, "Farms", "leaf", "farms"),
                _ent(company, "Plots", "grid", "plots"),
                _ent(company, "Plants & Groups", "sprout", "plants"),
                _ent(company, "Plant Health", "heart", "plant-health"),
                _ent(company, "Harvests", "basket", "harvests"),
                _ent(company, "Agri Inputs", "flask", "farm-inputs"),
                _ent(company, "Farm Visits", "eye", "farm-visits"),
            ]},
            {"name": "Sites", "icon": "building", "pages": [
                _ent(company, "Coffee Sites", "building", "sites"),
                _ent(company, "Site Staff", "user", "site-staff"),
            ]},
            {"name": "Procurement", "icon": "file", "badge": _b("coffee_po"),
             "pages": [
                _ent(company, "Purchase Orders", "file", "purchase-orders"),
                _ent(company, "Coffee Purchases", "basket", "purchases"),
                _ent(company, "Purchase Receipts", "check", "purchase-receipts"),
                _ent(company, "Price Management", "tag", "prices"),
            ]},
            {"name": "Collection & Intake", "icon": "truck", "pages": [
                _ent(company, "Deliveries", "truck", "deliveries"),
                _ent(company, "Weighbridge", "scale", "weighbridge"),
                _ent(company, "Intake Batches", "package", "intake-batches"),
            ]},
            {"name": "Processing", "icon": "cog", "pages": [
                _ent(company, "Processing Orders", "cog", "processing-orders"),
                _ent(company, "Processing Batches", "layers", "processing-batches"),
                _ent(company, "Drying Records", "sun", "drying"),
            ]},
            {"name": "Quality Lab", "icon": "flask", "badge": _b("coffee_qc"), "pages": [
                _ent(company, "Samples", "flask", "samples"),
                _ent(company, "Moisture Tests", "drop", "moisture-tests"),
                _ent(company, "Cupping Sessions", "coffee", "cuppings"),
                _ent(company, "Quality Certificates", "award", "quality-certs"),
            ]},
            {"name": "Warehouse", "icon": "box", "pages": [
                _ent(company, "Warehouses", "building", "warehouses"),
                _ent(company, "Lots", "box", "lots"),
                _ent(company, "Movements", "arrow", "movements"),
                _ent(company, "Adjustments", "edit", "adjustments"),
            ]},
            {"name": "Export", "icon": "send", "badge": _b("coffee_exp"), "pages": [
                _ent(company, "Buyers", "users", "buyers"),
                _ent(company, "Contracts", "clipboard", "export-contracts"),
                _ent(company, "Export Orders", "package", "export-orders"),
                _ent(company, "Documents", "file", "export-docs"),
                _ent(company, "Shipments", "truck", "shipments"),
                _ent(company, "Export Invoices", "receipt", "export-invoices"),
            ]},
            {"name": "Logistics", "icon": "truck", "pages": [
                _ent(company, "Transporters", "truck", "transporters"),
                _ent(company, "Dispatches", "send", "dispatches"),
            ]},
            {"name": "Equipment", "icon": "wrench", "pages": [
                _ent(company, "Equipment", "cog", "equipment"),
                _ent(company, "Maintenance", "wrench", "maintenance"),
                _ent(company, "Spare Parts", "box", "spare-parts"),
            ]},
            {"name": "Security", "icon": "shield", "pages": [
                _ent(company, "Cameras", "eye", "cameras"),
                _ent(company, "Incidents", "shield", "incidents"),
            ]},
        ]},
    ]
