# Orbit ERP — Multi-Company Enterprise Platform

World-class, production-ready ERP with a **Transportation & Fleet Management** module.
Premium dark enterprise UI, role-based access, per-company isolated workspaces.

## Quick start (local demo)

```bash
cd ~/workspace/orbit-erp
.venv/bin/python manage.py migrate
.venv/bin/python seed.py          # demo data (Heleph Coffee Group + Abyssinia Freight Lines)
.venv/bin/python manage.py runserver 127.0.0.1:8901
```

Open http://127.0.0.1:8901/ — demo login: **admin / Orbit@2026**

Or use `./start.sh`.

## What is built

**Platform (core app)**
- Professional login / signup, company registration page, company hub (card grid)
- Per-company ERP workspace with module launcher + KPIs
- Roles: Owner, Administrator, Operations Manager, Dispatcher, Accountant, Viewer
- Company switcher in sidebar; cross-company access is blocked

**Transport & Fleet module (fleet app)** — 23 entities, full CRUD with search:
- Transport dashboard: 8 KPI cards, 5 Chart.js charts, live compliance alerts
- Trip workspace: workflow timeline (Planned → Dispatched → En Route → Delivered → Completed),
  one-click advance with auto dispatch-order creation, auto-invoice on completion, POD capture
- Live GPS tracking: Leaflet map, animated vehicles, route polylines, geofences, 20s telemetry feed
- Fleet: vehicles, documents, routes, geofences
- Drivers & HR: drivers, documents, employees, attendance, payroll runs
- Fuel & maintenance: fuel logs, service records, inspections, spare parts, workshop jobs, part issues
- Finance: trip expenses, driver advances, invoices, payments (auto paid-status)
- Reports & BI: utilization, fuel efficiency (km/L), cost/km, trip profitability, on-time delivery

**Full flow supported:** Transport Request → Route Planning → Vehicle & Driver Assignment →
Dispatch → GPS / Live Monitoring → Delivery → POD → Trip Settlement → Billing → Finance → Reports.

## Tech
- Django 5.2, SQLite locally (PostgreSQL via `DATABASE_URL`), WhiteNoise, Gunicorn
- Chart.js + Leaflet vendored locally in `static/` (no CDN dependency)
- Timezone Africa/Addis_Ababa

## Deploy notes
- `DATABASE_URL` env switches to PostgreSQL; Render auto-trusts `RENDER_EXTERNAL_HOSTNAME`
  for ALLOWED_HOSTS and CSRF (same pattern as hms-enterprise).
- `seed.py` wipes + reseeds the two demo companies (idempotent for demos).

## UI Icon System (2026-10-13)

All emojis were removed from the interface and replaced with a professional
stroke-style SVG icon set (`core/templatetags/icons.py`, 45 icons). Usage in
templates: `{% load icons %}` then `{% icon 'truck' %}` or `{% icon name 20 %}`.
Nav/entity/workspace icons are icon *names* (not glyphs) defined in
`fleet/views.py` (`NAV`, `ENTITIES`) and `core/views.py` (module cards).
