"""Finance post-hooks: journal postings triggered by CRUD + workflows."""
from datetime import date


def on_ar_invoice_saved(company, inv, created, request):
    """Manual AR invoice -> Dr AR / Cr Revenue (sector-synced ones already post)."""
    if not created or (inv.source or "").count(":") == 2:
        return
    from core.integrations import post_journal
    post_journal(company, inv.invoice_date, f"AR-{inv.invoice_no}", [
        ("1100", "Accounts Receivable", float(inv.amount), 0),
        ("4000", "Sales Revenue", 0, float(inv.amount)),
    ], description=f"AR invoice {inv.invoice_no}", user=getattr(request, "user", None))


def on_ar_receipt_saved(company, receipt, created, request):
    """Collection -> Dr Cash/Bank / Cr AR."""
    if not created:
        return
    from core.integrations import post_journal
    post_journal(company, receipt.receipt_date, f"RCPT-{receipt.receipt_no}", [
        ("1000", "Cash & Bank", float(receipt.amount), 0),
        ("1100", "Accounts Receivable", 0, float(receipt.amount)),
    ], description=f"Receipt {receipt.receipt_no} on {receipt.invoice.invoice_no}",
        user=getattr(request, "user", None))
    # mirror cash movement into the bank account ledger
    if receipt.bank_account:
        from finance.models import BankTransaction
        BankTransaction.objects.create(
            company=company, account=receipt.bank_account, date=receipt.receipt_date,
            transaction_type="deposit", amount=receipt.amount,
            description=f"Receipt {receipt.receipt_no}", reference=receipt.receipt_no)


def on_expense_approved(company, claim, request):
    """Approved expense claim -> Bill (AP) + journal Dr Expense / Cr AP."""
    from shared.models import Bill
    from core.integrations import post_journal
    bill, _ = Bill.objects.get_or_create(
        company=company, bill_no=claim.claim_no, vendor_name=claim.employee.name,
        defaults={"bill_date": claim.claim_date, "amount": claim.amount,
                  "status": "unpaid",
                  "notes": f"Auto-created from expense claim {claim.claim_no}"})
    post_journal(company, claim.claim_date, f"EXP-{claim.claim_no}", [
        ("5200", "Operating Expenses", float(claim.amount), 0),
        ("2100", "Accounts Payable", 0, float(claim.amount)),
    ], description=f"Expense claim {claim.claim_no}", user=getattr(request, "user", None))
