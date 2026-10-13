"""Export Management views: module dashboard (CRUD served by core.crud)."""
from django.db.models import Count, Sum
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
    months = D.last_n_months(6)

    open_orders = m.ExportOrder.objects.filter(company=c).exclude(status__in=["delivered", "cancelled"])
    open_val = open_orders.aggregate(t=Sum("total_amount"))["t"] or 0
    transit = m.Shipment.objects.filter(company=c, status="in_transit").count()
    recv = m.ExportInvoice.objects.filter(company=c).exclude(status="paid").aggregate(
        a=Sum("amount"), p=Sum("paid_amount"))
    receivables = (recv["a"] or 0) - (recv["p"] or 0)
    qc_pending = m.QualityInspection.objects.filter(company=c, result="conditional").count() \
        + m.ExportOrder.objects.filter(company=c, status="preparing").count()

    order_monthly = D.monthly_sums(m.ExportOrder.objects.filter(company=c),
                                   "order_date", "total_amount", months)
    ord_delta, ord_dir = D.pct_delta(order_monthly[-1] if len(order_monthly) > 1 else 0,
                                     order_monthly[-2] if len(order_monthly) > 1 else 0)
    by_status = list(m.ExportOrder.objects.filter(company=c).values("status").annotate(n=Count("id")))

    # receivables aging (unpaid portion by due-date bucket)
    today = timezone.now().date()
    unpaid = m.ExportInvoice.objects.filter(company=c).exclude(status="paid")
    buckets = [("Not due", 0), ("1–30 days", 0), ("31–60 days", 0), ("60+ days", 0)]
    bvals = [0, 0, 0, 0]
    for i in unpaid:
        bal = float(i.amount - i.paid_amount)
        if not i.due_date or i.due_date >= today:
            bvals[0] += bal
        elif (today - i.due_date).days <= 30:
            bvals[1] += bal
        elif (today - i.due_date).days <= 60:
            bvals[2] += bal
        else:
            bvals[3] += bal
    top_buyers = (m.ExportOrder.objects.filter(company=c)
                  .values("buyer__name").annotate(n=Count("id"), t=Sum("total_amount"))
                  .order_by("-t")[:5])
    top_max = max([float(r["t"] or 0) for r in top_buyers] or [1])

    alerts = []
    for o in m.ExportOrder.objects.filter(company=c, status="preparing").order_by("delivery_date")[:4]:
        alerts.append({"icon": "package", "level": "warn",
                       "text": f"Order {o.order_no} preparing — QC pending",
                       "time": f"Deliver by {o.delivery_date:%b %d}" if o.delivery_date else o.buyer.name})
    for i in m.ExportInvoice.objects.filter(company=c).exclude(status="paid").order_by("due_date")[:4]:
        alerts.append({"icon": "receipt", "level": "danger",
                       "text": f"Invoice {i.invoice_no} unpaid ({i.amount - i.paid_amount:,.0f})",
                       "time": f"Due {i.due_date:%b %d}" if i.due_date else i.buyer.name})
    for s in m.Shipment.objects.filter(company=c, status="in_transit").order_by("eta")[:4]:
        alerts.append({"icon": "truck", "level": "info",
                       "text": f"Shipment {s.shipment_no} in transit",
                       "time": f"ETA {s.eta:%b %d} · {s.destination_port}" if s.eta else s.destination_port})

    def el(entity):
        return reverse("exports_entity_list", kwargs={"company_slug": c.slug, "entity": entity})

    cfg = {
        "title": "Export Dashboard", "subtitle": "Export Management",
        "kpis": [
            D.kpi("Open Orders Value", f"{open_val:,.0f}", "package", "#3b82f6",
                  "USD · open orders", delta=ord_delta, delta_dir=ord_dir, spark=order_monthly),
            D.kpi("Shipments In Transit", f"{transit}", "truck", "#22c55e", "on the water"),
            D.kpi("Receivables", f"{receivables:,.0f}", "receipt", "#f59e0b", "unpaid invoices"),
            D.kpi("QC / Prep Pending", f"{qc_pending}", "shield", "#ef4444", "needs attention"),
        ],
        "line": {"title": "Export Orders (6 months)", "subtitle": "Order value per month",
                 "labels": [l for _, _, l in months], "label": "Order value (USD)",
                 "data": order_monthly, "color": "#22c55e"},
        "donut": {"title": "Orders by Status", "subtitle": "Current pipeline",
                  "labels": [dict(m.ExportOrder.STATUS).get(r["status"], r["status"]) for r in by_status],
                  "data": [r["n"] for r in by_status]},
        "alerts": alerts,
        "actions": [
            {"label": "New Order", "icon": "plus", "url": el("orders")},
            {"label": "New Quotation", "icon": "file", "url": el("quotations")},
            {"label": "New Shipment", "icon": "truck", "url": el("shipments")},
            {"label": "New Buyer", "icon": "users", "url": el("buyers")},
            {"label": "New Inspection", "icon": "shield", "url": el("inspections")},
            {"label": "New Invoice", "icon": "receipt", "url": el("invoices")},
        ],
        "tables": [
            {"title": "Recent Export Orders", "icon": "package", "url": el("orders"),
             "headers": ["Order No", "Buyer", "Date", "Total", "Status"],
             "rows": [[o.order_no, o.buyer.name, f"{o.order_date:%b %d}", f"{o.total_amount:,.0f}",
                       o.get_status_display()]
                      for o in m.ExportOrder.objects.filter(company=c).order_by("-order_date")[:6]]},
            {"title": "Recent Invoices", "icon": "receipt", "url": el("invoices"),
             "headers": ["Invoice", "Buyer", "Amount", "Paid", "Status"],
             "rows": [[i.invoice_no, i.buyer.name, f"{i.amount:,.0f}", f"{i.paid_amount:,.0f}",
                       i.get_status_display()]
                      for i in m.ExportInvoice.objects.filter(company=c).order_by("-invoice_date")[:6]]},
        ],
        "aging": {
            "title": "Receivables Aging", "subtitle": "Unpaid balance by overdue bucket (USD)",
            "cells": [{"label": lbl, "value": f"{v:,.0f}"} for (lbl, _), v in zip(buckets, bvals)],
        },
        "bars": [
            {"title": "Top Buyers by Order Value", "subtitle": "Revenue concentration",
             "icon": "users",
             "rows": [{"label": r["buyer__name"], "value": f"{r['t']:,.0f}",
                       "pct": round(float(r["t"] or 0) / top_max * 100)}
                      for r in top_buyers]},
        ],
    }
    return D.render_module_dashboard(request, c, cfg)
