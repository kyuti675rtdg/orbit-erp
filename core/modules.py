"""Industry module registry + hierarchical sidebar builder.

Sidebar shape (per company)::
    [
      {"module": "Transport Operations", "icon": "truck", "open": True,
       "submodules": [
           {"name": "Trips & Dispatch", "open": True,
            "pages": [{"label": "Trips", "icon": "trips",
                       "url": "/c/x/fleet/trips/", "url_name": "fleet_entity_list",
                       "entity": "trips", "active": True},
                      ...]},
       ]},
    ]
"""
from django.urls import reverse

from core.models import INDUSTRY_CHOICES

INDUSTRY_LABELS = dict(INDUSTRY_CHOICES)


def _page(label, icon, url_name, company, kwargs=None, entity=None):
    kw = {"company_slug": company.slug}
    kw.update(kwargs or {})
    return {
        "label": label, "icon": icon, "url_name": url_name, "entity": entity,
        "url": reverse(url_name, kwargs=kw),
    }


def _ns(url_name):
    """App namespace of a url name: fleet_entity_list -> fleet, fleet_trips -> fleet."""
    if not url_name:
        return ""
    if "_entity_" in url_name:
        return url_name.split("_entity_")[0]
    parts = url_name.rsplit("_", 1)
    return parts[0] if len(parts) > 1 else url_name


def _mark_active(modules, url_name, url_kwargs):
    entity = (url_kwargs or {}).get("entity")
    uns = _ns(url_name)
    for mod in modules:
        if mod.get("flat"):
            for p in mod.get("pages", []):
                p["active"] = p["url_name"] == url_name
            mod["open"] = any(p["active"] for p in mod["pages"])
            continue
        mod_open = False
        for sub in mod["submodules"]:
            sub_open = False
            for p in sub["pages"]:
                if p["entity"] and entity:
                    active = _ns(p["url_name"]) == uns and p["entity"] == entity
                else:
                    active = p["url_name"] == url_name
                p["active"] = active
                if active:
                    sub_open = True
            sub["open"] = sub_open
            mod_open = mod_open or sub_open
        mod["open"] = mod_open
    return modules


def attention_counts(company):
    """Pending-action counts per area, shown as sidebar badges. Cheap queries only."""
    key = company.industry_key or "transport"
    c = {}
    try:
        if key == "transport":
            from fleet.models import Alert, Trip
            c["alerts"] = Alert.objects.filter(company=company, is_resolved=False).count()
            c["trips"] = Trip.objects.filter(company=company, status="planned").count()
        elif key == "import":
            from imports.models import CustomsDeclaration, ImportRequest
            c["requests"] = ImportRequest.objects.filter(company=company, status="submitted").count()
            c["customs"] = CustomsDeclaration.objects.filter(company=company).exclude(status="cleared").count()
        elif key == "export":
            from exports.models import ExportInvoice, ExportOrder
            c["qc"] = ExportOrder.objects.filter(company=company, status="preparing").count()
            c["receivables"] = ExportInvoice.objects.filter(company=company).exclude(status="paid").count()
        elif key == "manufacturing":
            from django.db.models import F
            from manufacturing.models import ProductionOrder, RawMaterial
            c["lowstock"] = RawMaterial.objects.filter(
                company=company, stock_qty__lte=F("reorder_level")).count()
            c["qc"] = ProductionOrder.objects.filter(company=company, status="qc").count()
        elif key == "rental":
            from rentals.models import MaintenanceRequest, RentSchedule
            c["overdue"] = RentSchedule.objects.filter(company=company, status="overdue").count()
            c["maint"] = MaintenanceRequest.objects.filter(
                company=company, status__in=["open", "in_progress"]).count()
        from shared.models import Bill, LeaveRequest
        c["leave"] = LeaveRequest.objects.filter(company=company, status="pending").count()
        c["bills"] = Bill.objects.filter(company=company).exclude(status="paid").count()
    except Exception:
        pass
    return {k: v for k, v in c.items() if v}


def build_sidebar(request):
    """Full hierarchical sidebar for the request's active company."""
    company = request.company
    key = company.industry_key or "transport"
    counts = attention_counts(company)

    modules = [
        {
            "module": "Dashboard", "icon": "dashboard", "flat": True,
            "pages": [_page("Company Dashboard", "dashboard", "company_dashboard", company)],
        },
    ]

    if key == "transport":
        from fleet import sidebar as fleet_sb
        modules.extend(fleet_sb.get_modules(company, counts))
        from shared import sidebar as shared_sb
        modules.extend(shared_sb.get_modules(company, counts, include_hr=False, include_finance=False))
    elif key == "import":
        from imports import sidebar as sb
        modules.extend(sb.get_modules(company, counts))
        from shared import sidebar as shared_sb
        modules.extend(shared_sb.get_modules(company, counts))
    elif key == "export":
        from exports import sidebar as sb
        modules.extend(sb.get_modules(company, counts))
        from shared import sidebar as shared_sb
        modules.extend(shared_sb.get_modules(company, counts))
    elif key == "manufacturing":
        from manufacturing import sidebar as sb
        modules.extend(sb.get_modules(company, counts))
        from shared import sidebar as shared_sb
        modules.extend(shared_sb.get_modules(company, counts))
    elif key == "rental":
        from rentals import sidebar as sb
        modules.extend(sb.get_modules(company, counts))
        from shared import sidebar as shared_sb
        modules.extend(shared_sb.get_modules(company, counts))
    else:
        from shared import sidebar as shared_sb
        modules.extend(shared_sb.get_modules(company, counts))

    # Module Hub link (workspace)
    modules.append({
        "module": "Workspace", "icon": "home",
        "submodules": [{
            "name": "General",
            "pages": [
                _page("Module Hub", "home", "workspace", company),
                {"label": "All Companies", "icon": "building", "url_name": "company_hub",
                 "entity": None, "url": reverse("company_hub")},
            ],
        }],
    })

    resolver = request.resolver_match
    if resolver:
        _mark_active(modules, resolver.url_name, resolver.kwargs)
    return modules


__all__ = ["INDUSTRY_LABELS", "build_sidebar", "_page"]
