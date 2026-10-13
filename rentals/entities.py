"""Entity registry for Building & Property Rental."""
from . import models as m

E = lambda **kw: kw  # noqa: E731

ENTITIES = {
    "properties": E(
        title="Properties", singular="Property", icon="building",
        model=m.Property,
        list_display=[("Name", "name"), ("Type", "property_type"), ("City", "city"), ("Manager", "manager")],
        search=["name", "city"],
        form_fields=["name", "property_type", "city", "address", "manager"],
        detail_related=[
            ("Buildings", "buildings", [("Name", "name"), ("Floors", "floors")]),
            ("Expenses", "expenses", [("Category", "category"), ("Amount", "amount")]),
        ],
    ),
    "buildings": E(
        title="Buildings", singular="Building", icon="building",
        model=m.Building,
        list_display=[("Name", "name"), ("Property", "property__name"), ("Floors", "floors")],
        search=["name", "property__name"],
        form_fields=["property", "name", "floors", "address"],
        detail_related=[
            ("Units", "units", [("Unit No", "unit_no"), ("Rent", "monthly_rent"), ("Status", "status")]),
        ],
    ),
    "units": E(
        title="Units", singular="Unit", icon="home",
        model=m.Unit,
        list_display=[("Unit No", "unit_no"), ("Building", "building__name"), ("Floor", "floor"),
                      ("Beds", "bedrooms"), ("Rent", "monthly_rent"), ("Status", "status")],
        search=["unit_no", "building__name"],
        form_fields=["unit_no", "building", "floor", "bedrooms", "bathrooms", "area_sqm", "monthly_rent", "status"],
        detail_related=[
            ("Leases", "leases", [("Lease No", "lease_no"), ("Tenant", "tenant__name")]),
            ("Maintenance", "maintenance_requests", [("Request No", "request_no"), ("Status", "status")]),
        ],
    ),
    "tenants": E(
        title="Tenants", singular="Tenant", icon="users",
        model=m.Tenant,
        list_display=[("Name", "name"), ("Phone", "phone"), ("Email", "email"), ("Status", "status")],
        search=["name", "phone", "email"],
        form_fields=["name", "phone", "email", "id_number", "status"],
        detail_related=[
            ("Leases", "leases", [("Lease No", "lease_no"), ("Unit", "unit__unit_no")]),
        ],
    ),
    "leases": E(
        title="Lease Management", singular="Lease", icon="clipboard",
        model=m.Lease,
        list_display=[("Lease No", "lease_no"), ("Unit", "unit__unit_no"), ("Tenant", "tenant__name"),
                      ("Start", "start_date"), ("End", "end_date"), ("Rent", "monthly_rent"), ("Status", "status")],
        search=["lease_no", "tenant__name"],
        form_fields=["lease_no", "unit", "tenant", "start_date", "end_date", "monthly_rent", "deposit", "status"],
        detail_related=[
            ("Rent Schedule", "schedule", [("Due", "due_date"), ("Amount", "amount")]),
            ("Invoices", "invoices", [("Invoice No", "invoice_no"), ("Status", "status")]),
            ("Deposits", "deposits", [("Amount", "amount"), ("Status", "status")]),
        ],
    ),
    "rent-schedule": E(
        title="Rent Schedule", singular="Schedule Line", icon="calendar",
        model=m.RentSchedule,
        list_display=[("Lease", "lease__lease_no"), ("Due Date", "due_date"), ("Amount", "amount"), ("Status", "status")],
        search=["lease__lease_no"],
        form_fields=["lease", "due_date", "amount", "status"],
    ),
    "rent-invoices": E(
        title="Rent Invoices", singular="Invoice", icon="receipt", finance=True,
        model=m.RentInvoice,
        list_display=[("Invoice No", "invoice_no"), ("Lease", "lease__lease_no"),
                      ("Due", "due_date"), ("Amount", "amount"), ("Paid", "paid_amount"), ("Status", "status")],
        search=["invoice_no", "lease__lease_no"],
        form_fields=["invoice_no", "lease", "issue_date", "due_date", "amount", "paid_amount", "status"],
        detail_related=[
            ("Payments", "payments", [("Payment No", "payment_no"), ("Date", "payment_date"), ("Amount", "amount")]),
        ],
    ),
    "rent-payments": E(
        title="Rent Payments", singular="Payment", icon="bank", finance=True,
        model=m.RentPayment,
        list_display=[("Payment No", "payment_no"), ("Invoice", "invoice__invoice_no"),
                      ("Date", "payment_date"), ("Amount", "amount"), ("Method", "method")],
        search=["payment_no", "reference"],
        form_fields=["payment_no", "invoice", "payment_date", "amount", "method", "reference"],
    ),
    "deposits": E(
        title="Deposit Management", singular="Deposit", icon="wallet",
        model=m.Deposit,
        list_display=[("Lease", "lease__lease_no"), ("Amount", "amount"),
                      ("Status", "status"), ("Refund Date", "refund_date")],
        search=["lease__lease_no"],
        form_fields=["lease", "amount", "status", "refund_date"],
    ),
    "maintenance-requests": E(
        title="Maintenance Requests", singular="Request", icon="wrench",
        model=m.MaintenanceRequest,
        list_display=[("Request No", "request_no"), ("Unit", "unit__unit_no"),
                      ("Priority", "priority"), ("Date", "request_date"), ("Status", "status")],
        search=["request_no", "description"],
        form_fields=["request_no", "unit", "tenant", "request_date", "category", "description", "priority", "status"],
        detail_related=[
            ("Work Orders", "work_orders", [("WO No", "wo_no"), ("Assigned", "assigned_to")]),
        ],
    ),
    "work-orders": E(
        title="Work Orders", singular="Work Order", icon="gear",
        model=m.MaintenanceWorkOrder,
        list_display=[("WO No", "wo_no"), ("Request", "request__request_no"),
                      ("Assigned To", "assigned_to"), ("Cost", "cost"), ("Status", "status")],
        search=["wo_no", "assigned_to"],
        form_fields=["wo_no", "request", "assigned_to", "scheduled_date", "cost", "status"],
    ),
    "utilities": E(
        title="Utilities & Charges", singular="Utility Bill", icon="file",
        model=m.UtilityBill,
        list_display=[("Unit", "unit__unit_no"), ("Type", "utility_type"),
                      ("Month", "billing_month"), ("Amount", "amount"), ("Status", "status")],
        search=["unit__unit_no"],
        form_fields=["unit", "utility_type", "billing_month", "amount", "status"],
    ),
    "property-expenses": E(
        title="Property Expenses", singular="Expense", icon="wallet",
        model=m.PropertyExpense,
        list_display=[("Property", "property__name"), ("Category", "category"),
                      ("Date", "expense_date"), ("Amount", "amount")],
        search=["category", "description"],
        form_fields=["property", "category", "description", "expense_date", "amount"],
    ),
}
