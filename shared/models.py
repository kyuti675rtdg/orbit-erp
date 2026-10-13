"""Shared modules for every company: HR & Payroll, Finance & Accounting,
Document Management, Communication, User & Access, Administration."""
from django.conf import settings
from django.db import models

from core.models import Company, CompanyOwned


# ------------------------------------------------------------ HR & Payroll
class Department(CompanyOwned):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Employee(CompanyOwned):
    TYPE_CHOICES = [("full_time", "Full-time"), ("part_time", "Part-time"),
                    ("contract", "Contract"), ("intern", "Intern")]
    STATUS_CHOICES = [("active", "Active"), ("on_leave", "On Leave"),
                      ("terminated", "Terminated")]
    employee_id = models.CharField(max_length=30)
    name = models.CharField(max_length=150)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="employees")
    position = models.CharField(max_length=120, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    employment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="full_time")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    def __str__(self):
        return f"{self.name} ({self.employee_id})"


class Attendance(CompanyOwned):
    STATUS_CHOICES = [("present", "Present"), ("absent", "Absent"),
                      ("late", "Late"), ("leave", "On Leave")]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="present")

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee.name} — {self.date}"


class LeaveRequest(CompanyOwned):
    TYPE_CHOICES = [("annual", "Annual"), ("sick", "Sick"), ("maternity", "Maternity"),
                    ("unpaid", "Unpaid"), ("other", "Other")]
    STATUS_CHOICES = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leaves")
    leave_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="annual")
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveIntegerField(default=1)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    def __str__(self):
        return f"{self.employee.name} — {self.leave_type} ({self.status})"


class PayrollRun(CompanyOwned):
    STATUS_CHOICES = [("draft", "Draft"), ("approved", "Approved"), ("paid", "Paid")]
    month = models.DateField(help_text="First day of the payroll month")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    total_gross = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_net = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Payroll {self.month:%b %Y} ({self.get_status_display()})"


# ------------------------------------------------------------ Finance & Accounting
class GLAccount(CompanyOwned):
    TYPE_CHOICES = [("asset", "Asset"), ("liability", "Liability"), ("equity", "Equity"),
                    ("revenue", "Revenue"), ("expense", "Expense")]
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=150)
    account_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} — {self.name}"


class JournalEntry(CompanyOwned):
    date = models.DateField()
    reference = models.CharField(max_length=40, blank=True)
    account = models.ForeignKey(GLAccount, on_delete=models.PROTECT, related_name="journal_entries")
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.date} — {self.account.code} ({self.reference})"


class Bill(CompanyOwned):
    STATUS_CHOICES = [("draft", "Draft"), ("unpaid", "Unpaid"),
                      ("partial", "Partially Paid"), ("paid", "Paid")]
    vendor_name = models.CharField(max_length=150)
    bill_no = models.CharField(max_length=40)
    bill_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unpaid")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.bill_no} — {self.vendor_name}"


class CompanyAsset(CompanyOwned):
    STATUS_CHOICES = [("in_use", "In Use"), ("idle", "Idle"),
                      ("maintenance", "Maintenance"), ("disposed", "Disposed")]
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=80, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    assigned_to = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_use")

    def __str__(self):
        return self.name


# ------------------------------------------------------------ Communication
class Announcement(CompanyOwned):
    title = models.CharField(max_length=200)
    body = models.TextField()
    publish_date = models.DateField()
    audience = models.CharField(max_length=80, default="All employees")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class Notification(models.Model):
    """Per-user notification inbox (topbar bell)."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="notifications")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.title}"


# ------------------------------------------------------------ Document Management
class CompanyDocument(CompanyOwned):
    CATEGORY_CHOICES = [("policy", "Policy"), ("contract", "Contract"),
                        ("certificate", "Certificate"), ("report", "Report"),
                        ("hr", "HR"), ("finance", "Finance"), ("other", "Other")]
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    description = models.TextField(blank=True)
    version = models.CharField(max_length=20, default="1.0")
    reference_no = models.CharField(max_length=40, blank=True)
    file = models.FileField(upload_to="documents/%Y/%m/", blank=True, null=True)
    uploaded_by = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"{self.title} (v{self.version})"


# ------------------------------------------------------------ Administration
class AuditLog(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="audit_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True)
    action = models.CharField(max_length=20)  # created / updated / deleted
    model_name = models.CharField(max_length=80)
    object_repr = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.user} {self.action} {self.model_name}"


class CompanySettings(CompanyOwned):
    currency = models.CharField(max_length=10, default="ETB")
    fiscal_year_start = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField("Tax ID", max_length=40, blank=True)

    class Meta:
        verbose_name_plural = "company settings"

    def __str__(self):
        return f"Settings — {self.company.name}"
