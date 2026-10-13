"""Executive Management & BI: consolidated dashboards, drill-down analytics,
budget vs actual, custom report builder."""
import csv
from datetime import date

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from core import dashboards as D
from core.models import Company, Membership
from core.modules import build_sidebar
from core.views import company_access_required
from shared.models import Bill, Employee, LeaveRequest

from . import models as m


def _el(company, url_name, entity=None):
    kw = {"company_slug": company.slug}
    if entity:
        kw["entity"] = entity
    return reverse(url_name, kwargs=kw)


def _companies(user):
    return Company.objects.filter(
        memberships__user=user, memberships__is_active=True).distinct()


def _fin_totals(company, since):
    from finance.models import JournalLine
    rev = JournalLine.objects.filter(
        company=company, account__account_type="revenue",
        entry__date__gte=since).aggregate(t=Sum("credit"))["t"] or 0
    exp = JournalLine.objects.filter(
        company=company, account__account_type="expense",
        entry__date__gte=since).aggregate(t=Sum("debit"))["t"] or 0
    return float(rev), float(exp)


@company_access_required
def dashboard(request, company_slug):
    c = request.company
    today = timezone.now().date()
    year_start = today.replace(month=1, day=1)
    months = D.last_n_months(6)

    companies = list(_companies(request.user))
    per_company = []
    tot_rev = tot_exp = tot_hc = 0
    rev_series = [0.0] * 6
    exp_series = [0.0] * 6
    for co in companies:
        rev, exp = _fin_totals(co, year_start)
        hc = Employee.objects.filter(company=co, status="active").count()
        tot_rev += rev; tot_exp += exp; tot_hc += hc
        per_company.append({"name": co.name, "slug": co.slug, "industry": co.get_industry_key_display(),
                            "revenue": rev, "expenses": exp, "net": rev - exp, "headcount": hc})
        for i, (y, mo, _lbl) in enumerate(months):
            from finance.models import JournalLine
            r = JournalLine.objects.filter(
                company=co, account__account_type="revenue",
                entry__date__year=y, entry__date__month=mo
            ).aggregate(t=Sum("credit"))["t"] or 0
            e = JournalLine.objects.filter(
                company=co, account__account_type="expense",
                entry__date__year=y, entry__date__month=mo
            ).aggregate(t=Sum("debit"))["t"] or 0
            rev_series[i] += float(r); exp_series[i] += float(e)

    # pending approvals across companies
    pending = []
    for co in companies:
        n_leave = LeaveRequest.objects.filter(company=co, status="pending").count()
        if n_leave:
            pending.append((co, "Leave requests", n_leave, _el(co, "hr_entity_list", "leave-requests")))
    try:
        from finance.models import ExpenseClaim
        for co in companies:
            n_exp = ExpenseClaim.objects.filter(company=co, status="submitted").count()
            if n_exp:
                pending.append((co, "Expense claims", n_exp, _el(co, "finance_entity_list", "expense-claims")))
    except Exception:
        pass
    pending_total = sum(p[2] for p in pending)

    # sector comparison: revenue proxy per industry from sector invoices
    sector_rev = []
    try:
        from exports.models import ExportInvoice
        v = sum(float(x.amount or 0) for x in ExportInvoice.objects.filter(
            company__in=companies, invoice_date__gte=year_start))
        if v: sector_rev.append(("Export", v))
    except Exception:
        pass
    try:
        from rentals.models import RentInvoice
        v = sum(float(x.amount or 0) for x in RentInvoice.objects.filter(
            company__in=companies, issue_date__gte=year_start))
        if v: sector_rev.append(("Rental", v))
    except Exception:
        pass
    try:
        from fleet.models import Invoice as FleetInvoice
        v = sum(float(x.total or 0) for x in FleetInvoice.objects.filter(
            company__in=companies, issued_date__gte=year_start).exclude(status="cancelled"))
        if v: sector_rev.append(("Transport", v))
    except Exception:
        pass
    try:
        from imports.models import PurchaseOrder
        v = sum(float(x.total_amount or 0) for x in PurchaseOrder.objects.filter(
            company__in=companies, order_date__gte=year_start).exclude(status="cancelled"))
        if v: sector_rev.append(("Import spend", v))
    except Exception:
        pass

    kpis = [
        D.kpi("Consolidated Revenue", f"{tot_rev:,.0f}", "chart", "green",
              sub=f"YTD · {len(companies)} companies", spark=rev_series),
        D.kpi("Consolidated Expenses", f"{tot_exp:,.0f}", "wallet", "orange",
              sub="YTD", spark=exp_series),
        D.kpi("Net Profit", f"{tot_rev - tot_exp:,.0f}", "chart", "purple", sub="YTD"),
        D.kpi("Total Headcount", f"{tot_hc}", "users", "blue", sub="active employees"),
        D.kpi("Pending Approvals", f"{pending_total}", "shield", "orange",
              sub="across companies"),
        D.kpi("Companies", f"{len(companies)}", "building", "green", sub="under management"),
    ]
    cfg = {
        "title": "Executive Dashboard",
        "subtitle": f"Consolidated view · {c.name} in focus",
        "kpis": kpis,
        "line": {"labels": [lbl for _, _, lbl in months], "label": "Revenue",
                 "data": rev_series, "color": "#22c55e"},
        "bars": [{"labels": [lbl for _, _, lbl in months], "label": "Expenses",
                  "data": exp_series, "color": "#ff7a18"}],
        "donut": ({"labels": [s[0] for s in sector_rev], "data": [s[1] for s in sector_rev],
                   "colors": ["#ff7a18", "#3b82f6", "#22c55e", "#a855f7"]}
                  if sector_rev else None),
        "tables": [
            {"title": "Company Performance (YTD)", "headers": ["Company", "Sector", "Revenue", "Expenses", "Net", "Staff"],
             "rows": [[p["name"], p["industry"], f"{p['revenue']:,.0f}", f"{p['expenses']:,.0f}",
                       f"{p['net']:,.0f}", p["headcount"]] for p in per_company],
             "link": reverse("company_hub"), "link_label": "All companies"},
            {"title": "Pending Approvals", "headers": ["Company", "Type", "Count"],
             "rows": [[co.name, typ, n] for co, typ, n, _ in pending],
             "link": None, "link_label": ""},
        ],
        "alerts": [
            {"level": "warning", "text": f"{pending_total} items awaiting management approval",
             "link": reverse("company_hub")},
        ] if pending_total else [],
        "actions": [
            {"label": "Custom Reports", "icon": "chart",
             "url": _el(c, "exec_entity_list", "report-definitions")},
            {"label": "Budget vs Actual", "icon": "file", "url": _el(c, "exec_budget")},
            {"label": "Financial Statements", "icon": "file", "url": _el(c, "finance_statements")},
        ],
    }
    # attach drill-down links to pending rows
    return D.render_module_dashboard(request, c, cfg)


@company_access_required
def budget_vs_actual(request, company_slug):
    c = request.company
    from finance.models import Budget
    budgets = Budget.objects.filter(company=c).prefetch_related("lines__account")
    rows = []
    for b in budgets:
        for line in b.lines.all():
            actual = line.actual
            rows.append({"budget": b.name, "account": f"{line.account.code} — {line.account.name}",
                         "budgeted": float(line.budgeted), "actual": actual,
                         "variance": float(line.budgeted) - actual})
    ctx = {
        "company": c, "membership": request.membership, "sidebar": build_sidebar(request),
        "rows": rows, "budgets": budgets,
    }
    return render(request, "executive/budget.html", ctx)


# ------------------------------------------------------------ report builder
def _dataset(company, key):
    from finance.models import ARInvoice, ExpenseClaim, JournalEntry
    from hr.models import Payslip
    from shared.models import Employee, LeaveRequest, Bill
    mapping = {
        "hr.employees": (Employee.objects.filter(company=company),
                         ["employee_id", "name", "department__name", "position", "status"]),
        "hr.leave": (LeaveRequest.objects.filter(company=company),
                     ["employee__name", "leave_type", "start_date", "end_date", "status"]),
        "hr.payslips": (Payslip.objects.filter(company=company),
                        ["employee__name", "period", "basic", "net", "status"]),
        "finance.bills": (Bill.objects.filter(company=company),
                          ["bill_no", "vendor_name", "bill_date", "amount", "status"]),
        "finance.ar": (ARInvoice.objects.filter(company=company),
                       ["invoice_no", "customer_name", "invoice_date", "amount", "status"]),
        "finance.journal": (JournalEntry.objects.filter(company=company),
                            ["date", "reference", "account__code", "debit", "credit"]),
        "finance.expenses": (ExpenseClaim.objects.filter(company=company),
                             ["claim_no", "employee__name", "claim_date", "amount", "status"]),
    }
    try:
        from imports.models import PurchaseOrder, Shipment
        mapping["imports.po"] = (PurchaseOrder.objects.filter(company=company),
                                 ["po_number", "supplier__name", "order_date", "total_amount", "status"])
        mapping["imports.shipments"] = (Shipment.objects.filter(company=company),
                                       ["shipment_no", "status", "eta"])
    except Exception:
        pass
    try:
        from exports.models import ExportInvoice, ExportOrder
        mapping["exports.orders"] = (ExportOrder.objects.filter(company=company),
                                     ["order_no", "buyer__name", "order_date", "total_amount", "status"])
        mapping["exports.invoices"] = (ExportInvoice.objects.filter(company=company),
                                       ["invoice_no", "buyer__name", "invoice_date", "amount", "status"])
    except Exception:
        pass
    try:
        from manufacturing.models import ProductionOrder
        mapping["manufacturing.orders"] = (ProductionOrder.objects.filter(company=company),
                                           ["order_no", "product__name", "status"])
    except Exception:
        pass
    try:
        from rentals.models import Lease, RentPayment
        mapping["rentals.leases"] = (Lease.objects.filter(company=company),
                                     ["lease_no", "tenant__name", "status"])
        mapping["rentals.payments"] = (RentPayment.objects.filter(company=company),
                                       ["payment_no", "amount", "payment_date"])
    except Exception:
        pass
    try:
        from fleet.models import Invoice as FleetInvoice, Trip
        mapping["fleet.trips"] = (Trip.objects.filter(company=company),
                                  ["trip_no", "status", "origin", "destination"])
        mapping["fleet.invoices"] = (FleetInvoice.objects.filter(company=company),
                                     ["invoice_no", "customer_name", "total", "status"])
    except Exception:
        pass
    return mapping.get(key)


def _run_dataset(company, definition):
    found = _dataset(company, definition.dataset)
    if not found:
        return [], []
    qs, default_cols = found
    cols = definition.columns or default_cols
    if definition.status_filter:
        qs = qs.filter(status=definition.status_filter)
    from core.crud import resolve
    rows = [[resolve(obj, col) for col in cols] for obj in qs[:500]]
    return cols, rows


@company_access_required
def run_report(request, company_slug, pk):
    definition = get_object_or_404(m.ReportDefinition, company=request.company, pk=pk)
    cols, rows = _run_dataset(request.company, definition)
    definition.schedules.filter(is_active=True).update(last_run=timezone.now())
    ctx = {
        "company": request.company, "membership": request.membership,
        "sidebar": build_sidebar(request), "definition": definition,
        "cols": cols, "rows": rows,
        "csv_url": reverse("exec_report_csv",
                           kwargs={"company_slug": request.company.slug, "pk": pk}),
    }
    return render(request, "executive/report_run.html", ctx)


@company_access_required
def report_csv(request, company_slug, pk):
    definition = get_object_or_404(m.ReportDefinition, company=request.company, pk=pk)
    cols, rows = _run_dataset(request.company, definition)
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="report-{pk}.csv"'
    w = csv.writer(resp)
    w.writerow(cols)
    w.writerows(rows)
    return resp
