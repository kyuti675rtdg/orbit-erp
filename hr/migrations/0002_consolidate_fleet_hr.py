"""Consolidate fleet HR data into the centralized HR system.

fleet.Employee -> shared.Employee, fleet.Attendance -> shared.Attendance,
fleet.Payroll -> hr.Payslip, fleet.Driver.employee link -> fleet.Driver.shared_employee.
Idempotent: skips records that were already migrated.
"""
from django.db import migrations


def migrate_hr(apps, schema_editor):
    FleetEmployee = apps.get_model("fleet", "Employee")
    FleetAttendance = apps.get_model("fleet", "Attendance")
    FleetPayroll = apps.get_model("fleet", "Payroll")
    FleetDriver = apps.get_model("fleet", "Driver")
    Employee = apps.get_model("shared", "Employee")
    Attendance = apps.get_model("shared", "Attendance")
    Payslip = apps.get_model("hr", "Payslip")

    emp_map = {}
    for fe in FleetEmployee.objects.all():
        emp, created = Employee.objects.get_or_create(
            company_id=fe.company_id, name=fe.name,
            defaults={
                "employee_id": f"FLT-{fe.company_id}-{fe.pk}",
                "position": fe.role or "",
                "phone": fe.phone or "",
                "hire_date": fe.hire_date,
                "salary": fe.salary_monthly or 0,
                "status": fe.status if fe.status in ("active", "on_leave", "terminated") else "active",
            },
        )
        emp_map[fe.pk] = emp.pk
        # move driver link
        if fe.driver_id:
            FleetDriver.objects.filter(pk=fe.driver_id).update(shared_employee_id=emp.pk)

    for fa in FleetAttendance.objects.all():
        new_emp_id = emp_map.get(fa.employee_id)
        if not new_emp_id:
            continue
        Attendance.objects.get_or_create(
            company_id=fa.company_id, employee_id=new_emp_id, date=fa.date,
            defaults={
                "status": "present" if fa.present else "absent",
                "notes": fa.note or "",
            },
        )

    for fp in FleetPayroll.objects.all():
        new_emp_id = emp_map.get(fp.employee_id)
        if not new_emp_id:
            continue
        Payslip.objects.get_or_create(
            company_id=fp.company_id, employee_id=new_emp_id, period=fp.month,
            defaults={
                "basic": fp.gross or 0,
                "deductions": fp.deductions or 0,
                "net": fp.net or 0,
                "status": fp.status if fp.status in ("draft", "approved", "paid") else "draft",
            },
        )


def unmigrate_hr(apps, schema_editor):
    # Reverse: remove migrated records (identified by FLT- employee ids).
    Employee = apps.get_model("shared", "Employee")
    emp_ids = list(Employee.objects.filter(employee_id__startswith="FLT-").values_list("pk", flat=True))
    apps.get_model("hr", "Payslip").objects.filter(employee_id__in=emp_ids).delete()
    apps.get_model("shared", "Attendance").objects.filter(employee_id__in=emp_ids).delete()
    Employee.objects.filter(pk__in=emp_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0001_initial"),
        ("fleet", "0003_driver_shared_employee"),
        ("shared", "0002_attendance_notes_employee_branch_employee_user"),
    ]

    operations = [
        migrations.RunPython(migrate_hr, unmigrate_hr),
    ]
