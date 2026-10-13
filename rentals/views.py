"""Rental views: module dashboard (CRUD served by core.crud)."""
from datetime import timedelta

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
    today = timezone.now().date()
    months = D.last_n_months(6)

    units = m.Unit.objects.filter(company=c)
    occupied = units.filter(status="occupied").count()
    total_units = units.count() or 1
    occupancy = round(occupied / total_units * 100)
    due_month = m.RentSchedule.objects.filter(
        company=c, due_date__year=today.year, due_date__month=today.month,
        status__in=["pending", "overdue"]).aggregate(t=Sum("amount"))["t"] or 0
    overdue = m.RentSchedule.objects.filter(company=c, status="overdue").aggregate(t=Sum("amount"))["t"] or 0
    open_maint = m.MaintenanceRequest.objects.filter(company=c, status__in=["open", "in_progress"]).count()

    collected = []
    for y, mo, _lbl in months:
        collected.append(float(m.RentPayment.objects.filter(
            company=c, payment_date__year=y, payment_date__month=mo
        ).aggregate(t=Sum("amount"))["t"] or 0))
    by_status = list(units.values("status").annotate(n=Count("id")))

    # collection rate: billed vs collected (last 3 months)
    billed_3m = float(m.RentInvoice.objects.filter(
        company=c, issue_date__gte=today - timedelta(days=90)).aggregate(t=Sum("amount"))["t"] or 0)
    coll_3m = float(m.RentPayment.objects.filter(
        company=c, payment_date__gte=today - timedelta(days=90)).aggregate(t=Sum("amount"))["t"] or 0)
    coll_rate = round(coll_3m / billed_3m * 100) if billed_3m else 0
    coll_delta, coll_dir = D.pct_delta(collected[-1] if len(collected) > 1 else 0,
                                       collected[-2] if len(collected) > 1 else 0)
    # revenue by property
    by_prop = (m.RentPayment.objects.filter(company=c)
               .values("invoice__lease__unit__building__property__name")
               .annotate(t=Sum("amount")).order_by("-t")[:5])
    prop_max = max([float(r["t"] or 0) for r in by_prop] or [1])

    alerts = []
    for rs in m.RentSchedule.objects.filter(company=c, status="overdue").order_by("due_date")[:4]:
        alerts.append({"icon": "receipt", "level": "danger",
                       "text": f"Overdue rent: {rs.lease.lease_no} ({rs.amount:,.0f})",
                       "time": f"Due {rs.due_date:%b %d}"})
    for ls in m.Lease.objects.filter(company=c, status="active",
                                      end_date__lte=today + timedelta(days=30),
                                      end_date__gte=today)[:4]:
        alerts.append({"icon": "clipboard", "level": "warn",
                       "text": f"Lease {ls.lease_no} expires {ls.end_date:%b %d}",
                       "time": f"{ls.tenant.name} · Unit {ls.unit.unit_no}"})
    for mr in m.MaintenanceRequest.objects.filter(company=c, priority="urgent",
                                                  status__in=["open", "in_progress"])[:4]:
        alerts.append({"icon": "wrench", "level": "danger",
                       "text": f"Urgent maintenance: {mr.request_no}",
                       "time": f"Unit {mr.unit.unit_no} · {mr.category}"})

    def el(entity):
        return reverse("rentals_entity_list", kwargs={"company_slug": c.slug, "entity": entity})

    cfg = {
        "title": "Rental Dashboard", "subtitle": "Building & Property Rental",
        "kpis": [
            D.kpi("Occupancy", f"{occupancy}%", "building", "#3b82f6", f"{occupied}/{total_units} units"),
            D.kpi("Collection Rate", f"{coll_rate}%", "bank", "#22c55e",
                  f"{coll_3m:,.0f} / {billed_3m:,.0f} · 90d"),
            D.kpi("Rent Collected (Mo)", f"{collected[-1] if collected else 0:,.0f}", "receipt", "#f59e0b",
                  "this month", delta=coll_delta, delta_dir=coll_dir, spark=collected),
            D.kpi("Overdue Rent", f"{overdue:,.0f}", "wallet", "#ef4444", "needs collection"),
        ],
        "line": {"title": "Rent Collected (6 months)", "subtitle": "Payments received per month",
                 "labels": [l for _, _, l in months], "label": "Collected",
                 "data": collected, "color": "#ff7a18"},
        "donut": {"title": "Units by Status", "subtitle": "Portfolio overview",
                  "labels": [dict(m.Unit._meta.get_field("status").choices).get(r["status"], r["status"])
                             for r in by_status],
                  "data": [r["n"] for r in by_status]},
        "alerts": alerts,
        "actions": [
            {"label": "New Lease", "icon": "plus", "url": el("leases")},
            {"label": "New Tenant", "icon": "users", "url": el("tenants")},
            {"label": "New Invoice", "icon": "receipt", "url": el("rent-invoices")},
            {"label": "Record Payment", "icon": "bank", "url": el("rent-payments")},
            {"label": "Maintenance", "icon": "wrench", "url": el("maintenance-requests")},
            {"label": "New Unit", "icon": "home", "url": el("units")},
        ],
        "tables": [
            {"title": "Leases Expiring Soon", "icon": "clipboard", "url": el("leases"),
             "headers": ["Lease", "Tenant", "Unit", "Ends", "Rent"],
             "rows": [[l.lease_no, l.tenant.name, l.unit.unit_no,
                       l.end_date.strftime("%b %d, %Y"), f"{l.monthly_rent:,.0f}"]
                      for l in m.Lease.objects.filter(company=c, status="active").order_by("end_date")[:6]]},
            {"title": "Recent Payments", "icon": "bank", "url": el("rent-payments"),
             "headers": ["Payment", "Invoice", "Date", "Amount", "Method"],
             "rows": [[p.payment_no, p.invoice.invoice_no, f"{p.payment_date:%b %d}",
                       f"{p.amount:,.0f}", p.method or "—"]
                      for p in m.RentPayment.objects.filter(company=c).order_by("-payment_date")[:6]]},
        ],
        "bars": [
            {"title": "Revenue by Property", "subtitle": "Total rent collected",
             "icon": "building",
             "rows": [{"label": r["invoice__lease__unit__building__property__name"] or "—",
                       "value": f"{r['t']:,.0f}",
                       "pct": round(float(r["t"] or 0) / prop_max * 100)}
                      for r in by_prop]},
        ],
    }
    return D.render_module_dashboard(request, c, cfg)
