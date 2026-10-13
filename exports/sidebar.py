"""Hierarchical sidebar for Export Management."""
from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "exports_entity_list", company, {"entity": entity}, entity=entity)


def get_modules(company, counts=None):
    _b = lambda k: (counts or {}).get(k) or None
    return [
        {"module": "Export Operations", "icon": "package", "submodules": [
            {"name": "Overview", "pages": [
                _page("Export Dashboard", "dashboard", "exports_dashboard", company),
            ]},
            {"name": "Customers", "pages": [
                _ent(company, "Buyers", "users", "buyers"),
                _ent(company, "Buyer Contacts", "user", "buyer-contacts"),
                _ent(company, "Export Products", "package", "products"),
            ]},
            {"name": "Sales", "pages": [
                _ent(company, "Quotations", "file", "quotations"),
                _ent(company, "Contracts", "clipboard", "contracts"),
                _ent(company, "Export Orders", "package", "orders"),
            ]},
            {"name": "Quality & Documents", "badge": _b("qc"), "pages": [
                _ent(company, "Quality Inspections", "shield", "inspections"),
                _ent(company, "Export Documents", "file", "documents"),
            ]},
            {"name": "Shipments", "pages": [
                _ent(company, "Shipments", "truck", "shipments"),
                _ent(company, "Containers", "box", "containers"),
                _ent(company, "Customs Declarations", "shield", "declarations"),
            ]},
            {"name": "Finance", "badge": _b("receivables"), "pages": [
                _ent(company, "Export Invoices", "receipt", "invoices"),
                _ent(company, "Payment Receipts", "bank", "receipts"),
                _ent(company, "Export Costing", "wallet", "costs"),
            ]},
        ]},
    ]
