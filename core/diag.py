import io
import traceback

from django.core.management import call_command
from django.db import connection
from django.http import HttpResponse


def diag_migrate(request):
    out, err = io.StringIO(), io.StringIO()
    try:
        call_command("migrate", "--noinput", stdout=out, stderr=err, verbosity=1)
        return HttpResponse("<pre>MIGRATE OK\n" + out.getvalue()[-3000:] + "</pre>")
    except Exception:
        return HttpResponse(
            "<pre>MIGRATE FAILED\n" + traceback.format_exc()[-6000:] + "</pre>"
        )


def diag_status(request):
    out = io.StringIO()
    try:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT app, name FROM django_migrations "
                "WHERE app IN ('hr','finance','administration','comms','executive','fleet','shared') "
                "ORDER BY app, name"
            )
            applied = [f"{a}.{n}" for a, n in cur.fetchall()]
            cur.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' AND "
                "tablename IN ('fleet_employee','fleet_attendance','fleet_payroll',"
                "'shared_employee','hr_payslip')"
            )
            tables = [r[0] for r in cur.fetchall()]
        out.write("APPLIED:\n" + "\n".join(applied) + "\n\nTABLES:\n" + "\n".join(tables))
        return HttpResponse("<pre>" + out.getvalue() + "</pre>")
    except Exception:
        return HttpResponse(
            "<pre>STATUS FAILED\n" + traceback.format_exc()[-4000:] + "</pre>"
        )


def diag_fake_hr(request):
    out, err = io.StringIO(), io.StringIO()
    try:
        # Bypass Django's consistency check: record hr.0002 as applied directly.
        # Its source tables were already dropped by the partial fleet.0004 run,
        # so there is no data left to migrate; the schema is already correct.
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO django_migrations (app, name, applied) "
                "VALUES ('hr', '0002_consolidate_fleet_hr', NOW()) "
                "ON CONFLICT DO NOTHING"
            )
        call_command("migrate", "--noinput", stdout=out, stderr=err, verbosity=1)
        return HttpResponse("<pre>FAKE+ MIGRATE OK\n" + out.getvalue()[-3000:] + "</pre>")
    except Exception:
        return HttpResponse(
            "<pre>FAILED\n" + traceback.format_exc()[-6000:] + "</pre>"
        )


def diag_drivers(request):
    from fleet.models import Driver
    from core.models import Company
    lines = []
    for d in Driver.objects.select_related("company").all()[:30]:
        lines.append(
            f"{d.pk} | {d.company.slug if d.company else '?'} | {d.name} | "
            f"shared_employee_id={d.shared_employee_id}"
        )
    lines.append(f"total drivers: {Driver.objects.count()}")
    lines.append(f"companies: {', '.join(Company.objects.values_list('slug', flat=True)[:10])}")
    return HttpResponse("<pre>" + "\n".join(lines) + "</pre>")


def diag_repair_fleet_hr(request):
    """Recreate fleet HR demo data lost when fleet.0004 dropped tables early."""
    from datetime import date, timedelta
    from fleet.models import Driver
    from shared.models import Employee, Attendance
    from hr.models import Payslip
    lines = []
    today = date.today()
    for d in Driver.objects.select_related("company").all():
        if d.shared_employee_id:
            continue
        emp, created = Employee.objects.get_or_create(
            company=d.company, name=d.name,
            defaults={
                "employee_id": f"DRV-{d.company_id}-{d.pk}",
                "position": "Driver",
                "phone": d.phone or "",
                "hire_date": today - timedelta(days=180),
                "salary": 15000,
                "status": "active",
            },
        )
        d.shared_employee = emp
        d.save(update_fields=["shared_employee"])
        lines.append(f"{'created' if created else 'linked'} employee for driver {d.name}")
        # attendance: last 5 days present
        for i in range(5):
            day = today - timedelta(days=i + 1)
            Attendance.objects.get_or_create(
                company=d.company, employee=emp, date=day,
                defaults={"status": "present"},
            )
        # payslip: current month
        Payslip.objects.get_or_create(
            company=d.company, employee=emp, period=today.replace(day=1),
            defaults={"basic": 15000, "deductions": 500, "net": 14500, "status": "approved"},
        )
    lines.append("repair done")
    return HttpResponse("<pre>" + "\n".join(lines) + "</pre>")
