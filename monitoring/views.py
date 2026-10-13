"""Business Monitoring views: consolidated + per-company real-time dashboards.

Gated to management roles (owner / admin / manager) — this is the CEO's
oversight tool. All KPIs come from the analytics engine, computed live
from ERP records.
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Company, Membership

from .analytics import MANAGEMENT_ROLES, company_metrics, consolidated_metrics


def management_required(view_func):
    """User must hold a management role in at least one active company."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        has = Membership.objects.filter(
            user=request.user, is_active=True, company__is_active=True,
            role__in=MANAGEMENT_ROLES).exists()
        if not has:
            messages.error(request, "Business Monitoring is available to management only.")
            return redirect("company_hub")
        return view_func(request, *args, **kwargs)

    return _wrapped


def _my_companies(user):
    return list(Company.objects.filter(
        memberships__user=user, memberships__is_active=True,
        memberships__role__in=MANAGEMENT_ROLES,
        is_active=True).distinct().order_by("name"))


@management_required
def overview(request):
    companies = _my_companies(request.user)
    data = consolidated_metrics(companies)
    series = data["series"]
    chart_max = max([max(s["revenue"], s["expenses"]) for s in series] + [1])
    ctx = {
        "companies": companies,
        "totals": data["totals"],
        "per_company": data["per_company"],
        "series": series,
        "chart_max": chart_max,
        "company_count": data["company_count"],
        "active_nav": "monitoring",
    }
    return render(request, "monitoring/overview.html", ctx)


@management_required
def company_view(request, company_slug):
    company = get_object_or_404(Company, slug=company_slug, is_active=True)
    if not Membership.objects.filter(
            user=request.user, company=company, is_active=True,
            role__in=MANAGEMENT_ROLES).exists():
        messages.error(request, "You don't have management access to that company.")
        return redirect("monitoring_overview")
    m = company_metrics(company)
    # sibling companies for the switcher
    siblings = _my_companies(request.user)
    series = m["monthly"]
    chart_max = max([max(s["revenue"], s["expenses"]) for s in series] + [1])
    ctx = {
        "m": m, "company": company, "siblings": siblings,
        "series": series, "chart_max": chart_max,
        "active_nav": "monitoring",
    }
    return render(request, "monitoring/company.html", ctx)
