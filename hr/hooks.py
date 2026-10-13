"""HR workflow post-hooks: notifications, employee creation, payroll posting."""
from datetime import date


def _notify(company, user, title, message, link=""):
    if not user:
        return
    try:
        from shared.models import Notification
        Notification.objects.create(company=company, user=user,
                                    title=title, message=message, link=link)
    except Exception:
        pass


def on_leave_decided(company, leave, request):
    """Notify the employee when their leave is approved/rejected."""
    user = getattr(leave.employee, "user", None)
    _notify(company, user, f"Leave {leave.status}",
            f"Your {leave.get_leave_type_display()} leave "
            f"({leave.start_date} → {leave.end_date}) was {leave.status}.",
            link=f"/c/{company.slug}/hr/leave-requests/{leave.pk}/")


def on_applicant_hired(company, applicant, request):
    """Create the employee record when an applicant is hired."""
    from shared.models import Employee
    emp_id = f"EMP-{company.pk}-{Employee.objects.filter(company=company).count() + 1:04d}"
    employee = Employee.objects.create(
        company=company, employee_id=emp_id, name=applicant.name,
        email=applicant.email or "", phone=applicant.phone or "",
        department=applicant.vacancy.department,
        position=applicant.vacancy.position.title if applicant.vacancy.position else "",
        hire_date=date.today(), status="active",
    )
    applicant.vacancy.openings = max(0, applicant.vacancy.openings - 1)
    applicant.vacancy.save(update_fields=["openings"])
    return employee


def on_payroll_approved(company, run, request):
    """Generate payslips and post the payroll journal to Finance."""
    from django.db.models import Sum
    from shared.models import Employee
    from hr.models import Payslip
    created = 0
    for emp in Employee.objects.filter(company=company, status="active"):
        _p, was_created = Payslip.objects.get_or_create(
            company=company, employee=emp, period=run.month,
            defaults={"payroll_run": run, "basic": float(emp.salary or 0),
                      "status": "approved"})
        if was_created:
            created += 1
    totals = Payslip.objects.filter(company=company, period=run.month).aggregate(
        g=Sum("basic"), a=Sum("allowances"), d=Sum("deductions"), t=Sum("tax"), n=Sum("net"))
    run.total_gross = totals["g"] or 0
    run.total_deductions = (totals["d"] or 0) + (totals["t"] or 0)
    run.total_net = totals["n"] or 0
    run.save(update_fields=["total_gross", "total_deductions", "total_net"])
    # post to GL: Dr Salary Expense / Cr Salary Payable
    try:
        from core.integrations import post_journal
        if float(run.total_gross or 0) > 0:
            post_journal(
                company, run.month,
                reference=f"PAY-{run.month:%Y-%m}",
                lines=[
                    ("5000", "Salary Expense", float(run.total_gross), 0),
                    ("2000", "Salary Payable", 0, float(run.total_gross)),
                ],
                description=f"Payroll {run.month:%B %Y}",
                user=request.user,
            )
    except Exception:
        pass
    return created
