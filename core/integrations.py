"""Sector <-> Finance integration.

Sector apps keep their operational documents (purchase orders, invoices,
rent receipts ...). This module mirrors the financial effect into the
centralized finance ledgers (AP/AR + double-entry journals) and is
idempotent: re-saving a sector document updates the linked finance record
instead of duplicating it.
"""
from datetime import date


def get_account(company, code, name, account_type):
    from shared.models import GLAccount
    acct, _ = GLAccount.objects.get_or_create(
        company=company, code=code,
        defaults={"name": name, "account_type": account_type, "is_active": True},
    )
    return acct


def post_journal(company, on_date, reference, lines, description="", user=None):
    """lines: [(account_code, account_name, debit, credit), ...]. Balanced."""
    from shared.models import JournalEntry
    from finance.models import JournalLine
    if abs(sum(d for _, _, d, _ in lines) - sum(c for _, _, _, c in lines)) > 0.01:
        raise ValueError("Journal is not balanced")
    entry, created = JournalEntry.objects.get_or_create(
        company=company, reference=reference,
        defaults={"date": on_date or date.today(), "description": description[:255],
                  "account": get_account(company, lines[0][0], lines[0][1], "expense"),
                  "debit": lines[0][2], "credit": lines[0][3]},
    )
    if created:
        for code, name, debit, credit in lines:
            acct_type = ("revenue" if code.startswith("4") else
                         "liability" if code.startswith("2") else
                         "asset" if code.startswith("1") else "expense")
            JournalLine.objects.create(
                company=company, entry=entry,
                account=get_account(company, code, name, acct_type),
                debit=debit, credit=credit, description=description[:255])
    return entry


# ------------------------------------------------------------ sector sync
def _src(app, entity, pk):
    return f"{app}:{entity}:{pk}"


def sync_supplier_invoice_to_bill(company, inv, created, request):
    """imports.SupplierInvoice -> finance Bill (AP) + journal."""
    from shared.models import Bill
    source = _src("imports", "supplier-invoices", inv.pk)
    bill, _ = Bill.objects.update_or_create(
        company=company, bill_no=inv.invoice_no, vendor_name=str(inv.supplier),
        defaults={"bill_date": inv.invoice_date, "due_date": inv.due_date,
                  "amount": inv.amount, "paid_amount": inv.paid_amount,
                  "status": "paid" if inv.status == "paid" else
                            ("partial" if inv.status == "partial" else "unpaid"),
                  "notes": f"Auto-created from import supplier invoice {inv.invoice_no} [{source}]"},
    )
    post_journal(company, inv.invoice_date, f"AP-{inv.invoice_no}", [
        ("5100", "Purchases", float(inv.amount), 0),
        ("2100", "Accounts Payable", 0, float(inv.amount)),
    ], description=f"Supplier invoice {inv.invoice_no}", user=getattr(request, "user", None))
    return bill


def sync_export_invoice_to_ar(company, inv, created, request):
    from finance.models import ARInvoice
    ar, _ = ARInvoice.objects.update_or_create(
        company=company, source=_src("exports", "invoices", inv.pk),
        defaults={"customer_name": str(inv.buyer), "invoice_no": inv.invoice_no,
                  "invoice_date": inv.invoice_date, "due_date": inv.due_date,
                  "amount": inv.amount, "paid_amount": inv.paid_amount,
                  "status": inv.status if inv.status in ("unpaid", "partial", "paid") else "unpaid"},
    )
    post_journal(company, inv.invoice_date, f"AR-{inv.invoice_no}", [
        ("1100", "Accounts Receivable", float(inv.amount), 0),
        ("4000", "Sales Revenue", 0, float(inv.amount)),
    ], description=f"Export invoice {inv.invoice_no}", user=getattr(request, "user", None))
    return ar


def sync_coffee_invoice_to_ar(company, inv, created, request):
    """Post a Bean Power Coffee export invoice into Finance (AR + journal)."""
    from finance.models import ARInvoice
    ar, _ = ARInvoice.objects.update_or_create(
        company=company, source=_src("coffee", "export-invoices", inv.pk),
        defaults={"customer_name": str(inv.order.buyer), "invoice_no": inv.invoice_no,
                  "invoice_date": inv.invoice_date, "due_date": inv.due_date,
                  "amount": inv.amount, "paid_amount": inv.paid_amount,
                  "status": inv.status if inv.status in ("unpaid", "partial", "paid") else "unpaid"},
    )
    post_journal(company, inv.invoice_date, f"AR-{inv.invoice_no}", [
        ("1100", "Accounts Receivable", float(inv.amount), 0),
        ("4000", "Coffee Sales Revenue", 0, float(inv.amount)),
    ], description=f"Coffee export invoice {inv.invoice_no}", user=getattr(request, "user", None))
    return ar


def sync_rent_invoice_to_ar(company, inv, created, request):
    from finance.models import ARInvoice
    tenant = inv.lease.tenant.name if inv.lease and inv.lease.tenant else ""
    ar, _ = ARInvoice.objects.update_or_create(
        company=company, source=_src("rentals", "rent-invoices", inv.pk),
        defaults={"customer_name": tenant, "invoice_no": inv.invoice_no,
                  "invoice_date": inv.issue_date, "due_date": inv.due_date,
                  "amount": inv.amount, "paid_amount": inv.paid_amount,
                  "status": inv.status if inv.status in ("unpaid", "partial", "paid") else "unpaid"},
    )
    post_journal(company, inv.issue_date, f"AR-{inv.invoice_no}", [
        ("1100", "Accounts Receivable", float(inv.amount), 0),
        ("4100", "Rental Income", 0, float(inv.amount)),
    ], description=f"Rent invoice {inv.invoice_no}", user=getattr(request, "user", None))
    return ar


def sync_fleet_invoice_to_ar(company, inv, created, request):
    from finance.models import ARInvoice
    ar, _ = ARInvoice.objects.update_or_create(
        company=company, source=_src("fleet", "invoices", inv.pk),
        defaults={"customer_name": inv.customer_name, "invoice_no": inv.invoice_no,
                  "invoice_date": inv.issued_date, "due_date": inv.due_date,
                  "amount": inv.total, "paid_amount": 0,
                  "status": "unpaid" if inv.status != "paid" else "paid"},
    )
    post_journal(company, inv.issued_date, f"AR-{inv.invoice_no}", [
        ("1100", "Accounts Receivable", float(inv.total), 0),
        ("4200", "Transport Revenue", 0, float(inv.total)),
    ], description=f"Transport invoice {inv.invoice_no}", user=getattr(request, "user", None))
    return ar
