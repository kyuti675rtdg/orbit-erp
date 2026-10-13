"""Seed Bean Power Coffee company with a full value-chain demo dataset.

Idempotent: does nothing if the company already has farmer records.
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Company, Membership
from coffee import models as m


class Command(BaseCommand):
    help = "Seed the Bean Power Coffee company (coffee value chain)."

    def handle(self, *args, **opts):
        from django.contrib.auth.models import User
        admin = User.objects.filter(is_superuser=True).first()
        co, created = Company.objects.get_or_create(
            slug="bean-power-coffee",
            defaults={"name": "Bean Power Coffee", "industry": "Coffee Production & Export",
                      "industry_key": "coffee", "city": "Addis Ababa",
                      "country": "Ethiopia", "phone": "+251911000111",
                      "email": "info@beanpowercoffee.et"},
        )
        if not created:
            co.industry_key = "coffee"
            co.save()
        if admin:
            Membership.objects.get_or_create(
                user=admin, company=co,
                defaults={"role": "owner", "is_active": True})
        if m.Farmer.objects.filter(company=co).exists():
            self.stdout.write("Bean Power Coffee already seeded — skipping.")
            return
        self._seed(co, admin)
        self.stdout.write(self.style.SUCCESS("Bean Power Coffee seeded."))

    # ------------------------------------------------------------------
    def _seed(self, co, admin):
        today = timezone.now().date()
        D = lambda **kw: m.Farmer.objects.create(company=co, **kw)

        coop1 = m.Cooperative.objects.create(
            company=co, name="Yirgacheffe Coffee Farmers Cooperative",
            registration_no="COOP-2019-041", location="Yirgacheffe, Gedeo",
            contact_person="Ato Bekele Tadesse", phone="+251911220011", member_count=240)
        coop2 = m.Cooperative.objects.create(
            company=co, name="Sidamo Coffee Growers Union",
            registration_no="COOP-2020-117", location="Hawassa, Sidama",
            contact_person="W/ro Almaz Girma", phone="+251911330022", member_count=185)

        farmers_data = [
            ("Abebe Tesfaye", "+251911111001", coop1, "Organic"),
            ("Kebede Alemu", "+251911111002", coop1, "Organic, FairTrade"),
            ("Tadesse Haile", "+251911111003", coop1, ""),
            ("Girma Bekele", "+251911111004", coop2, "Rainforest"),
            ("Desta Wolde", "+251911111005", coop2, ""),
            ("Mulugeta Assefa", "+251911111006", coop2, "Organic"),
            ("Hailu Negash", "+251911111007", None, ""),
            ("Senait Girma", "+251911111008", coop1, "FairTrade"),
        ]
        farmers = [D(full_name=n, phone=p, cooperative=c_, certifications=cert)
                   for n, p, c_, cert in farmers_data]

        regions = [("Yirgacheffe", 6.16, 38.20), ("Sidamo", 7.05, 38.47)]
        farms, groups, harvests = [], [], []
        for i, f in enumerate(farmers):
            region, lat, lon = regions[i % 2]
            farm = m.Farm.objects.create(
                company=co, farmer=f, name=f"{f.full_name.split()[0]} Farm",
                location=f"{region}, Ethiopia", area_hectares=2 + (i % 4),
                gps_latitude=lat + i * 0.01, gps_longitude=lon + i * 0.01,
                certification_status=f.certifications or "Conventional")
            farms.append(farm)
            plot = m.Plot.objects.create(
                company=co, farm=farm, name="Plot A", area_hectares=1.5,
                gps_latitude=farm.gps_latitude, gps_longitude=farm.gps_longitude,
                soil_type="Nitosol")
            for g_i, variety in enumerate(["Heirloom", "Kurume"]):
                g = m.PlantGroup.objects.create(
                    company=co, farm=farm, plot=plot, record_type="group",
                    species="Arabica", variety=variety, plant_count=400 + g_i * 150,
                    planting_date=date(2018, 3, 15), age_years=8.5,
                    gps_latitude=farm.gps_latitude, gps_longitude=farm.gps_longitude)
                groups.append(g)
                h = m.HarvestRecord.objects.create(
                    company=co, plant_group=g, farm=farm,
                    harvest_date=today - timedelta(days=20 - i),
                    cherry_kg=850 + i * 120, expected_kg=900 + i * 100,
                    season="2026/27")
                harvests.append(h)
            m.FarmVisit.objects.create(
                company=co, farm=farm, visit_date=today - timedelta(days=30),
                visitor="Agronomist Dawit", observations="Healthy canopy, good cherry set.",
                recommendations="Continue organic mulching.")

        wash = m.CoffeeSite.objects.create(
            company=co, name="Yirgacheffe Washing Station", site_type="washing",
            location="Yirgacheffe, Gedeo", capacity_kg=50000,
            gps_latitude=6.162, gps_longitude=38.205,
            water_source="Spring", electricity="Grid + generator",
            equipment_notes="2 pulpers, 12 fermentation tanks, 40 drying beds")
        mill = m.CoffeeSite.objects.create(
            company=co, name="Addis Dry Mill", site_type="dry_mill",
            location="Addis Ababa, Akaki", capacity_kg=120000,
            equipment_notes="Huller, grader, color sorter, bagging line")
        wh = m.Warehouse.objects.create(
            company=co, name="Addis Ababa Coffee Warehouse",
            location="Addis Ababa, Kality", capacity_kg=200000,
            manager="Ato Samuel Bekele")

        sup1 = m.Supplier.objects.create(
            company=co, name="Gedeo Cherry Traders", supplier_type="trader",
            contact_person="Ato Yonas", phone="+251911440033")
        m.CoffeePrice.objects.create(
            company=co, coffee_type="Yirgacheffe", grade="Grade 1",
            season="2026/27", price_per_kg=185, currency="ETB",
            effective_date=today - timedelta(days=60))
        m.CoffeePrice.objects.create(
            company=co, coffee_type="Sidamo", grade="Grade 2",
            season="2026/27", price_per_kg=150, currency="ETB",
            effective_date=today - timedelta(days=60))

        # ---- deliveries -> intake (traceable chain)
        intake_batches = []
        for i, (f, h) in enumerate(zip(farmers, harvests[::2])):
            d = m.Delivery.objects.create(
                company=co, farmer=f, farm=f.farms.first(), harvest=h, site=wash,
                delivery_date=today - timedelta(days=18 - i),
                coffee_type="Yirgacheffe" if i % 2 == 0 else "Sidamo",
                status="accepted")
            m.WeighbridgeTicket.objects.create(
                company=co, delivery=d, gross_kg=float(h.cherry_kg) + 25,
                tare_kg=25, operator="Weighbridge Op")
            ib = m.IntakeBatch.objects.create(
                company=co, delivery=d, site=wash,
                intake_date=d.delivery_date, cherry_kg=h.cherry_kg,
                moisture_pct=11.2, defect_pct=2.1,
                grade="Grade 1" if i % 2 == 0 else "Grade 2", status="stored")
            intake_batches.append(ib)
            s = m.Sample.objects.create(company=co, intake_batch=ib, sampled_by="QC Alem")
            m.MoistureTest.objects.create(company=co, sample=s, moisture_pct=10.8,
                                          tested_by="QC Alem")
            m.CuppingSession.objects.create(
                company=co, sample=s, aroma=8.5, flavor=8.75, acidity=8.5, body=8.25,
                overall=8.6, cupper="Q-Grader Hanna")
            m.QualityCertificate.objects.create(
                company=co, sample=s, grade=ib.grade, screen_size="14+",
                verdict="approved", issued_by="QC Manager")

        # ---- processing
        po = m.ProcessingOrder.objects.create(
            company=co, site=wash, method="washed",
            start_date=today - timedelta(days=15), status="completed")
        proc_batches = []
        for ib in intake_batches[:4]:
            pb = m.ProcessingBatch.objects.create(
                company=co, processing_order=po, intake_batch=ib,
                input_kg=ib.cherry_kg, output_kg=float(ib.cherry_kg) * 0.22,
                water_liters=float(ib.cherry_kg) * 3, status="completed")
            proc_batches.append(pb)
            m.DryingRecord.objects.create(
                company=co, processing_batch=pb, bed_no=f"BED-{len(proc_batches):02d}",
                start_date=today - timedelta(days=12),
                end_date=today - timedelta(days=3),
                moisture_start=55.0, moisture_end=10.5)

        # ---- warehouse lots + movements (genealogy preserved)
        lots = []
        for pb in proc_batches:
            lot = m.WarehouseLot.objects.create(
                company=co, warehouse=wh, processing_batch=pb,
                grade="Grade 1", quantity_kg=pb.output_kg,
                unit_cost=220, status="stored")
            lots.append(lot)
            m.BatchMovement.objects.create(
                company=co, lot=lot, movement_type="receipt",
                quantity_kg=lot.quantity_kg, to_location=wh.name,
                reference=pb.batch_no)

        # ---- buyers / export
        buyers = [
            m.CoffeeBuyer.objects.create(
                company=co, name="Hamburg Kaffee GmbH", country="Germany",
                contact_person="Herr Schmidt", email="buy@hamburg-kaffee.de",
                payment_terms="LC at sight"),
            m.CoffeeBuyer.objects.create(
                company=co, name="Tokyo Specialty Coffee KK", country="Japan",
                contact_person="Tanaka-san", email="buy@tokyo-specialty.jp",
                payment_terms="TT 30 days"),
            m.CoffeeBuyer.objects.create(
                company=co, name="Portland Roasters Inc", country="USA",
                contact_person="J. Miller", email="buy@portlandroasters.com",
                payment_terms="LC 60 days"),
        ]
        contract = m.ExportContract.objects.create(
            company=co, buyer=buyers[0], coffee_type="Yirgacheffe", grade="Grade 1",
            quantity_kg=19200, unit_price=8.40, currency="USD",
            delivery_terms="FOB Djibouti", status="active")
        order = m.ExportOrder.objects.create(
            company=co, buyer=buyers[0], contract=contract,
            order_date=today - timedelta(days=5), quantity_kg=19200,
            unit_price=8.40, currency="USD", status="preparing")
        order.lots.set(lots[:2])
        for l in lots[:2]:
            l.status = "reserved"
            l.reserved_kg = l.quantity_kg
            l.save()
        m.ExportDocument.objects.create(
            company=co, order=order, doc_type="invoice", doc_no="INV-2026-001")
        m.ExportDocument.objects.create(
            company=co, order=order, doc_type="certificate",
            doc_no="COO-2026-001")
        ship = m.Shipment.objects.create(
            company=co, order=order, container_no="MSKU-482913-7",
            vessel="MV Addis Express", origin_port="Djibouti",
            destination_port="Hamburg", etd=today + timedelta(days=10),
            eta=today + timedelta(days=38), status="planned")
        inv = m.CoffeeExportInvoice.objects.create(
            company=co, order=order, invoice_date=today - timedelta(days=2),
            due_date=today + timedelta(days=58),
            amount=19200 * 8.40, paid_amount=0, currency="USD", status="unpaid")
        # post to finance (AR + journal)
        from core import integrations as integ
        integ.sync_coffee_invoice_to_ar(co, inv, True, None)

        # ---- logistics / equipment / security
        tr = m.Transporter.objects.create(
            company=co, name="Abyssinia Cargo Transport",
            contact_person="Ato Fikru", phone="+251911550044")
        m.Dispatch.objects.create(
            company=co, transporter=tr, shipment=ship, vehicle_plate="AA-3-48291",
            origin="Addis Ababa Warehouse", destination="Djibouti Port",
            dispatch_date=today + timedelta(days=8), quantity_kg=19200,
            freight_cost=45000, status="planned")
        pulper = m.Equipment.objects.create(
            company=co, name="Penagos Pulper #1", equipment_type="Pulper",
            site=wash, serial_no="PNG-2019-001")
        m.MaintenanceOrder.objects.create(
            company=co, equipment=pulper, order_type="preventive",
            description="Pre-season service: discs, bearings, washdown",
            assigned_to="Technician Girma", status="completed",
            completed_date=today - timedelta(days=40), cost=8500)
        m.SparePart.objects.create(
            company=co, name="Pulper disc set", part_no="PNG-DISC-02",
            stock_qty=4, reorder_level=2, unit_cost=3200)
        m.Camera.objects.create(
            company=co, name="Gate Camera 01", site=wash,
            location="Main gate", status="online")
        m.Camera.objects.create(
            company=co, name="Warehouse Camera 02", site=mill,
            location="Storage hall", status="online")
        m.PurchaseOrder.objects.create(
            company=co, supplier=sup1, coffee_type="Yirgacheffe", grade="Grade 1",
            quantity_kg=5000, unit_price=185, status="approved")
