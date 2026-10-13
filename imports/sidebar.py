"""Hierarchical sidebar for Import Management."""
from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "imports_entity_list", company, {"entity": entity}, entity=entity)


def get_modules(company):
    return [
        {"module": "Import Operations", "icon": "package", "submodules": [
            {"name": "Overview", "pages": [
                _page("Import Dashboard", "dashboard", "imports_dashboard", company),
            ]},
            {"name": "Sourcing", "pages": [
                _ent(company, "Suppliers", "truck", "suppliers"),
                _ent(company, "Supplier Contacts", "user", "supplier-contacts"),
                _ent(company, "Import Products", "package", "products"),
            ]},
            {"name": "Procurement", "pages": [
                _ent(company, "Import Requests", "clipboard", "import-requests"),
                _ent(company, "Purchase Orders", "file", "purchase-orders"),
                _ent(company, "Proforma Invoices", "receipt", "proforma-invoices"),
            ]},
            {"name": "Shipments", "pages": [
                _ent(company, "Shipments", "truck", "shipments"),
                _ent(company, "Containers", "box", "containers"),
                _ent(company, "Import Documents", "file", "documents"),
            ]},
            {"name": "Customs & Warehouse", "pages": [
                _ent(company, "Customs Declarations", "shield", "customs"),
                _ent(company, "Goods Receiving", "package", "goods-receipts"),
                _ent(company, "Warehouse Stock", "warehouse", "warehouse-stock"),
            ]},
            {"name": "Payables", "pages": [
                _ent(company, "Supplier Invoices", "receipt", "supplier-invoices"),
                _ent(company, "Supplier Payments", "bank", "supplier-payments"),
            ]},
        ]},
    ]
