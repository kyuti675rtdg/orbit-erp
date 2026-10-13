"""HR Management entity registry: centralized HRMS for every company.

Presents shared.Department/Employee/Attendance/LeaveRequest/PayrollRun
(the centralized HR data layer) plus the hr app's depth models.
"""
from core.models import Membership  # noqa: F401 (kept for admin module use)

from shared import models as sm

from . import models as m

E = lambda **kw: kw  # noqa: E731

APPROVER_ROLES = ["owner", "admin", "manager"]

ENTITIES = {
    # ---- Workforce
    "departments": E(
        title="Departments", singular="Department", icon="building",
        model=sm.Department,
        list_display=[("Name", "name"), ("Code", "code"), ("Description", "description")],
        search=["name", "code"],
        form_fields=["name", "code", "description"],
        detail_related=[
            ("Employees", "employees", [("ID", "employee_id"), ("Name", "name"), ("Status", "status")]),
        ],
    ),
    "positions": E(
        title="Positions", singular="Position", icon="layers",
        model=m.Position,
        list_display=[("Title", "title"), ("Department", "department__name"), ("Level", "level")],
        search=["title", "level"],
        form_fields=["title", "department", "level", "description"],
    ),
    "employees": E(
        title="Employees", singular="Employee", icon="users",
        model=sm.Employee,
        list_display=[("ID", "employee_id"), ("Name", "name"), ("Department", "department__name"),
                      ("Position", "position"), ("Type", "employment_type"), ("Status", "status")],
        search=["name", "employee_id", "position"],
        form_fields=["employee_id", "name", "user", "department", "branch", "position",
                     "hire_date", "phone", "email", "salary", "employment_type", "status"],
        detail_related=[
            ("Attendance", "attendance", [("Date", "date"), ("Status", "status")]),
            ("Leave Requests", "leaves", [("Type", "leave_type"), ("Start", "start_date"), ("Status", "status")]),
            ("Payslips", "payslips", [("Period", "period"), ("Net", "net"), ("Status", "status")]),
            ("Objectives", "objectives", [("Title", "title"), ("Progress", "progress"), ("Status", "status")]),
        ],
    ),
    "employment-events": E(
        title="Promotions, Transfers & Disciplinary", singular="Employment Event", icon="clipboard",
        model=m.EmploymentEvent,
        list_display=[("Employee", "employee__name"), ("Type", "event_type"),
                      ("Date", "date"), ("New Position", "new_position")],
        search=["employee__name", "description"],
        form_fields=["employee", "event_type", "date", "new_position", "new_department", "description"],
    ),
    # ---- Recruitment
    "vacancies": E(
        title="Job Vacancies", singular="Vacancy", icon="search",
        model=m.JobVacancy,
        list_display=[("Title", "title"), ("Department", "department__name"),
                      ("Openings", "openings"), ("Closing", "closing_date"), ("Status", "status")],
        search=["title", "description"],
        form_fields=["title", "department", "position", "description", "openings",
                     "posted_date", "closing_date", "status"],
        detail_related=[
            ("Applicants", "applicants", [("Name", "name"), ("Stage", "stage"), ("Rating", "rating")]),
        ],
        workflow={
            "status_field": "status",
            "transitions": [
                {"name": "close", "label": "Close", "from": ["open", "on_hold"],
                 "to": "closed", "roles": APPROVER_ROLES},
                {"name": "reopen", "label": "Reopen", "from": ["closed", "on_hold"],
                 "to": "open", "roles": APPROVER_ROLES},
            ],
        },
    ),
    "applicants": E(
        title="Applicants", singular="Applicant", icon="users",
        model=m.Applicant,
        list_display=[("Name", "name"), ("Vacancy", "vacancy__title"),
                      ("Stage", "stage"), ("Rating", "rating"), ("Applied", "applied_date")],
        search=["name", "email", "cover_note"],
        form_fields=["vacancy", "name", "email", "phone", "cover_note", "cv",
                     "stage", "rating", "applied_date"],
        workflow={
            "status_field": "stage",
            "transitions": [
                {"name": "hire", "label": "Hire", "from": ["applied", "screening", "interview", "offer"],
                 "to": "hired", "roles": APPROVER_ROLES, "post": "hr.hooks.on_applicant_hired"},
                {"name": "reject", "label": "Reject",
                 "from": ["applied", "screening", "interview", "offer"],
                 "to": "rejected", "roles": APPROVER_ROLES},
            ],
        },
    ),
    "onboarding": E(
        title="Onboarding Tasks", singular="Onboarding Task", icon="clipboard",
        model=m.OnboardingTask,
        list_display=[("Employee", "employee__name"), ("Task", "title"),
                      ("Due", "due_date"), ("Done", "is_completed")],
        search=["title", "employee__name"],
        form_fields=["employee", "title", "description", "due_date", "is_completed", "completed_date"],
    ),
    # ---- Time
    "shifts": E(
        title="Shifts", singular="Shift", icon="clock",
        model=m.Shift,
        list_display=[("Name", "name"), ("Start", "start_time"), ("End", "end_time")],
        search=["name"],
        form_fields=["name", "start_time", "end_time", "description"],
    ),
    "attendance": E(
        title="Attendance", singular="Attendance Record", icon="clock",
        model=sm.Attendance,
        list_display=[("Employee", "employee__name"), ("Date", "date"),
                      ("Check In", "check_in"), ("Check Out", "check_out"), ("Status", "status")],
        search=["employee__name", "notes"],
        form_fields=["employee", "date", "check_in", "check_out", "status", "notes"],
    ),
    "timesheets": E(
        title="Timesheets", singular="Timesheet Entry", icon="file",
        model=m.TimesheetEntry,
        list_display=[("Employee", "employee__name"), ("Date", "date"), ("Hours", "hours"),
                      ("Overtime", "overtime_hours"), ("Status", "status")],
        search=["employee__name", "note"],
        form_fields=["employee", "date", "shift", "hours", "overtime_hours", "note", "status"],
        workflow={
            "status_field": "status",
            "transitions": [
                {"name": "submit", "label": "Submit", "from": ["draft"], "to": "submitted",
                 "roles": ["owner", "admin", "manager", "dispatcher", "accountant", "viewer"]},
                {"name": "approve", "label": "Approve", "from": ["submitted"],
                 "to": "approved", "roles": APPROVER_ROLES},
            ],
        },
    ),
    "leave-requests": E(
        title="Leave Requests", singular="Leave Request", icon="calendar",
        model=sm.LeaveRequest,
        list_display=[("Employee", "employee__name"), ("Type", "leave_type"),
                      ("Start", "start_date"), ("End", "end_date"), ("Days", "days"), ("Status", "status")],
        search=["employee__name", "reason"],
        form_fields=["employee", "leave_type", "start_date", "end_date", "days", "reason", "status"],
        workflow={
            "status_field": "status",
            "transitions": [
                {"name": "approve", "label": "Approve", "from": ["pending"],
                 "to": "approved", "roles": APPROVER_ROLES,
                 "post": "hr.hooks.on_leave_decided"},
                {"name": "reject", "label": "Reject", "from": ["pending"],
                 "to": "rejected", "roles": APPROVER_ROLES,
                 "post": "hr.hooks.on_leave_decided"},
            ],
        },
    ),
    # ---- Payroll
    "salary-structures": E(
        title="Salary Structures", singular="Salary Structure", icon="layers",
        model=m.SalaryStructure,
        list_display=[("Name", "name"), ("Active", "is_active")],
        search=["name"],
        form_fields=["name", "description", "is_active"],
        detail_related=[
            ("Components", "components", [("Name", "name"), ("Kind", "kind"), ("Value", "value")]),
        ],
    ),
    "salary-components": E(
        title="Allowances & Deductions", singular="Salary Component", icon="wallet",
        model=m.SalaryComponent,
        list_display=[("Structure", "structure__name"), ("Name", "name"),
                      ("Kind", "kind"), ("Type", "amount_type"), ("Value", "value")],
        search=["name"],
        form_fields=["structure", "name", "kind", "amount_type", "value"],
    ),
    "payroll-runs": E(
        title="Payroll Runs", singular="Payroll Run", icon="card", finance=True,
        model=sm.PayrollRun,
        list_display=[("Month", "month"), ("Status", "status"), ("Gross", "total_gross"),
                      ("Deductions", "total_deductions"), ("Net", "total_net")],
        search=["notes"],
        form_fields=["month", "status", "total_gross", "total_deductions", "total_net", "notes"],
        detail_related=[
            ("Payslips", "payslips", [("Employee", "employee__name"), ("Net", "net"), ("Status", "status")]),
        ],
        workflow={
            "status_field": "status",
            "transitions": [
                {"name": "approve", "label": "Approve & Post", "from": ["draft"],
                 "to": "approved", "roles": ["owner", "admin", "accountant"],
                 "post": "hr.hooks.on_payroll_approved"},
                {"name": "pay", "label": "Mark Paid", "from": ["approved"],
                 "to": "paid", "roles": ["owner", "admin", "accountant"]},
            ],
        },
    ),
    "payslips": E(
        title="Payslips", singular="Payslip", icon="receipt", finance=True,
        model=m.Payslip,
        list_display=[("Employee", "employee__name"), ("Period", "period"),
                      ("Basic", "basic"), ("Allowances", "allowances"),
                      ("Tax", "tax"), ("Net", "net"), ("Status", "status")],
        search=["employee__name"],
        form_fields=["employee", "payroll_run", "period", "basic", "allowances",
                     "deductions", "tax", "status"],
    ),
    "benefits": E(
        title="Benefits", singular="Benefit", icon="gift",
        model=m.Benefit,
        list_display=[("Name", "name"), ("Eligibility", "eligibility")],
        search=["name"],
        form_fields=["name", "description", "eligibility"],
    ),
    "employee-benefits": E(
        title="Employee Benefits", singular="Employee Benefit", icon="gift",
        model=m.EmployeeBenefit,
        list_display=[("Employee", "employee__name"), ("Benefit", "benefit__name"),
                      ("Start", "start_date"), ("Amount", "amount")],
        search=["employee__name"],
        form_fields=["employee", "benefit", "start_date", "end_date", "amount"],
    ),
    "loans": E(
        title="Loans & Advances", singular="Loan", icon="bank",
        model=m.EmployeeLoan,
        list_display=[("Employee", "employee__name"), ("Amount", "amount"),
                      ("Monthly", "monthly_deduction"), ("Remaining", "remaining"),
                      ("Status", "status")],
        search=["employee__name", "purpose"],
        form_fields=["employee", "amount", "monthly_deduction", "remaining",
                     "purpose", "request_date", "status"],
        workflow={
            "status_field": "status",
            "transitions": [
                {"name": "approve", "label": "Approve", "from": ["pending"],
                 "to": "approved", "roles": APPROVER_ROLES},
                {"name": "reject", "label": "Reject", "from": ["pending"],
                 "to": "rejected", "roles": APPROVER_ROLES},
            ],
        },
    ),
    # ---- Performance
    "reviews": E(
        title="Performance Reviews", singular="Performance Review", icon="chart",
        model=m.PerformanceReview,
        list_display=[("Employee", "employee__name"), ("Reviewer", "reviewer"),
                      ("Period End", "period_end"), ("Rating", "rating"), ("Status", "status")],
        search=["employee__name", "reviewer"],
        form_fields=["employee", "reviewer", "period_start", "period_end", "rating",
                     "strengths", "improvements", "status"],
    ),
    "objectives": E(
        title="Objectives & KPIs", singular="Objective", icon="target",
        model=m.Objective,
        list_display=[("Employee", "employee__name"), ("Title", "title"),
                      ("Target", "target_date"), ("Progress", "progress"), ("Status", "status")],
        search=["title", "employee__name"],
        form_fields=["employee", "title", "description", "target_date", "progress", "status"],
    ),
    "trainings": E(
        title="Trainings", singular="Training", icon="book",
        model=m.Training,
        list_display=[("Title", "title"), ("Provider", "provider"),
                      ("Start", "start_date"), ("Cost", "cost")],
        search=["title", "provider"],
        form_fields=["title", "provider", "start_date", "end_date", "cost", "description"],
        detail_related=[
            ("Enrollments", "enrollments", [("Employee", "employee__name"), ("Status", "status")]),
        ],
    ),
    "training-enrollments": E(
        title="Training Enrollments", singular="Enrollment", icon="users",
        model=m.TrainingEnrollment,
        list_display=[("Training", "training__title"), ("Employee", "employee__name"),
                      ("Status", "status"), ("Completed", "completed_date")],
        search=["employee__name"],
        form_fields=["training", "employee", "status", "completed_date"],
    ),
    "certifications": E(
        title="Certifications", singular="Certification", icon="shield",
        model=m.Certification,
        list_display=[("Employee", "employee__name"), ("Name", "name"),
                      ("Issuer", "issuer"), ("Expiry", "expiry_date")],
        search=["name", "employee__name", "certificate_no"],
        form_fields=["employee", "name", "issuer", "issue_date", "expiry_date", "certificate_no"],
    ),
    # ---- Documents
    "hr-documents": E(
        title="HR Documents & Policies", singular="HR Document", icon="file",
        model=m.HRDocument,
        list_display=[("Title", "title"), ("Category", "category"), ("Version", "version")],
        search=["title", "description"],
        form_fields=["title", "category", "description", "version", "file"],
    ),
}
