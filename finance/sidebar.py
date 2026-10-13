"""Finance & Accounting sidebar."""
from django.urls import reverse

from core.modules import _page


def _ent(company, label, icon, entity):
    return _page(label, icon, "finance_entity_list", company, {"entity": entity}, entity=entity)


def get_section(company, counts=None):
    _b = lambda k: (counts or {}).get(k) or None
    dash = {"type": "link", "label": "Finance Dashboard", "icon": "dashboard",
            "url": reverse("finance_dashboard", kwargs={"company_slug": company.slug}),
            "url_name": "finance_dashboard"}
    return [
        {"type": "section", "label": "FINANCE & ACCOUNTING"},
        dash,
        {"type": "group", "name": "Accounting", "icon": "book", "pages": [
            _ent(company, "Chart of Accounts", "file", "gl-accounts"),
            _ent(company, "Journal Entries", "pencil", "journal"),
            _ent(company, "Journal Lines", "file", "journal-lines"),
            _ent(company, "Financial Periods", "calendar", "periods"),
            _ent(company, "Cost Centers", "layers", "cost-centers"),
        ]},
        {"type": "group", "name": "Payables", "icon": "receipt",
         "badge": _b("bills"), "pages": [
            _ent(company, "Bills (AP)", "receipt", "bills"),
        ]},
        {"type": "group", "name": "Receivables", "icon": "bank",
         "badge": _b("receivables"), "pages": [
            _ent(company, "AR Invoices", "receipt", "ar-invoices"),
            _ent(company, "AR Receipts", "bank", "ar-receipts"),
        ]},
        {"type": "group", "name": "Cash & Bank", "icon": "bank", "pages": [
            _ent(company, "Bank Accounts", "bank", "bank-accounts"),
            _ent(company, "Bank Transactions", "file", "bank-transactions"),
            _ent(company, "Reconciliations", "shield", "reconciliations"),
        ]},
        {"type": "group", "name": "Budgets & Expenses", "icon": "chart", "pages": [
            _ent(company, "Budgets", "chart", "budgets"),
            _ent(company, "Budget Lines", "file", "budget-lines"),
            _ent(company, "Expense Claims", "wallet", "expense-claims"),
        ]},
        {"type": "group", "name": "Tax", "icon": "receipt", "pages": [
            _ent(company, "Tax Rates", "receipt", "tax-rates"),
            _ent(company, "Tax Returns", "file", "tax-returns"),
        ]},
        {"type": "group", "name": "Assets & Projects", "icon": "box", "pages": [
            _ent(company, "Fixed Assets", "box", "assets"),
            _ent(company, "Projects", "briefcase", "projects"),
        ]},
        {"type": "link", "label": "Financial Statements", "icon": "file",
         "url": reverse("finance_statements", kwargs={"company_slug": company.slug}),
         "url_name": "finance_statements"},
    ]
