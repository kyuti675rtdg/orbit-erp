from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CompanyForm
from .models import Company, Membership


# ---------------------------------------------------------------- helpers
def company_access_required(view_func):
    """Resolve company from URL slug; require an active membership."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, company_slug, *args, **kwargs):
        company = get_object_or_404(Company, slug=company_slug, is_active=True)
        try:
            membership = Membership.objects.select_related("company", "user").get(
                user=request.user, company=company, is_active=True
            )
        except Membership.DoesNotExist:
            messages.error(request, "You do not have access to that company workspace.")
            return redirect("company_hub")
        request.company = company
        request.membership = membership
        request.session["active_company_id"] = company.id
        return view_func(request, company_slug, *args, **kwargs)

    return _wrapped


def role_required(*roles):
    """Require one of the given company roles (use after company_access_required)."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, company_slug, *args, **kwargs):
            if request.membership.role not in roles:
                messages.error(request, "Your role does not permit this action.")
                return redirect("workspace", company_slug=company_slug)
            return view_func(request, company_slug, *args, **kwargs)

        return _wrapped

    return decorator


editor_required = role_required(*settings.EDITOR_ROLES)
finance_required = role_required(*settings.FINANCE_ROLES)


# ---------------------------------------------------------------- auth
class LoginView(auth_views.LoginView):
    template_name = "auth/login.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        if not self.request.POST.get("remember"):
            self.request.session.set_expiry(0)  # expire on browser close
        return resp


def signup(request):
    if request.user.is_authenticated:
        return redirect("company_hub")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome, {user.username}! Register your first company to begin.")
        return redirect("company_create")
    return render(request, "auth/signup.html", {"form": form})


# ---------------------------------------------------------------- company hub
@login_required
def company_hub(request):
    memberships = (
        Membership.objects.select_related("company")
        .filter(user=request.user, is_active=True, company__is_active=True)
        .order_by("company__name")
    )
    return render(request, "core/company_hub.html", {"memberships": memberships})


@login_required
def company_create(request):
    form = CompanyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        company = form.save()
        Membership.objects.create(user=request.user, company=company, role=settings.ROLE_OWNER)
        request.session["active_company_id"] = company.id
        messages.success(request, f"Company “{company.name}” registered. Welcome to your ERP workspace.")
        return redirect("workspace", company_slug=company.slug)
    return render(request, "core/company_form.html", {"form": form})


@company_access_required
def workspace(request, company_slug):
    """ERP workspace home: module launcher + cross-module KPIs."""
    company = request.company
    from fleet.models import DeliveryOrder, Invoice, Trip, Vehicle

    now = timezone.now()
    ctx = {
        "company": company,
        "membership": request.membership,
        "kpis": {
            "vehicles": Vehicle.objects.filter(company=company, status="active").count(),
            "active_trips": Trip.objects.filter(
                company=company, status__in=["planned", "dispatched", "en_route"]
            ).count(),
            "deliveries_month": DeliveryOrder.objects.filter(
                company=company, created_at__year=now.year, created_at__month=now.month
            ).count(),
            "receivable": Invoice.objects.filter(
                company=company, status__in=["sent", "overdue"]
            ).aggregate(t=Sum("total"))["t"]
            or 0,
        },
        "recent_trips": Trip.objects.filter(company=company)
        .select_related("route", "vehicle", "driver")
        .order_by("-created_at")[:6],
        "modules": [
            {
                "name": "Transport & Fleet",
                "desc": "Vehicles, drivers, routes, trips, GPS tracking, fuel, maintenance, delivery, billing.",
                "url": "fleet_dashboard",
                "icon": "truck",
                "accent": "orange",
            },
            {
                "name": "Finance & Billing",
                "desc": "Transport invoices, receivables, payments, expenses and settlements.",
                "url": "fleet_invoices",
                "icon": "receipt",
                "accent": "green",
            },
            {
                "name": "HR & Payroll",
                "desc": "Driver and employee records, attendance, monthly payroll.",
                "url": "fleet_employees",
                "icon": "users",
                "accent": "blue",
            },
            {
                "name": "Reports & BI",
                "desc": "Fleet utilization, fuel analytics, trip profitability, maintenance costs.",
                "url": "fleet_reports",
                "icon": "chart",
                "accent": "purple",
            },
        ],
    }
    return render(request, "core/workspace.html", ctx)
