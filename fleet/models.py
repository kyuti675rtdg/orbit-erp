"""Transportation & Fleet Management module models."""
from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import Company

User = settings.AUTH_USER_MODEL


class CompanyScoped(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="%(class)ss")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------- Fleet
class Vehicle(CompanyScoped):
    TYPE_CHOICES = [
        ("truck", "Truck"), ("trailer", "Trailer / Articulated"), ("pickup", "Pickup"),
        ("van", "Van"), ("bus", "Bus"), ("sedan", "Sedan"), ("forklift", "Forklift"),
        ("tanker", "Fuel Tanker"),
    ]
    OWNERSHIP_CHOICES = [("owned", "Owned"), ("leased", "Leased"), ("rented", "Rented")]
    STATUS_CHOICES = [
        ("active", "Active"), ("on_trip", "On Trip"), ("maintenance", "In Maintenance"),
        ("idle", "Idle"), ("retired", "Retired"),
    ]
    FUEL_CHOICES = [("diesel", "Diesel"), ("petrol", "Petrol"), ("electric", "Electric"), ("cng", "CNG")]

    plate_no = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="truck")
    make = models.CharField(max_length=60, blank=True)
    model = models.CharField(max_length=60, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    capacity_tons = models.DecimalField(max_digits=6, decimal_places=2, default=0, blank=True)
    fuel_type = models.CharField(max_length=10, choices=FUEL_CHOICES, default="diesel")
    ownership = models.CharField(max_length=10, choices=OWNERSHIP_CHOICES, default="owned")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="active")
    odometer_km = models.PositiveIntegerField(default=0, blank=True)
    vin = models.CharField("VIN / Chassis No", max_length=60, blank=True)
    registration_no = models.CharField(max_length=60, blank=True)
    insurance_policy = models.CharField(max_length=60, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["plate_no"]
        unique_together = ("company", "plate_no")

    def __str__(self):
        return f"{self.plate_no} ({self.get_vehicle_type_display()})"


class VehicleDocument(CompanyScoped):
    DOC_TYPES = [
        ("registration", "Vehicle Registration"), ("insurance", "Insurance Policy"),
        ("inspection", "Roadworthiness Inspection"), ("transport_permit", "Transport Permit"),
        ("emission", "Emission Certificate"), ("other", "Other"),
    ]
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES)
    doc_no = models.CharField(max_length=80, blank=True)
    issued_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["expiry_date"]

    def __str__(self):
        return f"{self.vehicle.plate_no} — {self.get_doc_type_display()}"


# ---------------------------------------------------------------- Drivers
class Driver(CompanyScoped):
    STATUS_CHOICES = [
        ("available", "Available"), ("on_trip", "On Trip"), ("off_duty", "Off Duty"),
        ("suspended", "Suspended"),
    ]
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40, blank=True)
    national_id = models.CharField(max_length=40, blank=True)
    license_no = models.CharField(max_length=60, blank=True)
    license_class = models.CharField(max_length=10, default="C")
    license_expiry = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="available")
    hire_date = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    emergency_contact = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    shared_employee = models.OneToOneField(
        "shared.Employee", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="driver_profile",
        help_text="Link to the centralized HR employee record")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DriverDocument(CompanyScoped):
    DOC_TYPES = [
        ("license", "Driving License"), ("id", "National ID"), ("medical", "Medical Certificate"),
        ("training", "Training Certificate"), ("other", "Other"),
    ]
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES)
    doc_no = models.CharField(max_length=80, blank=True)
    issued_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["expiry_date"]


# ---------------------------------------------------------------- Routes
class Route(CompanyScoped):
    name = models.CharField(max_length=200)
    origin = models.CharField(max_length=120)
    destination = models.CharField(max_length=120)
    distance_km = models.PositiveIntegerField(default=0, blank=True)
    est_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0, blank=True)
    stops = models.TextField(blank=True, help_text="Intermediate stops, one per line")
    restricted_zones = models.TextField(blank=True, help_text="Restricted zones / geofence notes")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("company", "name")

    def __str__(self):
        return self.name


class Geofence(CompanyScoped):
    name = models.CharField(max_length=120)
    zone_type = models.CharField(
        max_length=20,
        choices=[("depot", "Depot"), ("customer", "Customer Site"), ("restricted", "Restricted Zone"), ("checkpoint", "Checkpoint")],
        default="checkpoint",
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius_m = models.PositiveIntegerField(default=500, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_zone_type_display()})"


# ---------------------------------------------------------------- Trips & dispatch
class Trip(CompanyScoped):
    STATUS_CHOICES = [
        ("planned", "Planned"), ("dispatched", "Dispatched"), ("en_route", "En Route"),
        ("delivered", "Delivered"), ("completed", "Completed"), ("cancelled", "Cancelled"),
    ]
    PRIORITY_CHOICES = [("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")]

    trip_no = models.CharField(max_length=30)
    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name="trips")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="trips")
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name="trips")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="planned")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")
    cargo_desc = models.CharField(max_length=255, blank=True)
    cargo_weight_tons = models.DecimalField(max_digits=8, decimal_places=2, default=0, blank=True)
    departure_planned = models.DateTimeField(null=True, blank=True)
    departure_actual = models.DateTimeField(null=True, blank=True)
    arrival_planned = models.DateTimeField(null=True, blank=True)
    arrival_actual = models.DateTimeField(null=True, blank=True)
    odometer_start = models.PositiveIntegerField(default=0, blank=True)
    odometer_end = models.PositiveIntegerField(default=0, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("company", "trip_no")

    def __str__(self):
        return f"{self.trip_no} — {self.route}"

    @property
    def distance_km(self):
        d = self.odometer_end - self.odometer_start
        return d if d > 0 else (self.route.distance_km or 0)


class DispatchOrder(CompanyScoped):
    STATUS_CHOICES = [("scheduled", "Scheduled"), ("dispatched", "Dispatched"), ("cancelled", "Cancelled")]
    order_no = models.CharField(max_length=30)
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name="dispatch_order")
    scheduled_departure = models.DateTimeField()
    priority = models.CharField(max_length=10, choices=Trip.PRIORITY_CHOICES, default="normal")
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="scheduled")
    assigned_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-scheduled_departure"]

    def __str__(self):
        return self.order_no


class GPSPing(CompanyScoped):
    """Simulated / ingested GPS telemetry for a trip."""
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="pings")
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed_kmh = models.FloatField(default=0)
    event = models.CharField(max_length=30, blank=True, help_text="departed, checkpoint, deviation, idle, arrived")
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["recorded_at"]
        indexes = [models.Index(fields=["trip", "recorded_at"])]

    def __str__(self):
        return f"{self.trip.trip_no} @ {self.recorded_at:%H:%M}"


# ---------------------------------------------------------------- Fuel
class FuelLog(CompanyScoped):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="fuel_logs")
    trip = models.ForeignKey(Trip, null=True, blank=True, on_delete=models.SET_NULL, related_name="fuel_logs")
    date = models.DateField(default=timezone.now)
    station = models.CharField(max_length=120, blank=True)
    liters = models.DecimalField(max_digits=8, decimal_places=2)
    cost = models.DecimalField(max_digits=12, decimal_places=2)
    odometer_km = models.PositiveIntegerField(default=0, blank=True)
    receipt_no = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.vehicle.plate_no} — {self.liters}L on {self.date}"


# ---------------------------------------------------------------- Maintenance & inspection
class ServiceRecord(CompanyScoped):
    TYPE_CHOICES = [("preventive", "Preventive"), ("corrective", "Corrective"), ("inspection", "Inspection Service")]
    STATUS_CHOICES = [("scheduled", "Scheduled"), ("in_progress", "In Progress"), ("completed", "Completed"), ("cancelled", "Cancelled")]
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="services")
    service_type = models.CharField(max_length=15, choices=TYPE_CHOICES, default="preventive")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    odometer_km = models.PositiveIntegerField(default=0, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    workshop = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="scheduled")

    class Meta:
        ordering = ["-scheduled_date"]

    def __str__(self):
        return f"{self.vehicle.plate_no} — {self.title}"


class Inspection(CompanyScoped):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="inspections")
    driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name="inspections")
    date = models.DateField(default=timezone.now)
    checklist = models.JSONField(default=dict, blank=True)
    defects_found = models.TextField(blank=True)
    passed = models.BooleanField(default=True)
    approved_by = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.vehicle.plate_no} inspection {self.date}"


# ---------------------------------------------------------------- Parts & workshop
class SparePart(CompanyScoped):
    name = models.CharField(max_length=150)
    part_no = models.CharField(max_length=60, blank=True)
    category = models.CharField(max_length=80, blank=True)
    unit = models.CharField(max_length=20, default="pcs")
    qty_on_hand = models.PositiveIntegerField(default=0, blank=True)
    reorder_level = models.PositiveIntegerField(default=5, blank=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    location = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("company", "part_no", "name")

    def __str__(self):
        return self.name

    @property
    def low_stock(self):
        return self.qty_on_hand <= self.reorder_level


class WorkshopJob(CompanyScoped):
    STATUS_CHOICES = [("open", "Open"), ("in_progress", "In Progress"), ("waiting_parts", "Waiting Parts"), ("closed", "Closed")]
    job_no = models.CharField(max_length=30)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="workshop_jobs")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="open")
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    labor_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    parts_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    technician = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-opened_at"]
        unique_together = ("company", "job_no")

    def __str__(self):
        return self.job_no


class PartIssue(CompanyScoped):
    part = models.ForeignKey(SparePart, on_delete=models.CASCADE, related_name="issues")
    job = models.ForeignKey(WorkshopJob, on_delete=models.CASCADE, related_name="part_issues")
    quantity = models.PositiveIntegerField(default=1, blank=True)
    issued_at = models.DateTimeField(default=timezone.now)
    issued_to = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"{self.quantity}× {self.part.name} → {self.job.job_no}"


# ---------------------------------------------------------------- Delivery
class DeliveryOrder(CompanyScoped):
    STATUS_CHOICES = [
        ("pending", "Pending"), ("in_transit", "In Transit"), ("delivered", "Delivered"),
        ("failed", "Failed"), ("returned", "Returned"),
    ]
    order_no = models.CharField(max_length=30)
    trip = models.ForeignKey(Trip, null=True, blank=True, on_delete=models.SET_NULL, related_name="deliveries")
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=40, blank=True)
    destination = models.CharField(max_length=200)
    cargo_desc = models.CharField(max_length=255, blank=True)
    cargo_weight_tons = models.DecimalField(max_digits=8, decimal_places=2, default=0, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending")
    pod_signed_by = models.CharField(max_length=120, blank=True)
    pod_time = models.DateTimeField(null=True, blank=True)
    pod_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("company", "order_no")

    def __str__(self):
        return self.order_no


# ---------------------------------------------------------------- Expenses & finance
class TripExpense(CompanyScoped):
    CATEGORY_CHOICES = [
        ("fuel", "Fuel"), ("toll", "Toll / Road Fee"), ("allowance", "Driver Allowance"),
        ("repair", "Roadside Repair"), ("loading", "Loading / Unloading"), ("other", "Other"),
    ]
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="expenses")
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default="fuel")
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    paid_by = models.CharField(max_length=120, blank=True)
    receipt_no = models.CharField(max_length=60, blank=True)
    approved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.trip.trip_no} — {self.get_category_display()} {self.amount}"


class DriverAdvance(CompanyScoped):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="advances")
    trip = models.ForeignKey(Trip, null=True, blank=True, on_delete=models.SET_NULL, related_name="advances")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    purpose = models.CharField(max_length=255, blank=True)
    settled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date"]


class Invoice(CompanyScoped):
    STATUS_CHOICES = [
        ("draft", "Draft"), ("sent", "Sent"), ("paid", "Paid"),
        ("overdue", "Overdue"), ("cancelled", "Cancelled"),
    ]
    invoice_no = models.CharField(max_length=30)
    customer_name = models.CharField(max_length=200)
    trip = models.ForeignKey(Trip, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    delivery = models.ForeignKey(DeliveryOrder, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=0, blank=True)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="draft")
    issued_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_date"]
        unique_together = ("company", "invoice_no")

    def save(self, *args, **kwargs):
        self.total = (self.amount or 0) + (self.tax or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_no


class Payment(CompanyScoped):
    METHOD_CHOICES = [("cash", "Cash"), ("bank", "Bank Transfer"), ("mobile", "Mobile Money"), ("cheque", "Cheque")]
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default="bank")
    date = models.DateField(default=timezone.now)
    reference = models.CharField(max_length=80, blank=True)
    received_by = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.amount} → {self.invoice.invoice_no}"


# ---------------------------------------------------------------- HR & payroll



# ---------------------------------------------------------------- Alerts
class Alert(CompanyScoped):
    LEVEL_CHOICES = [("info", "Info"), ("warning", "Warning"), ("critical", "Critical")]
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="info")
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_level_display()}] {self.title}"
