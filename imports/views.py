"""Import Management views: module dashboard (CRUD served by core.crud)."""
from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from core import dashboards as D
from core.modules import build_sidebar
from core.views import company_access_required

from . import models as m


def _sidebar(request):
    return build_sidebar(request)


@company_access_required
def dashboard(request, company_slug):
    c = request.company
    today = timezone.now().date()
    months = D.last_n_months(6)

    pending_req = m.ImportRequest.objects.filter(company=c, status__in=["draft", "submitted"]).count()
    open_pos = m.PurchaseOrder.objects.filter(company=c).exclude(status__in=["received", "cancelled"])
    open_po_val = open_pos.aggregate(t=Sum("total_amount"))["t"] or 0
    transit = m.Shipment.objects.filter(company=c, status__in=["in_transit", "at_port"]).count()
    duties = m.CustomsDeclaration.objects.filter(company=c).exclude(status="cleared").aggregate(
        d=Sum("duty_amount"), t=Sum("tax_amount"))
    duties_val = (duties["d"] or 0) + (duties["t"] or 0)

    po_monthly = D.monthly_sums(m.PurchaseOrder.objects.filter(company=c),
                                "order_date", "total_amount", months)
    by_status = list(m.Shipment.objects.filter(company=c).values("status").annotate(n=Count("id")))

    alerts = []
    for r in m.ImportRequest.objects.filter(company=c, status="submitted").order_by("-request_date")[:4]:
        alerts.append({"icon": "clipboard", "level": "warn", "text": f"Request {r.request_no} awaiting approval",
                       "time": f"{r.product_description[:60]}"})
    for s in m.Shipment.objects.filter(company=c, eta__lte=today + timedelta(days=7),
                                       eta__gte=today).exclude(status="delivered")[:4]:
        alerts.append({"icon": "truck", "level": "info",
                       "text": f"Shipment {s.shipment_no} ETA {s.eta:%b %d}", "time": s.destination})
    for d in m.CustomsDeclaration.objects.filter(company=c).exclude(status="cleared")[:4]:
        alerts.append({"icon": "shield", "level": "danger",
                       "text": f"Customs {d.declaration_no} not cleared", "time": f"{d.shipment.shipment_no}"})

    def el(entity):
        from django.urls import reverse
        return reverse("imports_entity_list", kwargs={"company_slug": c.slug, "entity": entity})

    cfg = {
        "title": "Import Dashboard", "subtitle": "Import Management",
        "kpis": [
            D.kpi("Pending Requests", f"{pending_req}", "clipboard", "#f59e0b", "draft + submitted"),
            D.kpi("Open POs Value", f"{open_po_val:,.0f}", "file", "#3b82f6", "USD"),
            D.kpi("Shipments In Transit", f"{transit}", "truck", "#22c55e", "in transit / at port"),
            D.kpi("Duties & Taxes Due", f"{duties_val:,.0f}", "shield", "#ef4444", "not cleared"),
        ],
        "line": {"title": "Purchase Orders (6 months)", "subtitle": "Order value per month",
                 "labels": [l for _, _, l in months], "label": "PO value (USD)",
                 "data": po_monthly, "color": "#ff7a18"},
        "donut": {"title": "Shipments by Status", "subtitle": "Current pipeline",
                  "labels": [dict(m.Shipment.STATUS).get(r["status"], r["status"]) for r in by_status],
                  "data": [r["n"] for r in by_status]},
        "alerts": alerts,
        "actions": [
            {"label": "New Request", "icon": "plus", "url": el("import-requests")},
            {"label": "New PO", "icon": "file", "url": el("purchase-orders")},
            {"label": "New Shipment", "icon": "truck", "url": el("shipments")},
            {"label": "New Supplier", "icon": "users", "url": el("suppliers")},
            {"label": "Customs", "icon": "shield", "url": el("customs")},
            {"label": "Stock", "icon": "warehouse", "url": el("warehouse-stock")},
        ],
        "tables": [
            {"title": "Recent Purchase Orders", "icon": "file", "url": el("purchase-orders"),
             "headers": ["PO No", "Supplier", "Date", "Total", "Status"],
             "rows": [[p.po_no, p.supplier.name, f"{p.order_date:%b %d}", f"{p.total_amount:,.0f}",
                       p.get_status_display()]
                      for p in m.PurchaseOrder.objects.filter(company=c).order_by("-order_date")[:6]]},
            {"title": "Recent Shipments", "icon": "truck", "url": el("shipments"),
             "headers": ["Shipment", "Origin → Dest", "ETA", "Status"],
             "rows": [[s.shipment_no, f"{s.origin} → {s.destination}",
                       s.eta.strftime("%b %d") if s.eta else "—", s.get_status_display()]
                      for s in m.Shipment.objects.filter(company=c).order_by("-created_at")[:6]]},
        ],
    }
    return D.render_module_dashboard(request, c, cfg)
