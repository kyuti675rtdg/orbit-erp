"""Business Monitoring analytics engine.

Every KPI is computed live from ERP records — GL journal lines, AR/AP,
tax returns and bank transactions. No static or hardcoded figures.
"""
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum

MANAGEMENT_ROLES = ["owner", "admin", "manager"]


def _f(x):
    return float(x or 0)


def _month_starts(n=6):
    """First day of each of the last n months, oldest first."""
    today = date.today()
    out = []
    y, m = today.year, today.month
    for _ in range(n):
        out.append(date(y, m, 1))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(out))


def company_metrics(company):
    """Real-time business metrics for one company, from ERP records."""
    from finance.models import (ARInvoice, BankAccount, BankTransaction,
                                JournalLine, TaxReturn)
    from shared.models import Bill

    today = date.today()
    year_start = today.replace(month=1, day=1)

    # ---- Revenue & expenses from the GL (year to date)
    rev_ytd = _f(JournalLine.objects.filter(
        company=company, account__account_type="revenue",
        entry__date__gte=year_start).aggregate(t=Sum("credit"))["t"])
    exp_ytd = _f(JournalLine.objects.filter(
        company=company, account__account_type="expense",
        entry__date__gte=year_start).aggregate(t=Sum("debit"))["t"])
    profit_ytd = rev_ytd - exp_ytd
    margin = (profit_ytd / rev_ytd * 100) if rev_ytd else 0.0

    # ---- Monthly revenue/expense series (last 6 months)
    starts = _month_starts(6)
    monthly = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else date(today.year + (1 if today.month == 12 else 0),
                                                           1 if today.month == 12 else today.month + 1, 1)
        rev = _f(JournalLine.objects.filter(
            company=company, account__account_type="revenue",
            entry__date__gte=s, entry__date__lt=e).aggregate(t=Sum("credit"))["t"])
        exp = _f(JournalLine.objects.filter(
            company=company, account__account_type="expense",
            entry__date__gte=s, entry__date__lt=e).aggregate(t=Sum("debit"))["t"])
        monthly.append({"label": s.strftime("%b"), "revenue": rev, "expenses": exp,
                        "profit": rev - exp})

    # ---- Taxes: paid vs outstanding
    taxes_paid = _f(TaxReturn.objects.filter(
        company=company, status="paid").aggregate(t=Sum("tax_due"))["t"])
    taxes_outstanding = _f(TaxReturn.objects.filter(
        company=company, status__in=["draft", "filed"]).aggregate(t=Sum("tax_due"))["t"])
    tax_returns = TaxReturn.objects.filter(company=company).select_related("tax")

    # ---- Cash position & recent flow (last 30 days)
    accounts = list(BankAccount.objects.filter(company=company, is_active=True))
    cash_position = sum(_f(a.opening_balance) + sum(
        _f(t.amount) for t in a.transactions.all()) for a in accounts)
    inflow_30 = _f(BankTransaction.objects.filter(
        company=company, date__gte=today.replace(day=1),
        amount__gt=0).aggregate(t=Sum("amount"))["t"])
    outflow_30 = _f(BankTransaction.objects.filter(
        company=company, date__gte=today.replace(day=1),
        amount__lt=0).aggregate(t=Sum("amount"))["t"])
    net_flow_30 = inflow_30 + outflow_30  # outflow stored negative

    # ---- Receivables & payables
    ar_open = ARInvoice.objects.filter(
        company=company).exclude(status__in=["paid", "draft"])
    receivables = sum(_f(i.amount) - _f(i.paid_amount) for i in ar_open)
    overdue_receivables = sum(
        _f(i.amount) - _f(i.paid_amount) for i in ar_open
        if i.due_date and i.due_date < today and (_f(i.amount) - _f(i.paid_amount)) > 0)
    ap_open = Bill.objects.filter(company=company).exclude(status="paid")
    payables = sum(_f(b.amount) - _f(b.paid_amount) for b in ap_open)

    # ---- Workforce (context)
    from shared.models import Employee
    headcount = Employee.objects.filter(company=company, status="active").count()

    # ---- Business status: transparent rule-based health score
    score = 100
    reasons = []
    if profit_ytd < 0:
        score -= 30
        reasons.append("Operating at a loss year-to-date")
    elif margin < 10 and rev_ytd > 0:
        score -= 10
        reasons.append("Thin profit margin (<10%)")
    if receivables > 0 and overdue_receivables / receivables > 0.25:
        score -= 15
        reasons.append("Over 25% of receivables overdue")
    if cash_position < 0:
        score -= 20
        reasons.append("Negative cash position")
    if receivables > 0 and payables > receivables * 2:
        score -= 10
        reasons.append("Payables more than 2× receivables")
    if not reasons:
        reasons.append("All key indicators within healthy ranges")
    if score >= 80:
        status = "Excellent"
    elif score >= 60:
        status = "Healthy"
    elif score >= 40:
        status = "Needs Attention"
    else:
        status = "At Risk"

    return {
        "company": company,
        "revenue_ytd": rev_ytd, "expenses_ytd": exp_ytd,
        "profit_ytd": profit_ytd, "margin": margin,
        "monthly": monthly,
        "taxes_paid": taxes_paid, "taxes_outstanding": taxes_outstanding,
        "tax_returns": tax_returns,
        "cash_position": cash_position,
        "inflow_30": inflow_30, "outflow_30": abs(outflow_30),
        "net_flow_30": net_flow_30,
        "receivables": receivables, "overdue_receivables": overdue_receivables,
        "payables": payables, "headcount": headcount,
        "status": status, "score": max(score, 0), "reasons": reasons,
        "computed_at": today,
    }


def consolidated_metrics(companies):
    """Aggregate metrics across companies + per-company comparison rows."""
    per_company = []
    totals = {"revenue_ytd": 0.0, "expenses_ytd": 0.0, "profit_ytd": 0.0,
              "taxes_paid": 0.0, "taxes_outstanding": 0.0,
              "cash_position": 0.0, "receivables": 0.0, "payables": 0.0,
              "headcount": 0}
    for co in companies:
        m = company_metrics(co)
        per_company.append(m)
        for k in totals:
            totals[k] += m[k]
    totals["margin"] = (totals["profit_ytd"] / totals["revenue_ytd"] * 100
                        if totals["revenue_ytd"] else 0.0)
    # consolidated monthly series
    months = [r["label"] for r in per_company[0]["monthly"]] if per_company else []
    series = []
    for i, label in enumerate(months):
        series.append({
            "label": label,
            "revenue": sum(m["monthly"][i]["revenue"] for m in per_company),
            "expenses": sum(m["monthly"][i]["expenses"] for m in per_company),
        })
    per_company.sort(key=lambda m: m["revenue_ytd"], reverse=True)
    return {"per_company": per_company, "totals": totals, "series": series,
            "company_count": len(companies)}
