"""Executive Management & Business Intelligence: custom report builder and
scheduled reports. Dashboards aggregate live data from every module."""
from django.db import models

from core.models import CompanyOwned


class ReportDefinition(CompanyOwned):
    """Custom report: pick a dataset, columns and a simple filter."""
    DATASET_CHOICES = [
        ("hr.employees", "HR — Employees"),
        ("hr.leave", "HR — Leave Requests"),
        ("hr.payslips", "HR — Payslips"),
        ("finance.bills", "Finance — Bills (AP)"),
        ("finance.ar", "Finance — AR Invoices"),
        ("finance.journal", "Finance — Journal Entries"),
        ("finance.expenses", "Finance — Expense Claims"),
        ("imports.po", "Import — Purchase Orders"),
        ("imports.shipments", "Import — Shipments"),
        ("exports.orders", "Export — Orders"),
        ("exports.invoices", "Export — Invoices"),
        ("manufacturing.orders", "Manufacturing — Production Orders"),
        ("rentals.leases", "Rental — Leases"),
        ("rentals.payments", "Rental — Rent Payments"),
        ("fleet.trips", "Fleet — Trips"),
        ("fleet.invoices", "Fleet — Invoices"),
    ]
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    dataset = models.CharField(max_length=40, choices=DATASET_CHOICES)
    columns = models.JSONField(default=list, blank=True,
                               help_text="Accessors, e.g. ['invoice_no','customer_name','amount']")
    status_filter = models.CharField(max_length=40, blank=True,
                                     help_text="Optional status value to filter by")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ScheduledReport(CompanyOwned):
    FREQUENCY_CHOICES = [("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")]
    report = models.ForeignKey(ReportDefinition, on_delete=models.CASCADE,
                               related_name="schedules")
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default="weekly")
    recipients = models.CharField(max_length=255, blank=True,
                                  help_text="Comma-separated emails")
    last_run = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.report.name} ({self.frequency})"
