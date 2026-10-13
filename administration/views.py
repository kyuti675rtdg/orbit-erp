"""Administration & System Management dashboard."""
from datetime import timedelta

from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from core import dashboards as D
from core.models import Membership
from core.views import company_access_required
from shared.models import AuditLog, CompanySettings

from . import models as m


def _el(company, url_name, entity=None):
    kw = {"company_slug": company.slug}
    if entity:
        kw["entity"] = entity
    return reverse(url_name, kwargs=kw)


@company_access_required
def dashboard(request, company_slug):
    c = request.company
    today = timezone.now().date()

    users = Membership.objects.filter(company=c, is_active=True).count()
    roles = {m["role"] for m in Membership.objects.filter(company=c).values("role")}
    branches = m.Branch.objects.filter(company=c, is_active=True).count()
    sessions_7d = m.LoginSession.objects.filter(
        company=c, login_at__date__gte=today - timedelta(days=7)).count()
    audit_7d = AuditLog.objects.filter(
        company=c, timestamp__date__gte=today - timedelta(days=7)).count()
    integrations = m.Integration.objects.filter(company=c)
    int_ok = integrations.filter(status="active").count()
    backups = m.SystemBackup.objects.filter(company=c).order_by("-scheduled_at")[:5]
    last_backup = backups[0] if backups else None
    settings_obj = CompanySettings.objects.filter(company=c).first()

    kpis = [
        D.kpi("Active Users", f"{users}", "users", "orange", sub=f"{len(roles)} roles in use"),
        D.kpi("Branches", f"{branches}", "building", "blue", sub="active branches"),
        D.kpi("Logins (7d)", f"{sessions_7d}", "clock", "green", sub="login sessions"),
        D.kpi("Audit Events (7d)", f"{audit_7d}", "shield", "purple", sub="tracked changes"),
        D.kpi("Integrations", f"{int_ok}/{integrations.count()}", "layers", "orange",
              sub="active integrations"),
        D.kpi("Last Backup", last_backup.get_status_display() if last_backup else "—",
              "box", "green", sub=str(last_backup.scheduled_at.date()) if last_backup and last_backup.scheduled_at else "none scheduled"),
    ]
    role_rows = list(Membership.objects.filter(company=c, is_active=True).values(
        "role").annotate(n=Count("id")))
    cfg = {
        "title": "Administration Dashboard",
        "subtitle": "System health, access control & configuration",
        "kpis": kpis,
        "donut": {"labels": [r["role"].title() for r in role_rows],
                  "data": [r["n"] for r in role_rows] or [1],
                  "colors": ["#ff7a18", "#3b82f6", "#22c55e", "#a855f7", "#eab308", "#64748b"]},
        "tables": [
            {"title": "Recent Audit Activity", "headers": ["Time", "User", "Action", "Object"],
             "rows": [[a.timestamp.strftime("%m-%d %H:%M"), str(a.user or "—"), a.action, a.object_repr[:40]]
                      for a in AuditLog.objects.filter(company=c).order_by("-timestamp")[:8]],
             "link": _el(c, "admin_entity_list", "audit-logs"), "link_label": "All logs"},
            {"title": "Recent Logins", "headers": ["User", "When", "IP"],
             "rows": [[s.user.username, s.login_at.strftime("%m-%d %H:%M"), s.ip_address or "—"]
                      for s in m.LoginSession.objects.filter(company=c).order_by("-login_at")[:8]],
             "link": _el(c, "admin_entity_list", "sessions"), "link_label": "All sessions"},
            {"title": "Backups", "headers": ["Name", "Scheduled", "Status"],
             "rows": [[b.name, b.scheduled_at.strftime("%m-%d %H:%M") if b.scheduled_at else "—",
                       b.get_status_display()] for b in backups],
             "link": _el(c, "admin_entity_list", "backups"), "link_label": "All backups"},
        ],
        "alerts": (
            [{"level": "warning", "text": "No company settings configured",
              "link": _el(c, "admin_entity_list", "settings")}] if not settings_obj else []
        ),
        "actions": [
            {"label": "Add User", "icon": "plus", "url": _el(c, "admin_entity_create", "members")},
            {"label": "New Branch", "icon": "plus", "url": _el(c, "admin_entity_create", "branches")},
            {"label": "Schedule Backup", "icon": "plus", "url": _el(c, "admin_entity_create", "backups")},
            {"label": "New Integration", "icon": "plus", "url": _el(c, "admin_entity_create", "integrations")},
        ],
    }
    return D.render_module_dashboard(request, c, cfg)
