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
        "bars": cfg.get("bars", []),
        "aging": cfg.get("aging"),
        "alerts": cfg.get("alerts", []),
        "actions": cfg.get("actions", []),
    }
    if ctx["line"]:
        ctx["line_json"] = json.dumps(ctx["line"])
    if ctx["donut"]:
        ctx["donut_json"] = json.dumps(ctx["donut"])
    return render(request, "crud/module_dashboard.html", ctx)


def kpi(label, value, icon, color="orange", sub="", delta=None, delta_dir=None, spark=None):
    """KPI card spec. delta: '+12.4%' text; delta_dir: up|down|flat; spark: [numbers]."""
    return {"label": label, "value": value, "icon": icon, "color": color,
            "sub": sub, "delta": delta, "delta_dir": delta_dir,
            "spark": sparkline(spark, color) if spark else None}


def pct_delta(current, previous):
    """(' +12.4%', 'up') style delta of current vs previous. Guards div-by-zero."""
    try:
        cur, prev = float(current or 0), float(previous or 0)
    except (TypeError, ValueError):
        return None, None
    if prev == 0:
        if cur == 0:
            return "0%", "flat"
        return "+100%", "up"
    pct = (cur - prev) / abs(prev) * 100
    if abs(pct) < 0.05:
        return "0%", "flat"
    return f"{'+' if pct > 0 else ''}{pct:.1f}%", ("up" if pct > 0 else "down")


def sparkline(values, color="#ff7a18"):
    """Inline-SVG polyline points for a tiny trend sparkline."""
    vals = [float(v or 0) for v in values]
    if len(vals) < 2:
        return None
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pts = []
    for i, v in enumerate(vals):
        x = i / (len(vals) - 1) * 100
        y = 26 - (v - lo) / span * 22
        pts.append(f"{x:.1f},{y:.1f}")
    return {"points": " ".join(pts), "color": color}


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
