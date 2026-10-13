"""Seed Orbit ERP demo data: companies, fleet, drivers, trips, GPS, finance, HR.

Run:  .venv/bin/python seed.py
Idempotent-ish: wipes demo companies first (DEMO seed only).
"""
import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "orbit_erp.settings")
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Company, Membership
from fleet.models import (
    Alert, DeliveryOrder, DispatchOrder, Driver, DriverAdvance,
    DriverDocument, FuelLog, Geofence, GPSPing, Inspection, Invoice,
    PartIssue, Payment, Route, ServiceRecord, SparePart, Trip,
    TripExpense, Vehicle, VehicleDocument, WorkshopJob,
)
from shared.models import Attendance as SharedAttendance, Employee as SharedEmployee
from hr.models import Payslip
from fleet.utils import CITY_COORDS, interpolate_points

random.seed(20261013)
now = timezone.now()
ETB = Decimal


def backdate(obj, days=None, months=None, dt=None):
    if dt is None:
        dt = now - timedelta(days=days or 0) - timedelta(days=30 * (months or 0))
    type(obj).objects.filter(pk=obj.pk).update(created_at=dt, updated_at=dt)
    obj.created_at = dt
    return obj


# ------------------------------------------------------------- users


def seed_company(co, admin, full=True):
    # --------------------------------------------------------- vehicles
    makes = [("Sinotruk", "Howo 371", "trailer", 40), ("Sinotruk", "Howo 336", "truck", 30),
             ("Isuzu", "FSR 700", "truck", 12), ("Isuzu", "NPR 71", "truck", 7),
             ("Toyota", "Hilux", "pickup", 1), ("Toyota", "Hiace", "van", 1.5),
             ("MAN", "TGS 18.440", "trailer", 40), ("FAW", "J6P", "tanker", 25)]
    vehicles = []
    n_veh = 10 if full else 4
    for i in range(n_veh):
        make, model, vtype, cap = makes[i % len(makes)]
        v = Vehicle.objects.create(
            company=co, plate_no=f"{3}-AA-{45210 + i * 137}",
            vehicle_type=vtype, make=make, model=model, year=2019 + (i % 5),
            capacity_tons=cap, fuel_type="diesel", ownership="owned" if i % 4 else "leased",
            status="active", odometer_km=random.randint(60000, 320000),
            vin=f"VIN{co.id}{i:05d}ET", registration_no=f"REG-{co.id}-{1000+i}",
            insurance_policy=f"POL-{co.id}-{2000+i}",
            insurance_expiry=(now + timedelta(days=random.choice([20, 200, 320]))).date(),
            purchase_cost=ETB(str(random.randint(2500000, 8500000))),
        )
        vehicles.append(v)
        # documents
        VehicleDocument.objects.create(company=co, vehicle=v, doc_type="registration",
                                       doc_no=f"REG-{1000+i}", expiry_date=(now + timedelta(days=400)).date())
        VehicleDocument.objects.create(company=co, vehicle=v, doc_type="insurance",
                                       doc_no=f"POL-{2000+i}",
                                       expiry_date=(now + timedelta(days=random.choice([12, 25, 200, 330]))).date())
    # --------------------------------------------------------- drivers
    names = ["Abebe Tesfaye", "Kebede Alemu", "Tadesse Bekele", "Mulugeta Haile",
             "Dawit Girma", "Samuel Negash", "Yonas Fikru", "Henok Assefa",
             "Getachew Wolde", "Fikru Tadesse", "Alemayehu Bekele", "Tesfaye Girma"]
    drivers = []
    for i, name in enumerate(names[: 8 if full else 4]):
        d = Driver.objects.create(
            company=co, name=name, phone=f"+251 9{random.randint(10,99)} {random.randint(100000,999999):06d}",
            national_id=f"ET{random.randint(1000000,9999999)}",
            license_no=f"DL-{co.id}-{3000+i}", license_class=random.choice(["C", "D", "E"]),
            license_expiry=(now + timedelta(days=random.choice([18, 150, 400]))).date(),
            status="available", hire_date=(now - timedelta(days=random.randint(200, 1500))).date(),
            address=random.choice(["Addis Ababa", "Adama", "Modjo", "Hawassa"]),
            emergency_contact=f"+251 9{random.randint(10,99)} {random.randint(100000,999999):06d}",
        )
        drivers.append(d)
        DriverDocument.objects.create(company=co, driver=d, doc_type="license", doc_no=d.license_no,
                                      expiry_date=d.license_expiry)
    # --------------------------------------------------------- routes
    route_defs = [
        ("Addis Ababa – Modjo Dry Port", "Addis Ababa", "Modjo", 75, 2.0),
        ("Addis Ababa – Adama", "Addis Ababa", "Adama", 100, 2.5),
        ("Addis Ababa – Hawassa", "Addis Ababa", "Hawassa", 275, 6.0),
        ("Addis Ababa – Shashemene", "Addis Ababa", "Shashemene", 250, 5.5),
        ("Addis Ababa – Dire Dawa", "Addis Ababa", "Dire Dawa", 515, 11.0),
        ("Addis Ababa – Dessie", "Addis Ababa", "Dessie", 400, 8.5),
        ("Addis Ababa – Bahir Dar", "Addis Ababa", "Bahir Dar", 565, 12.0),
        ("Addis Ababa – Gondar", "Addis Ababa", "Gondar", 730, 15.0),
        ("Addis Ababa – Mekelle", "Addis Ababa", "Mekelle", 780, 16.0),
        ("Addis Ababa – Jimma", "Addis Ababa", "Jimma", 350, 7.5),
        ("Addis Ababa – Arba Minch", "Addis Ababa", "Arba Minch", 500, 10.5),
        ("Modjo – Djibouti Corridor", "Modjo", "Djibouti", 900, 20.0),
    ]
    routes = []
    for name, o, dst, km, hrs in route_defs[: 12 if full else 4]:
        routes.append(Route.objects.create(
            company=co, name=name, origin=o, destination=dst, distance_km=km, est_hours=hrs,
            stops="Fuel stop · Checkpoint", restricted_zones="City center during peak hours" if "Addis" in name else ""))
    # geofences
    for gname, ztype, city, radius in [
        ("Addis Depot", "depot", "Addis Ababa", 800), ("Modjo Dry Port", "depot", "Modjo", 1200),
        ("Hawassa Customer Site", "customer", "Hawassa", 500),
        ("Bole Restricted Zone", "restricted", "Addis Ababa", 2000)]:
        lat, lng = CITY_COORDS[city]
        Geofence.objects.create(company=co, name=gname, zone_type=ztype,
                                latitude=lat + random.uniform(-.02, .02),
                                longitude=lng + random.uniform(-.02, .02), radius_m=radius)
    # --------------------------------------------------------- trips (spread over 6 months)
    cargos = ["Green coffee beans (export)", "Coffee husks", "Fertilizer bags", "Construction cement",
              "Wheat grain", "Edible oil cartons", "Machinery parts", "Packed coffee for export"]
    customers = ["Heleph Export Dept", "Abyssinia Traders", "Modjo Logistics Hub", "Hawassa Agro Union",
                 "Dire Dawa Distributors", "Bahir Dar Wholesalers"]
    trips = []
    statuses_plan = (["completed"] * (8 if full else 3) + ["en_route"] * 3 + ["dispatched"] * 2
                     + ["planned"] * 3 + ["cancelled"] * 1)
    for i, st in enumerate(statuses_plan):
        route = random.choice(routes)
        veh = vehicles[i % len(vehicles)]
        drv = drivers[i % len(drivers)]
        months_ago = random.randint(0, 5) if st == "completed" else 0
        dep = now - timedelta(days=random.randint(2, 28) if st == "completed" else -random.randint(0, 5),
                              hours=random.randint(0, 12))
        if st in ("planned", "dispatched"):
            dep = now + timedelta(days=random.randint(0, 4), hours=random.randint(1, 10))
        trip = Trip.objects.create(
            company=co, trip_no=f"TRP-{now.year}-{i+1:03d}", route=route, vehicle=veh, driver=drv,
            status=st, priority=random.choice(["normal", "normal", "high", "urgent"]),
            cargo_desc=random.choice(cargos), cargo_weight_tons=round(random.uniform(5, 38), 1),
            departure_planned=dep, arrival_planned=dep + timedelta(hours=float(route.est_hours)),
            departure_actual=dep if st in ("en_route", "delivered", "completed") else None,
            arrival_actual=dep + timedelta(hours=float(route.est_hours) + random.uniform(-1, 3))
            if st == "completed" else None,
            odometer_start=veh.odometer_km,
            odometer_end=veh.odometer_km + route.distance_km if st == "completed" else veh.odometer_km,
            created_by=admin,
        )
        if st == "completed":
            backdate(trip, dt=dep - timedelta(hours=2))
        trips.append(trip)
        if st in ("dispatched", "en_route"):
            DispatchOrder.objects.create(
                company=co, order_no=f"DSP-{trip.trip_no}", trip=trip,
                scheduled_departure=trip.departure_planned, priority=trip.priority,
                instructions="Follow assigned route. Report checkpoints every 2 hours.",
                status="dispatched" if st == "en_route" else "scheduled", assigned_by=admin)
        if st == "en_route":
            veh.status = "on_trip"
            veh.save(update_fields=["status"])
            drv.status = "on_trip"
            drv.save(update_fields=["status"])
            pts = interpolate_points(CITY_COORDS[route.origin] if route.origin in CITY_COORDS else (9.0, 38.76),
                                     CITY_COORDS[route.destination] if route.destination in CITY_COORDS else (9.0, 38.76),
                                     n=26)
            base = now - timedelta(hours=3)
            for j, (lat, lng) in enumerate(pts[: random.randint(14, 22)]):
                GPSPing.objects.create(company=co, trip=trip, latitude=lat, longitude=lng,
                                       speed_kmh=round(random.uniform(45, 78), 1),
                                       event="departed" if j == 0 else ("checkpoint" if j % 6 == 0 else ""),
                                       recorded_at=base + timedelta(minutes=j * 8))
        # deliveries
        for k in range(random.randint(1, 2)):
            cust = random.choice(customers)
            dstat = {"completed": "delivered", "en_route": "in_transit",
                     "dispatched": "pending", "planned": "pending", "cancelled": "failed"}[st]
            d = DeliveryOrder.objects.create(
                company=co, order_no=f"DLV-{trip.trip_no}-{k+1}", trip=trip,
                customer_name=cust, customer_phone=f"+251 11 {random.randint(1000000,9999999)}",
                destination=route.destination, cargo_desc=trip.cargo_desc,
                cargo_weight_tons=trip.cargo_weight_tons, status=dstat,
                pod_signed_by=f"Receiver {random.randint(1,9)}" if dstat == "delivered" else "",
                pod_time=trip.arrival_actual if dstat == "delivered" else None,
                pod_notes="Goods received in good condition." if dstat == "delivered" else "",
            )
            if st == "completed":
                backdate(d, dt=dep)
        # expenses + fuel for completed & en_route
        if st in ("completed", "en_route"):
            for cat, amt in [("fuel", random.uniform(8000, 30000)), ("toll", random.uniform(300, 1500)),
                             ("allowance", random.uniform(1500, 5000))]:
                TripExpense.objects.create(company=co, trip=trip, category=cat,
                                           description=f"{cat.title()} for {trip.trip_no}",
                                           amount=ETB(str(round(amt, 2))), date=(dep.date()),
                                           paid_by=drv.name, approved=st == "completed")
            FuelLog.objects.create(company=co, vehicle=veh, trip=trip, date=dep.date(),
                                   station=random.choice(["Total Addis", "Shell Modjo", "Petro Adama"]),
                                   liters=ETB(str(round(route.distance_km / random.uniform(2.2, 3.4), 1))),
                                   cost=ETB(str(round(random.uniform(9000, 32000), 2))),
                                   odometer_km=veh.odometer_km + route.distance_km)
            DriverAdvance.objects.create(company=co, driver=drv, trip=trip,
                                         amount=ETB(str(random.randint(3000, 12000))),
                                         date=dep.date(), purpose="Trip allowance advance",
                                         settled=st == "completed")
    # monthly fuel history (for charts) — realistic: monthly km ÷ km-per-liter
    for m_ago in range(1, 6):
        for v in vehicles:
            monthly_km = random.randint(3000, 6000)
            liters_total = monthly_km / random.uniform(2.4, 3.6)
            n_logs = random.randint(2, 3)
            odo = v.odometer_km - sum(random.randint(3000, 6000) for _ in range(m_ago))
            for _ in range(n_logs):
                d = (now - timedelta(days=30 * m_ago)).date().replace(day=random.randint(3, 26))
                liters = ETB(str(round(liters_total / n_logs, 1)))
                odo += monthly_km // n_logs
                FuelLog.objects.create(company=co, vehicle=v, date=d,
                                       station=random.choice(["Total Addis", "Shell Modjo", "Petro Adama"]),
                                       liters=liters, cost=(liters * ETB("78.50")).quantize(ETB("0.01")),
                                       odometer_km=odo)
    # monthly invoices + payments (revenue charts)
    inv_n = 0
    for m_ago in range(5, -1, -1):
        for _ in range(random.randint(2, 4)):
            inv_n += 1
            issued = (now - timedelta(days=30 * m_ago)).date().replace(day=random.randint(2, 27))
            trip = random.choice([t for t in trips if t.status == "completed"]) if trips else None
            amount = ETB(str(round(random.uniform(25000, 180000), 2)))
            tax = (amount * ETB("0.15")).quantize(ETB("0.01"))
            status = "paid" if m_ago >= 2 else random.choice(["sent", "sent", "overdue", "paid"])
            inv = Invoice.objects.create(
                company=co, invoice_no=f"INV-{now.year}-{inv_n:04d}",
                customer_name=random.choice(customers), trip=trip,
                description=f"Transport service — {trip.route.name}" if trip else "Transport service",
                amount=amount, tax=tax, status=status, issued_date=issued,
                due_date=issued + timedelta(days=30))
            backdate(inv, dt=timezone.make_aware(datetime.combine(issued, datetime.min.time())))
            if status == "paid":
                Payment.objects.create(company=co, invoice=inv, amount=inv.total, method="bank",
                                       date=issued + timedelta(days=random.randint(5, 25)),
                                       reference=f"TRX-{inv_n:06d}", received_by="Finance")
    # maintenance
    for v in random.sample(vehicles, k=min(5, len(vehicles))):
        ServiceRecord.objects.create(
            company=co, vehicle=v, service_type="preventive", title="Engine oil & filters service",
            scheduled_date=(now - timedelta(days=random.randint(10, 90))).date(),
            completed_date=(now - timedelta(days=random.randint(5, 80))).date(),
            cost=ETB(str(random.randint(15000, 45000))), workshop="Orbit Workshop — Kaliti",
            status="completed")
        ServiceRecord.objects.create(
            company=co, vehicle=v, service_type=random.choice(["preventive", "corrective"]),
            title=random.choice(["Brake system overhaul", "Tire replacement (6)", "Suspension repair"]),
            scheduled_date=(now + timedelta(days=random.randint(3, 40))).date(),
            cost=ETB(str(random.randint(20000, 90000))), status="scheduled")
    for v in random.sample(vehicles, k=2):
        Inspection.objects.create(company=co, vehicle=v, driver=random.choice(drivers),
                                  date=(now - timedelta(days=random.randint(1, 20))).date(),
                                  defects_found="" if random.random() > 0.4 else "Worn wiper blades.",
                                  passed=random.random() > 0.2, approved_by="Safety Officer")
    # parts
    parts = [("Engine oil filter", "FLT-001", "Filters", 40), ("Brake pads (set)", "BRK-210", "Brakes", 3),
             ("Air filter", "FLT-014", "Filters", 25), ("Tire 12R22.5", "TYR-122", "Tires", 8),
             ("Clutch kit", "CLT-088", "Transmission", 2), ("Headlight bulb", "ELC-331", "Electrical", 60),
             ("Fuel pump", "FUP-102", "Engine", 4), ("Shock absorber", "SUS-077", "Suspension", 1)]
    part_objs = []
    for name, pno, cat, qty in parts[: 8 if full else 5]:
        part_objs.append(SparePart.objects.create(
            company=co, name=name, part_no=pno, category=cat, qty_on_hand=qty,
            reorder_level=5, unit_cost=ETB(str(random.randint(800, 45000))), location="Main Store — A2"))
    for i, v in enumerate(random.sample(vehicles, k=2)):
        job = WorkshopJob.objects.create(company=co, job_no=f"WO-{now.year}-{i+1:03d}", vehicle=v,
                                         title="Brake overhaul & service", status="in_progress",
                                         technician="Mechanic Alemu", labor_cost=ETB("12000"))
        PartIssue.objects.create(company=co, part=part_objs[1], job=job, quantity=2, issued_to="Mechanic Alemu")
    # employees / HR
    employees = []
    for drv in drivers:
        emp = SharedEmployee.objects.create(company=co, name=drv.name, position="Driver",
                                            phone=drv.phone, salary=ETB(str(random.randint(12000, 20000))))
        drv.shared_employee = emp
        drv.save(update_fields=["shared_employee"])
        employees.append(emp)
    for nm, role, sal in [("Hanna Girma", "Dispatcher", 18000), ("Dawit Bekele", "Accountant", 25000),
                          ("Sara Tesfaye", "Fleet Manager", 35000)]:
        employees.append(SharedEmployee.objects.create(company=co, name=nm, position=role,
                                                       phone=f"+251 9{random.randint(10,99)} 555010",
                                                       salary=ETB(str(sal))))
    for e in employees:
        for back in range(1, 6):
            d = (now - timedelta(days=back)).date()
            if d.weekday() < 5:
                SharedAttendance.objects.create(company=co, employee=e, date=d,
                                                status="present" if random.random() > 0.08 else "absent")
    last_month = (now.replace(day=1) - timedelta(days=1)).replace(day=1).date()
    for e in employees:
        gross = e.salary
        ded = (gross * ETB("0.15")).quantize(ETB("0.01"))
        Payslip.objects.create(company=co, employee=e, period=last_month, basic=gross,
                               deductions=ded, net=gross - ded, status="paid")
    # alerts
    Alert.objects.create(company=co, level="warning", title="2 vehicle insurance policies expire within 30 days",
                         message="Renew before expiry to stay compliant.")
    Alert.objects.create(company=co, level="critical", title="Brake pads stock below reorder level",
                         message="Only 3 sets left in Main Store — A2.")
    print(f"seeded {co.name}: {len(vehicles)} vehicles, {len(drivers)} drivers, {len(trips)} trips")




def run():
    """Seed demo companies.

    Self-healing per company: a demo company is (re)seeded whenever it lacks
    trip data — this repairs partial seeds from interrupted boots. Companies
    that already have trips are never touched.
    """
    admin, _ = User.objects.get_or_create(username="admin", defaults={"is_superuser": True, "is_staff": True, "email": "admin@orbit.et"})
    admin.set_password("Orbit@2026")
    admin.is_superuser = True
    admin.is_staff = True
    admin.save()
    print("user: admin / Orbit@2026")

    specs = [
        ("heleph-coffee-group",
         dict(name="Heleph Coffee Group", industry="Coffee Export & Logistics", country="Ethiopia",
              city="Addis Ababa", phone="+251 11 557 0000", email="info@helephcoffee.et",
              tin="0023456789", address="Bole Sub-city, Addis Ababa", plan="enterprise"),
         True),
        ("abyssinia-freight-lines",
         dict(name="Abyssinia Freight Lines", industry="Freight & Transport", country="Ethiopia",
              city="Modjo", phone="+251 11 448 1122", email="ops@abyssiniafreight.et",
              address="Modjo Dry Port Area", plan="professional"),
         False),
    ]
    for slug, kwargs, full in specs:
        co = Company.objects.filter(slug=slug).first()
        if co and Trip.objects.filter(company=co).exists():
            print(f"{co.name}: already seeded, skipping")
            continue
        if co:
            # Partial seed from an interrupted boot — wipe cleanly and reseed.
            # Delete trips first: Trip PROTECTs vehicle/driver/route.
            print(f"{co.name}: incomplete data found, reseeding")
            Trip.objects.filter(company=co).delete()
            co.delete()
        co = Company.objects.create(slug=slug, **kwargs)
        Membership.objects.get_or_create(user=admin, company=co, defaults={"role": "owner"})
        print("seeding:", co.name)
        seed_company(co, admin, full=full)
    print("DONE")


if __name__ == "__main__":
    run()