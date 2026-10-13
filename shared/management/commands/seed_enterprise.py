"""Seed enterprise-module demo data (HR, Finance, Admin, Comms, Executive).

Self-healing: only seeds a company when it has no enterprise data yet.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Company

TODAY = timezone.now().date()


def seed_hr(co):
    from hr import models as h
    from shared import models as s
    if h.Position.objects.filter(company=co).exists():
        return
    ops = s.Department.objects.filter(company=co).first()
    for title, level in [("General Manager", "Executive"), ("Accountant", "Mid"),
                         ("HR Officer", "Mid"), ("Driver", "Junior"),
                         ("Warehouse Keeper", "Junior")]:
        h.Position.objects.create(company=co, department=ops, title=title, level=level)
    h.Shift.objects.create(company=co, name="Morning", start_time="08:00", end_time="17:00")
    h.Shift.objects.create(company=co, name="Evening", start_time="14:00", end_time="22:00")
    vac = h.JobVacancy.objects.create(
        company=co, title="Senior Accountant", department=ops, openings=2,
        description="Manage GL, AP/AR and monthly close.", posted_date=TODAY,
        closing_date=TODAY + timedelta(days=30), status="open")
    for name, stage, rating in [("Selamawit Kassa", "interview", 4),
                               ("Yonas Fikru", "screening", 3),
                               ("Tigist Alemayehu", "applied", 0)]:
        h.Applicant.objects.create(company=co, vacancy=vac, name=name, stage=stage,
                                   rating=rating, applied_date=TODAY - timedelta(days=6))
    struct = h.SalaryStructure.objects.create(company=co, name="Standard Monthly",
                                              description="Default salary structure")
    h.SalaryComponent.objects.create(company=co, structure=struct, name="Transport Allowance",
                                     kind="allowance", amount_type="fixed", value=3000)
    h.SalaryComponent.objects.create(company=co, structure=struct, name="Pension (7%)",
                                     kind="deduction", amount_type="percent", value=7)
    h.Benefit.objects.create(company=co, name="Health Insurance",
                             description="Annual medical cover", eligibility="All full-time staff")
    h.Benefit.objects.create(company=co, name="Annual Bonus",
                             description="13th month salary", eligibility="1+ year of service")
    h.Training.objects.create(company=co, title="Workplace Safety",
                              provider="Orbit Academy", start_date=TODAY + timedelta(days=14),
                              cost=12000, description="Mandatory safety training.")
    h.HRDocument.objects.create(company=co, title="Employee Handbook",
                                category="handbook", version="2.0",
                                description="Company policies and code of conduct.")


def seed_finance(co):
    from finance import models as f
    from shared import models as s
    _seed_chart(co, s)
    if not f.BankAccount.objects.filter(company=co).exists():
        _seed_bank(co, f)
    if not f.TaxRate.objects.filter(company=co).exists():
        _seed_tax(co, f, s)


def _seed_chart(co, s):
    chart = [
        ("1000", "Cash & Bank", "asset"), ("1100", "Accounts Receivable", "asset"),
        ("1200", "Inventory", "asset"), ("1500", "Fixed Assets", "asset"),
        ("2000", "Salary Payable", "liability"), ("2100", "Accounts Payable", "liability"),
        ("2200", "Tax Payable", "liability"), ("3000", "Owner Capital", "equity"),
        ("4000", "Sales Revenue", "revenue"), ("4100", "Rental Income", "revenue"),
        ("4200", "Transport Revenue", "revenue"), ("5000", "Salary Expense", "expense"),
        ("5100", "Purchases", "expense"), ("5200", "Operating Expenses", "expense"),
    ]
    for code, name, typ in chart:
        s.GLAccount.objects.get_or_create(
            company=co, code=code, defaults={"name": name, "account_type": typ})


def _seed_bank(co, f):
    f.BankAccount.objects.create(company=co, name="CBE Main", bank_name="Commercial Bank of Ethiopia",
                                 account_no="1000123456789", opening_balance=2500000)
    f.BankAccount.objects.create(company=co, name="Awash USD", bank_name="Awash Bank",
                                 account_no="2000987654321", currency="USD", opening_balance=45000)


def _seed_tax(co, f, s):
    f.TaxRate.objects.create(company=co, name="VAT", code="VAT15", rate=15)
    f.TaxRate.objects.create(company=co, name="Employment Income Tax", code="PIT", rate=30)
    f.CostCenter.objects.create(company=co, code="CC-01", name="Head Office")
    f.CostCenter.objects.create(company=co, code="CC-02", name="Operations")
    bud = f.Budget.objects.create(company=co, name="Annual Budget 2026", fiscal_year="2026/27",
                                  start_date=TODAY.replace(month=1, day=1),
                                  end_date=TODAY.replace(month=12, day=31), status="approved")
    for code, amount in [("5000", 2400000), ("5200", 1800000), ("5100", 5000000)]:
        acct = s.GLAccount.objects.get(company=co, code=code)
        f.BudgetLine.objects.create(company=co, budget=bud, account=acct, budgeted=amount)


def seed_admin(co):
    from administration import models as a
    if a.Branch.objects.filter(company=co).exists():
        return
    a.Branch.objects.create(company=co, name="Head Office", code="HO",
                            city="Addis Ababa", phone="+251115570000", is_active=True)
    a.Branch.objects.create(company=co, name="Djibouti Branch", code="DJI",
                            city="Djibouti", is_active=True)
    a.Currency.objects.create(company=co, code="ETB", name="Ethiopian Birr",
                              symbol="Br", exchange_rate=1, is_base=True)
    a.Currency.objects.create(company=co, code="USD", name="US Dollar",
                              symbol="$", exchange_rate=140)
    a.ApprovalRule.objects.create(company=co, document_type="leave",
                                  approver_role="manager", steps=1)
    a.ApprovalRule.objects.create(company=co, document_type="expense", min_amount=10000,
                                  approver_role="admin", steps=1)
    for event in ["leave_approved", "leave_rejected", "invoice_overdue", "task_assigned"]:
        a.NotificationSetting.objects.create(company=co, event=event, channel="in_app")
    a.SystemBackup.objects.create(company=co, name="Weekly DB Backup",
                                  scheduled_at=timezone.now() + timedelta(days=2),
                                  status="scheduled")


def backfill_finance_ledger(co):
    """Post existing sector invoices/bills into the finance ledger.

    Sector seeds create operational invoices directly, bypassing the CRUD
    post-save hooks that normally post them to Finance. This backfill runs
    the same idempotent sync functions (AR/AP use source refs, journals use
    references) so the GL becomes the accurate system of record without
    duplicating anything already posted.
    """
    from core import integrations as integ
    try:
        from imports.models import SupplierInvoice
        for inv in SupplierInvoice.objects.filter(company=co).exclude(status="draft"):
            integ.sync_supplier_invoice_to_bill(co, inv, True, None)
    except Exception:
        pass
    try:
        from exports.models import ExportInvoice
        for inv in ExportInvoice.objects.filter(company=co).exclude(status="draft"):
            integ.sync_export_invoice_to_ar(co, inv, True, None)
    except Exception:
        pass
    try:
        from coffee.models import CoffeeExportInvoice
        for inv in CoffeeExportInvoice.objects.filter(company=co).exclude(status="draft"):
            integ.sync_coffee_invoice_to_ar(co, inv, True, None)
    except Exception:
        pass
    try:
        from rentals.models import RentInvoice
        for inv in RentInvoice.objects.filter(company=co):
            integ.sync_rent_invoice_to_ar(co, inv, True, None)
    except Exception:
        pass
    try:
        from fleet.models import Invoice
        for inv in Invoice.objects.filter(company=co).exclude(status__in=["draft", "cancelled"]):
            integ.sync_fleet_invoice_to_ar(co, inv, True, None)
    except Exception:
        pass


def seed_comms(co, admin):
    from comms import models as cm
    if cm.Task.objects.filter(company=co).exists():
        return
    conv = cm.Conversation.objects.create(company=co, title="Management",
                                          conversation_type="department")
    conv.participants.add(admin)
    cm.Message.objects.create(company=co, conversation=conv, sender=admin,
                              body="Welcome to the company channel. Please review the Q4 targets.")
    for title, prio, days in [("Prepare monthly financial summary", "high", 5),
                              ("Update employee attendance records", "normal", 3),
                              ("Review pending leave requests", "urgent", 2)]:
        cm.Task.objects.create(company=co, title=title, priority=prio,
                               due_date=TODAY + timedelta(days=days),
                               assigned_to=admin, created_by=admin)
    cm.Meeting.objects.create(company=co, title="Weekly Management Review",
                              agenda="KPIs, pending approvals, blockers",
                              start=timezone.now() + timedelta(days=2),
                              location="Board Room")


def seed_requests(co, admin):
    """Sample requests across the workflow: submitted, approved, returned, draft."""
    from datetime import timedelta
    from django.utils import timezone
    from req import hooks as rq_hooks
    from req.models import Request
    if Request.objects.filter(company=co).exists():
        return
    today = timezone.now().date()
    approver = rq_hooks.pick_approver(co, admin) or admin
    samples = [
        ("leave", "Annual leave — family event", "Requesting 5 days annual leave.",
         None, today + timedelta(days=14), today + timedelta(days=14),
         today + timedelta(days=18), "submitted"),
        ("purchase", "Purchase 10 office chairs", "Ergonomic chairs for the new hires.",
         85000, today + timedelta(days=10), None, None, "submitted"),
        ("expense", "Fuel reimbursement — October", "Field trips fuel receipts attached.",
         12500, None, None, None, "approved"),
        ("maintenance", "Generator servicing", "Quarterly service for the backup generator.",
         18000, today + timedelta(days=7), None, None, "returned"),
        ("advance", "Salary advance", "Advance against November salary.",
         20000, None, None, None, "draft"),
        ("loan", "Emergency loan request", "Medical emergency in the family.",
         60000, None, None, None, "submitted"),
    ]
    for rtype, title, desc, amt, needed, start, end, status in samples:
        r = Request.objects.create(
            company=co, requester=admin, request_type=rtype, title=title,
            description=desc, amount=amt, needed_by=needed,
            start_date=start, end_date=end, priority="normal", status="draft")
        rq_hooks.log_event(co, r, admin, "created", "Request created as draft.")
        if status != "draft":
            r.status = "submitted"
            r.save(update_fields=["status"])
            rq_hooks.on_submitted(co, r, admin)
        if status == "approved":
            r.status = "approved"
            r.review_notes = "Approved — within budget."
            r.save(update_fields=["status", "review_notes"])
            rq_hooks.on_decided(co, r, approver, "approved")
        elif status == "returned":
            r.status = "returned"
            r.review_notes = "Please attach a supplier quotation."
            r.save(update_fields=["status", "review_notes"])
            rq_hooks.on_returned(co, r, approver)


def seed_communication(co, admin):
    """Department channels, a management group, and sample messages."""
    from communication.models import Channel, ChannelMember, ChatMessage
    from shared.models import Department
    if Channel.objects.filter(company=co).exists():
        return
    depts = list(Department.objects.filter(company=co)[:6])
    if not depts:
        for name, code in [("Operations", "OPS"), ("Administration", "ADM")]:
            depts.append(Department.objects.create(
                company=co, name=name, code=code,
                description=f"{name} department"))
    for dept in depts:
        ch, _ = Channel.objects.get_or_create(
            company=co, channel_type="department", department=dept,
            defaults={"name": f"{dept.name} — Team", "created_by": admin,
                      "description": f"Team discussions for {dept.name}."})
        ChannelMember.objects.get_or_create(channel=ch, user=admin,
                                            defaults={"is_admin": True})
    first = Channel.objects.filter(company=co, channel_type="department").first()
    if first:
        ChatMessage.objects.create(
            company=co, channel=first, sender=admin,
            body="Welcome to the team channel. Please use this space for "
                 "department updates and coordination.")
    mgmt = Channel.objects.create(
        company=co, name="Management", channel_type="group",
        description="Cross-department management coordination.",
        created_by=admin)
    ChannelMember.objects.create(channel=mgmt, user=admin, is_admin=True)
    ChatMessage.objects.create(
        company=co, channel=mgmt, sender=admin,
        body="Weekly priorities: clear pending approvals and review the budget.")


def seed_executive(co):
    from executive import models as e
    if e.ReportDefinition.objects.filter(company=co).exists():
        return
    e.ReportDefinition.objects.create(
        company=co, name="Open Bills (AP Aging Watch)",
        description="All unpaid bills with vendor and due date.",
        dataset="finance.bills",
        columns=["bill_no", "vendor_name", "bill_date", "due_date", "amount", "status"],
        status_filter="unpaid")
    e.ReportDefinition.objects.create(
        company=co, name="Active Employees",
        description="Current workforce roster.",
        dataset="hr.employees",
        columns=["employee_id", "name", "department__name", "position", "status"],
        status_filter="active")
    e.ReportDefinition.objects.create(
        company=co, name="Receivables Outstanding",
        description="Unpaid customer invoices.",
        dataset="finance.ar",
        columns=["invoice_no", "customer_name", "invoice_date", "amount", "status"],
        status_filter="unpaid")


class Command(BaseCommand):
    help = "Seed enterprise module demo data (self-healing)"

    @transaction.atomic
    def handle(self, *args, **options):
        admin = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not admin:
            self.stdout.write(self.style.WARNING("no users yet; skipping"))
            return
        n = 0
        for co in Company.objects.filter(is_active=True):
            seed_hr(co)
            seed_finance(co)
            seed_admin(co)
            seed_comms(co, admin)
            seed_executive(co)
            seed_requests(co, admin)
            seed_communication(co, admin)
            backfill_finance_ledger(co)
            n += 1
        self.stdout.write(self.style.SUCCESS(f"enterprise seed ok ({n} companies)"))
