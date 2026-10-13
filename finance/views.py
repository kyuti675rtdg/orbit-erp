"""Finance & Accounting dashboard + financial statements."""
from datetime import timedelta

from django.db.models import Sum
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from core import dashboards as D
from core.modules import build_sidebar
from core.views import company_access_required
from shared.models import Bill, GLAccount, JournalEntry

from . import models as m


def _el(company, url_name, entity=None):
    kw = {"company_slug": company.slug}
    if entity:
        kw["entity"] = entity
    return reverse(url_name, kwargs=kw)


def account_balance(company, account, up_to=None):
    """Net balance of a GL account from opening + journal lines."""
    lines = m.JournalLine.objects.filter(company=company, account=account)
    if up_to:
        lines = lines.filter(entry__date__lte=up_to)
    agg = lines.aggregate(d=Sum("debit"), c=Sum("credit"))
    d, c = float(agg["d"] or 0), float(agg["c"] or 0)
    if account.account_type in ("asset", "expense"):
        return float(account.opening_balance) + d - c
    return float(account.opening_balance) + c - d


@company_access_required
def dashboard(request, company_slug):
    c = request.company
    today = timezone.now().date()

    cash = sum(float(a.opening_balance) + sum(float(t.amount) for t in a.transactions.all())
               for a in m.BankAccount.objects.filter(company=c, is_active=True))
    ar = m.ARInvoice.objects.filter(company=c).exclude(status="paid").aggregate(
        t=Sum("amount"), p=Sum("paid_amount"))
    ar_out = float(ar["t"] or 0) - float(ar["p"] or 0)
    ap = Bill.objects.filter(company=c).exclude(status="paid").aggregate(
        t=Sum("amount"), p=Sum("paid_amount"))
    ap_out = float(ap["t"] or 0) - float(ap["p"] or 0)

    first = today.replace(day=1)
    rev_lines = m.JournalLine.objects.filter(
        company=c, account__account_type="revenue", entry__date__gte=first)
    exp_lines = m.JournalLine.objects.filter(
        company=c, account__account_type="expense", entry__date__gte=first)
    rev_mtd = rev_lines.aggregate(t=Sum("credit"))["t"] or 0
    exp_mtd = exp_lines.aggregate(t=Sum("debit"))["t"] or 0

    months = D.last_n_months(6)
    rev_series, exp_series = [], []
    for y, mo, _lbl in months:
        r = m.JournalLine.objects.filter(
            company=c, account__account_type="revenue",
            entry__date__year=y, entry__date__month=mo
        ).aggregate(t=Sum("credit"))["t"] or 0
        e = m.JournalLine.objects.filter(
            company=c, account__account_type="expense",
            entry__date__year=y, entry__date__month=mo
        ).aggregate(t=Sum("debit"))["t"] or 0
        rev_series.append(float(r)); exp_series.append(float(e))
    d_txt, d_dir = D.pct_delta(rev_mtd, rev_series[-2] if len(rev_series) > 1 else 0)

    overdue_bills = Bill.objects.filter(company=c, due_date__lt=today).exclude(status="paid").count()
    overdue_ar = m.ARInvoice.objects.filter(company=c, due_date__lt=today).exclude(status="paid").count()

    kpis = [
        D.kpi("Cash Position", f"{cash:,.0f}", "bank", "green", sub="bank balances"),
        D.kpi("Receivables", f"{ar_out:,.0f}", "receipt", "blue",
              sub=f"{overdue_ar} overdue invoices", spark=rev_series),
        D.kpi("Payables", f"{ap_out:,.0f}", "receipt", "orange",
              sub=f"{overdue_bills} overdue bills"),
        D.kpi("Revenue (MTD)", f"{float(rev_mtd):,.0f}", "chart", "purple",
              sub="month to date", delta=d_txt, delta_dir=d_dir, spark=rev_series),
        D.kpi("Expenses (MTD)", f"{float(exp_mtd):,.0f}", "wallet", "orange",
              sub="month to date", spark=exp_series),
        D.kpi("Net (MTD)", f"{float(rev_mtd) - float(exp_mtd):,.0f}", "chart", "green",
              sub="revenue − expenses"),
    ]
    cfg = {
        "title": "Finance Dashboard", "subtitle": "Financial KPIs & accounting health",
        "kpis": kpis,
        "line": {"labels": [lbl for _, _, lbl in months], "label": "Revenue",
                 "data": rev_series, "color": "#22c55e"},
        "bars": [{"labels": [lbl for _, _, lbl in months], "label": "Expenses",
                  "data": exp_series, "color": "#ff7a18"}],
        "tables": [
            {"title": "Overdue Bills", "headers": ["Bill", "Vendor", "Due", "Balance"],
             "rows": [[b.bill_no, b.vendor_name, str(b.due_date or "—"),
                       f"{float(b.amount) - float(b.paid_amount):,.0f}"]
                      for b in Bill.objects.filter(company=c, due_date__lt=today)
                      .exclude(status="paid")[:8]],
             "link": _el(c, "finance_entity_list", "bills"), "link_label": "All bills"},
            {"title": "Uncollected Receivables", "headers": ["Invoice", "Customer", "Due", "Balance"],
             "rows": [[i.invoice_no, i.customer_name, str(i.due_date or "—"),
                       f"{float(i.amount) - float(i.paid_amount):,.0f}"]
                      for i in m.ARInvoice.objects.filter(company=c).exclude(status="paid")[:8]],
             "link": _el(c, "finance_entity_list", "ar-invoices"), "link_label": "All AR"},
            {"title": "Recent Journal Entries", "headers": ["Date", "Reference", "Account", "Dr / Cr"],
             "rows": [[str(j.date), j.reference, j.account.code,
                       f"{float(j.debit):,.0f} / {float(j.credit):,.0f}"]
                      for j in JournalEntry.objects.filter(company=c).order_by("-date")[:8]],
             "link": _el(c, "finance_entity_list", "journal"), "link_label": "Journal"},
        ],
        "alerts": [
            {"level": "warning",
             "text": f"{overdue_bills} overdue bills · {overdue_ar} overdue receivables",
             "link": _el(c, "finance_entity_list", "bills")},
        ] if (overdue_bills or overdue_ar) else [],
        "actions": [
            {"label": "New Journal Entry", "icon": "plus", "url": _el(c, "finance_entity_create", "journal")},
            {"label": "New Bill", "icon": "plus", "url": _el(c, "finance_entity_create", "bills")},
            {"label": "New AR Invoice", "icon": "plus", "url": _el(c, "finance_entity_create", "ar-invoices")},
            {"label": "Financial Statements", "icon": "file", "url": _el(c, "finance_statements")},
        ],
    }
    return D.render_module_dashboard(request, c, cfg)


@company_access_required
def statements(request, company_slug):
    """Balance Sheet, Income Statement, Cash Flow from real GL data."""
    c = request.company
    today = timezone.now().date()
    year_start = today.replace(month=1, day=1)

    accounts = list(GLAccount.objects.filter(company=c, is_active=True).order_by("code"))
    rows = []
    totals = {"asset": 0, "liability": 0, "equity": 0, "revenue": 0, "expense": 0}
    for a in accounts:
        bal = account_balance(c, a)
        ytd_lines = m.JournalLine.objects.filter(
            company=c, account=a, entry__date__gte=year_start)
        agg = ytd_lines.aggregate(d=Sum("debit"), cr=Sum("credit"))
        if a.account_type in ("revenue", "equity", "liability"):
            ytd = float(agg["cr"] or 0) - float(agg["d"] or 0)
        else:
            ytd = float(agg["d"] or 0) - float(agg["cr"] or 0)
        rows.append({"code": a.code, "name": a.name, "type": a.account_type,
                     "balance": bal, "ytd": ytd})
        totals[a.account_type] += bal

    net_income = totals["revenue"] - totals["expense"]
    # simplified cash flow: operating = net income; investing/financing from bank tx
    bank_in = m.BankTransaction.objects.filter(
        company=c, date__gte=year_start, amount__gt=0).aggregate(t=Sum("amount"))["t"] or 0
    bank_out = m.BankTransaction.objects.filter(
        company=c, date__gte=year_start, amount__lt=0).aggregate(t=Sum("amount"))["t"] or 0

    ctx = {
        "company": c, "membership": request.membership,
        "sidebar": build_sidebar(request),
        "rows": rows, "totals": totals, "net_income": net_income,
        "bank_in": float(bank_in), "bank_out": float(bank_out),
        "net_cash": float(bank_in) + float(bank_out),
        "today": today, "year_start": year_start,
    }
    return render(request, "finance/statements.html", ctx)
