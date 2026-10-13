"""Executive Management & BI entity registry."""
from . import models as m

E = lambda **kw: kw  # noqa: E731

ENTITIES = {
    "report-definitions": E(
        title="Custom Reports", singular="Report", icon="chart",
        model=m.ReportDefinition,
        list_display=[("Name", "name"), ("Dataset", "dataset"), ("Created", "created_at")],
        search=["name", "description"],
        form_fields=["name", "description", "dataset", "columns", "status_filter"],
        detail_related=[
            ("Schedules", "schedules", [("Frequency", "frequency"), ("Active", "is_active")]),
        ],
    ),
    "scheduled-reports": E(
        title="Scheduled Reports", singular="Scheduled Report", icon="clock",
        model=m.ScheduledReport,
        list_display=[("Report", "report__name"), ("Frequency", "frequency"),
                      ("Last Run", "last_run"), ("Active", "is_active")],
        search=["report__name"],
        form_fields=["report", "frequency", "recipients", "is_active"],
    ),
}
