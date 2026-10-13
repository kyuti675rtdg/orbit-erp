"""Seed industry demo companies (import, export, manufacturing, rental).

Self-healing per company: a demo company is (re)seeded only when it has no
records in its industry app; existing companies are never touched.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Company, Membership

User = get_user_model()
TODAY = date.today()


def get_or_demo_company(name, industry_key, industry_label, admin):
    co, created = Company.objects.get_or_create(
        name=name,
        defaults={"industry": industry_label, "industry_key": industry_key,
                  "country": "Ethiopia", "city": "Addis Ababa"},
    )
    if created:
        Membership.objects.get_or_create(
            user=admin, company=co,
            defaults={"role": "owner", "is_active": True})
    return co


def seed_shared(co):
    """Departments, employees, announcements, notifications for a company."""
    from shared import models as s
    if s.Employee.objects.filter(company=co).exists():
        return
    ops = s.Department.objects.create(company=co, name="Operations", code="OPS")
    fin = s.Department.objects.create(company=co, name="Finance", code="FIN")
    hr = s.Department.objects.create(company=co, name="Human Resources", code="HR")
    emps = [
        ("EMP-001", "Abebe Tesfaye", ops, "Operations Manager", 45000),
        ("EMP-002", "Hanna Girma", fin, "Senior Accountant", 38000),
        ("EMP-003", "Dawit Alemu", ops, "Logistics Officer", 28000),
        ("EMP-004", "Meron Bekele", hr, "HR Officer", 30000),
    ]
    for eid, name, dept, pos, sal in emps:
        s.Employee.objects.create(company=co, employee_id=eid, name=name,
                                  department=dept, position=pos, salary=sal,
                                  hire_date=TODAY - timedelta(days=400),
                                  phone="+251911000000", status="active")
    s.Announcement.objects.create(
        company=co, title="Welcome to Orbit ERP",
        body="Your company workspace is ready. Explore the modules in the sidebar.",
        publish_date=TODAY, audience="All employees", is_active=True)


class Command(BaseCommand):
    help = "Seed industry demo companies (self-healing)"

    @transaction.atomic
    def handle(self, *args, **options):
        admin = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not admin:
            self.stdout.write(self.style.WARNING("no users yet; skipping"))
            return

        # ---- existing companies stay transport
        for co in Company.objects.all():
            if not co.industry_key:
                co.industry_key = "transport"
                co.save(update_fields=["industry_key"])

        # ---- Import demo company
        co = get_or_demo_company("Abyssinia Import Trading", "import",
                                 "Import & Trading", admin)
        from imports import models as im
        if not im.Supplier.objects.filter(company=co).exists():
            s1 = im.Supplier.objects.create(company=co, name="Dubai Auto Trading LLC",
                                            country="UAE", city="Dubai",
                                            contact_person="Ahmed Khalid",
                                            email="sales@dubai-auto.ae", payment_terms="30 days")
            s2 = im.Supplier.objects.create(company=co, name="Guangzhou Machinery Co.",
                                            country="China", city="Guangzhou",
                                            contact_person="Li Wei", payment_terms="LC at sight")
            im.SupplierContact.objects.create(company=co, supplier=s1, name="Ahmed Khalid",
                                              role="Sales Manager", email="sales@dubai-auto.ae")
            po1 = im.PurchaseOrder.objects.create(
                company=co, po_no="PO-2026-001", supplier=s1, order_date=TODAY - timedelta(days=40),
                delivery_date=TODAY + timedelta(days=20), total_amount=185000, currency="USD",
                status="confirmed")
            po2 = im.PurchaseOrder.objects.create(
                company=co, po_no="PO-2026-002", supplier=s2, order_date=TODAY - timedelta(days=12),
                total_amount=96400, currency="USD", status="sent")
            im.ImportRequest.objects.create(
                company=co, request_no="IR-2026-014", product_description="Toyota Hilux pickup trucks x6",
                quantity=6, estimated_value=210000, requested_by="Abebe Tesfaye",
                request_date=TODAY - timedelta(days=5), status="submitted")
            sh = im.Shipment.objects.create(
                company=co, shipment_no="SH-2026-031", purchase_order=po1,
                origin="Jebel Ali, UAE", destination="Djibouti Port", mode="sea",
                etd=TODAY - timedelta(days=10), eta=TODAY + timedelta(days=8),
                status="in_transit")
            im.Container.objects.create(company=co, container_no="MSKU-482913-0",
                                        shipment=sh, container_type="40ft", seal_no="SL-88912")
            im.CustomsDeclaration.objects.create(
                company=co, declaration_no="CUS-2026-118", shipment=sh,
                declaration_date=TODAY - timedelta(days=2),
                duty_amount=42000, tax_amount=18500, status="submitted")
            prod = im.ImportProduct.objects.create(company=co, name="Toyota Hilux 2.8L",
                                                   category="cars", unit="pcs", unit_price=31000)
            im.WarehouseStock.objects.create(company=co, product=prod,
                                            warehouse="Kality Warehouse", quantity=4)
            inv = im.SupplierInvoice.objects.create(
                company=co, invoice_no="SI-2026-041", supplier=s1, purchase_order=po1,
                invoice_date=TODAY - timedelta(days=20), due_date=TODAY + timedelta(days=10),
                amount=185000, paid_amount=90000, status="partial")
            im.SupplierPayment.objects.create(company=co, payment_no="SP-2026-019",
                                              invoice=inv, payment_date=TODAY - timedelta(days=18),
                                              amount=90000, method="bank", reference="TT-88213")
            self.stdout.write(self.style.SUCCESS("seeded Abyssinia Import Trading"))

        # ---- Export demo company
        co = get_or_demo_company("Buna Coffee Export", "export",
                                 "Coffee Export", admin)
        from exports import models as ex
        if not ex.Buyer.objects.filter(company=co).exists():
            b1 = ex.Buyer.objects.create(company=co, name="Hamburg Kaffee GmbH",
                                         country="Germany", city="Hamburg",
                                         contact_person="Jonas Meyer",
                                         email="buy@hamburg-kaffee.de")
            b2 = ex.Buyer.objects.create(company=co, name="Tokyo Roast Co.",
                                         country="Japan", city="Tokyo",
                                         contact_person="Yuki Tanaka")
            ex.BuyerContact.objects.create(company=co, buyer=b1, name="Jonas Meyer",
                                           role="Procurement Head")
            ex.ExportProduct.objects.create(company=co, name="Yirgacheffe Washed Grade 1",
                                            category="coffee", unit="kg", unit_price=8.40,
                                            stock_qty=12500)
            ex.ExportProduct.objects.create(company=co, name="Sidamo Natural Grade 2",
                                            category="coffee", unit="kg", unit_price=7.10,
                                            stock_qty=8200)
            ct = ex.ExportContract.objects.create(
                company=co, contract_no="EC-2026-007", buyer=b1,
                sign_date=TODAY - timedelta(days=60), total_value=252000,
                currency="USD", status="active")
            o1 = ex.ExportOrder.objects.create(
                company=co, order_no="EO-2026-021", buyer=b1, contract=ct,
                order_date=TODAY - timedelta(days=25),
                delivery_date=TODAY + timedelta(days=15), total_amount=84000,
                currency="USD", status="preparing")
            o2 = ex.ExportOrder.objects.create(
                company=co, order_no="EO-2026-022", buyer=b2,
                order_date=TODAY - timedelta(days=8), total_amount=56800,
                currency="USD", status="confirmed")
            ex.QualityInspection.objects.create(
                company=co, inspection_no="QI-2026-033", order=o1,
                inspection_date=TODAY - timedelta(days=3), inspector="Alemayehu R.",
                result="conditional", certificate_no="",
                notes="Moisture slightly high; re-test before stuffing.")
            sh = ex.Shipment.objects.create(
                company=co, shipment_no="ES-2026-012", order=o2,
                destination_port="Yokohama", vessel="MV Addis Star",
                etd=TODAY - timedelta(days=4), eta=TODAY + timedelta(days=26),
                status="in_transit")
            ex.Container.objects.create(company=co, container_no="TCLU-771204-5",
                                        shipment=sh, seal_no="SL-44190")
            ex.ExportDocument.objects.create(company=co, doc_no="ED-2026-051", order=o2,
                                             doc_type="commercial",
                                             title="Commercial Invoice + Packing List",
                                             status="issued")
            inv = ex.ExportInvoice.objects.create(
                company=co, invoice_no="EI-2026-028", buyer=b1, order=o1,
                invoice_date=TODAY - timedelta(days=15), due_date=TODAY + timedelta(days=15),
                amount=84000, paid_amount=0, status="unpaid")
            ex.ExportCost.objects.create(company=co, order=o1, cost_type="Inland transport",
                                         description="Addis -> Djibouti trucking",
                                         amount=4200, date=TODAY - timedelta(days=10))
            ex.ExportCost.objects.create(company=co, order=o1, cost_type="Export documentation",
                                         amount=850, date=TODAY - timedelta(days=6))
            self.stdout.write(self.style.SUCCESS("seeded Buna Coffee Export"))

        # ---- Manufacturing demo company
        co = get_or_demo_company("Addis Food Manufacturing", "manufacturing",
                                 "Food Processing", admin)
        from manufacturing import models as mf
        if not mf.Product.objects.filter(company=co).exists():
            cat = mf.ProductCategory.objects.create(company=co, name="Biscuits",
                                                   description="Baked biscuit products")
            p1 = mf.Product.objects.create(company=co, name="Marie Biscuits 400g",
                                           sku="BSC-MAR-400", category=cat, unit="carton",
                                           unit_price=520)
            p2 = mf.Product.objects.create(company=co, name="Digestive Biscuits 250g",
                                           sku="BSC-DIG-250", category=cat, unit="carton",
                                           unit_price=380)
            fl = mf.RawMaterial.objects.create(company=co, name="Wheat Flour",
                                               unit="quintal", unit_cost=2400,
                                               stock_qty=180, reorder_level=200,
                                               supplier="Gojjam Millers")
            sg = mf.RawMaterial.objects.create(company=co, name="Sugar",
                                               unit="quintal", unit_cost=3100,
                                               stock_qty=320, reorder_level=150,
                                               supplier="Wonji Sugar")
            bom = mf.BOM.objects.create(company=co, product=p1, version="2.1",
                                        description="Marie recipe 2026", is_active=True)
            mf.BOMLine.objects.create(company=co, bom=bom, material=fl, quantity=60)
            mf.BOMLine.objects.create(company=co, bom=bom, material=sg, quantity=22)
            wc = mf.WorkCenter.objects.create(company=co, name="Baking Line 1",
                                              center_type="Oven line", capacity_per_day=800)
            mc = mf.Machine.objects.create(company=co, name="Rotary Oven R-2",
                                           work_center=wc, model="RX-9000",
                                           status="running",
                                           last_maintenance=TODAY - timedelta(days=30))
            mf.MaintenanceRecord.objects.create(
                company=co, machine=mc, maintenance_type="preventive",
                scheduled_date=TODAY + timedelta(days=12), technician="Tsegaye M.",
                status="scheduled")
            po = mf.ProductionOrder.objects.create(
                company=co, order_no="MFG-2026-104", product=p1, quantity=1200,
                order_date=TODAY - timedelta(days=6), due_date=TODAY + timedelta(days=4),
                status="in_progress")
            mf.MaterialIssue.objects.create(company=co, issue_no="MI-2026-210",
                                            production_order=po, material=fl, quantity=72,
                                            issue_date=TODAY - timedelta(days=5),
                                            issued_by="Kebede A.")
            mf.QualityCheck.objects.create(company=co, check_no="QC-2026-089",
                                           production_order=po,
                                           check_date=TODAY - timedelta(days=1),
                                           inspector="Selam T.", result="pass",
                                           defects_found=3)
            mf.Batch.objects.create(company=co, batch_no="B-2026-104-A",
                                    production_order=po, product=p1, quantity=1200,
                                    production_date=TODAY - timedelta(days=1),
                                    expiry_date=TODAY + timedelta(days=300),
                                    status="released")
            wh = mf.Warehouse.objects.create(company=co, name="Finished Goods Store",
                                             location="Akaki", manager="Yonas D.")
            mf.Stock.objects.create(company=co, warehouse=wh, item_type="finished",
                                    item_name="Marie Biscuits 400g", quantity=5400,
                                    unit="carton")
            self.stdout.write(self.style.SUCCESS("seeded Addis Food Manufacturing"))

        # ---- Rental demo company
        co = get_or_demo_company("Sheger Property Management", "rental",
                                 "Property Rental", admin)
        from rentals import models as rn
        if not rn.Property.objects.filter(company=co).exists():
            prop = rn.Property.objects.create(
                company=co, name="Bole Friendship Center",
                property_type="commercial", city="Addis Ababa",
                address="Bole, Friendship St", manager="Rahel S.")
            bld = rn.Building.objects.create(company=co, property=prop,
                                             name="Tower A", floors=8)
            units = []
            for i, (fl, rent, st) in enumerate([(3, 45000, "occupied"), (3, 45000, "occupied"),
                                                (5, 68000, "occupied"), (5, 68000, "vacant"),
                                                (7, 95000, "occupied")], start=301):
                units.append(rn.Unit.objects.create(
                    company=co, unit_no=f"A-{i}", building=bld, floor=fl,
                    bedrooms=2, bathrooms=2, area_sqm=120, monthly_rent=rent,
                    status=st))
            t1 = rn.Tenant.objects.create(company=co, name="Zemen Bank SC",
                                          phone="+251115570000", email="admin@zemenbank.et")
            t2 = rn.Tenant.objects.create(company=co, name="Abyssinia Steel PLC",
                                          phone="+251115580000")
            l1 = rn.Lease.objects.create(
                company=co, lease_no="LS-2026-011", unit=units[0], tenant=t1,
                start_date=TODAY - timedelta(days=200), end_date=TODAY + timedelta(days=165),
                monthly_rent=45000, deposit=90000, status="active")
            l2 = rn.Lease.objects.create(
                company=co, lease_no="LS-2026-012", unit=units[2], tenant=t2,
                start_date=TODAY - timedelta(days=90), end_date=TODAY + timedelta(days=20),
                monthly_rent=68000, deposit=136000, status="active")
            rs1 = rn.RentSchedule.objects.create(company=co, lease=l1,
                                                 due_date=TODAY.replace(day=5),
                                                 amount=45000, status="paid")
            rn.RentSchedule.objects.create(company=co, lease=l2,
                                           due_date=(TODAY - timedelta(days=35)).replace(day=5),
                                           amount=68000, status="overdue")
            inv = rn.RentInvoice.objects.create(
                company=co, invoice_no="RI-2026-073", lease=l2,
                issue_date=TODAY - timedelta(days=30),
                due_date=TODAY - timedelta(days=5), amount=68000,
                paid_amount=0, status="unpaid")
            rn.RentPayment.objects.create(company=co, payment_no="RP-2026-051",
                                          invoice=rn.RentInvoice.objects.create(
                                              company=co, invoice_no="RI-2026-070", lease=l1,
                                              issue_date=TODAY - timedelta(days=32),
                                              due_date=TODAY - timedelta(days=7),
                                              amount=45000, paid_amount=45000,
                                              status="paid"),
                                          payment_date=TODAY - timedelta(days=10),
                                          amount=45000, method="bank",
                                          reference="TRF-99120")
            rn.Deposit.objects.create(company=co, lease=l1, amount=90000, status="held")
            rn.Deposit.objects.create(company=co, lease=l2, amount=136000, status="held")
            mr = rn.MaintenanceRequest.objects.create(
                company=co, request_no="MR-2026-019", unit=units[2], tenant=t2,
                request_date=TODAY - timedelta(days=2), category="Plumbing",
                description="Bathroom faucet leaking in unit A-303",
                priority="high", status="open")
            rn.MaintenanceWorkOrder.objects.create(
                company=co, wo_no="WO-2026-033", request=mr,
                assigned_to="Girma T.", scheduled_date=TODAY + timedelta(days=1),
                status="open")
            rn.UtilityBill.objects.create(company=co, unit=units[0],
                                          utility_type="electricity",
                                          billing_month=TODAY.replace(day=1),
                                          amount=3200, status="unpaid")
            self.stdout.write(self.style.SUCCESS("seeded Sheger Property Management"))

        # shared data for every industry demo company
        for co in Company.objects.filter(
                name__in=["Abyssinia Import Trading", "Buna Coffee Export",
                          "Addis Food Manufacturing", "Sheger Property Management"]):
            seed_shared(co)
            Membership.objects.get_or_create(user=admin, company=co,
                                             defaults={"role": "owner", "is_active": True})

        self.stdout.write(self.style.SUCCESS("seed_industries finished"))
