"""Finance & Accounting: AR, cash & bank, budgets, expenses, tax, periods,
cost centers, projects, journal lines.

Works alongside shared.GLAccount / shared.JournalEntry / shared.Bill /
shared.CompanyAsset (the centralized finance data layer)."""
from django.db import models

from core.models import CompanyOwned


# ------------------------------------------------------------ double-entry lines
class JournalLine(CompanyOwned):
    entry = models.ForeignKey("shared.JournalEntry", on_delete=models.CASCADE,
                              related_name="lines")
    account = models.ForeignKey("shared.GLAccount", on_delete=models.PROTECT,
                                related_name="journal_lines")
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.entry} — {self.account.code}"


# ------------------------------------------------------------ accounts receivable
class ARInvoice(CompanyOwned):
    STATUS_CHOICES = [("draft", "Draft"), ("unpaid", "Unpaid"),
                      ("partial", "Partially Paid"), ("paid", "Paid"),
                      ("overdue", "Overdue")]
    customer_name = models.CharField(max_length=150)
    invoice_no = models.CharField(max_length=40)
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unpaid")
    source = models.CharField(max_length=120, blank=True,
                              help_text="Origin, e.g. exports:invoices:12")
    notes = models.TextField(blank=True)

    @property
    def balance(self):
        return (self.amount or 0) - (self.paid_amount or 0)

    def __str__(self):
        return f"{self.invoice_no} — {self.customer_name}"


class ARReceipt(CompanyOwned):
    invoice = models.ForeignKey(ARInvoice, on_delete=models.CASCADE, related_name="receipts")
    receipt_no = models.CharField(max_length=40)
    receipt_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=40, blank=True)
    bank_account = models.ForeignKey("BankAccount", on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name="receipts")
    reference = models.CharField(max_length=80, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        inv = self.invoice
        total = sum(float(r.amount) for r in inv.receipts.all())
        inv.paid_amount = total
        inv.status = "paid" if total >= float(inv.amount) else ("partial" if total > 0 else inv.status)
        inv.save(update_fields=["paid_amount", "status"])

    def __str__(self):
        return f"{self.receipt_no} — {self.amount:,.0f}"


# ------------------------------------------------------------ cash & bank
class BankAccount(CompanyOwned):
    name = models.CharField(max_length=120)
    bank_name = models.CharField(max_length=120, blank=True)
    account_no = models.CharField(max_length=60, blank=True)
    currency = models.CharField(max_length=10, default="ETB")
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    @property
    def balance(self):
        tx = sum(float(t.amount) for t in self.transactions.all())
        return float(self.opening_balance) + tx

    def __str__(self):
        return self.name


class BankTransaction(CompanyOwned):
    TYPE_CHOICES = [("deposit", "Deposit"), ("withdrawal", "Withdrawal"),
                    ("transfer", "Transfer")]
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE,
                                related_name="transactions")
    date = models.DateField()
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2,
                                 help_text="Signed: +deposit, −withdrawal")
    description = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.account.name} {self.date}: {self.amount:,.0f}"


class BankReconciliation(CompanyOwned):
    STATUS_CHOICES = [("draft", "Draft"), ("completed", "Completed")]
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE,
                                related_name="reconciliations")
    period_end = models.DateField()
    book_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bank_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    difference = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.difference = (self.book_balance or 0) - (self.bank_balance or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.account.name} — {self.period_end:%b %Y}"


# ------------------------------------------------------------ budgeting
class Budget(CompanyOwned):
    STATUS_CHOICES = [("draft", "Draft"), ("approved", "Approved"), ("closed", "Closed")]
    name = models.CharField(max_length=150)
    fiscal_year = models.CharField(max_length=9, help_text="e.g. 2026/27")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.fiscal_year})"


class BudgetLine(CompanyOwned):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey("shared.GLAccount", on_delete=models.PROTECT,
                                related_name="budget_lines")
    cost_center = models.ForeignKey("CostCenter", on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="budget_lines")
    budgeted = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    @property
    def actual(self):
        from django.db.models import Sum
        agg = self.account.journal_lines.filter(
            entry__company=self.company).aggregate(
            d=Sum("debit"), c=Sum("credit"))
        if self.account.account_type in ("revenue", "equity", "liability"):
            return float(agg["c"] or 0) - float(agg["d"] or 0)
        return float(agg["d"] or 0) - float(agg["c"] or 0)

    @property
    def variance(self):
        return float(self.budgeted) - self.actual

    def __str__(self):
        return f"{self.budget.name}: {self.account.code}"


# ------------------------------------------------------------ expenses
class ExpenseClaim(CompanyOwned):
    STATUS_CHOICES = [("draft", "Draft"), ("submitted", "Submitted"),
                      ("approved", "Approved"), ("rejected", "Rejected"), ("paid", "Paid")]
    employee = models.ForeignKey("shared.Employee", on_delete=models.CASCADE,
                                 related_name="expense_claims")
    claim_no = models.CharField(max_length=40)
    claim_date = models.DateField()
    category = models.CharField(max_length=80, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    description = models.TextField(blank=True)
    receipt = models.FileField(upload_to="finance/expenses/%Y/%m/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    def __str__(self):
        return f"{self.claim_no} — {self.employee.name}"


# ------------------------------------------------------------ tax
class TaxRate(CompanyOwned):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, blank=True)
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percent")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class TaxReturn(CompanyOwned):
    STATUS_CHOICES = [("draft", "Draft"), ("filed", "Filed"), ("paid", "Paid")]
    tax = models.ForeignKey(TaxRate, on_delete=models.PROTECT, related_name="returns")
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    taxable_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_due = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    filed_date = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.tax_due = float(self.taxable_amount or 0) * float(self.tax.rate or 0) / 100
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tax.name} — {self.period_end:%b %Y}" if self.period_end else self.tax.name


# ------------------------------------------------------------ periods & cost centers
class FinancialPeriod(CompanyOwned):
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed")]
    name = models.CharField(max_length=60)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name


class CostCenter(CompanyOwned):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} — {self.name}"


class Project(CompanyOwned):
    STATUS_CHOICES = [("planning", "Planning"), ("active", "Active"),
                      ("on_hold", "On Hold"), ("completed", "Completed")]
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, blank=True)
    client = models.CharField(max_length=150, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planning")
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
