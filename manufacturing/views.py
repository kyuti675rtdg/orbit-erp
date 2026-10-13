"""Manufacturing views: module dashboard (CRUD served by core.crud)."""
from datetime import timedelta

from django.db.models import Count, F, Sum
from django.urls import reverse
from django.utils import timezone

from core import dashboards as D
from core.views import company_access_required

from . import models as m


def _sidebar(request):
    from core.modules import build_sidebar
    return build_sidebar(request)


@company_access_required
def dashboard(request, company_slug):
    c = request.company
    today = timezone.now().date()
    months = D.last_n_months(6)

    active_orders = m.ProductionOrder.objects.filter(
        company=c, status__in=["released", "in_progress", "qc"]).count()
    low_stock = m.RawMaterial.objects.filter(company=c, stock_qty__lte=F("reorder_level")).count()
    qc_pending = m.QualityCheck.objects.filter(company=c, result="rework").count() \
        + m.ProductionOrder.objects.filter(company=c, status="qc").count()
    output = m.Batch.objects.filter(company=c, production_date__year=today.year,
                                    production_date__month=today.month
                                    ).aggregate(t=Sum("quantity"))["t"] or 0

    order_counts = []
    for y, mo, _lbl in months:
        order_counts.append(m.ProductionOrder.objects.filter(
            company=c, order_date__year=y, order_date__month=mo).count())
    # monthly output trend (batches released)
    out_monthly = []
    for y, mo, _lbl in months:
        out_monthly.append(float(m.Batch.objects.filter(
            company=c, production_date__year=y, production_date__month=mo)
            .aggregate(t=Sum("quantity"))["t"] or 0))
    out_delta, out_dir = D.pct_delta(out_monthly[-1] if len(out_monthly) > 1 else 0,
                                     out_monthly[-2] if len(out_monthly) > 1 else 0)
    # QC pass rate (last 90 days)
    qc_recent = m.QualityCheck.objects.filter(
        company=c, check_date__gte=timezone.now().date() - timedelta(days=90))
    qc_total = qc_recent.count()
    qc_pass = qc_recent.filter(result="pass").count()
    qc_rate = round(qc_pass / qc_total * 100) if qc_total else 0
    # output by product
    by_prod = (m.Batch.objects.filter(company=c)
               .values("product__name").annotate(t=Sum("quantity")).order_by("-t")[:5])
    prod_max = max([float(r["t"] or 0) for r in by_prod] or [1])
    by_status = list(m.ProductionOrder.objects.filter(company=c).values("status").annotate(n=Count("id")))

    alerts = []
    for rm in m.RawMaterial.objects.filter(company=c, stock_qty__lte=F("reorder_level"))[:5]:
        alerts.append({"icon": "box", "level": "danger",
                       "text": f"Low stock: {rm.name} ({rm.stock_qty} {rm.unit})",
                       "time": f"Reorder level {rm.reorder_level} {rm.unit}"})
    for mc in m.Machine.objects.filter(company=c, status="down")[:4]:
        alerts.append({"icon": "gear", "level": "danger",
                       "text": f"Machine down: {mc.name}", "time": mc.work_center.name if mc.work_center else ""})
    for o in m.ProductionOrder.objects.filter(company=c, status="qc")[:4]:
        alerts.append({"icon": "shield", "level": "warn",
                       "text": f"Order {o.order_no} awaiting QC", "time": o.product.name})

    def el(entity):
        return reverse("manufacturing_entity_list", kwargs={"company_slug": c.slug, "entity": entity})

    cfg = {
        "title": "Manufacturing Dashboard", "subtitle": "Manufacturing Management",
        "kpis": [
            D.kpi("Active Orders", f"{active_orders}", "gear", "#3b82f6", "released / in progress"),
            D.kpi("Output This Month", f"{out_monthly[-1] if out_monthly else 0:,.0f}", "package", "#22c55e",
                  "units produced", delta=out_delta, delta_dir=out_dir, spark=out_monthly),
            D.kpi("QC Pass Rate", f"{qc_rate}%", "shield", "#f59e0b",
                  f"{qc_pass}/{qc_total} checks · 90d"),
            D.kpi("Materials Low Stock", f"{low_stock}", "box", "#ef4444", "at or below reorder"),
        ],
        "line": {"title": "Production Orders (6 months)", "subtitle": "Orders started per month",
                 "labels": [l for _, _, l in months], "label": "Orders",
                 "data": order_counts, "color": "#a855f7"},
        "donut": {"title": "Orders by Status", "subtitle": "Current pipeline",
                  "labels": [dict(m.ProductionOrder.STATUS).get(r["status"], r["status"]) for r in by_status],
                  "data": [r["n"] for r in by_status]},
        "alerts": alerts,
        "actions": [
            {"label": "New Prod. Order", "icon": "plus", "url": el("production-orders")},
            {"label": "New Plan", "icon": "calendar", "url": el("plans")},
            {"label": "Issue Material", "icon": "box", "url": el("material-issues")},
            {"label": "QC Check", "icon": "shield", "url": el("quality-checks")},
            {"label": "New Batch", "icon": "package", "url": el("batches")},
            {"label": "Maintenance", "icon": "wrench", "url": el("maintenance")},
        ],
        "tables": [
            {"title": "Recent Production Orders", "icon": "gear", "url": el("production-orders"),
             "headers": ["Order No", "Product", "Qty", "Due", "Status"],
             "rows": [[o.order_no, o.product.name, f"{o.quantity:,.0f}",
                       o.due_date.strftime("%b %d") if o.due_date else "—", o.get_status_display()]
                      for o in m.ProductionOrder.objects.filter(company=c).order_by("-order_date")[:6]]},
            {"title": "Raw Material Stock", "icon": "box", "url": el("raw-materials"),
             "headers": ["Material", "Stock", "Reorder Level", "Unit"],
             "rows": [[r.name, f"{r.stock_qty:,.1f}", f"{r.reorder_level:,.1f}", r.unit]
                      for r in m.RawMaterial.objects.filter(company=c).order_by("stock_qty")[:6]]},
        ],
        "bars": [
            {"title": "Output by Product", "subtitle": "Total units produced (batches)",
             "icon": "package",
             "rows": [{"label": r["product__name"], "value": f"{r['t']:,.0f}",
                       "pct": round(float(r["t"] or 0) / prod_max * 100)}
                      for r in by_prod]},
        ],
    }
    return D.render_module_dashboard(request, c, cfg)
