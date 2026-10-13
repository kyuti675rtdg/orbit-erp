"""HR Management: recruitment, onboarding, shifts, payroll depth, benefits,
performance, training, employment events, HR documents.

Works alongside shared.Department / shared.Employee / shared.Attendance /
shared.LeaveRequest / shared.PayrollRun (the centralized HR data layer)."""
from django.db import models

from core.models import CompanyOwned


# ------------------------------------------------------------ organization
class Position(CompanyOwned):
    department = models.ForeignKey("shared.Department", on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="positions")
    title = models.CharField(max_length=120)
    level = models.CharField(max_length=60, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title


# ------------------------------------------------------------ recruitment
class JobVacancy(CompanyOwned):
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed"), ("on_hold", "On Hold")]
    title = models.CharField(max_length=150)
    department = models.ForeignKey("shared.Department", on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="vacancies")
    position = models.ForeignKey(Position, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="vacancies")
    description = models.TextField(blank=True)
    openings = models.PositiveIntegerField(default=1)
    posted_date = models.DateField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")

    def __str__(self):
        return self.title


class Applicant(CompanyOwned):
    STAGE_CHOICES = [("applied", "Applied"), ("screening", "Screening"),
                     ("interview", "Interview"), ("offer", "Offer"),
                     ("hired", "Hired"), ("rejected", "Rejected")]
    vacancy = models.ForeignKey(JobVacancy, on_delete=models.CASCADE, related_name="applicants")
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    cover_note = models.TextField(blank=True)
    cv = models.FileField(upload_to="hr/cv/%Y/%m/", blank=True, null=True)
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default="applied")
    rating = models.PositiveIntegerField(default=0, help_text="0–5")
    applied_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} — {self.vacancy.title}"


# ------------------------------------------------------------ onboarding
class OnboardingTask(CompanyOwned):
    employee = models.ForeignKey("shared.Employee", on_delete=models.CASCADE,
                                 related_name="onboarding_tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee.name}: {self.title}"


# ------------------------------------------------------------ shifts & timesheets
class Shift(CompanyOwned):
    name = models.CharField(max_length=80)
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class TimesheetEntry(CompanyOwned):
    STATUS_CHOICES = [("draft", "Draft"), ("submitted", "Submitted"), ("approved", "Approved")]
    employee = models.ForeignKey("shared.Employee", on_delete=models.CASCADE,
                                 related_name="timesheets")
    date = models.DateField()
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="timesheets")
    hours = models.DecimalField(max_digits=5, decimal_places=2, default=8)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    note = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee.name} — {self.date} ({self.hours}h)"


# ------------------------------------------------------------ payroll depth
class SalaryStructure(CompanyOwned):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class SalaryComponent(CompanyOwned):
    KIND_CHOICES = [("allowance", "Allowance"), ("deduction", "Deduction")]
    TYPE_CHOICES = [("fixed", "Fixed Amount"), ("percent", "Percent of Basic")]
    structure = models.ForeignKey(SalaryStructure, on_delete=models.CASCADE,
                                  related_name="components")
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="allowance")
    amount_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="fixed")
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.structure.name}: {self.name}"


class Payslip(CompanyOwned):
    STATUS_CHOICES = [("draft", "Draft"), ("approved", "Approved"), ("paid", "Paid")]
    employee = models.ForeignKey("shared.Employee", on_delete=models.CASCADE,
                                 related_name="payslips")
    payroll_run = models.ForeignKey("shared.PayrollRun", on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="payslips")
    period = models.DateField(help_text="First day of the pay period")
    basic = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    class Meta:
        ordering = ["-period"]

    def save(self, *args, **kwargs):
        self.net = (self.basic or 0) + (self.allowances or 0) - (self.deductions or 0) - (self.tax or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.name} — {self.period:%b %Y}"


# ------------------------------------------------------------ benefits & loans
class Benefit(CompanyOwned):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    eligibility = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class EmployeeBenefit(CompanyOwned):
    employee = models.ForeignKey("shared.Employee", on_delete=models.CASCADE,
                                 related_name="benefits")
    benefit = models.ForeignKey(Benefit, on_delete=models.CASCADE, related_name="assignments")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.employee.name}: {self.benefit.name}"


class EmployeeLoan(CompanyOwned):
    STATUS_CHOICES = [("pending", "Pending"), ("approved", "Approved"),
                      ("rejected", "Rejected"), ("repaying", "Repaying"), ("closed", "Closed")]
    employee = models.ForeignKey("shared.Employee", on_delete=models.CASCADE,
                                 related_name="loans")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remaining = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    purpose = models.CharField(max_length=200, blank=True)
    request_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    def save(self, *args, **kwargs):
        if not self.pk and not self.remaining:
            self.remaining = self.amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.name}: {self.amount:,.0f}"


# ------------------------------------------------------------ performance
class PerformanceReview(CompanyOwned):
    STATUS_CHOICES = [("draft", "Draft"), ("in_review", "In Review"), ("completed", "Completed")]
    employee = models.ForeignKey("shared.Employee", on_delete=models.CASCADE,
                                 related_name="reviews")
    reviewer = models.CharField(max_length=150, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0, help_text="0–5")
    strengths = models.TextField(blank=True)
    improvements = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    def __str__(self):
        per = self.period_end.strftime("%Y") if self.period_end else "—"
        return f"{self.employee.name} review ({per})"


class Objective(CompanyOwned):
    STATUS_CHOICES = [("not_started", "Not Started"), ("in_progress", "In Progress"),
                      ("achieved", "Achieved"), ("missed", "Missed")]
    employee = models.ForeignKey("shared.Employee", on_delete=models.CASCADE,
                                 related_name="objectives")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_date = models.DateField(null=True, blank=True)
    progress = models.PositiveIntegerField(default=0, help_text="0–100%")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="not_started")

    def __str__(self):
        return f"{self.employee.name}: {self.title}"


# ------------------------------------------------------------ training
class Training(CompanyOwned):
    title = models.CharField(max_length=200)
    provider = models.CharField(max_length=150, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title


class TrainingEnrollment(CompanyOwned):
    STATUS_CHOICES = [("enrolled", "Enrolled"), ("completed", "Completed"), ("dropped", "Dropped")]
    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name="enrollments")
    employee = models.ForeignKey("shared.Employee", on_delete=models.CASCADE,
                                 related_name="trainings")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="enrolled")
    completed_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee.name}: {self.training.title}"


class Certification(CompanyOwned):
    employee = models.ForeignKey("shared.Employee", on_delete=models.CASCADE,
                                 related_name="certifications")
    name = models.CharField(max_length=200)
    issuer = models.CharField(max_length=150, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    certificate_no = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return f"{self.employee.name}: {self.name}"


# ------------------------------------------------------------ employment events
class EmploymentEvent(CompanyOwned):
    TYPE_CHOICES = [("promotion", "Promotion"), ("transfer", "Transfer"),
                    ("warning", "Warning"), ("disciplinary", "Disciplinary Action"),
                    ("probation_end", "Probation Completed"), ("exit", "Exit / Offboarding")]
    employee = models.ForeignKey("shared.Employee", on_delete=models.CASCADE,
                                 related_name="events")
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date = models.DateField(null=True, blank=True)
    new_position = models.CharField(max_length=120, blank=True)
    new_department = models.ForeignKey("shared.Department", on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name="events")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee.name}: {self.get_event_type_display()}"


# ------------------------------------------------------------ HR documents
class HRDocument(CompanyOwned):
    CATEGORY_CHOICES = [("policy", "Policy"), ("contract", "Contract"),
                        ("handbook", "Handbook"), ("form", "Form"), ("other", "Other")]
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="policy")
    description = models.TextField(blank=True)
    version = models.CharField(max_length=20, default="1.0")
    file = models.FileField(upload_to="hr/documents/%Y/%m/", blank=True, null=True)

    def __str__(self):
        return f"{self.title} (v{self.version})"
