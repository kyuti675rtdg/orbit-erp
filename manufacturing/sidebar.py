"""Hierarchical sidebar for Manufacturing."""
from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "manufacturing_entity_list", company, {"entity": entity}, entity=entity)


def get_modules(company, counts=None):
    _b = lambda k: (counts or {}).get(k) or None
    return [
        {"module": "Manufacturing", "icon": "gear", "submodules": [
            {"name": "Overview", "icon": "dashboard", "pages": [
                _page("Manufacturing Dashboard", "dashboard", "manufacturing_dashboard", company),
            ]},
            {"name": "Products & BOM", "pages": [
                _ent(company, "Products", "package", "products"),
                _ent(company, "Categories", "box", "categories"),
                _ent(company, "BOM & Recipes", "clipboard", "boms"),
                _ent(company, "BOM Lines", "pencil", "bom-lines"),
            ]},
            {"name": "Materials", "icon": "box", "badge": _b("lowstock"), "pages": [
                _ent(company, "Raw Materials", "box", "raw-materials"),
                _ent(company, "Material Issues", "package", "material-issues"),
            ]},
            {"name": "Production", "icon": "gear", "pages": [
                _ent(company, "Production Plans", "calendar", "plans"),
                _ent(company, "Production Orders", "gear", "production-orders"),
                _ent(company, "Work Centers", "warehouse", "work-centers"),
                _ent(company, "Machines", "gear", "machines"),
            ]},
            {"name": "Quality & Inventory", "icon": "shield", "badge": _b("qc"), "pages": [
                _ent(company, "Quality Checks", "shield", "quality-checks"),
                _ent(company, "Batches & Lots", "package", "batches"),
                _ent(company, "Warehouses", "warehouse", "warehouses"),
                _ent(company, "Inventory", "box", "stock"),
            ]},
            {"name": "Maintenance", "pages": [
                _ent(company, "Maintenance Records", "wrench", "maintenance"),
            ]},
        ]},
    ]
