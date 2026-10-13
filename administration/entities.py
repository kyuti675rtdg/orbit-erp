"""Administration & System Management entity registry."""
from core.models import Membership
from shared import models as sm

from . import models as m

E = lambda **kw: kw  # noqa: E731

ADMIN_ROLES = ["owner", "admin"]

ENTITIES = {
    # ---- Organization
    "branches": E(
        title="Branches", singular="Branch", icon="building",
        model=m.Branch,
        list_display=[("Name", "name"), ("Code", "code"), ("City", "city"),
                      ("Manager", "manager"), ("Active", "is_active")],
        search=["name", "code", "city"],
        form_fields=["name", "code", "city", "address", "phone", "manager", "is_active"],
        detail_related=[
            ("Employees", "employees", [("ID", "employee_id"), ("Name", "name"), ("Status", "status")]),
        ],
    ),
    "members": E(
        title="Users & Roles", singular="Member", icon="users",
        model=Membership,
        list_display=[("User", "user__username"), ("Role", "role"), ("Active", "is_active"), ("Joined", "joined_at")],
        search=["user__username"],
        form_fields=["user", "role", "is_active"],
    ),
    "roles": E(
        title="Custom Roles & Permissions", singular="Role", icon="shield",
        model=m.Role,
        list_display=[("Name", "name"), ("Approve", "can_approve"),
                      ("Finance", "can_manage_finance"), ("Users", "can_manage_users"),
                      ("Active", "is_active")],
        search=["name"],
        form_fields=["name", "description", "can_view", "can_create", "can_edit",
                     "can_delete", "can_approve", "can_manage_finance",
                     "can_manage_users", "is_active"],
    ),
    "approval-rules": E(
        title="Approval Rules", singular="Approval Rule", icon="clipboard",
        model=m.ApprovalRule,
        list_display=[("Document", "document_type"), ("Min Amount", "min_amount"),
                      ("Approver Role", "approver_role"), ("Steps", "steps"), ("Active", "is_active")],
        search=["document_type"],
        form_fields=["document_type", "min_amount", "approver_role", "steps", "is_active"],
    ),
    # ---- Master data
    "currencies": E(
        title="Currencies", singular="Currency", icon="bank",
        model=m.Currency,
        list_display=[("Code", "code"), ("Name", "name"), ("Rate", "exchange_rate"),
                      ("Base", "is_base"), ("Active", "is_active")],
        search=["code", "name"],
        form_fields=["code", "name", "symbol", "exchange_rate", "is_base", "is_active"],
    ),
    "numbering": E(
        title="Numbering Sequences", singular="Sequence", icon="file",
        model=m.NumberingSequence,
        list_display=[("Document", "document_type"), ("Prefix", "prefix"),
                      ("Next", "next_number")],
        search=["document_type"],
        form_fields=["document_type", "prefix", "next_number", "padding"],
    ),
    "fiscal-calendars": E(
        title="Fiscal Calendars", singular="Fiscal Calendar", icon="calendar",
        model=m.FiscalCalendar,
        list_display=[("Name", "name"), ("Start", "start_date"), ("End", "end_date"),
                      ("Active", "is_active")],
        search=["name"],
        form_fields=["name", "start_date", "end_date", "is_active"],
    ),
    "settings": E(
        title="Company Settings", singular="Settings", icon="gear",
        model=sm.CompanySettings,
        list_display=[("Currency", "currency"), ("Fiscal Year Start", "fiscal_year_start"),
                      ("Phone", "phone"), ("Email", "email")],
        search=["currency"],
        form_fields=["currency", "fiscal_year_start", "phone", "email", "address", "tax_id"],
    ),
    # ---- Security & monitoring
    "audit-logs": E(
        title="Audit Logs", singular="Audit Log", icon="shield", readonly=True,
        model=sm.AuditLog,
        list_display=[("Time", "timestamp"), ("User", "user__username"), ("Action", "action"),
                      ("Model", "model_name"), ("Object", "object_repr")],
        search=["action", "model_name", "object_repr", "user__username"],
        form_fields=[],
    ),
    "sessions": E(
        title="Login Sessions", singular="Session", icon="clock", readonly=True,
        model=m.LoginSession,
        list_display=[("User", "user__username"), ("Login At", "login_at"), ("IP", "ip_address")],
        search=["user__username", "ip_address"],
        form_fields=[],
    ),
    "notification-settings": E(
        title="Notification Settings", singular="Setting", icon="bell",
        model=m.NotificationSetting,
        list_display=[("Event", "event"), ("Channel", "channel"), ("Enabled", "is_enabled")],
        search=["event"],
        form_fields=["event", "channel", "is_enabled"],
    ),
    # ---- Data & integrations
    "backups": E(
        title="Backups", singular="Backup", icon="box",
        model=m.SystemBackup,
        list_display=[("Name", "name"), ("Type", "backup_type"), ("Size MB", "size_mb"),
                      ("Status", "status")],
        search=["name"],
        form_fields=["name", "backup_type", "scheduled_at", "completed_at",
                     "size_mb", "location", "status", "notes"],
    ),
    "integrations": E(
        title="API Integrations", singular="Integration", icon="layers",
        model=m.Integration,
        list_display=[("Name", "name"), ("Provider", "provider"),
                      ("Direction", "direction"), ("Last Sync", "last_sync"), ("Status", "status")],
        search=["name", "provider"],
        form_fields=["name", "provider", "direction", "last_sync", "status"],
    ),
}
