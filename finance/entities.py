"""Finance & Accounting entity registry: the centralized financial system."""
from shared import models as sm

from . import models as m

E = lambda **kw: kw  # noqa: E731

FIN_ROLES = ["owner", "admin", "accountant"]

ENTITIES = {
    # ---- Core accounting
    "gl-accounts": E(
        title="Chart of Accounts", singular="GL Account", icon="file", finance=True,
        model=sm.GLAccount,
        list_display=[("Code", "code"), ("Name", "name"), ("Type", "account_type"),
                      ("Opening Balance", "opening_balance"), ("Active", "is_active")],
        search=["code", "name"],
        form_fields=["code", "name", "account_type", "opening_balance", "is_active"],
        detail_related=[
            ("Journal Entries", "journal_entries", [("Date", "date"), ("Debit", "debit"), ("Credit", "credit")]),
        ],
    ),
    "journal": E(
        title="Journal Entries", singular="Journal Entry", icon="pencil", finance=True,
        model=sm.JournalEntry,
        list_display=[("Date", "date"), ("Reference", "reference"), ("Account", "account__name"),
                      ("Debit", "debit"), ("Credit", "credit")],
        search=["reference", "description", "account__name"],
        form_fields=["date", "reference", "account", "debit", "credit", "description"],
        detail_related=[
            ("Lines", "lines", [("Account", "account__code"), ("Debit", "debit"), ("Credit", "credit")]),
        ],
    ),
    "journal-lines": E(
        title="Journal Lines", singular="Journal Line", icon="file", finance=True,
        model=m.JournalLine,
        list_display=[("Entry", "entry__reference"), ("Account", "account__code"),
                      ("Debit", "debit"), ("Credit", "credit")],
        search=["entry__reference", "description"],
        form_fields=["entry", "account", "debit", "credit", "description"],
    ),
    "periods": E(
        title="Financial Periods", singular="Financial Period", icon="calendar", finance=True,
        model=m.FinancialPeriod,
        list_display=[("Name", "name"), ("Start", "start_date"), ("End", "end_date"), ("Status", "status")],
        search=["name"],
        form_fields=["name", "start_date", "end_date", "status"],
        workflow={
            "status_field": "status",
            "transitions": [
                {"name": "close", "label": "Close Period", "from": ["open"],
                 "to": "closed", "roles": FIN_ROLES},
                {"name": "reopen", "label": "Reopen", "from": ["closed"],
                 "to": "open", "roles": FIN_ROLES},
            ],
        },
    ),
    "cost-centers": E(
        title="Cost Centers", singular="Cost Center", icon="layers", finance=True,
        model=m.CostCenter,
        list_display=[("Code", "code"), ("Name", "name"), ("Active", "is_active")],
        search=["code", "name"],
        form_fields=["code", "name", "description", "is_active"],
    ),
    # ---- Payables & receivables
    "bills": E(
        title="Bills (AP)", singular="Bill", icon="receipt", finance=True,
        model=sm.Bill,
        list_display=[("Bill No", "bill_no"), ("Vendor", "vendor_name"), ("Date", "bill_date"),
                      ("Due", "due_date"), ("Amount", "amount"), ("Paid", "paid_amount"), ("Status", "status")],
        search=["bill_no", "vendor_name"],
        form_fields=["vendor_name", "bill_no", "bill_date", "due_date", "amount", "paid_amount", "status", "notes"],
    ),
    "ar-invoices": E(
        title="AR Invoices", singular="AR Invoice", icon="receipt", finance=True,
        model=m.ARInvoice,
        list_display=[("Invoice No", "invoice_no"), ("Customer", "customer_name"),
                      ("Date", "invoice_date"), ("Amount", "amount"),
                      ("Paid", "paid_amount"), ("Status", "status")],
        search=["invoice_no", "customer_name"],
        form_fields=["customer_name", "invoice_no", "invoice_date", "due_date",
                     "amount", "paid_amount", "status", "notes"],
        detail_related=[
            ("Receipts", "receipts", [("Receipt No", "receipt_no"), ("Date", "receipt_date"), ("Amount", "amount")]),
        ],
        post_save="finance.hooks.on_ar_invoice_saved",
    ),
    "ar-receipts": E(
        title="AR Receipts", singular="AR Receipt", icon="bank", finance=True,
        model=m.ARReceipt,
        list_display=[("Receipt No", "receipt_no"), ("Invoice", "invoice__invoice_no"),
                      ("Date", "receipt_date"), ("Amount", "amount"), ("Method", "method")],
        search=["receipt_no", "reference"],
        form_fields=["invoice", "receipt_no", "receipt_date", "amount", "method", "bank_account", "reference"],
        post_save="finance.hooks.on_ar_receipt_saved",
    ),
    # ---- Cash & bank
    "bank-accounts": E(
        title="Bank Accounts", singular="Bank Account", icon="bank", finance=True,
        model=m.BankAccount,
        list_display=[("Name", "name"), ("Bank", "bank_name"), ("Account No", "account_no"),
                      ("Currency", "currency"), ("Active", "is_active")],
        search=["name", "account_no"],
        form_fields=["name", "bank_name", "account_no", "currency", "opening_balance", "is_active"],
    ),
    "bank-transactions": E(
        title="Bank Transactions", singular="Bank Transaction", icon="file", finance=True,
        model=m.BankTransaction,
        list_display=[("Account", "account__name"), ("Date", "date"), ("Type", "transaction_type"),
                      ("Amount", "amount"), ("Reference", "reference")],
        search=["description", "reference"],
        form_fields=["account", "date", "transaction_type", "amount", "description", "reference"],
    ),
    "reconciliations": E(
        title="Bank Reconciliations", singular="Reconciliation", icon="shield", finance=True,
        model=m.BankReconciliation,
        list_display=[("Account", "account__name"), ("Period End", "period_end"),
                      ("Book", "book_balance"), ("Bank", "bank_balance"),
                      ("Difference", "difference"), ("Status", "status")],
        search=["account__name"],
        form_fields=["account", "period_end", "book_balance", "bank_balance", "status", "notes"],
        workflow={
            "status_field": "status",
            "transitions": [
                {"name": "complete", "label": "Complete", "from": ["draft"],
                 "to": "completed", "roles": FIN_ROLES},
            ],
        },
    ),
    # ---- Budgets & expenses
    "budgets": E(
        title="Budgets", singular="Budget", icon="chart", finance=True,
        model=m.Budget,
        list_display=[("Name", "name"), ("Fiscal Year", "fiscal_year"), ("Status", "status")],
        search=["name"],
        form_fields=["name", "fiscal_year", "start_date", "end_date", "status", "notes"],
        detail_related=[
            ("Lines", "lines", [("Account", "account__code"), ("Budgeted", "budgeted")]),
        ],
        workflow={
            "status_field": "status",
            "transitions": [
                {"name": "approve", "label": "Approve", "from": ["draft"],
                 "to": "approved", "roles": FIN_ROLES},
                {"name": "close", "label": "Close", "from": ["approved"],
                 "to": "closed", "roles": FIN_ROLES},
            ],
        },
    ),
    "budget-lines": E(
        title="Budget Lines", singular="Budget Line", icon="file", finance=True,
        model=m.BudgetLine,
        list_display=[("Budget", "budget__name"), ("Account", "account__code"), ("Budgeted", "budgeted")],
        search=["budget__name"],
        form_fields=["budget", "account", "cost_center", "budgeted"],
    ),
    "expense-claims": E(
        title="Expense Claims", singular="Expense Claim", icon="wallet", finance=True,
        model=m.ExpenseClaim,
        list_display=[("Claim No", "claim_no"), ("Employee", "employee__name"),
                      ("Date", "claim_date"), ("Amount", "amount"), ("Status", "status")],
        search=["claim_no", "description"],
        form_fields=["employee", "claim_no", "claim_date", "category", "amount",
                     "description", "receipt", "status"],
        workflow={
            "status_field": "status",
            "transitions": [
                {"name": "submit", "label": "Submit", "from": ["draft"], "to": "submitted",
                 "roles": ["owner", "admin", "manager", "dispatcher", "accountant", "viewer"]},
                {"name": "approve", "label": "Approve", "from": ["submitted"],
                 "to": "approved", "roles": ["owner", "admin", "manager", "accountant"],
                 "post": "finance.hooks.on_expense_approved"},
                {"name": "reject", "label": "Reject", "from": ["submitted"],
                 "to": "rejected", "roles": ["owner", "admin", "manager", "accountant"]},
                {"name": "pay", "label": "Mark Paid", "from": ["approved"],
                 "to": "paid", "roles": FIN_ROLES},
            ],
        },
    ),
    # ---- Tax
    "tax-rates": E(
        title="Tax Rates", singular="Tax Rate", icon="receipt", finance=True,
        model=m.TaxRate,
        list_display=[("Name", "name"), ("Code", "code"), ("Rate %", "rate"), ("Active", "is_active")],
        search=["name", "code"],
        form_fields=["name", "code", "rate", "is_active"],
    ),
    "tax-returns": E(
        title="Tax Returns", singular="Tax Return", icon="file", finance=True,
        model=m.TaxReturn,
        list_display=[("Tax", "tax__name"), ("Period End", "period_end"),
                      ("Taxable", "taxable_amount"), ("Due", "tax_due"), ("Status", "status")],
        search=["tax__name"],
        form_fields=["tax", "period_start", "period_end", "taxable_amount", "status", "filed_date"],
        workflow={
            "status_field": "status",
            "transitions": [
                {"name": "file", "label": "File", "from": ["draft"], "to": "filed", "roles": FIN_ROLES},
                {"name": "pay", "label": "Mark Paid", "from": ["filed"], "to": "paid", "roles": FIN_ROLES},
            ],
        },
    ),
    # ---- Assets & projects
    "assets": E(
        title="Fixed Assets", singular="Asset", icon="box",
        model=sm.CompanyAsset,
        list_display=[("Name", "name"), ("Category", "category"), ("Purchase Date", "purchase_date"),
                      ("Cost", "cost"), ("Assigned To", "assigned_to"), ("Status", "status")],
        search=["name", "category", "assigned_to"],
        form_fields=["name", "category", "purchase_date", "cost", "assigned_to", "status"],
    ),
    "projects": E(
        title="Projects", singular="Project", icon="briefcase", finance=True,
        model=m.Project,
        list_display=[("Name", "name"), ("Code", "code"), ("Client", "client"),
                      ("Budget", "budget"), ("Status", "status")],
        search=["name", "code", "client"],
        form_fields=["name", "code", "client", "start_date", "end_date", "budget", "status", "description"],
    ),
}
