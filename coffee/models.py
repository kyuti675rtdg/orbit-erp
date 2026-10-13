"""Bean Power Coffee ERP: full coffee value-chain data model.

Traceability chain (mandatory):
Farmer -> Farm -> PlantGroup -> HarvestRecord -> Delivery -> IntakeBatch
  -> ProcessingBatch -> WarehouseLot -> ExportOrder -> Shipment -> Buyer

Plant-level data is recorded only when actually available; otherwise
farm/plot-level records are used (never fabricated).
"""
from django.db import models
from django.utils import timezone

from core.models import CompanyOwned


def _code(prefix, company_id, seq):
    return f"{prefix}-{timezone.now():%Y}-{seq:04d}"


class Cooperative(CompanyOwned):
    name = models.CharField(max_length=200)
    registration_no = models.CharField(max_length=60, blank=True)
    location = models.CharField(max_length=200, blank=True)
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    member_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Farmer(CompanyOwned):
    farmer_id = models.CharField(max_length=30, blank=True, unique=False,
                                 help_text="Auto-generated unique farmer ID")
    full_name = models.CharField(max_length=150)
    national_id = models.CharField(max_length=40, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    photo = models.ImageField(upload_to="coffee/farmers/%Y/%m/", blank=True, null=True)
    cooperative = models.ForeignKey(Cooperative, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="farmers")
    certifications = models.CharField(max_length=255, blank=True,
                                      help_text="e.g. Organic, FairTrade, Rainforest")
    status = models.CharField(max_length=15, choices=[
        ("active", "Active"), ("inactive", "Inactive")], default="active")

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.farmer_id or 'FRM'} — {self.full_name}"

    def save(self, *args, **kwargs):
        if not self.farmer_id and self.company_id:
            seq = Farmer.objects.filter(company_id=self.company_id).count() + 1
            self.farmer_id = _code("FRM", self.company_id, seq)
        super().save(*args, **kwargs)


class Supplier(CompanyOwned):
    name = models.CharField(max_length=200)
    supplier_type = models.CharField(max_length=20, choices=[
        ("farmer", "Farmer"), ("cooperative", "Cooperative"),
        ("trader", "Trader"), ("other", "Other")], default="trader")
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    contract_terms = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=[
        ("active", "Active"), ("inactive", "Inactive")], default="active")

    def __str__(self):
        return self.name


class FarmerContract(CompanyOwned):
    STATUS = [("draft", "Draft"), ("active", "Active"), ("completed", "Completed"),
              ("cancelled", "Cancelled")]
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="contracts")
    contract_no = models.CharField(max_length=40, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    coffee_type = models.CharField(max_length=60, blank=True)
    agreed_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    terms = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="draft")

    def __str__(self):
        return f"{self.contract_no or 'CTR'} — {self.farmer.full_name}"

    def save(self, *args, **kwargs):
        if not self.contract_no and self.company_id:
            seq = FarmerContract.objects.filter(company_id=self.company_id).count() + 1
            self.contract_no = _code("CTR", self.company_id, seq)
        super().save(*args, **kwargs)


class FarmerPayment(CompanyOwned):
    STATUS = [("pending", "Pending"), ("paid", "Paid"), ("partial", "Partial")]
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="payments")
    payment_no = models.CharField(max_length=40, blank=True)
    payment_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=20, choices=[
        ("delivery", "Delivery Payment"), ("advance", "Advance"),
        ("bonus", "Bonus"), ("other", "Other")], default="delivery")
    method = models.CharField(max_length=40, blank=True)
    reference = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="pending")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.payment_no or 'PAY'} — {self.farmer.full_name}"

    def save(self, *args, **kwargs):
        if not self.payment_no and self.company_id:
            seq = FarmerPayment.objects.filter(company_id=self.company_id).count() + 1
            self.payment_no = _code("FPAY", self.company_id, seq)
        super().save(*args, **kwargs)


# ------------------------------------------------------------ farms & plants
class Farm(CompanyOwned):
    farm_id = models.CharField(max_length=30, blank=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="farms")
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=200, blank=True)
    area_hectares = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gps_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    boundary_notes = models.TextField(blank=True)
    certification_status = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=15, choices=[
        ("active", "Active"), ("inactive", "Inactive")], default="active")

    def __str__(self):
        return f"{self.farm_id or 'FRM'} — {self.name}"

    def save(self, *args, **kwargs):
        if not self.farm_id and self.company_id:
            seq = Farm.objects.filter(company_id=self.company_id).count() + 1
            self.farm_id = _code("FARM", self.company_id, seq)
        super().save(*args, **kwargs)


class Plot(CompanyOwned):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="plots")
    name = models.CharField(max_length=100)
    area_hectares = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gps_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    soil_type = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.farm.name} / {self.name}"


class PlantGroup(CompanyOwned):
    """A uniquely identified plant or a mapped plant group.

    Individual plants get their own record when tracked; otherwise a group
    record represents a mapped set of plants (never fabricated detail).
    """
    group_id = models.CharField(max_length=30, blank=True)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="plant_groups")
    plot = models.ForeignKey(Plot, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="plant_groups")
    record_type = models.CharField(max_length=15, choices=[
        ("plant", "Individual Plant"), ("group", "Plant Group")], default="group")
    species = models.CharField(max_length=80, blank=True, help_text="e.g. Arabica")
    variety = models.CharField(max_length=80, blank=True, help_text="e.g. Heirloom, Kurume")
    plant_count = models.PositiveIntegerField(default=1)
    planting_date = models.DateField(null=True, blank=True)
    age_years = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    gps_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    qr_code = models.CharField(max_length=60, blank=True)
    health_status = models.CharField(max_length=20, choices=[
        ("healthy", "Healthy"), ("stressed", "Stressed"),
        ("diseased", "Diseased"), ("dead", "Dead")], default="healthy")

    def __str__(self):
        return f"{self.group_id or 'PLT'} ({self.get_record_type_display()})"

    def save(self, *args, **kwargs):
        if not self.group_id and self.company_id:
            seq = PlantGroup.objects.filter(company_id=self.company_id).count() + 1
            self.group_id = _code("PLT", self.company_id, seq)
        if not self.qr_code:
            self.qr_code = self.group_id
        super().save(*args, **kwargs)


class PlantHealthRecord(CompanyOwned):
    plant_group = models.ForeignKey(PlantGroup, on_delete=models.CASCADE,
                                    related_name="health_records")
    inspection_date = models.DateField(default=timezone.now)
    disease = models.CharField(max_length=120, blank=True)
    treatment = models.CharField(max_length=200, blank=True)
    inspector = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.plant_group.group_id} — {self.inspection_date}"


class HarvestRecord(CompanyOwned):
    harvest_id = models.CharField(max_length=30, blank=True)
    plant_group = models.ForeignKey(PlantGroup, on_delete=models.SET_NULL, null=True,
                                    blank=True, related_name="harvests")
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="harvests")
    harvest_date = models.DateField(default=timezone.now)
    cherry_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expected_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    season = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.harvest_id or 'HRV'} — {self.cherry_kg} kg"

    def save(self, *args, **kwargs):
        if not self.harvest_id and self.company_id:
            seq = HarvestRecord.objects.filter(company_id=self.company_id).count() + 1
            self.harvest_id = _code("HRV", self.company_id, seq)
        super().save(*args, **kwargs)


class AgriculturalInput(CompanyOwned):
    INPUT_TYPES = [("fertilizer", "Fertilizer"), ("pesticide", "Pesticide"),
                   ("tool", "Tool"), ("other", "Other")]
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="inputs")
    input_type = models.CharField(max_length=20, choices=INPUT_TYPES, default="fertilizer")
    name = models.CharField(max_length=120)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default="kg")
    applied_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} — {self.farm.name}"


class FarmVisit(CompanyOwned):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="visits")
    visit_date = models.DateField(default=timezone.now)
    visitor = models.CharField(max_length=120, blank=True)
    observations = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)

    def __str__(self):
        return f"{self.farm.name} — {self.visit_date}"


# ------------------------------------------------------------ coffee sites
class CoffeeSite(CompanyOwned):
    SITE_TYPES = [("washing", "Washing Station"), ("dry_mill", "Dry Mill"),
                  ("drying", "Drying Site"), ("warehouse", "Warehouse Site"),
                  ("office", "Office")]
    name = models.CharField(max_length=150)
    site_type = models.CharField(max_length=15, choices=SITE_TYPES, default="washing")
    location = models.CharField(max_length=200, blank=True)
    capacity_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    gps_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    water_source = models.CharField(max_length=120, blank=True)
    electricity = models.CharField(max_length=120, blank=True)
    equipment_notes = models.TextField(blank=True)
    licenses = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=[
        ("active", "Active"), ("inactive", "Inactive")], default="active")

    def __str__(self):
        return f"{self.name} ({self.get_site_type_display()})"


class SiteStaff(CompanyOwned):
    site = models.ForeignKey(CoffeeSite, on_delete=models.CASCADE, related_name="staff")
    employee = models.ForeignKey("shared.Employee", on_delete=models.CASCADE,
                                 related_name="coffee_site_assignments")
    role = models.CharField(max_length=80, blank=True)
    assigned_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.employee.name} @ {self.site.name}"


# ------------------------------------------------------------ procurement
class PurchaseOrder(CompanyOwned):
    STATUS = [("draft", "Draft"), ("submitted", "Submitted"), ("approved", "Approved"),
              ("received", "Received"), ("cancelled", "Cancelled")]
    order_no = models.CharField(max_length=40, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="orders")
    order_date = models.DateField(default=timezone.now)
    coffee_type = models.CharField(max_length=60, blank=True)
    grade = models.CharField(max_length=40, blank=True)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=15, choices=STATUS, default="draft")
    notes = models.TextField(blank=True)

    @property
    def total(self):
        return (self.quantity_kg or 0) * (self.unit_price or 0)

    def __str__(self):
        return f"{self.order_no or 'PO'} — {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.order_no and self.company_id:
            seq = PurchaseOrder.objects.filter(company_id=self.company_id).count() + 1
            self.order_no = _code("CPO", self.company_id, seq)
        super().save(*args, **kwargs)


class CoffeePurchase(CompanyOwned):
    """Farmer-linked purchase record (cherry or green coffee)."""
    purchase_no = models.CharField(max_length=40, blank=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="purchases")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="purchases")
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name="purchases")
    purchase_date = models.DateField(default=timezone.now)
    coffee_type = models.CharField(max_length=60, blank=True)
    grade = models.CharField(max_length=40, blank=True)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    @property
    def total(self):
        return (self.quantity_kg or 0) * (self.unit_price or 0)

    def __str__(self):
        who = self.farmer.full_name if self.farmer else (self.supplier.name if self.supplier else "?")
        return f"{self.purchase_no or 'PUR'} — {who}"

    def save(self, *args, **kwargs):
        if not self.purchase_no and self.company_id:
            seq = CoffeePurchase.objects.filter(company_id=self.company_id).count() + 1
            self.purchase_no = _code("PUR", self.company_id, seq)
        super().save(*args, **kwargs)


class PurchaseReceipt(CompanyOwned):
    purchase = models.ForeignKey(CoffeePurchase, on_delete=models.CASCADE,
                                 related_name="receipts")
    receipt_no = models.CharField(max_length=40, blank=True)
    received_date = models.DateField(default=timezone.now)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    moisture_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    defect_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade_confirmed = models.CharField(max_length=40, blank=True)
    accepted = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.receipt_no or 'PRC'} — {self.quantity_kg} kg"

    def save(self, *args, **kwargs):
        if not self.receipt_no and self.company_id:
            seq = PurchaseReceipt.objects.filter(company_id=self.company_id).count() + 1
            self.receipt_no = _code("PRC", self.company_id, seq)
        super().save(*args, **kwargs)


class CoffeePrice(CompanyOwned):
    coffee_type = models.CharField(max_length=60)
    grade = models.CharField(max_length=40, blank=True)
    season = models.CharField(max_length=20, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="prices")
    price_per_kg = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="ETB")
    effective_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.coffee_type}/{self.grade or '-'} — {self.price_per_kg}"


# ------------------------------------------------------------ collection & intake
class Delivery(CompanyOwned):
    STATUS = [("registered", "Registered"), ("weighed", "Weighed"),
              ("accepted", "Accepted"), ("rejected", "Rejected")]
    delivery_no = models.CharField(max_length=40, blank=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="deliveries")
    farm = models.ForeignKey(Farm, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="deliveries")
    harvest = models.ForeignKey(HarvestRecord, on_delete=models.SET_NULL, null=True,
                                blank=True, related_name="deliveries")
    site = models.ForeignKey(CoffeeSite, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="deliveries")
    delivery_date = models.DateField(default=timezone.now)
    coffee_type = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="registered")
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.delivery_no or 'DLV'} — {self.farmer.full_name}"

    def save(self, *args, **kwargs):
        if not self.delivery_no and self.company_id:
            seq = Delivery.objects.filter(company_id=self.company_id).count() + 1
            self.delivery_no = _code("DLV", self.company_id, seq)
        super().save(*args, **kwargs)


class WeighbridgeTicket(CompanyOwned):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name="tickets")
    ticket_no = models.CharField(max_length=40, blank=True)
    gross_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tare_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    weighed_at = models.DateTimeField(default=timezone.now)
    operator = models.CharField(max_length=120, blank=True)

    @property
    def net_kg(self):
        return (self.gross_kg or 0) - (self.tare_kg or 0)

    def __str__(self):
        return f"{self.ticket_no or 'WB'} — net {self.net_kg} kg"

    def save(self, *args, **kwargs):
        if not self.ticket_no and self.company_id:
            seq = WeighbridgeTicket.objects.filter(company_id=self.company_id).count() + 1
            self.ticket_no = _code("WB", self.company_id, seq)
        super().save(*args, **kwargs)


class IntakeBatch(CompanyOwned):
    STATUS = [("received", "Received"), ("inspecting", "Inspecting"),
              ("accepted", "Accepted"), ("rejected", "Rejected"),
              ("processing", "In Processing"), ("stored", "Stored")]
    batch_no = models.CharField(max_length=40, blank=True)
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name="intake_batches")
    site = models.ForeignKey(CoffeeSite, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="intake_batches")
    intake_date = models.DateField(default=timezone.now)
    cherry_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    moisture_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    defect_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="received")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.batch_no or 'INB'} — {self.cherry_kg} kg"

    def save(self, *args, **kwargs):
        if not self.batch_no and self.company_id:
            seq = IntakeBatch.objects.filter(company_id=self.company_id).count() + 1
            self.batch_no = _code("INB", self.company_id, seq)
        super().save(*args, **kwargs)


# ------------------------------------------------------------ processing
class ProcessingOrder(CompanyOwned):
    STATUS = [("planned", "Planned"), ("in_progress", "In Progress"),
              ("completed", "Completed"), ("cancelled", "Cancelled")]
    order_no = models.CharField(max_length=40, blank=True)
    site = models.ForeignKey(CoffeeSite, on_delete=models.CASCADE, related_name="processing_orders")
    method = models.CharField(max_length=20, choices=[
        ("washed", "Washed"), ("natural", "Natural"), ("honey", "Honey"),
        ("other", "Other")], default="washed")
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="planned")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.order_no or 'PCO'} — {self.get_method_display()}"

    def save(self, *args, **kwargs):
        if not self.order_no and self.company_id:
            seq = ProcessingOrder.objects.filter(company_id=self.company_id).count() + 1
            self.order_no = _code("PCO", self.company_id, seq)
        super().save(*args, **kwargs)


class ProcessingBatch(CompanyOwned):
    STATUS = [("started", "Started"), ("fermenting", "Fermenting"), ("drying", "Drying"),
              ("milling", "Milling"), ("completed", "Completed")]
    batch_no = models.CharField(max_length=40, blank=True)
    processing_order = models.ForeignKey(ProcessingOrder, on_delete=models.CASCADE,
                                         related_name="batches")
    intake_batch = models.ForeignKey(IntakeBatch, on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name="processing_batches")
    input_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    output_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    loss_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    water_liters = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="started")
    notes = models.TextField(blank=True)

    @property
    def yield_pct(self):
        if self.input_kg and self.output_kg:
            return float(self.output_kg) / float(self.input_kg) * 100
        return None

    def __str__(self):
        return f"{self.batch_no or 'PRB'}"

    def save(self, *args, **kwargs):
        if not self.batch_no and self.company_id:
            seq = ProcessingBatch.objects.filter(company_id=self.company_id).count() + 1
            self.batch_no = _code("PRB", self.company_id, seq)
        if self.input_kg and self.output_kg and self.loss_kg is None:
            self.loss_kg = self.input_kg - self.output_kg
        super().save(*args, **kwargs)


class DryingRecord(CompanyOwned):
    processing_batch = models.ForeignKey(ProcessingBatch, on_delete=models.CASCADE,
                                         related_name="drying_records")
    bed_no = models.CharField(max_length=40, blank=True)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    moisture_start = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    moisture_end = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Drying {self.bed_no or ''} — {self.processing_batch.batch_no}"


# ------------------------------------------------------------ quality lab
class Sample(CompanyOwned):
    sample_id = models.CharField(max_length=40, blank=True)
    intake_batch = models.ForeignKey(IntakeBatch, on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name="samples")
    processing_batch = models.ForeignKey(ProcessingBatch, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name="samples")
    sampled_date = models.DateField(default=timezone.now)
    sampled_by = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.sample_id or "SMP"

    def save(self, *args, **kwargs):
        if not self.sample_id and self.company_id:
            seq = Sample.objects.filter(company_id=self.company_id).count() + 1
            self.sample_id = _code("SMP", self.company_id, seq)
        super().save(*args, **kwargs)


class MoistureTest(CompanyOwned):
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name="moisture_tests")
    test_date = models.DateField(default=timezone.now)
    moisture_pct = models.DecimalField(max_digits=5, decimal_places=2)
    tested_by = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"{self.sample.sample_id} — {self.moisture_pct}%"


class CuppingSession(CompanyOwned):
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name="cuppings")
    session_date = models.DateField(default=timezone.now)
    aroma = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    flavor = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    acidity = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    body = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    overall = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    cupper = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Cupping {self.sample.sample_id} — {self.overall or '-'}"


class QualityCertificate(CompanyOwned):
    cert_no = models.CharField(max_length=40, blank=True)
    sample = models.ForeignKey(Sample, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="certificates")
    grade = models.CharField(max_length=40, blank=True)
    screen_size = models.CharField(max_length=40, blank=True)
    verdict = models.CharField(max_length=15, choices=[
        ("approved", "Approved"), ("rejected", "Rejected"), ("hold", "On Hold")],
        default="approved")
    issued_date = models.DateField(default=timezone.now)
    issued_by = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.cert_no or 'QCT'} — {self.verdict}"

    def save(self, *args, **kwargs):
        if not self.cert_no and self.company_id:
            seq = QualityCertificate.objects.filter(company_id=self.company_id).count() + 1
            self.cert_no = _code("QCT", self.company_id, seq)
        super().save(*args, **kwargs)


# ------------------------------------------------------------ warehouse lots & genealogy
class Warehouse(CompanyOwned):
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=200, blank=True)
    capacity_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    manager = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=15, choices=[
        ("active", "Active"), ("inactive", "Inactive")], default="active")

    def __str__(self):
        return self.name


class WarehouseLot(CompanyOwned):
    """A stored lot of green coffee. Genealogy via parent_lot (splits/merges)."""
    STATUS = [("stored", "Stored"), ("reserved", "Reserved"),
              ("shipped", "Shipped"), ("consumed", "Consumed")]
    lot_no = models.CharField(max_length=40, blank=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True,
                                  blank=True, related_name="lots")
    processing_batch = models.ForeignKey(ProcessingBatch, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name="lots")
    parent_lot = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="child_lots",
                                   help_text="Parent lot for splits/merges (genealogy)")
    grade = models.CharField(max_length=40, blank=True)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reserved_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="stored")
    notes = models.TextField(blank=True)

    @property
    def available_kg(self):
        return (self.quantity_kg or 0) - (self.reserved_kg or 0)

    def __str__(self):
        return f"{self.lot_no or 'LOT'} — {self.quantity_kg} kg"

    def save(self, *args, **kwargs):
        if not self.lot_no and self.company_id:
            seq = WarehouseLot.objects.filter(company_id=self.company_id).count() + 1
            self.lot_no = _code("LOT", self.company_id, seq)
        super().save(*args, **kwargs)


class BatchMovement(CompanyOwned):
    lot = models.ForeignKey(WarehouseLot, on_delete=models.CASCADE, related_name="movements")
    movement_date = models.DateField(default=timezone.now)
    movement_type = models.CharField(max_length=20, choices=[
        ("receipt", "Receipt"), ("transfer", "Transfer"), ("issue", "Issue"),
        ("adjustment", "Adjustment"), ("shipment", "Shipment")], default="receipt")
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    from_location = models.CharField(max_length=120, blank=True)
    to_location = models.CharField(max_length=120, blank=True)
    reference = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.lot.lot_no} {self.movement_type} {self.quantity_kg} kg"


class StockAdjustment(CompanyOwned):
    lot = models.ForeignKey(WarehouseLot, on_delete=models.CASCADE, related_name="adjustments")
    adjustment_date = models.DateField(default=timezone.now)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2,
                                      help_text="Signed: +gain, -loss")
    reason = models.CharField(max_length=200, blank=True)
    approved_by = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"{self.lot.lot_no} adj {self.quantity_kg} kg"


# ------------------------------------------------------------ export
class CoffeeBuyer(CompanyOwned):
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=80, blank=True)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=255, blank=True)
    payment_terms = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=15, choices=[
        ("active", "Active"), ("inactive", "Inactive")], default="active")

    def __str__(self):
        return self.name


class ExportContract(CompanyOwned):
    STATUS = [("draft", "Draft"), ("active", "Active"), ("fulfilled", "Fulfilled"),
              ("cancelled", "Cancelled")]
    contract_no = models.CharField(max_length=40, blank=True)
    buyer = models.ForeignKey(CoffeeBuyer, on_delete=models.PROTECT, related_name="contracts")
    signed_date = models.DateField(default=timezone.now)
    coffee_type = models.CharField(max_length=60, blank=True)
    grade = models.CharField(max_length=40, blank=True)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="USD")
    delivery_terms = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="draft")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.contract_no or 'ECT'} — {self.buyer.name}"

    def save(self, *args, **kwargs):
        if not self.contract_no and self.company_id:
            seq = ExportContract.objects.filter(company_id=self.company_id).count() + 1
            self.contract_no = _code("ECT", self.company_id, seq)
        super().save(*args, **kwargs)


class ExportOrder(CompanyOwned):
    STATUS = [("draft", "Draft"), ("confirmed", "Confirmed"), ("preparing", "Preparing"),
              ("shipped", "Shipped"), ("delivered", "Delivered"), ("cancelled", "Cancelled")]
    order_no = models.CharField(max_length=40, blank=True)
    buyer = models.ForeignKey(CoffeeBuyer, on_delete=models.PROTECT, related_name="orders")
    contract = models.ForeignKey(ExportContract, on_delete=models.SET_NULL, null=True,
                                 blank=True, related_name="orders")
    lots = models.ManyToManyField(WarehouseLot, blank=True, related_name="export_orders")
    order_date = models.DateField(default=timezone.now)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=15, choices=STATUS, default="draft")
    notes = models.TextField(blank=True)

    @property
    def total_amount(self):
        return (self.quantity_kg or 0) * (self.unit_price or 0)

    def __str__(self):
        return f"{self.order_no or 'EXO'} — {self.buyer.name}"

    def save(self, *args, **kwargs):
        if not self.order_no and self.company_id:
            seq = ExportOrder.objects.filter(company_id=self.company_id).count() + 1
            self.order_no = _code("EXO", self.company_id, seq)
        super().save(*args, **kwargs)


class ExportDocument(CompanyOwned):
    order = models.ForeignKey(ExportOrder, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=30, choices=[
        ("invoice", "Commercial Invoice"), ("packing", "Packing List"),
        ("certificate", "Certificate of Origin"), ("phytosanitary", "Phytosanitary"),
        ("quality", "Quality Certificate"), ("other", "Other")], default="invoice")
    doc_no = models.CharField(max_length=60, blank=True)
    issued_date = models.DateField(default=timezone.now)
    file = models.FileField(upload_to="coffee/export-docs/%Y/%m/", blank=True, null=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.order.order_no}"


class Shipment(CompanyOwned):
    STATUS = [("planned", "Planned"), ("in_transit", "In Transit"),
              ("cleared", "Cleared"), ("delivered", "Delivered")]
    shipment_no = models.CharField(max_length=40, blank=True)
    order = models.ForeignKey(ExportOrder, on_delete=models.CASCADE, related_name="shipments")
    container_no = models.CharField(max_length=40, blank=True)
    vessel = models.CharField(max_length=120, blank=True)
    origin_port = models.CharField(max_length=80, blank=True)
    destination_port = models.CharField(max_length=80, blank=True)
    etd = models.DateField(null=True, blank=True)
    eta = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="planned")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.shipment_no or 'SHP'} — {self.destination_port or ''}"

    def save(self, *args, **kwargs):
        if not self.shipment_no and self.company_id:
            seq = Shipment.objects.filter(company_id=self.company_id).count() + 1
            self.shipment_no = _code("SHP", self.company_id, seq)
        super().save(*args, **kwargs)


class CoffeeExportInvoice(CompanyOwned):
    STATUS = [("draft", "Draft"), ("unpaid", "Unpaid"), ("partial", "Partially Paid"),
              ("paid", "Paid"), ("overdue", "Overdue")]
    order = models.ForeignKey(ExportOrder, on_delete=models.CASCADE, related_name="invoices")
    invoice_no = models.CharField(max_length=40, blank=True)
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=15, choices=STATUS, default="unpaid")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.invoice_no or 'EINV'} — {self.order.buyer.name}"

    def save(self, *args, **kwargs):
        if not self.invoice_no and self.company_id:
            seq = CoffeeExportInvoice.objects.filter(company_id=self.company_id).count() + 1
            self.invoice_no = _code("EINV", self.company_id, seq)
        super().save(*args, **kwargs)


# ------------------------------------------------------------ logistics
class Transporter(CompanyOwned):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    contract_ref = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=15, choices=[
        ("active", "Active"), ("inactive", "Inactive")], default="active")

    def __str__(self):
        return self.name


class Dispatch(CompanyOwned):
    STATUS = [("planned", "Planned"), ("dispatched", "Dispatched"),
              ("in_transit", "In Transit"), ("delivered", "Delivered")]
    dispatch_no = models.CharField(max_length=40, blank=True)
    transporter = models.ForeignKey(Transporter, on_delete=models.SET_NULL, null=True,
                                    blank=True, related_name="dispatches")
    shipment = models.ForeignKey(Shipment, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="dispatches")
    vehicle_plate = models.CharField(max_length=40, blank=True)
    origin = models.CharField(max_length=120, blank=True)
    destination = models.CharField(max_length=120, blank=True)
    dispatch_date = models.DateField(default=timezone.now)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    freight_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pod_received = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=STATUS, default="planned")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.dispatch_no or 'DSP'} — {self.destination}"

    def save(self, *args, **kwargs):
        if not self.dispatch_no and self.company_id:
            seq = Dispatch.objects.filter(company_id=self.company_id).count() + 1
            self.dispatch_no = _code("DSP", self.company_id, seq)
        super().save(*args, **kwargs)


# ------------------------------------------------------------ equipment & maintenance
class Equipment(CompanyOwned):
    STATUS = [("operational", "Operational"), ("maintenance", "Under Maintenance"),
              ("broken", "Broken Down"), ("retired", "Retired")]
    name = models.CharField(max_length=150)
    equipment_type = models.CharField(max_length=60, blank=True)
    site = models.ForeignKey(CoffeeSite, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="equipment")
    serial_no = models.CharField(max_length=80, blank=True)
    installed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="operational")
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class MaintenanceOrder(CompanyOwned):
    STATUS = [("open", "Open"), ("in_progress", "In Progress"),
              ("completed", "Completed"), ("cancelled", "Cancelled")]
    order_no = models.CharField(max_length=40, blank=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="orders")
    order_type = models.CharField(max_length=15, choices=[
        ("preventive", "Preventive"), ("corrective", "Corrective")], default="corrective")
    reported_date = models.DateField(default=timezone.now)
    description = models.TextField(blank=True)
    assigned_to = models.CharField(max_length=120, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    downtime_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="open")

    def __str__(self):
        return f"{self.order_no or 'MNT'} — {self.equipment.name}"

    def save(self, *args, **kwargs):
        if not self.order_no and self.company_id:
            seq = MaintenanceOrder.objects.filter(company_id=self.company_id).count() + 1
            self.order_no = _code("MNT", self.company_id, seq)
        super().save(*args, **kwargs)


class SparePart(CompanyOwned):
    name = models.CharField(max_length=150)
    part_no = models.CharField(max_length=60, blank=True)
    stock_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default="pcs")
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.name


# ------------------------------------------------------------ security
class Camera(CompanyOwned):
    name = models.CharField(max_length=120)
    site = models.ForeignKey(CoffeeSite, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="cameras")
    location = models.CharField(max_length=150, blank=True)
    stream_url = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=15, choices=[
        ("online", "Online"), ("offline", "Offline"), ("fault", "Fault")],
        default="online")
    installed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class SecurityIncident(CompanyOwned):
    STATUS = [("open", "Open"), ("investigating", "Investigating"),
              ("resolved", "Resolved")]
    site = models.ForeignKey(CoffeeSite, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="incidents")
    incident_date = models.DateField(default=timezone.now)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    reported_by = models.CharField(max_length=120, blank=True)
    action_taken = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="open")

    def __str__(self):
        return f"{self.title} — {self.incident_date}"
