"""Shared module-dashboard renderer (reference-style overview pages).

Each industry app builds a plain ``cfg`` dict and calls
``render_module_dashboard`` — KPIs, charts, tables, alerts, quick actions.
"""
import json

from django.shortcuts import render

from core.modules import build_sidebar
from core.views import company_access_required


def render_module_dashboard(request, company, cfg):
    ctx = {
        "company": company,
        "membership": request.membership,
        "sidebar": build_sidebar(request),
        "title": cfg.get("title", "Dashboard"),
        "subtitle": cfg.get("subtitle", ""),
        "kpis": cfg.get("kpis", []),
        "line": cfg.get("line"),      # {labels:[], label:"", data:[], color:""}
        "donut": cfg.get("donut"),    # {labels:[], data:[], colors:[]}
        "tables": cfg.get("tables", []),
        "alerts": cfg.get("alerts", []),
        "actions": cfg.get("actions", []),
    }
    if ctx["line"]:
        ctx["line_json"] = json.dumps(ctx["line"])
    if ctx["donut"]:
        ctx["donut_json"] = json.dumps(ctx["donut"])
    return render(request, "crud/module_dashboard.html", ctx)


def kpi(label, value, icon, color="orange", sub=""):
    return {"label": label, "value": value, "icon": icon, "color": color, "sub": sub}


def last_n_months(n=6):
    """[(year, month, 'Jan 26'), ...] oldest -> newest."""
    from datetime import date
    out, y, mo = [], date.today().year, date.today().month
    for _ in range(n):
        out.append((y, mo, date(y, mo, 1).strftime("%b %y")))
        mo -= 1
        if mo == 0:
            mo, y = 12, y - 1
    return list(reversed(out))


def monthly_sums(qs, date_field, amount_field, months):
    from django.db.models import Sum
    vals = []
    for y, mo, _lbl in months:
        v = qs.filter(**{f"{date_field}__year": y, f"{date_field}__month": mo}
                      ).aggregate(t=Sum(amount_field))["t"] or 0
        vals.append(float(v))
    return vals
