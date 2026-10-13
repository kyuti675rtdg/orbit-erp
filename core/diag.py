import io
import traceback

from django.core.management import call_command
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
