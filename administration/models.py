"""Administration & System Management: branches, roles, approval rules, master
data, sessions, integrations, backups.

Works alongside shared.Membership / shared.CompanySettings / shared.AuditLog."""
from django.conf import settings
from django.db import models

from core.models import CompanyOwned


class Branch(CompanyOwned):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    manager = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Role(CompanyOwned):
    """Custom role with a permission matrix (beyond the 6 built-in roles)."""
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    can_view = models.BooleanField(default=True)
    can_create = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=True)
    can_delete = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    can_manage_finance = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ApprovalRule(CompanyOwned):
    """Which role must approve which document type above a threshold."""
    DOC_CHOICES = [("leave", "Leave Request"), ("expense", "Expense Claim"),
                   ("purchase_order", "Purchase Order"), ("payroll", "Payroll Run"),
                   ("loan", "Employee Loan"), ("bill", "Bill Payment")]
    document_type = models.CharField(max_length=30, choices=DOC_CHOICES)
    min_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    approver_role = models.CharField(max_length=20, choices=settings.ROLES,
                                     default=settings.ROLE_MANAGER)
    steps = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_document_type_display()} → {self.approver_role}"


class Currency(CompanyOwned):
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=80)
    symbol = models.CharField(max_length=8, blank=True)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=4, default=1,
                                        help_text="To company base currency")
    is_base = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} — {self.name}"


class NumberingSequence(CompanyOwned):
    """Document numbering: prefix + next number per document type."""
    document_type = models.CharField(max_length=60)
    prefix = models.CharField(max_length=20, blank=True)
    next_number = models.PositiveIntegerField(default=1)
    padding = models.PositiveIntegerField(default=4)

    def next(self):
        num = f"{self.prefix}{str(self.next_number).zfill(self.padding)}"
        self.next_number += 1
        self.save(update_fields=["next_number"])
        return num

    def __str__(self):
        return f"{self.document_type}: {self.prefix}…"


class FiscalCalendar(CompanyOwned):
    name = models.CharField(max_length=80)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LoginSession(models.Model):
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE,
                                related_name="login_sessions", null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="login_sessions")
    login_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-login_at"]

    def __str__(self):
        return f"{self.user.username} @ {self.login_at:%Y-%m-%d %H:%M}"


class NotificationSetting(CompanyOwned):
    CHANNEL_CHOICES = [("in_app", "In-App"), ("email", "Email"), ("sms", "SMS")]
    event = models.CharField(max_length=80, help_text="e.g. leave_approved, invoice_overdue")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="in_app")
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.event} → {self.channel}"


class SystemBackup(CompanyOwned):
    STATUS_CHOICES = [("scheduled", "Scheduled"), ("completed", "Completed"),
                      ("failed", "Failed")]
    name = models.CharField(max_length=120)
    backup_type = models.CharField(max_length=40, default="Database")
    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    size_mb = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.status})"


class Integration(CompanyOwned):
    STATUS_CHOICES = [("active", "Active"), ("inactive", "Inactive"), ("error", "Error")]
    name = models.CharField(max_length=120)
    provider = models.CharField(max_length=80, blank=True)
    direction = models.CharField(max_length=20, default="outbound")
    last_sync = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="inactive")
    config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.name} ({self.status})"
