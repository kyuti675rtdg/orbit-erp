"""Export Management: buyers, orders, contracts, QC, shipments, documentation."""
from django.db import models

from core.models import CompanyOwned


class Buyer(CompanyOwned):
    name = models.CharField(max_length=150)
    country = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=80, blank=True)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=20, choices=[("active", "Active"), ("inactive", "Inactive")], default="active")

    def __str__(self):
        return self.name


class BuyerContact(CompanyOwned):
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)

    def __str__(self):
        return f"{self.name} ({self.buyer.name})"


class ExportQuotation(CompanyOwned):
    quote_no = models.CharField(max_length=40)
    buyer = models.ForeignKey(Buyer, on_delete=models.PROTECT, related_name="quotations")
    issue_date = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=20, choices=[("draft", "Draft"), ("sent", "Sent"), ("accepted", "Accepted"), ("expired", "Expired")], default="draft")

    def __str__(self):
        return self.quote_no


class ExportContract(CompanyOwned):
    contract_no = models.CharField(max_length=40)
    buyer = models.ForeignKey(Buyer, on_delete=models.PROTECT, related_name="contracts")
    sign_date = models.DateField()
    total_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=20, choices=[("draft", "Draft"), ("active", "Active"), ("completed", "Completed"), ("cancelled", "Cancelled")], default="draft")

    def __str__(self):
        return self.contract_no


class ExportOrder(CompanyOwned):
    STATUS = [("draft", "Draft"), ("confirmed", "Confirmed"), ("preparing", "Preparing"),
              ("shipped", "Shipped"), ("delivered", "Delivered"), ("cancelled", "Cancelled")]
    order_no = models.CharField(max_length=40)
    buyer = models.ForeignKey(Buyer, on_delete=models.PROTECT, related_name="orders")
    contract = models.ForeignKey(ExportContract, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="orders")
    order_date = models.DateField()
    delivery_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=20, choices=STATUS, default="draft")

    def __str__(self):
        return self.order_no


class ExportProduct(CompanyOwned):
    CATEGORY = [("coffee", "Coffee Beans"), ("sesame", "Sesame Seeds"), ("other", "Other Products")]
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=CATEGORY, default="coffee")
    unit = models.CharField(max_length=20, default="kg")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return self.name


class ExportDocument(CompanyOwned):
    DOC_TYPE = [("commercial", "Commercial"), ("shipping", "Shipping"), ("compliance", "Compliance")]
    doc_no = models.CharField(max_length=40)
    order = models.ForeignKey(ExportOrder, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE, default="commercial")
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("issued", "Issued"), ("verified", "Verified")], default="pending")

    def __str__(self):
        return f"{self.doc_no} — {self.title}"


class QualityInspection(CompanyOwned):
    inspection_no = models.CharField(max_length=40)
    order = models.ForeignKey(ExportOrder, on_delete=models.CASCADE, related_name="inspections")
    inspection_date = models.DateField()
    inspector = models.CharField(max_length=120, blank=True)
    result = models.CharField(max_length=20, choices=[("pass", "Pass"), ("fail", "Fail"), ("conditional", "Conditional")], default="pass")
    certificate_no = models.CharField(max_length=60, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.inspection_no


class Shipment(CompanyOwned):
    STATUS = [("planned", "Planned"), ("in_transit", "In Transit"), ("arrived", "Arrived"), ("delivered", "Delivered")]
    shipment_no = models.CharField(max_length=40)
    order = models.ForeignKey(ExportOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="shipments")
    destination_port = models.CharField(max_length=120, blank=True)
    vessel = models.CharField(max_length=120, blank=True)
    etd = models.DateField(null=True, blank=True)
    eta = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="planned")

    def __str__(self):
        return self.shipment_no


class Container(CompanyOwned):
    container_no = models.CharField(max_length=40)
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="containers")
    container_type = models.CharField(max_length=20, default="40ft")
    seal_no = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=20, choices=[("stuffed", "Stuffed"), ("in_transit", "In Transit"), ("delivered", "Delivered")], default="stuffed")

    def __str__(self):
        return self.container_no


class ExportDeclaration(CompanyOwned):
    declaration_no = models.CharField(max_length=40)
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="declarations")
    declaration_date = models.DateField()
    status = models.CharField(max_length=20, choices=[("draft", "Draft"), ("submitted", "Submitted"), ("cleared", "Cleared")], default="draft")

    def __str__(self):
        return self.declaration_no


class ExportInvoice(CompanyOwned):
    STATUS = [("unpaid", "Unpaid"), ("partial", "Partially Paid"), ("paid", "Paid")]
    invoice_no = models.CharField(max_length=40)
    buyer = models.ForeignKey(Buyer, on_delete=models.PROTECT, related_name="invoices")
    order = models.ForeignKey(ExportOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="unpaid")

    def __str__(self):
        return self.invoice_no


class PaymentReceipt(CompanyOwned):
    receipt_no = models.CharField(max_length=40)
    invoice = models.ForeignKey(ExportInvoice, on_delete=models.CASCADE, related_name="receipts")
    receipt_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    method = models.CharField(max_length=40, blank=True)
    reference = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return self.receipt_no


class ExportCost(CompanyOwned):
    order = models.ForeignKey(ExportOrder, on_delete=models.CASCADE, related_name="costs")
    cost_type = models.CharField(max_length=80)
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    date = models.DateField()

    def __str__(self):
        return f"{self.order.order_no} — {self.cost_type}"
