"""Building & Property Rental: properties, units, tenants, leases, collections."""
from django.db import models

from core.models import CompanyOwned


class Property(CompanyOwned):
    name = models.CharField(max_length=150)
    property_type = models.CharField(max_length=20, choices=[("residential", "Residential"), ("commercial", "Commercial"), ("mixed", "Mixed Use")], default="residential")
    city = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=255, blank=True)
    manager = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.name


class Building(CompanyOwned):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="buildings")
    name = models.CharField(max_length=120)
    floors = models.PositiveIntegerField(default=1)
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.property.name} — {self.name}"


class Unit(CompanyOwned):
    unit_no = models.CharField(max_length=40)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="units")
    floor = models.PositiveIntegerField(default=0)
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    area_sqm = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    monthly_rent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[("vacant", "Vacant"), ("occupied", "Occupied"), ("maintenance", "Maintenance")], default="vacant")

    def __str__(self):
        return f"{self.building.name} — Unit {self.unit_no}"


class Tenant(CompanyOwned):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    id_number = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=20, choices=[("active", "Active"), ("former", "Former")], default="active")

    def __str__(self):
        return self.name


class Lease(CompanyOwned):
    STATUS = [("draft", "Draft"), ("active", "Active"), ("expiring", "Expiring Soon"),
              ("expired", "Expired"), ("terminated", "Terminated")]
    lease_no = models.CharField(max_length=40)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="leases")
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="leases")
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="draft")

    def __str__(self):
        return self.lease_no


class RentSchedule(CompanyOwned):
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="schedule")
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("paid", "Paid"), ("overdue", "Overdue")], default="pending")

    def __str__(self):
        return f"{self.lease.lease_no} — {self.due_date:%b %Y}"


class RentInvoice(CompanyOwned):
    STATUS = [("unpaid", "Unpaid"), ("partial", "Partially Paid"), ("paid", "Paid")]
    invoice_no = models.CharField(max_length=40)
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="invoices")
    issue_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="unpaid")

    def __str__(self):
        return self.invoice_no


class RentPayment(CompanyOwned):
    payment_no = models.CharField(max_length=40)
    invoice = models.ForeignKey(RentInvoice, on_delete=models.CASCADE, related_name="payments")
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    method = models.CharField(max_length=40, blank=True)
    reference = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return self.payment_no


class Deposit(CompanyOwned):
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="deposits")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[("held", "Held"), ("refunded", "Refunded"), ("forfeited", "Forfeited")], default="held")
    refund_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Deposit — {self.lease.lease_no}"


class MaintenanceRequest(CompanyOwned):
    STATUS = [("open", "Open"), ("in_progress", "In Progress"), ("resolved", "Resolved"), ("closed", "Closed")]
    request_no = models.CharField(max_length=40)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="maintenance_requests")
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_requests")
    request_date = models.DateField()
    category = models.CharField(max_length=80, blank=True)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")], default="medium")
    status = models.CharField(max_length=20, choices=STATUS, default="open")

    def __str__(self):
        return self.request_no


class MaintenanceWorkOrder(CompanyOwned):
    wo_no = models.CharField(max_length=40)
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name="work_orders")
    assigned_to = models.CharField(max_length=120, blank=True)
    scheduled_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[("open", "Open"), ("in_progress", "In Progress"), ("done", "Done")], default="open")

    def __str__(self):
        return self.wo_no


class UtilityBill(CompanyOwned):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="utility_bills")
    utility_type = models.CharField(max_length=40, choices=[("water", "Water"), ("electricity", "Electricity"), ("internet", "Internet"), ("other", "Other")], default="water")
    billing_month = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[("unpaid", "Unpaid"), ("paid", "Paid")], default="unpaid")

    def __str__(self):
        return f"{self.unit} — {self.utility_type} {self.billing_month:%b %Y}"


class PropertyExpense(CompanyOwned):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="expenses")
    category = models.CharField(max_length=80, blank=True)
    description = models.CharField(max_length=255, blank=True)
    expense_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.property.name} — {self.amount:,}"
