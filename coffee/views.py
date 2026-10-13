"""Bean Power Coffee views: dashboard, traceability (CRUD served by core.crud)."""
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from core import dashboards as D
from core.views import company_access_required

from . import models as m


def _el(company, url_name, **kw):
    from django.urls import reverse
    k = {"company_slug": company.slug}
    k.update(kw)
    return reverse(url_name, kwargs=k)


@company_access_required
def dashboard(request, company_slug):
    c = request.company
    today = timezone.now().date()
    year_start = today.replace(month=1, day=1)
    months = D.last_n_months(6)

    farmers = m.Farmer.objects.filter(company=c, status="active").count()
    cherry = m.IntakeBatch.objects.filter(
        company=c, intake_date__gte=year_start).aggregate(t=Sum("cherry_kg"))["t"] or 0
    in_process = m.IntakeBatch.objects.filter(
        company=c, status__in=["received", "inspecting", "processing"]).count()
    stock = m.WarehouseLot.objects.filter(
        company=c, status__in=["stored", "reserved"]).aggregate(t=Sum("quantity_kg"))["t"] or 0
    open_orders = m.ExportOrder.objects.filter(company=c).exclude(
        status__in=["delivered", "cancelled"])
    open_val = open_orders.aggregate(t=Sum("quantity_kg"))["t"] or 0
    export_rev = m.CoffeeExportInvoice.objects.filter(
        company=c, invoice_date__gte=year_start).aggregate(t=Sum("amount"))["t"] or 0
    qc_pending = m.Sample.objects.filter(company=c).count() - m.QualityCertificate.objects.filter(
        company=c).count()

    cherry_monthly = D.monthly_sums(
        m.IntakeBatch.objects.filter(company=c), "intake_date", "cherry_kg", months)
    rev_monthly = D.monthly_sums(
        m.CoffeeExportInvoice.objects.filter(company=c), "invoice_date", "amount", months)

    kpis = [
        D.kpi("Active Farmers", f"{farmers}", "user", "green", sub="registered suppliers"),
        D.kpi("Cherry Intake (YTD)", f"{float(cherry):,.0f} kg", "basket", "orange",
              sub="this year"),
        D.kpi("Batches In Process", f"{in_process}", "layers", "blue",
              sub="intake → processing"),
        D.kpi("Warehouse Stock", f"{float(stock):,.0f} kg", "box", "purple",
              sub="stored + reserved"),
        D.kpi("Open Export Orders", f"{open_orders.count()}", "package", "orange",
              sub=f"{float(open_val):,.0f} kg pending"),
        D.kpi("Export Revenue (YTD)", f"{float(export_rev):,.0f}", "cash", "green",
              sub="invoiced"),
    ]
    recent_deliveries = m.Delivery.objects.filter(company=c).select_related(
        "farmer").order_by("-delivery_date")[:8]
    recent_lots = m.WarehouseLot.objects.filter(company=c).order_by("-created_at")[:8]
    cfg = {
        "title": "Coffee Dashboard", "subtitle": "Bean Power Coffee — value chain overview",
        "kpis": kpis,
        "line": {"labels": months,
                 "series": [{"label": "Cherry intake (kg)", "data": cherry_monthly, "color": "orange"},
                            {"label": "Export revenue", "data": rev_monthly, "color": "green"}]},
        "tables": [
            {"title": "Recent Farmer Deliveries", "headers": ["Delivery", "Farmer", "Date", "Status"],
             "rows": [[d.delivery_no, d.farmer.full_name, str(d.delivery_date),
                       d.get_status_display()] for d in recent_deliveries],
             "link": _el(c, "coffee_entity_list", entity="deliveries"),
             "link_label": "All deliveries"},
            {"title": "Latest Warehouse Lots", "headers": ["Lot", "Grade", "Qty kg", "Status"],
             "rows": [[l.lot_no, l.grade or "—", f"{float(l.quantity_kg):,.0f}",
                       l.get_status_display()] for l in recent_lots],
             "link": _el(c, "coffee_entity_list", entity="lots"),
             "link_label": "All lots"},
        ],
        "actions": [
            {"label": "Register Delivery", "icon": "plus",
             "url": _el(c, "coffee_entity_create", entity="deliveries")},
            {"label": "Trace a Batch", "icon": "search", "url": _el(c, "coffee_traceability")},
            {"label": "New Export Order", "icon": "plus",
             "url": _el(c, "coffee_entity_create", entity="export-orders")},
        ],
    }
    return D.render_module_dashboard(request, c, cfg)


def _chain_for_lot(lot):
    """Walk the traceability chain backward from a warehouse lot."""
    steps = []
    pb = lot.processing_batch
    ib = pb.intake_batch if pb else None
    delivery = ib.delivery if ib else None
    harvest = delivery.harvest if delivery else None
    farm = (harvest.farm if harvest else None) or (delivery.farm if delivery else None)
    farmer = delivery.farmer if delivery else None
    plant_group = harvest.plant_group if harvest else None
    orders = list(lot.export_orders.select_related("buyer").all())
    shipments = []
    for o in orders:
        shipments.extend(list(o.shipments.all()))
    if farmer:
        steps.append(("Farmer", f"{farmer.farmer_id} — {farmer.full_name}"))
    if farm:
        steps.append(("Farm", f"{farm.farm_id} — {farm.name}"))
    if plant_group:
        steps.append(("Plant / Group",
                      f"{plant_group.group_id} ({plant_group.get_record_type_display()})"))
    if harvest:
        steps.append(("Harvest", f"{harvest.harvest_id} — {harvest.cherry_kg} kg on {harvest.harvest_date}"))
    if delivery:
        steps.append(("Delivery", f"{delivery.delivery_no} — {delivery.delivery_date}"))
    if ib:
        steps.append(("Intake Batch", f"{ib.batch_no} — {ib.cherry_kg} kg"))
    if pb:
        steps.append(("Processing Batch", f"{pb.batch_no}"))
    steps.append(("Warehouse Lot", f"{lot.lot_no} — {lot.quantity_kg} kg ({lot.get_status_display()})"))
    for o in orders:
        steps.append(("Export Order", f"{o.order_no} — {o.buyer.name}"))
    for s in shipments:
        steps.append(("Shipment", f"{s.shipment_no} → {s.destination_port or ''} ({s.get_status_display()})"))
    return steps


@company_access_required
def traceability(request, company_slug):
    c = request.company
    q = (request.GET.get("q") or "").strip()
    steps, found = [], None
    if q:
        lot = m.WarehouseLot.objects.filter(company=c, lot_no__iexact=q).first()
        if not lot:
            ib = m.IntakeBatch.objects.filter(company=c, batch_no__iexact=q).first()
            if ib:
                lot = m.WarehouseLot.objects.filter(
                    company=c, processing_batch__intake_batch=ib).first()
        if not lot:
            farmer = m.Farmer.objects.filter(company=c, farmer_id__iexact=q).first()
            if farmer:
                lot = m.WarehouseLot.objects.filter(
                    company=c,
                    processing_batch__intake_batch__delivery__farmer=farmer).first()
        if lot:
            found = lot
            steps = _chain_for_lot(lot)
    ctx = {"company": c, "membership": request.membership, "q": q,
           "steps": steps, "found": found, "sidebar": None}
    from core.modules import build_sidebar
    ctx["sidebar"] = build_sidebar(request)
    return render(request, "coffee/traceability.html", ctx)
