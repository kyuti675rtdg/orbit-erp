"""Fleet module views: generic CRUD engine + rich operational dashboards."""
import json
from datetime import timedelta
from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models as dj_models
from django.db.models import Count, Max, Min, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.views import company_access_required, editor_required, finance_required

from . import models as m
from .utils import CITY_COORDS, coords_for, interpolate_points


# ============================================================ helpers
def resolve(obj, accessor):
    """Resolve 'a__b' style accessor to a display value."""
    cur = obj
    for part in accessor.split("__"):
        cur = getattr(cur, part, None)
        if cur is None:
            return "—"
        if callable(cur) and not isinstance(cur, dj_models.Manager):
            try:
                cur = cur()
            except TypeError:
                return "—"
    return cur if cur not in ("", None) else "—"


def display_value(obj, field_name):
    """Human-friendly value for a model field (choices aware)."""
    try:
        field = obj._meta.get_field(field_name)
    except Exception:
        return resolve(obj, field_name)
    if field.choices:
        return getattr(obj, f"get_{field_name}_display")()
    val = getattr(obj, field_name, None)
    if isinstance(val, bool):
        return "Yes" if val else "No"
    if val in ("", None):
        return "—"
    return val


def scope_fk_fields(form, company):
    for name, field in form.fields.items():
        try:
            model_field = form._meta.model._meta.get_field(name)
        except Exception:
            continue
        if isinstance(model_field, dj_models.ForeignKey):
            rel = model_field.related_model
            if any(f.name == "company" for f in rel._meta.get_fields()):
                field.queryset = rel.objects.filter(company=company)


def entity_form_class(cfg, company):
    model = cfg["model"]
    fields = cfg["form_fields"]

    def _form_init(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        scope_fk_fields(self, company)
        for fname, f in self.fields.items():
            try:
                mf = model._meta.get_field(fname)
            except Exception:
                continue
            if isinstance(mf, dj_models.DateTimeField):
                f.widget = forms.DateTimeInput(attrs={"type": "datetime-local"})
            elif isinstance(mf, dj_models.DateField):
                f.widget = forms.DateInput(attrs={"type": "date"})
            elif isinstance(mf, dj_models.TextField):
                f.widget.attrs.update({"rows": 3})
            if isinstance(f.widget, (forms.TextInput, forms.NumberInput, forms.Select,
                                     forms.DateInput, forms.DateTimeInput, forms.Textarea,
                                     forms.EmailInput)):
                f.widget.attrs.setdefault("class", "input")

    Meta = type("Meta", (), {"model": model, "fields": fields})
    return type("_EntityForm", (forms.ModelForm,), {"Meta": Meta, "__init__": _form_init})


# ============================================================ entity registry
E = lambda **kw: kw  # noqa: E731

ENTITIES = {
    "vehicles": E(
        model=m.Vehicle, title="Vehicles", singular="Vehicle", icon="🚚",
        list_display=[("Plate No", "plate_no"), ("Type", "vehicle_type"), ("Make / Model", "make"),
                      ("Capacity (t)", "capacity_tons"), ("Status", "status"), ("Odometer (km)", "odometer_km")],
        form_fields=["plate_no", "vehicle_type", "make", "model", "year", "capacity_tons",
                     "fuel_type", "ownership", "status", "odometer_km", "vin",
                     "registration_no", "insurance_policy", "insurance_expiry",
                     "purchase_date", "purchase_cost", "notes"],
        search=["plate_no", "make", "model", "vin"],
        detail_related=[
            ("Trips", "trips", [("Trip No", "trip_no"), ("Route", "route"), ("Status", "status")]),
            ("Fuel Logs", "fuel_logs", [("Date", "date"), ("Liters", "liters"), ("Cost", "cost")]),
            ("Service Records", "services", [("Title", "title"), ("Type", "service_type"), ("Status", "status")]),
            ("Documents", "documents", [("Document", "doc_type"), ("Expiry", "expiry_date")]),
        ],
    ),
    "vehicle-documents": E(
        model=m.VehicleDocument, title="Vehicle Documents", singular="Vehicle Document", icon="📄",
        list_display=[("Vehicle", "vehicle"), ("Document", "doc_type"), ("Doc No", "doc_no"), ("Expiry", "expiry_date")],
        form_fields=["vehicle", "doc_type", "doc_no", "issued_date", "expiry_date", "notes"],
        search=["doc_no", "vehicle__plate_no"],
    ),
    "drivers": E(
        model=m.Driver, title="Drivers", singular="Driver", icon="🧑‍✈️",
        list_display=[("Name", "name"), ("Phone", "phone"), ("License No", "license_no"),
                      ("Class", "license_class"), ("License Expiry", "license_expiry"), ("Status", "status")],
        form_fields=["name", "phone", "national_id", "license_no", "license_class",
                     "license_expiry", "status", "hire_date", "address", "emergency_contact", "notes"],
        search=["name", "phone", "license_no"],
        detail_related=[
            ("Trips", "trips", [("Trip No", "trip_no"), ("Route", "route"), ("Status", "status")]),
            ("Documents", "documents", [("Document", "doc_type"), ("Expiry", "expiry_date")]),
            ("Advances", "advances", [("Date", "date"), ("Amount", "amount"), ("Settled", "settled")]),
        ],
    ),
    "driver-documents": E(
        model=m.DriverDocument, title="Driver Documents", singular="Driver Document", icon="🪪",
        list_display=[("Driver", "driver"), ("Document", "doc_type"), ("Doc No", "doc_no"), ("Expiry", "expiry_date")],
        form_fields=["driver", "doc_type", "doc_no", "issued_date", "expiry_date", "notes"],
        search=["doc_no", "driver__name"],
    ),
    "routes": E(
        model=m.Route, title="Routes", singular="Route", icon="🗺️",
        list_display=[("Route", "name"), ("Origin", "origin"), ("Destination", "destination"),
                      ("Distance (km)", "distance_km"), ("Est. Hours", "est_hours"), ("Active", "is_active")],
        form_fields=["name", "origin", "destination", "distance_km", "est_hours",
                     "stops", "restricted_zones", "is_active"],
        search=["name", "origin", "destination"],
        detail_related=[
            ("Trips", "trips", [("Trip No", "trip_no"), ("Vehicle", "vehicle"), ("Status", "status")]),
        ],
    ),
    "geofences": E(
        model=m.Geofence, title="Geofences", singular="Geofence", icon="📍",
        list_display=[("Name", "name"), ("Type", "zone_type"), ("Radius (m)", "radius_m")],
        form_fields=["name", "zone_type", "latitude", "longitude", "radius_m", "notes"],
        search=["name"],
    ),
    "trips": E(
        model=m.Trip, title="Trips", singular="Trip", icon="🛣️",
        list_display=[("Trip No", "trip_no"), ("Route", "route"), ("Vehicle", "vehicle"),
                      ("Driver", "driver"), ("Status", "status"), ("Priority", "priority"),
                      ("Departure", "departure_planned")],
        form_fields=["trip_no", "route", "vehicle", "driver", "status", "priority",
                     "cargo_desc", "cargo_weight_tons", "departure_planned", "arrival_planned",
                     "odometer_start", "odometer_end", "notes"],
        search=["trip_no", "cargo_desc", "vehicle__plate_no", "driver__name"],
        custom_detail="trip_detail",
    ),
    "dispatches": E(
        model=m.DispatchOrder, title="Dispatch Orders", singular="Dispatch Order", icon="📋",
        list_display=[("Order No", "order_no"), ("Trip", "trip"), ("Scheduled Departure", "scheduled_departure"),
                      ("Priority", "priority"), ("Status", "status")],
        form_fields=["order_no", "trip", "scheduled_departure", "priority", "instructions", "status"],
        search=["order_no", "trip__trip_no"],
    ),
    "fuel": E(
        model=m.FuelLog, title="Fuel Logs", singular="Fuel Log", icon="⛽",
        list_display=[("Date", "date"), ("Vehicle", "vehicle"), ("Trip", "trip"),
                      ("Liters", "liters"), ("Cost (ETB)", "cost"), ("Station", "station")],
        form_fields=["vehicle", "trip", "date", "station", "liters", "cost", "odometer_km", "receipt_no"],
        search=["station", "receipt_no", "vehicle__plate_no"],
    ),
    "services": E(
        model=m.ServiceRecord, title="Maintenance", singular="Service Record", icon="🔧",
        list_display=[("Vehicle", "vehicle"), ("Title", "title"), ("Type", "service_type"),
                      ("Scheduled", "scheduled_date"), ("Cost (ETB)", "cost"), ("Status", "status")],
        form_fields=["vehicle", "service_type", "title", "description", "scheduled_date",
                     "completed_date", "odometer_km", "cost", "workshop", "status"],
        search=["title", "vehicle__plate_no", "workshop"],
    ),
    "inspections": E(
        model=m.Inspection, title="Vehicle Inspections", singular="Inspection", icon="✅",
        list_display=[("Date", "date"), ("Vehicle", "vehicle"), ("Driver", "driver"),
                      ("Passed", "passed"), ("Approved By", "approved_by")],
        form_fields=["vehicle", "driver", "date", "defects_found", "passed", "approved_by"],
        search=["vehicle__plate_no", "driver__name"],
    ),
    "parts": E(
        model=m.SparePart, title="Spare Parts", singular="Spare Part", icon="⚙️",
        list_display=[("Part", "name"), ("Part No", "part_no"), ("Category", "category"),
                      ("On Hand", "qty_on_hand"), ("Reorder Level", "reorder_level"),
                      ("Unit Cost (ETB)", "unit_cost")],
        form_fields=["name", "part_no", "category", "unit", "qty_on_hand",
                     "reorder_level", "unit_cost", "location"],
        search=["name", "part_no", "category"],
        detail_related=[
            ("Issues", "issues", [("Job", "job"), ("Qty", "quantity"), ("Issued At", "issued_at")]),
        ],
    ),
    "workshop-jobs": E(
        model=m.WorkshopJob, title="Workshop Jobs", singular="Workshop Job", icon="🏭",
        list_display=[("Job No", "job_no"), ("Vehicle", "vehicle"), ("Title", "title"),
                      ("Status", "status"), ("Technician", "technician"), ("Opened", "opened_at")],
        form_fields=["job_no", "vehicle", "title", "description", "status",
                     "technician", "labor_cost", "parts_cost"],
        search=["job_no", "title", "vehicle__plate_no"],
        detail_related=[
            ("Parts Issued", "part_issues", [("Part", "part"), ("Qty", "quantity"), ("Issued To", "issued_to")]),
        ],
    ),
    "part-issues": E(
        model=m.PartIssue, title="Part Issues", singular="Part Issue", icon="📦",
        list_display=[("Part", "part"), ("Job", "job"), ("Qty", "quantity"), ("Issued At", "issued_at")],
        form_fields=["part", "job", "quantity", "issued_to"],
        search=["part__name", "job__job_no"],
    ),
    "deliveries": E(
        model=m.DeliveryOrder, title="Delivery Orders", singular="Delivery Order", icon="📬",
        list_display=[("Order No", "order_no"), ("Customer", "customer_name"), ("Destination", "destination"),
                      ("Trip", "trip"), ("Status", "status"), ("POD Signed By", "pod_signed_by")],
        form_fields=["order_no", "trip", "customer_name", "customer_phone", "destination",
                     "cargo_desc", "cargo_weight_tons", "status", "pod_signed_by", "pod_notes"],
        search=["order_no", "customer_name", "destination"],
    ),
    "expenses": E(
        model=m.TripExpense, title="Trip Expenses", singular="Trip Expense", icon="🧾",
        list_display=[("Date", "date"), ("Trip", "trip"), ("Category", "category"),
                      ("Description", "description"), ("Amount (ETB)", "amount"), ("Approved", "approved")],
        form_fields=["trip", "category", "description", "amount", "date", "paid_by", "receipt_no", "approved"],
        search=["description", "trip__trip_no", "receipt_no"],
    ),
    "advances": E(
        model=m.DriverAdvance, title="Driver Advances", singular="Driver Advance", icon="💵",
        list_display=[("Date", "date"), ("Driver", "driver"), ("Trip", "trip"),
                      ("Amount (ETB)", "amount"), ("Settled", "settled")],
        form_fields=["driver", "trip", "amount", "date", "purpose", "settled"],
        search=["driver__name", "purpose"],
    ),
    "invoices": E(
        model=m.Invoice, title="Invoices", singular="Invoice", icon="💰",
        list_display=[("Invoice No", "invoice_no"), ("Customer", "customer_name"), ("Trip", "trip"),
                      ("Total (ETB)", "total"), ("Status", "status"), ("Due", "due_date")],
        form_fields=["invoice_no", "customer_name", "trip", "delivery", "description",
                     "amount", "tax", "status", "issued_date", "due_date"],
        search=["invoice_no", "customer_name"],
        detail_related=[
            ("Payments", "payments", [("Date", "date"), ("Amount", "amount"), ("Method", "method"), ("Reference", "reference")]),
        ],
        finance=True,
    ),
    "payments": E(
        model=m.Payment, title="Payments", singular="Payment", icon="🏦",
        list_display=[("Date", "date"), ("Invoice", "invoice"), ("Amount (ETB)", "amount"),
                      ("Method", "method"), ("Reference", "reference")],
        form_fields=["invoice", "amount", "method", "date", "reference", "received_by"],
        search=["reference", "invoice__invoice_no"],
        finance=True,
    ),
    "employees": E(
        model=m.Employee, title="Employees", singular="Employee", icon="👥",
        list_display=[("Name", "name"), ("Role", "role"), ("Phone", "phone"),
                      ("Salary (ETB)", "salary_monthly"), ("Status", "status")],
        form_fields=["name", "role", "phone", "hire_date", "salary_monthly", "status", "driver"],
        search=["name", "role", "phone"],
    ),
    "attendance": E(
        model=m.Attendance, title="Attendance", singular="Attendance Record", icon="🕘",
        list_display=[("Date", "date"), ("Employee", "employee"), ("Present", "present"), ("Hours", "hours")],
        form_fields=["employee", "date", "present", "hours", "note"],
        search=["employee__name"],
    ),
    "payrolls": E(
        model=m.Payroll, title="Payroll", singular="Payroll", icon="💳",
        list_display=[("Month", "month"), ("Employee", "employee"), ("Gross (ETB)", "gross"),
                      ("Deductions", "deductions"), ("Net (ETB)", "net"), ("Status", "status")],
        form_fields=["employee", "month", "gross", "deductions", "status"],
        search=["employee__name"],
        finance=True,
    ),
    "alerts": E(
        model=m.Alert, title="Alerts", singular="Alert", icon="🔔",
        list_display=[("Level", "level"), ("Title", "title"), ("Created", "created_at"), ("Resolved", "is_resolved")],
        form_fields=["level", "title", "message", "link", "is_resolved"],
        search=["title", "message"],
    ),
}

# Sidebar navigation structure
NAV = [
    ("Dashboard", "📊", "fleet_dashboard", None),
    ("Live Tracking", "🛰️", "fleet_tracking", None),
    ("Operations", None, None, [
        ("Trips", "🛣️", "fleet_trips"),
        ("Dispatch Orders", "📋", "fleet_dispatches"),
        ("Deliveries & POD", "📬", "fleet_deliveries"),
    ]),
    ("Fleet", None, None, [
        ("Vehicles", "🚚", "fleet_vehicles"),
        ("Vehicle Documents", "📄", "fleet_vehicle-documents"),
        ("Routes", "🗺️", "fleet_routes"),
        ("Geofences", "📍", "fleet_geofences"),
    ]),
    ("Drivers & HR", None, None, [
        ("Drivers", "🧑‍✈️", "fleet_drivers"),
        ("Driver Documents", "🪪", "fleet_driver-documents"),
        ("Employees", "👥", "fleet_employees"),
        ("Attendance", "🕘", "fleet_attendance"),
        ("Payroll", "💳", "fleet_payrolls"),
    ]),
    ("Fuel & Maintenance", None, None, [
        ("Fuel Logs", "⛽", "fleet_fuel"),
        ("Maintenance", "🔧", "fleet_services"),
        ("Inspections", "✅", "fleet_inspections"),
        ("Spare Parts", "⚙️", "fleet_parts"),
        ("Workshop Jobs", "🏭", "fleet_workshop-jobs"),
        ("Part Issues", "📦", "fleet_part-issues"),
    ]),
    ("Finance", None, None, [
        ("Trip Expenses", "🧾", "fleet_expenses"),
        ("Driver Advances", "💵", "fleet_advances"),
        ("Invoices", "💰", "fleet_invoices"),
        ("Payments", "🏦", "fleet_payments"),
    ]),
    ("Intelligence", None, None, [
        ("Reports & BI", "📈", "fleet_reports", None),
        ("Alerts", "🔔", "fleet_alerts"),
    ]),
]


# ============================================================ generic CRUD
def _entity_or_404(entity):
    cfg = ENTITIES.get(entity)
    if not cfg:
        from django.http import Http404
        raise Http404("Unknown section")
    return cfg


@company_access_required
def entity_list(request, company_slug, entity):
    cfg = _entity_or_404(entity)
    company = request.company
    qs = cfg["model"].objects.filter(company=company).order_by("-created_at" if hasattr(cfg["model"], "created_at") else "id")
    q = request.GET.get("q", "").strip()
    if q and cfg.get("search"):
        cond = Q()
        for f in cfg["search"]:
            cond |= Q(**{f"{f}__icontains": q})
        qs = qs.filter(cond)
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))
    rows = []
    for obj in page.object_list:
        rows.append({"obj": obj, "cells": [display_value(obj, a) for _, a in cfg["list_display"]]})
    return render(request, "fleet/entity_list.html", {
        "company": company, "membership": request.membership, "cfg": cfg,
        "entity": entity, "headers": [h for h, _ in cfg["list_display"]],
        "rows": rows, "page": page, "q": q, "nav": NAV,
    })


@company_access_required
def entity_detail(request, company_slug, entity, pk):
    cfg = _entity_or_404(entity)
    company = request.company
    obj = get_object_or_404(cfg["model"], company=company, pk=pk)
    if cfg.get("custom_detail") == "trip_detail":
        return trip_detail(request, company_slug, obj)
    fields = []
    for f in cfg["model"]._meta.get_fields():
        if f.name in ("id", "company", "created_at", "updated_at") or f.auto_created:
            continue
        if isinstance(f, (dj_models.ForeignKey, dj_models.CharField, dj_models.TextField,
                          dj_models.IntegerField, dj_models.DecimalField, dj_models.FloatField,
                          dj_models.DateField, dj_models.DateTimeField, dj_models.BooleanField,
                          dj_models.PositiveIntegerField, dj_models.JSONField)):
            fields.append((f.verbose_name.title(), display_value(obj, f.name)))
    related = []
    for title, rel_name, cols in cfg.get("detail_related", []):
        manager = getattr(obj, rel_name, None)
        items = list(manager.all()[:8]) if manager is not None else []
        related.append({"title": title, "headers": [h for h, _ in cols],
                        "rows": [[display_value(i, a) for _, a in cols] for i in items],
                        "count": manager.count() if manager is not None else 0})
    return render(request, "fleet/entity_detail.html", {
        "company": company, "membership": request.membership, "cfg": cfg,
        "entity": entity, "obj": obj, "fields": fields, "related": related, "nav": NAV,
    })


@company_access_required
@editor_required
def entity_create(request, company_slug, entity):
    cfg = _entity_or_404(entity)
    if cfg.get("finance") and request.membership.role not in settings.FINANCE_ROLES | settings.EDITOR_ROLES:
        messages.error(request, "Your role does not permit this action.")
        return redirect("fleet_entity_list", company_slug=company_slug, entity=entity)
    Form = entity_form_class(cfg, request.company)
    form = Form(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.company = request.company
        obj.save()
        form.save_m2m()
        messages.success(request, f"{cfg['singular']} created.")
        return redirect("fleet_entity_detail", company_slug=company_slug, entity=entity, pk=obj.pk)
    return render(request, "fleet/entity_form.html", {
        "company": request.company, "membership": request.membership, "cfg": cfg,
        "entity": entity, "form": form, "mode": "Create", "nav": NAV,
    })


@company_access_required
@editor_required
def entity_update(request, company_slug, entity, pk):
    cfg = _entity_or_404(entity)
    obj = get_object_or_404(cfg["model"], company=request.company, pk=pk)
    Form = entity_form_class(cfg, request.company)
    form = Form(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{cfg['singular']} updated.")
        return redirect("fleet_entity_detail", company_slug=company_slug, entity=entity, pk=obj.pk)
    return render(request, "fleet/entity_form.html", {
        "company": request.company, "membership": request.membership, "cfg": cfg,
        "entity": entity, "form": form, "mode": "Edit", "nav": NAV,
    })


@company_access_required
@editor_required
def entity_delete(request, company_slug, entity, pk):
    cfg = _entity_or_404(entity)
    obj = get_object_or_404(cfg["model"], company=request.company, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, f"{cfg['singular']} deleted.")
        return redirect("fleet_entity_list", company_slug=company_slug, entity=entity)
    return render(request, "fleet/entity_confirm_delete.html", {
        "company": request.company, "membership": request.membership, "cfg": cfg,
        "entity": entity, "obj": obj, "nav": NAV,
    })


# ============================================================ trip workspace
def trip_detail(request, company_slug, obj):
    company = request.company
    pings = list(obj.pings.order_by("recorded_at"))
    ping_json = json.dumps([{"lat": p.latitude, "lng": p.longitude, "speed": p.speed_kmh,
                             "event": p.event, "t": p.recorded_at.strftime("%H:%M")} for p in pings])
    origin = coords_for(obj.route.origin)
    dest = coords_for(obj.route.destination)
    expenses = obj.expenses.order_by("-date")
    exp_total = expenses.aggregate(t=Sum("amount"))["t"] or 0
    fuel_total = obj.fuel_logs.aggregate(t=Sum("cost"))["t"] or 0
    adv_total = obj.advances.aggregate(t=Sum("amount"))["t"] or 0
    invoices = obj.invoices.order_by("-issued_date")
    flow = ["planned", "dispatched", "en_route", "delivered", "completed"]
    labels = dict(m.Trip.STATUS_CHOICES)
    try:
        cur_idx = flow.index(obj.status)
    except ValueError:
        cur_idx = -1
    steps = [{"key": s, "label": labels.get(s, s).replace("_", " ").title(),
              "state": "cur" if i == cur_idx else ("done" if 0 <= i < cur_idx or obj.status == "completed" else "todo")}
             for i, s in enumerate(flow)]
    next_step = {"planned": "Dispatch", "dispatched": "Start Trip",
                 "en_route": "Mark Delivered", "delivered": "Complete & Invoice"}.get(obj.status)
    return render(request, "fleet/trip_detail.html", {
        "company": company, "membership": request.membership, "cfg": ENTITIES["trips"],
        "entity": "trips", "trip": obj, "nav": NAV,
        "pings": pings, "ping_json": ping_json, "origin": origin, "dest": dest,
        "expenses": expenses, "exp_total": exp_total, "fuel_total": fuel_total,
        "adv_total": adv_total, "trip_cost": exp_total + fuel_total + adv_total,
        "invoices": invoices, "flow": flow, "steps": steps, "next_step": next_step,
        "deliveries": obj.deliveries.all(),
    })


@company_access_required
@editor_required
def trip_action(request, company_slug, pk):
    trip = get_object_or_404(m.Trip, company=request.company, pk=pk)
    action = request.POST.get("action")
    now = timezone.now()
    if action == "advance":
        if trip.status == "planned":
            trip.status = "dispatched"
            m.DispatchOrder.objects.get_or_create(
                company=request.company, trip=trip,
                defaults={"order_no": f"DO-{trip.trip_no}", "scheduled_departure": trip.departure_planned or now,
                          "priority": trip.priority, "assigned_by": request.user})
            messages.success(request, f"Trip {trip.trip_no} dispatched.")
        elif trip.status == "dispatched":
            trip.status = "en_route"
            trip.departure_actual = trip.departure_actual or now
            trip.vehicle.status = "on_trip"
            trip.vehicle.save(update_fields=["status"])
            trip.driver.status = "on_trip"
            trip.driver.save(update_fields=["status"])
            messages.success(request, f"Trip {trip.trip_no} is now en route.")
        elif trip.status == "en_route":
            trip.status = "delivered"
            trip.arrival_actual = trip.arrival_actual or now
            for d in trip.deliveries.filter(status="in_transit"):
                d.status = "delivered"
                d.pod_time = d.pod_time or now
                d.pod_signed_by = d.pod_signed_by or request.POST.get("pod_signed_by", "")
                d.save()
            messages.success(request, f"Trip {trip.trip_no} delivered. Capture POD on delivery orders.")
        elif trip.status == "delivered":
            trip.status = "completed"
            trip.vehicle.status = "active"
            trip.vehicle.save(update_fields=["status"])
            trip.driver.status = "available"
            trip.driver.save(update_fields=["status"])
            if not trip.invoices.exists():
                km = trip.distance_km or trip.route.distance_km or 100
                amount = Decimal(km) * Decimal("85")
                m.Invoice.objects.create(
                    company=request.company, invoice_no=f"INV-{trip.trip_no}",
                    customer_name=trip.deliveries.first().customer_name if trip.deliveries.exists() else "—",
                    trip=trip, description=f"Transport service — {trip.route.name} ({km} km)",
                    amount=amount, tax=amount * Decimal("0.15"),
                    due_date=(now + timedelta(days=30)).date())
                messages.success(request, f"Trip completed. Draft invoice INV-{trip.trip_no} generated.")
            else:
                messages.success(request, f"Trip {trip.trip_no} completed.")
        trip.save()
    elif action == "cancel":
        trip.status = "cancelled"
        trip.vehicle.status = "active"
        trip.vehicle.save(update_fields=["status"])
        trip.driver.status = "available"
        trip.driver.save(update_fields=["status"])
        trip.save()
        messages.warning(request, f"Trip {trip.trip_no} cancelled.")
    return redirect("fleet_entity_detail", company_slug=company_slug, entity="trips", pk=trip.pk)


# ============================================================ dashboards
@company_access_required
def fleet_dashboard(request, company_slug):
    company = request.company
    now = timezone.now()
    V, T, D, F = m.Vehicle, m.Trip, m.DeliveryOrder, m.FuelLog
    active_trips = T.objects.filter(company=company, status__in=["planned", "dispatched", "en_route"])
    kpis = {
        "vehicles": V.objects.filter(company=company).exclude(status="retired").count(),
        "on_trip": V.objects.filter(company=company, status="on_trip").count(),
        "drivers_avail": m.Driver.objects.filter(company=company, status="available").count(),
        "active_trips": active_trips.count(),
        "deliveries_month": D.objects.filter(company=company, created_at__year=now.year, created_at__month=now.month).count(),
        "fuel_month": F.objects.filter(company=company, date__year=now.year, date__month=now.month).aggregate(t=Sum("cost"))["t"] or 0,
        "maint_month": m.ServiceRecord.objects.filter(
            company=company, completed_date__year=now.year, completed_date__month=now.month).aggregate(t=Sum("cost"))["t"] or 0,
        "receivable": m.Invoice.objects.filter(company=company, status__in=["sent", "overdue"]).aggregate(t=Sum("total"))["t"] or 0,
        "open_alerts": m.Alert.objects.filter(company=company, is_resolved=False).count(),
    }
    # live alerts (computed)
    soon = now.date() + timedelta(days=30)
    live_alerts = []
    for doc in m.VehicleDocument.objects.filter(company=company, expiry_date__lte=soon).select_related("vehicle")[:5]:
        live_alerts.append({"level": "warning", "title": f"{doc.vehicle.plate_no}: {doc.get_doc_type_display()} expires {doc.expiry_date}", "link": ""})
    for doc in m.DriverDocument.objects.filter(company=company, expiry_date__lte=soon).select_related("driver")[:5]:
        live_alerts.append({"level": "warning", "title": f"{doc.driver.name}: {doc.get_doc_type_display()} expires {doc.expiry_date}", "link": ""})
    for p in m.SparePart.objects.filter(company=company, qty_on_hand__lte=dj_models.F("reorder_level"))[:5]:
        live_alerts.append({"level": "critical", "title": f"Low stock: {p.name} ({p.qty_on_hand} left)", "link": ""})
    stored_alerts = list(m.Alert.objects.filter(company=company, is_resolved=False)[:6])

    # charts
    status_counts = list(T.objects.filter(company=company).values("status").annotate(n=Count("id")))
    months, fuel_series, deliv_series, rev_series, coll_series = [], [], [], [], []
    for i in range(5, -1, -1):
        d = (now.replace(day=1) - timedelta(days=1)).replace(day=1) if i else now.replace(day=1)
        # simpler: walk back month by month
        y, mo = now.year, now.month - i
        while mo <= 0:
            mo += 12
            y -= 1
        months.append(f"{y}-{mo:02d}")
        fuel_series.append(float(F.objects.filter(company=company, date__year=y, date__month=mo).aggregate(t=Sum("cost"))["t"] or 0))
        deliv_series.append(D.objects.filter(company=company, created_at__year=y, created_at__month=mo).count())
        inv = m.Invoice.objects.filter(company=company, issued_date__year=y, issued_date__month=mo)
        rev_series.append(float(inv.aggregate(t=Sum("total"))["t"] or 0))
        coll_series.append(float(m.Payment.objects.filter(company=company, invoice__in=inv).aggregate(t=Sum("amount"))["t"] or 0))
    util = list(T.objects.filter(company=company, status="completed").values("vehicle__plate_no").annotate(n=Count("id")).order_by("-n")[:8])
    exp_by_cat = list(m.TripExpense.objects.filter(company=company).values("category").annotate(t=Sum("amount")))

    charts = {
        "status": {"labels": [s["status"].replace("_", " ").title() for s in status_counts],
                   "data": [s["n"] for s in status_counts]},
        "months": months, "fuel": fuel_series, "deliveries": deliv_series,
        "revenue": rev_series, "collected": coll_series,
        "util_labels": [u["vehicle__plate_no"] for u in util],
        "util_data": [u["n"] for u in util],
        "exp_labels": [e["category"].title() for e in exp_by_cat],
        "exp_data": [float(e["t"]) for e in exp_by_cat],
    }
    return render(request, "fleet/dashboard.html", {
        "company": company, "membership": request.membership, "nav": NAV,
        "kpis": kpis, "charts_json": json.dumps(charts),
        "active_trips": active_trips.select_related("route", "vehicle", "driver")[:8],
        "live_alerts": live_alerts, "stored_alerts": stored_alerts,
        "recent_deliveries": D.objects.filter(company=company).select_related("trip").order_by("-created_at")[:6],
    })


@company_access_required
def tracking(request, company_slug):
    company = request.company
    trips = m.Trip.objects.filter(company=company, status="en_route").select_related("route", "vehicle", "driver")
    data = []
    for t in trips:
        pings = list(t.pings.order_by("recorded_at"))
        path = [[p.latitude, p.longitude] for p in pings] or [list(coords_for(t.route.origin)), list(coords_for(t.route.destination))]
        latest = pings[-1] if pings else None
        data.append({
            "trip_no": t.trip_no, "vehicle": t.vehicle.plate_no, "driver": t.driver.name,
            "route": t.route.name, "cargo": t.cargo_desc,
            "path": path,
            "lat": latest.latitude if latest else path[-1][0],
            "lng": latest.longitude if latest else path[-1][1],
            "speed": latest.speed_kmh if latest else 0,
            "updated": latest.recorded_at.strftime("%H:%M") if latest else "—",
        })
    geofences = list(m.Geofence.objects.filter(company=company).values("name", "zone_type", "latitude", "longitude", "radius_m"))
    return render(request, "fleet/tracking.html", {
        "company": company, "membership": request.membership, "nav": NAV,
        "tracks_json": json.dumps(data), "geofences_json": json.dumps(geofences),
        "trips": trips,
    })


@company_access_required
def tracking_feed(request, company_slug):
    company = request.company
    out = []
    for t in m.Trip.objects.filter(company=company, status="en_route"):
        p = t.pings.order_by("-recorded_at").first()
        if p:
            out.append({"trip_no": t.trip_no, "lat": p.latitude, "lng": p.longitude,
                        "speed": p.speed_kmh, "event": p.event})
    return JsonResponse({"tracks": out, "server_time": timezone.now().strftime("%H:%M:%S")})


@company_access_required
def reports(request, company_slug):
    company = request.company
    # utilization per vehicle
    util_rows = []
    for v in m.Vehicle.objects.filter(company=company):
        trips = m.Trip.objects.filter(company=company, vehicle=v, status="completed")
        n = trips.count()
        trip_km = sum(t.distance_km for t in trips)
        odo = v.fuel_logs.aggregate(mx=Max("odometer_km"), mn=Min("odometer_km"))
        odo_km = (odo["mx"] or 0) - (odo["mn"] or 0)
        km = max(trip_km, odo_km)
        fuel_l = v.fuel_logs.aggregate(t=Sum("liters"))["t"] or 0
        fuel_c = v.fuel_logs.aggregate(t=Sum("cost"))["t"] or 0
        maint_c = v.services.filter(status="completed").aggregate(t=Sum("cost"))["t"] or 0
        eff = round(float(km) / float(fuel_l), 2) if fuel_l and km else 0
        util_rows.append({"vehicle": v.plate_no, "type": v.get_vehicle_type_display(), "trips": n,
                          "km": km, "fuel_l": float(fuel_l), "fuel_cost": float(fuel_c),
                          "maint_cost": float(maint_c), "km_per_l": eff,
                          "cost_per_km": round(float(fuel_c + maint_c) / float(km), 2) if km else 0})
    util_rows.sort(key=lambda r: r["trips"], reverse=True)
    # trip profitability
    profit_rows = []
    for t in m.Trip.objects.filter(company=company, status="completed").select_related("route", "vehicle")[:50]:
        cost = (t.expenses.aggregate(s=Sum("amount"))["s"] or 0) + (t.fuel_logs.aggregate(s=Sum("cost"))["s"] or 0)
        revenue = t.invoices.aggregate(s=Sum("total"))["s"] or 0
        profit_rows.append({"trip": t.trip_no, "route": t.route.name, "vehicle": t.vehicle.plate_no,
                            "cost": float(cost), "revenue": float(revenue), "margin": float(revenue - cost)})
    # delivery performance
    delivs = m.DeliveryOrder.objects.filter(company=company, status="delivered", pod_time__isnull=False)
    on_time = 0
    for d in delivs.select_related("trip"):
        if d.trip and d.trip.arrival_planned and d.pod_time:
            if d.pod_time <= d.trip.arrival_planned + timedelta(hours=6):
                on_time += 1
    total_rev = sum(r["revenue"] for r in profit_rows)
    total_cost = sum(r["cost"] for r in profit_rows)
    return render(request, "fleet/reports.html", {
        "company": company, "membership": request.membership, "nav": NAV,
        "util_rows": util_rows[:12], "profit_rows": profit_rows[:20],
        "on_time_pct": round(on_time / max(delivs.count(), 1) * 100),
        "delivered_count": delivs.count(),
        "total_rev": total_rev, "total_cost": total_cost,
        "margin": total_rev - total_cost,
    })


@company_access_required
@finance_required
def payroll_run(request, company_slug):
    from datetime import date
    if request.method == "POST":
        month_str = request.POST.get("month")  # YYYY-MM
        y, mo = map(int, month_str.split("-"))
        month = date(y, mo, 1)
        created = 0
        for emp in m.Employee.objects.filter(company=request.company, status="active"):
            gross = emp.salary_monthly
            deductions = (gross * Decimal("0.15")).quantize(Decimal("0.01"))
            _, was_created = m.Payroll.objects.get_or_create(
                company=request.company, employee=emp, month=month,
                defaults={"gross": gross, "deductions": deductions})
            created += 1 if was_created else 0
        messages.success(request, f"Payroll generated for {month:%B %Y}: {created} new records.")
        return redirect("fleet_entity_list", company_slug=company_slug, entity="payrolls")
    return render(request, "fleet/payroll_run.html", {
        "company": request.company, "membership": request.membership, "nav": NAV,
        "employees": m.Employee.objects.filter(company=request.company, status="active"),
    })


@company_access_required
@finance_required
def invoice_pay(request, company_slug, pk):
    inv = get_object_or_404(m.Invoice, company=request.company, pk=pk)
    if request.method == "POST":
        amount = Decimal(request.POST.get("amount") or 0)
        if amount > 0:
            m.Payment.objects.create(company=request.company, invoice=inv, amount=amount,
                                     method=request.POST.get("method", "bank"),
                                     reference=request.POST.get("reference", ""),
                                     received_by=request.user.username)
            paid = inv.payments.aggregate(t=Sum("amount"))["t"] or 0
            if paid >= inv.total:
                inv.status = "paid"
                inv.save(update_fields=["status"])
            messages.success(request, f"Payment of {amount:,.2f} recorded for {inv.invoice_no}.")
    return redirect("fleet_entity_detail", company_slug=company_slug, entity="invoices", pk=inv.pk)
