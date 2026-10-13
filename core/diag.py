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
        call_command("migrate", "hr", "0002", "--fake", stdout=out, stderr=err, verbosity=1)
        call_command("migrate", "--noinput", stdout=out, stderr=err, verbosity=1)
        return HttpResponse("<pre>FAKE+ MIGRATE OK\n" + out.getvalue()[-3000:] + "</pre>")
    except Exception:
        return HttpResponse(
            "<pre>FAILED\n" + traceback.format_exc()[-6000:] + "</pre>"
        )
