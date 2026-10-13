"""HR Management dashboard + employee self-service portal."""
from datetime import date, timedelta

from django.db.models import Avg, Count, Sum
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from core import dashboards as D
from core.modules import build_sidebar
from core.views import company_access_required
from shared.models import Attendance, Department, Employee, LeaveRequest, PayrollRun

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
    first_this = today.replace(day=1)
    first_last = (first_this - timedelta(days=1)).replace(day=1)

    headcount = Employee.objects.filter(company=c, status="active").count()
    headcount_prev = Employee.objects.filter(
        company=c, hire_date__lt=first_this).exclude(status="terminated").count()
    d_txt, d_dir = D.pct_delta(headcount, headcount_prev or headcount)

    on_leave = Employee.objects.filter(company=c, status="on_leave").count()
    pending_leave = LeaveRequest.objects.filter(company=c, status="pending").count()
    att_today = Attendance.objects.filter(company=c, date=today)
    present_today = att_today.filter(status="present").count()
    att_rate = round(present_today / max(att_today.count(), 1) * 100)

    payroll = PayrollRun.objects.filter(company=c).order_by("-month").first()
    payroll_val = float(payroll.total_net) if payroll else 0

    open_vac = m.JobVacancy.objects.filter(company=c, status="open").count()
    applicants = m.Applicant.objects.filter(
        company=c).exclude(stage__in=["hired", "rejected"]).count()

    months = D.last_n_months(6)
    hires = []
    for y, mo, _lbl in months:
        hires.append(Employee.objects.filter(
            company=c, hire_date__year=y, hire_date__month=mo).count())

    dept_rows = list(Department.objects.filter(company=c).annotate(
        n=Count("employees")).values_list("name", "n"))
    if not dept_rows:
        dept_rows = [("Unassigned", headcount)]

    att_trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        tot = Attendance.objects.filter(company=c, date=d).count()
        pr = Attendance.objects.filter(company=c, date=d, status="present").count()
        att_trend.append(round(pr / max(tot, 1) * 100))

    avg_rating = m.PerformanceReview.objects.filter(
        company=c, status="completed").aggregate(a=Avg("rating"))["a"] or 0

    kpis = [
        D.kpi("Headcount", f"{headcount}", "users", "orange",
              sub="active employees", delta=d_txt, delta_dir=d_dir, spark=hires),
        D.kpi("On Leave Today", f"{on_leave}", "calendar", "blue",
              sub=f"{pending_leave} pending requests"),
        D.kpi("Attendance Today", f"{att_rate}%", "clock", "green",
              sub=f"{present_today}/{att_today.count()} present", spark=att_trend),
        D.kpi("Latest Payroll", f"{payroll_val:,.0f}", "card", "purple",
              sub=payroll.month.strftime("%B %Y") if payroll else "no runs yet"),
        D.kpi("Open Vacancies", f"{open_vac}", "search", "orange",
              sub=f"{applicants} active applicants"),
        D.kpi("Avg Review Rating", f"{float(avg_rating):.1f}/5", "chart", "green",
              sub="completed reviews"),
    ]
    cfg = {
        "title": "HR Dashboard", "subtitle": "Workforce analytics & HR operations",
        "kpis": kpis,
        "line": {"labels": [lbl for _, _, lbl in months], "label": "New hires",
                 "data": hires, "color": "#ff7a18"},
        "donut": {"labels": [r[0] for r in dept_rows], "data": [r[1] for r in dept_rows],
                  "colors": ["#ff7a18", "#3b82f6", "#22c55e", "#a855f7", "#eab308", "#64748b"]},
        "tables": [
            {"title": "Pending Leave Approvals", "headers": ["Employee", "Type", "Dates"],
             "rows": [[l.employee.name, l.get_leave_type_display(),
                       f"{l.start_date} → {l.end_date}"]
                      for l in LeaveRequest.objects.filter(company=c, status="pending")[:8]],
             "link": _el(c, "hr_entity_list", "leave-requests"), "link_label": "Review all"},
            {"title": "Recent Hires", "headers": ["Employee", "Position", "Hired"],
             "rows": [[e.name, e.position, str(e.hire_date or "—")]
                      for e in Employee.objects.filter(company=c).order_by("-hire_date")[:8]],
             "link": _el(c, "hr_entity_list", "employees"), "link_label": "All employees"},
            {"title": "Upcoming Reviews", "headers": ["Employee", "Period End", "Status"],
             "rows": [[r.employee.name, str(r.period_end or "—"), r.get_status_display()]
                      for r in m.PerformanceReview.objects.filter(
                          company=c).exclude(status="completed")[:8]],
             "link": _el(c, "hr_entity_list", "reviews"), "link_label": "All reviews"},
        ],
        "alerts": [
            {"level": "warning", "text": f"{pending_leave} leave requests awaiting approval",
             "link": _el(c, "hr_entity_list", "leave-requests")},
        ] if pending_leave else [],
        "actions": [
            {"label": "New Employee", "icon": "plus", "url": _el(c, "hr_entity_create", "employees")},
            {"label": "Post Vacancy", "icon": "plus", "url": _el(c, "hr_entity_create", "vacancies")},
            {"label": "New Leave Request", "icon": "plus", "url": _el(c, "hr_entity_create", "leave-requests")},
            {"label": "Run Payroll", "icon": "plus", "url": _el(c, "hr_entity_create", "payroll-runs")},
        ],
    }
    return D.render_module_dashboard(request, c, cfg)


@company_access_required
def portal(request, company_slug):
    """Employee self-service portal for the logged-in user's profile."""
    c = request.company
    employee = Employee.objects.filter(company=c, user=request.user).first()
    ctx = {
        "company": c, "membership": request.membership,
        "sidebar": build_sidebar(request),
        "employee": employee,
    }
    if employee:
        from comms.models import Task
        ctx.update({
            "leaves": LeaveRequest.objects.filter(company=c, employee=employee).order_by("-start_date")[:10],
            "payslips": m.Payslip.objects.filter(company=c, employee=employee).order_by("-period")[:12],
            "objectives": m.Objective.objects.filter(company=c, employee=employee).order_by("-target_date")[:8],
            "tasks": Task.objects.filter(company=c, assigned_to=request.user).exclude(status="done")[:8],
            "reviews": m.PerformanceReview.objects.filter(company=c, employee=employee).order_by("-period_end")[:5],
        })
    return render(request, "hr/portal.html", ctx)
