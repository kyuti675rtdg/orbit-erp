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


def _mark_active(items, url_name, url_kwargs):
    entity = (url_kwargs or {}).get("entity")
    uns = _ns(url_name)
    for it in items:
        if it["type"] == "link":
            it["active"] = it.get("url_name") == url_name
        elif it["type"] == "group":
            is_open = False
            for p in it["pages"]:
                if p["entity"] and entity:
                    active = _ns(p["url_name"]) == uns and p["entity"] == entity
                else:
                    active = p["url_name"] == url_name
                p["active"] = active
                is_open = is_open or active
            it["open"] = is_open
    return items


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
        from hr.models import JobVacancy
        c["vacancies"] = JobVacancy.objects.filter(company=company, status="open").count()
        from finance.models import ARInvoice
        c["receivables"] = ARInvoice.objects.filter(company=company).exclude(status="paid").count()
        from comms.models import Task
        c["tasks"] = Task.objects.filter(company=company).exclude(status="done").count()
    except Exception:
        pass
    return {k: v for k, v in c.items() if v}


INDUSTRY_META = {
    "transport": ("FLEET OPERATIONS", "Fleet Dashboard", "fleet_dashboard"),
    "import": ("IMPORT OPERATIONS", "Import Dashboard", "imports_dashboard"),
    "export": ("EXPORT OPERATIONS", "Export Dashboard", "exports_dashboard"),
    "manufacturing": ("MANUFACTURING", "Manufacturing Dashboard", "manufacturing_dashboard"),
    "rental": ("PROPERTY RENTAL", "Rental Dashboard", "rentals_dashboard"),
    "other": ("OPERATIONS", "Overview", "company_dashboard"),
}


def build_sidebar(request):
    """Sidebar nav: flat, reference-style list.

    Structure: Dashboard link -> INDUSTRY section -> HR MANAGEMENT ->
    FINANCE & ACCOUNTING -> ADMINISTRATION -> COMMUNICATION -> EXECUTIVE ->
    divider -> Switch Company / Sign Out.
    """
    company = request.company
    key = company.industry_key or "transport"
    counts = attention_counts(company)
    section_label, dash_label, dash_url = INDUSTRY_META.get(key, INDUSTRY_META["other"])

    if key == "transport":
        from fleet import sidebar as ind_sb
        ind_modules = ind_sb.get_modules(company, counts)
    elif key == "import":
        from imports import sidebar as ind_sb
        ind_modules = ind_sb.get_modules(company, counts)
    elif key == "export":
        from exports import sidebar as ind_sb
        ind_modules = ind_sb.get_modules(company, counts)
    elif key == "manufacturing":
        from manufacturing import sidebar as ind_sb
        ind_modules = ind_sb.get_modules(company, counts)
    elif key == "rental":
        from rentals import sidebar as ind_sb
        ind_modules = ind_sb.get_modules(company, counts)
    else:
        ind_modules, dash_url = [], "company_dashboard"

    items = [
        {"type": "link", "label": "Dashboard", "icon": "dashboard",
         "url": reverse("company_dashboard", kwargs={"company_slug": company.slug}),
         "url_name": "company_dashboard"},
        {"type": "section", "label": section_label},
        {"type": "link", "label": dash_label, "icon": "chart",
         "url": reverse(dash_url, kwargs={"company_slug": company.slug}),
         "url_name": dash_url},
    ]
    # industry submodule groups (skip the single-page "Overview" -> covered by dash link)
    for mod in ind_modules:
        for sub in mod.get("submodules", []):
            if sub["name"] == "Overview" and len(sub["pages"]) <= 1:
                continue
            items.append({"type": "group", "name": sub["name"],
                          "icon": sub.get("icon", "file"),
                          "badge": sub.get("badge"), "pages": sub["pages"]})
    from hr import sidebar as hr_sb
    from finance import sidebar as fin_sb
    from administration import sidebar as adm_sb
    from comms import sidebar as com_sb
    from executive import sidebar as exe_sb
    items.extend(hr_sb.get_section(company, counts))
    items.extend(fin_sb.get_section(company, counts))
    items.extend(adm_sb.get_section(company, counts))
    items.extend(com_sb.get_section(company, counts))
    items.extend(exe_sb.get_section(company, counts))
    items.append({"type": "divider"})
    items.append({"type": "link", "label": "Switch Company", "icon": "globe",
                  "url": reverse("company_hub"), "url_name": "company_hub", "bottom": True})
    items.append({"type": "signout"})

    resolver = request.resolver_match
    if resolver:
        _mark_active(items, resolver.url_name, resolver.kwargs)
    return items


__all__ = ["INDUSTRY_LABELS", "build_sidebar", "_page"]
