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
        try:
            from administration.models import LoginSession
            sess = LoginSession.objects.filter(
                user=request.user, company__isnull=True).order_by("-login_at").first()
            if sess:
                sess.company = company
                sess.save(update_fields=["company"])
        except Exception:
            pass
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
def company_dashboard(request, company_slug):
    """Company Dashboard — executive overview for the selected company.

    Flow: Login -> Select Company -> Company Dashboard -> Modules -> Submodules.
    Industry-aware: KPIs, charts, alerts and quick actions adapt to the
    company's industry modules plus the shared HR / Finance modules.
    """
    from core import dashboards as D
    from core.modules import build_sidebar

    company = request.company
    key = company.industry_key or "transport"
    ind_label = dict(
        (("transport", "Transportation & Fleet"), ("import", "Import Management"),
         ("export", "Export Management"), ("manufacturing", "Manufacturing"),
         ("rental", "Building & Property Rental"), ("other", "General Business"))
    ).get(key, "Business")

    from shared.models import Announcement, Bill, Employee, LeaveRequest

    employees = Employee.objects.filter(company=company, status="active").count()
    pending_leave = LeaveRequest.objects.filter(company=company, status="pending").count()
    unpaid_bills = Bill.objects.filter(company=company).exclude(status="paid")
    bills_due = unpaid_bills.aggregate(t=Sum("amount"))["t"] or 0

    kpis, alerts, actions, tables = [], [], [], []
    line = donut = None

    def el(url_name, entity=None):
        from django.urls import reverse
        kw = {"company_slug": company.slug}
        if entity:
            kw["entity"] = entity
        return reverse(url_name, kwargs=kw)

    if key == "transport":
        from fleet.models import Alert, Invoice, Trip, Vehicle
        now = timezone.now()
        months = D.last_n_months(6)
        kpis = [
            D.kpi("Fleet Vehicles", Vehicle.objects.filter(company=company, status="active").count(),
                  "truck", "#ff7a18", "active"),
            D.kpi("Active Trips", Trip.objects.filter(company=company,
                  status__in=["planned", "dispatched", "en_route"]).count(),
                  "trips", "#3b82f6", "in pipeline"),
            D.kpi("Employees", employees, "users", "#22c55e", "active staff"),
            D.kpi("Receivable", f"{Invoice.objects.filter(company=company, status__in=['sent', 'overdue']).aggregate(t=Sum('total'))['t'] or 0:,.0f}",
                  "receipt", "#f59e0b", "open invoices"),
        ]
        rev = [float(Invoice.objects.filter(company=company, issued_date__year=y,
                     issued_date__month=mo).aggregate(t=Sum("total"))["t"] or 0)
               for y, mo, _ in months]
        rev_delta, rev_dir = D.pct_delta(rev[-1] if len(rev) > 1 else 0,
                                         rev[-2] if len(rev) > 1 else 0)
        kpis[3] = D.kpi("Revenue (Mo)", f"{rev[-1] if rev else 0:,.0f}",
                        "receipt", "#f59e0b", "invoiced this month",
                        delta=rev_delta, delta_dir=rev_dir, spark=rev)
        line = {"title": "Revenue (6 months)", "subtitle": "Invoiced transport revenue",
                "labels": [l for _, _, l in months], "label": "Revenue",
                "data": rev, "color": "#ff7a18"}
        by_status = list(Trip.objects.filter(company=company).values("status").annotate(n=Count("id")))
        donut = {"title": "Trips by Status", "subtitle": "Current pipeline",
                 "labels": [r["status"].replace("_", " ").title() for r in by_status],
                 "data": [r["n"] for r in by_status]}
        for a in Alert.objects.filter(company=company, is_resolved=False).order_by("-created_at")[:4]:
            alerts.append({"icon": "bell", "level": "warn", "text": a.title,
                           "time": a.created_at.strftime("%b %d, %H:%M")})
        for i in Invoice.objects.filter(company=company, status="overdue").order_by("due_date")[:3]:
            alerts.append({"icon": "receipt", "level": "danger",
                           "text": f"Invoice {i.invoice_no} overdue ({i.total:,.0f})",
                           "time": f"Due {i.due_date:%b %d}" if i.due_date else ""})
        actions = [
            {"label": "New Trip", "icon": "plus", "url": el("fleet_entity_list", "trips")},
            {"label": "Live Tracking", "icon": "tracking", "url": el("fleet_tracking")},
            {"label": "New Employee", "icon": "users", "url": el("fleet_entity_list", "employees")},
            {"label": "New Invoice", "icon": "receipt", "url": el("fleet_entity_list", "invoices")},
            {"label": "Fuel Log", "icon": "fuel", "url": el("fleet_entity_list", "fuel")},
            {"label": "Reports", "icon": "chart", "url": el("fleet_reports")},
        ]
        tables = [
            {"title": "Recent Trips", "icon": "trips", "url": el("fleet_entity_list", "trips"),
             "headers": ["Trip", "Route", "Vehicle", "Status"],
             "rows": [[t.trip_no, f"{t.route.origin} → {t.route.destination}",
                       t.vehicle.plate_no if t.vehicle else "—",
                       t.get_status_display()]
                      for t in Trip.objects.filter(company=company)
                      .select_related("route", "vehicle").order_by("-created_at")[:6]]},
        ]
    elif key == "import":
        from imports import models as im
        months = D.last_n_months(6)
        po_m = [float(im.PurchaseOrder.objects.filter(
            company=company, order_date__year=y, order_date__month=mo)
            .aggregate(t=Sum("total_amount"))["t"] or 0) for y, mo, _ in months]
        po_d, po_dr = D.pct_delta(po_m[-1] if len(po_m) > 1 else 0, po_m[-2] if len(po_m) > 1 else 0)
        kpis = [
            D.kpi("Pending Requests", im.ImportRequest.objects.filter(
                company=company, status__in=["draft", "submitted"]).count(),
                "clipboard", "#f59e0b", "needs review"),
            D.kpi("PO Value (Mo)", f"{po_m[-1] if po_m else 0:,.0f}",
                  "file", "#3b82f6", "USD · new orders",
                  delta=po_d, delta_dir=po_dr, spark=po_m),
            D.kpi("In Transit", im.Shipment.objects.filter(company=company, status="in_transit").count(),
                  "truck", "#22c55e", "shipments"),
            D.kpi("Employees", employees, "users", "#a855f7", "active staff"),
        ]
        for r in im.ImportRequest.objects.filter(company=company, status="submitted")[:4]:
            alerts.append({"icon": "clipboard", "level": "warn",
                           "text": f"Request {r.request_no} awaiting approval", "time": r.product_description[:60]})
        actions = [
            {"label": "New Request", "icon": "plus", "url": el("imports_entity_list", "import-requests")},
            {"label": "New PO", "icon": "file", "url": el("imports_entity_list", "purchase-orders")},
            {"label": "New Shipment", "icon": "truck", "url": el("imports_entity_list", "shipments")},
            {"label": "Suppliers", "icon": "users", "url": el("imports_entity_list", "suppliers")},
            {"label": "Customs", "icon": "shield", "url": el("imports_entity_list", "customs")},
            {"label": "Employees", "icon": "users", "url": el("hr_entity_list", "employees")},
        ]
        tables = [
            {"title": "Recent Purchase Orders", "icon": "file",
             "url": el("imports_entity_list", "purchase-orders"),
             "headers": ["PO No", "Supplier", "Total", "Status"],
             "rows": [[p.po_no, p.supplier.name, f"{p.total_amount:,.0f}", p.get_status_display()]
                      for p in im.PurchaseOrder.objects.filter(company=company).order_by("-order_date")[:6]]},
        ]
    elif key == "export":
        from exports import models as ex
        recv = ex.ExportInvoice.objects.filter(company=company).exclude(status="paid").aggregate(
            a=Sum("amount"), p=Sum("paid_amount"))
        months = D.last_n_months(6)
        eo_m = [float(ex.ExportOrder.objects.filter(
            company=company, order_date__year=y, order_date__month=mo)
            .aggregate(t=Sum("total_amount"))["t"] or 0) for y, mo, _ in months]
        eo_d, eo_dr = D.pct_delta(eo_m[-1] if len(eo_m) > 1 else 0, eo_m[-2] if len(eo_m) > 1 else 0)
        kpis = [
            D.kpi("Order Value (Mo)", f"{eo_m[-1] if eo_m else 0:,.0f}",
                  "package", "#3b82f6", "USD · new orders",
                  delta=eo_d, delta_dir=eo_dr, spark=eo_m),
            D.kpi("In Transit", ex.Shipment.objects.filter(company=company, status="in_transit").count(),
                  "truck", "#22c55e", "shipments"),
            D.kpi("Receivables", f"{(recv['a'] or 0) - (recv['p'] or 0):,.0f}",
                  "receipt", "#f59e0b", "unpaid"),
            D.kpi("Employees", employees, "users", "#a855f7", "active staff"),
        ]
        for o in ex.ExportOrder.objects.filter(company=company, status="preparing")[:4]:
            alerts.append({"icon": "package", "level": "warn",
                           "text": f"Order {o.order_no} preparing — QC pending", "time": o.buyer.name})
        actions = [
            {"label": "New Order", "icon": "plus", "url": el("exports_entity_list", "orders")},
            {"label": "New Quotation", "icon": "file", "url": el("exports_entity_list", "quotations")},
            {"label": "New Shipment", "icon": "truck", "url": el("exports_entity_list", "shipments")},
            {"label": "Buyers", "icon": "users", "url": el("exports_entity_list", "buyers")},
            {"label": "Invoices", "icon": "receipt", "url": el("exports_entity_list", "invoices")},
            {"label": "Employees", "icon": "users", "url": el("hr_entity_list", "employees")},
        ]
        tables = [
            {"title": "Recent Export Orders", "icon": "package",
             "url": el("exports_entity_list", "orders"),
             "headers": ["Order No", "Buyer", "Total", "Status"],
             "rows": [[o.order_no, o.buyer.name, f"{o.total_amount:,.0f}", o.get_status_display()]
                      for o in ex.ExportOrder.objects.filter(company=company).order_by("-order_date")[:6]]},
        ]
    elif key == "manufacturing":
        from django.db.models import F
        from manufacturing import models as mf
        kpis = [
            D.kpi("Active Orders", mf.ProductionOrder.objects.filter(
                company=company, status__in=["released", "in_progress", "qc"]).count(),
                "gear", "#3b82f6", "in production"),
            D.kpi("Low Stock Materials", mf.RawMaterial.objects.filter(
                company=company, stock_qty__lte=F("reorder_level")).count(),
                "box", "#ef4444", "reorder needed"),
            D.kpi("QC Pending", mf.ProductionOrder.objects.filter(company=company, status="qc").count(),
                  "shield", "#f59e0b", "awaiting check"),
            D.kpi("Employees", employees, "users", "#22c55e", "active staff"),
        ]
        for rm in mf.RawMaterial.objects.filter(company=company, stock_qty__lte=F("reorder_level"))[:4]:
            alerts.append({"icon": "box", "level": "danger",
                           "text": f"Low stock: {rm.name} ({rm.stock_qty} {rm.unit})",
                           "time": f"Reorder at {rm.reorder_level}"})
        actions = [
            {"label": "New Prod. Order", "icon": "plus", "url": el("manufacturing_entity_list", "production-orders")},
            {"label": "New Plan", "icon": "calendar", "url": el("manufacturing_entity_list", "plans")},
            {"label": "QC Check", "icon": "shield", "url": el("manufacturing_entity_list", "quality-checks")},
            {"label": "Materials", "icon": "box", "url": el("manufacturing_entity_list", "raw-materials")},
            {"label": "Batches", "icon": "package", "url": el("manufacturing_entity_list", "batches")},
            {"label": "Employees", "icon": "users", "url": el("hr_entity_list", "employees")},
        ]
        tables = [
            {"title": "Recent Production Orders", "icon": "gear",
             "url": el("manufacturing_entity_list", "production-orders"),
             "headers": ["Order No", "Product", "Qty", "Status"],
             "rows": [[o.order_no, o.product.name, f"{o.quantity:,.0f}", o.get_status_display()]
                      for o in mf.ProductionOrder.objects.filter(company=company).order_by("-order_date")[:6]]},
        ]
    elif key == "rental":
        from rentals import models as rn
        units = rn.Unit.objects.filter(company=company)
        occupied = units.filter(status="occupied").count()
        occ = round(occupied / (units.count() or 1) * 100)
        kpis = [
            D.kpi("Occupancy", f"{occ}%", "building", "#3b82f6", f"{occupied} units"),
            D.kpi("Collected (Mo)", f"{float(rn.RentPayment.objects.filter(company=company, payment_date__year=timezone.now().year, payment_date__month=timezone.now().month).aggregate(t=Sum('amount'))['t'] or 0):,.0f}",
                  "bank", "#22c55e", "rent received"),
            D.kpi("Open Maintenance", rn.MaintenanceRequest.objects.filter(
                company=company, status__in=["open", "in_progress"]).count(),
                "wrench", "#f59e0b", "requests"),
            D.kpi("Employees", employees, "users", "#22c55e", "active staff"),
        ]
        for rs in rn.RentSchedule.objects.filter(company=company, status="overdue")[:4]:
            alerts.append({"icon": "receipt", "level": "danger",
                           "text": f"Overdue rent: {rs.lease.lease_no} ({rs.amount:,.0f})",
                           "time": f"Due {rs.due_date:%b %d}"})
        actions = [
            {"label": "New Lease", "icon": "plus", "url": el("rentals_entity_list", "leases")},
            {"label": "New Tenant", "icon": "users", "url": el("rentals_entity_list", "tenants")},
            {"label": "New Invoice", "icon": "receipt", "url": el("rentals_entity_list", "rent-invoices")},
            {"label": "Record Payment", "icon": "bank", "url": el("rentals_entity_list", "rent-payments")},
            {"label": "Maintenance", "icon": "wrench", "url": el("rentals_entity_list", "maintenance-requests")},
            {"label": "Units", "icon": "home", "url": el("rentals_entity_list", "units")},
        ]
        tables = [
            {"title": "Recent Rent Payments", "icon": "bank",
             "url": el("rentals_entity_list", "rent-payments"),
             "headers": ["Payment", "Invoice", "Date", "Amount"],
             "rows": [[p.payment_no, p.invoice.invoice_no, f"{p.payment_date:%b %d}", f"{p.amount:,.0f}"]
                      for p in rn.RentPayment.objects.filter(company=company).order_by("-payment_date")[:6]]},
        ]
    else:
        kpis = [
            D.kpi("Employees", employees, "users", "#22c55e", "active staff"),
            D.kpi("Pending Leave", pending_leave, "calendar", "#f59e0b", "awaiting approval"),
            D.kpi("Bills Due", f"{bills_due:,.0f}", "receipt", "#ef4444", "unpaid"),
            D.kpi("Announcements", Announcement.objects.filter(company=company, is_active=True).count(),
                  "bell", "#3b82f6", "active"),
        ]
        actions = [
            {"label": "New Employee", "icon": "plus", "url": el("hr_entity_list", "employees")},
            {"label": "New Bill", "icon": "receipt", "url": el("finance_entity_list", "bills")},
            {"label": "Announcement", "icon": "bell", "url": el("comms_entity_list", "announcements")},
            {"label": "Documents", "icon": "file", "url": el("comms_entity_list", "documents")},
        ]

    # shared cross-module alerts
    if pending_leave:
        alerts.append({"icon": "calendar", "level": "info",
                       "text": f"{pending_leave} leave request(s) pending approval", "time": "HR & Payroll"})
    if bills_due:
        alerts.append({"icon": "receipt", "level": "warn",
                       "text": f"Bills payable: {bills_due:,.0f}", "time": "Finance & Accounting"})
    for an in Announcement.objects.filter(company=company, is_active=True).order_by("-publish_date")[:3]:
        alerts.append({"icon": "bell", "level": "info", "text": an.title,
                       "time": f"{an.publish_date:%b %d} · {an.audience}"})

    cfg = {
        "title": f"{company.name}", "subtitle": f"{ind_label} · Company Dashboard",
        "heading_icon": "dashboard",
        "kpis": kpis, "line": line, "donut": donut,
        "alerts": alerts, "actions": actions, "tables": tables,
    }
    request.company = company
    resp = D.render_module_dashboard(request, company, cfg)
    return resp


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
    from core.modules import build_sidebar
    ctx["sidebar"] = build_sidebar(request)
    return render(request, "core/workspace.html", ctx)
