"""Import Management: suppliers, requests, POs, shipments, customs, warehouse."""
from django.db import models

from core.models import CompanyOwned


class Supplier(CompanyOwned):
    name = models.CharField(max_length=150)
    country = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=80, blank=True)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    payment_terms = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=[("active", "Active"), ("inactive", "Inactive")], default="active")

    def __str__(self):
        return self.name


class SupplierContact(CompanyOwned):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)

    def __str__(self):
        return f"{self.name} ({self.supplier.name})"


class ImportRequest(CompanyOwned):
    STATUS = [("draft", "Draft"), ("submitted", "Submitted"),
              ("approved", "Approved"), ("rejected", "Rejected")]
    request_no = models.CharField(max_length=40)
    product_description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estimated_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    requested_by = models.CharField(max_length=120, blank=True)
    request_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS, default="draft")

    def __str__(self):
        return self.request_no


class PurchaseOrder(CompanyOwned):
    STATUS = [("draft", "Draft"), ("sent", "Sent"), ("confirmed", "Confirmed"),
              ("partial", "Partially Received"), ("received", "Received"), ("cancelled", "Cancelled")]
    po_no = models.CharField(max_length=40)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    order_date = models.DateField()
    delivery_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=20, choices=STATUS, default="draft")

    def __str__(self):
        return self.po_no


class ProformaInvoice(CompanyOwned):
    pi_no = models.CharField(max_length=40)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="proforma_invoices")
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name="proforma_invoices")
    issue_date = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[("valid", "Valid"), ("expired", "Expired"), ("accepted", "Accepted")], default="valid")

    def __str__(self):
        return self.pi_no


class ImportProduct(CompanyOwned):
    CATEGORY = [("cars", "Cars"), ("machinery", "Machinery"), ("metals", "Metals"),
                ("raw_materials", "Raw Materials"), ("other", "Other")]
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=CATEGORY, default="other")
    unit = models.CharField(max_length=20, default="pcs")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return self.name


class Shipment(CompanyOwned):
    STATUS = [("planned", "Planned"), ("in_transit", "In Transit"), ("at_port", "At Port"),
              ("clearing", "Clearing Customs"), ("delivered", "Delivered")]
    shipment_no = models.CharField(max_length=40)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name="shipments")
    origin = models.CharField(max_length=120, blank=True)
    destination = models.CharField(max_length=120, blank=True)
    mode = models.CharField(max_length=20, choices=[("sea", "Sea"), ("air", "Air"), ("land", "Land")], default="sea")
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
    status = models.CharField(max_length=20, choices=[("loaded", "Loaded"), ("in_transit", "In Transit"), ("released", "Released")], default="loaded")

    def __str__(self):
        return self.container_no


class ImportDocument(CompanyOwned):
    DOC_TYPE = [("commercial", "Commercial"), ("shipping", "Shipping"), ("compliance", "Compliance")]
    doc_no = models.CharField(max_length=40)
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE, default="commercial")
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("received", "Received"), ("verified", "Verified")], default="pending")

    def __str__(self):
        return f"{self.doc_no} — {self.title}"


class CustomsDeclaration(CompanyOwned):
    declaration_no = models.CharField(max_length=40)
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="declarations")
    declaration_date = models.DateField()
    duty_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[("draft", "Draft"), ("submitted", "Submitted"), ("cleared", "Cleared")], default="draft")

    def __str__(self):
        return self.declaration_no


class GoodsReceipt(CompanyOwned):
    grv_no = models.CharField(max_length=40)
    shipment = models.ForeignKey(Shipment, on_delete=models.SET_NULL, null=True, blank=True, related_name="receipts")
    receipt_date = models.DateField()
    received_by = models.CharField(max_length=120, blank=True)
    inspection_status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("passed", "Passed"), ("failed", "Failed")], default="pending")
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.grv_no


class WarehouseStock(CompanyOwned):
    product = models.ForeignKey(ImportProduct, on_delete=models.CASCADE, related_name="stock")
    warehouse = models.CharField(max_length=120, default="Main Warehouse")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default="pcs")

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse}"


class SupplierInvoice(CompanyOwned):
    STATUS = [("unpaid", "Unpaid"), ("partial", "Partially Paid"), ("paid", "Paid")]
    invoice_no = models.CharField(max_length=40)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="invoices")
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name="invoices")
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="unpaid")

    def __str__(self):
        return self.invoice_no


class SupplierPayment(CompanyOwned):
    payment_no = models.CharField(max_length=40)
    invoice = models.ForeignKey(SupplierInvoice, on_delete=models.CASCADE, related_name="payments")
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    method = models.CharField(max_length=40, blank=True)
    reference = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return self.payment_no
