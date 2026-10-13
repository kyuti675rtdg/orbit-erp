"""Entity registry for shared modules (HR, Finance, Documents, Communication,
User & Access, Administration). Consumed by core.crud."""
from core.models import Membership

from . import models as m

E = lambda **kw: kw  # noqa: E731

ENTITIES = {
    # ---- HR & Payroll
    "departments": E(
        title="Departments", singular="Department", icon="building",
        model=m.Department,
        list_display=[("Name", "name"), ("Code", "code"), ("Description", "description")],
        search=["name", "code"],
        form_fields=["name", "code", "description"],
    ),
    "employees": E(
        title="Employees", singular="Employee", icon="users",
        model=m.Employee,
        list_display=[("ID", "employee_id"), ("Name", "name"), ("Department", "department__name"),
                      ("Position", "position"), ("Type", "employment_type"), ("Status", "status")],
        search=["name", "employee_id", "position"],
        form_fields=["employee_id", "name", "department", "position", "hire_date",
                     "phone", "email", "salary", "employment_type", "status"],
        detail_related=[
            ("Attendance", "attendance", [("Date", "date"), ("Status", "status")]),
            ("Leave Requests", "leaves", [("Type", "leave_type"), ("Start", "start_date"), ("Status", "status")]),
        ],
    ),
    "attendance": E(
        title="Attendance", singular="Attendance Record", icon="clock",
        model=m.Attendance,
        list_display=[("Employee", "employee__name"), ("Date", "date"),
                      ("Check In", "check_in"), ("Check Out", "check_out"), ("Status", "status")],
        search=["employee__name"],
        form_fields=["employee", "date", "check_in", "check_out", "status"],
    ),
    "leave-requests": E(
        title="Leave Requests", singular="Leave Request", icon="calendar",
        model=m.LeaveRequest,
        list_display=[("Employee", "employee__name"), ("Type", "leave_type"),
                      ("Start", "start_date"), ("End", "end_date"), ("Days", "days"), ("Status", "status")],
        search=["employee__name", "reason"],
        form_fields=["employee", "leave_type", "start_date", "end_date", "days", "reason", "status"],
    ),
    "payroll-runs": E(
        title="Payroll Runs", singular="Payroll Run", icon="card", finance=True,
        model=m.PayrollRun,
        list_display=[("Month", "month"), ("Status", "status"), ("Gross", "total_gross"),
                      ("Deductions", "total_deductions"), ("Net", "total_net")],
        search=["notes"],
        form_fields=["month", "status", "total_gross", "total_deductions", "total_net", "notes"],
    ),
    # ---- Finance & Accounting
    "gl-accounts": E(
        title="Chart of Accounts", singular="GL Account", icon="file", finance=True,
        model=m.GLAccount,
        list_display=[("Code", "code"), ("Name", "name"), ("Type", "account_type"),
                      ("Opening Balance", "opening_balance"), ("Active", "is_active")],
        search=["code", "name"],
        form_fields=["code", "name", "account_type", "opening_balance", "is_active"],
        detail_related=[
            ("Journal Entries", "journal_entries", [("Date", "date"), ("Debit", "debit"), ("Credit", "credit")]),
        ],
    ),
    "journal": E(
        title="Journal Entries", singular="Journal Entry", icon="pencil", finance=True,
        model=m.JournalEntry,
        list_display=[("Date", "date"), ("Reference", "reference"), ("Account", "account__name"),
                      ("Debit", "debit"), ("Credit", "credit")],
        search=["reference", "description", "account__name"],
        form_fields=["date", "reference", "account", "debit", "credit", "description"],
    ),
    "bills": E(
        title="Bills (AP)", singular="Bill", icon="receipt", finance=True,
        model=m.Bill,
        list_display=[("Bill No", "bill_no"), ("Vendor", "vendor_name"), ("Date", "bill_date"),
                      ("Due", "due_date"), ("Amount", "amount"), ("Paid", "paid_amount"), ("Status", "status")],
        search=["bill_no", "vendor_name"],
        form_fields=["vendor_name", "bill_no", "bill_date", "due_date", "amount", "paid_amount", "status", "notes"],
    ),
    "assets": E(
        title="Fixed Assets", singular="Asset", icon="box",
        model=m.CompanyAsset,
        list_display=[("Name", "name"), ("Category", "category"), ("Purchase Date", "purchase_date"),
                      ("Cost", "cost"), ("Assigned To", "assigned_to"), ("Status", "status")],
        search=["name", "category", "assigned_to"],
        form_fields=["name", "category", "purchase_date", "cost", "assigned_to", "status"],
    ),
    # ---- Communication
    "announcements": E(
        title="Announcements", singular="Announcement", icon="bell",
        model=m.Announcement,
        list_display=[("Title", "title"), ("Publish Date", "publish_date"),
                      ("Audience", "audience"), ("Active", "is_active")],
        search=["title", "body"],
        form_fields=["title", "body", "publish_date", "audience", "is_active"],
    ),
    # ---- Document Management
    "documents": E(
        title="Documents", singular="Document", icon="file",
        model=m.CompanyDocument,
        list_display=[("Title", "title"), ("Category", "category"), ("Version", "version"),
                      ("Reference", "reference_no"), ("Uploaded By", "uploaded_by")],
        search=["title", "reference_no", "description"],
        form_fields=["title", "category", "description", "version", "reference_no", "file", "uploaded_by"],
    ),
    # ---- Administration
    "members": E(
        title="Users & Roles", singular="Member", icon="users",
        model=Membership,
        list_display=[("User", "user__username"), ("Role", "role"), ("Active", "is_active"), ("Joined", "joined_at")],
        search=["user__username"],
        form_fields=["user", "role", "is_active"],
    ),
    "audit-logs": E(
        title="Audit Logs", singular="Audit Log", icon="shield", readonly=True,
        model=m.AuditLog,
        list_display=[("Time", "timestamp"), ("User", "user__username"), ("Action", "action"),
                      ("Model", "model_name"), ("Object", "object_repr")],
        search=["action", "model_name", "object_repr", "user__username"],
        form_fields=[],
    ),
    "settings": E(
        title="Company Settings", singular="Settings", icon="gear",
        model=m.CompanySettings,
        list_display=[("Currency", "currency"), ("Fiscal Year Start", "fiscal_year_start"),
                      ("Phone", "phone"), ("Email", "email")],
        search=["currency"],
        form_fields=["currency", "fiscal_year_start", "phone", "email", "address", "tax_id"],
    ),
}
