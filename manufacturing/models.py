"""Manufacturing: products, BOMs, planning, production, QC, maintenance."""
from django.db import models

from core.models import CompanyOwned


class ProductCategory(CompanyOwned):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Product(CompanyOwned):
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=40, blank=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="products")
    unit = models.CharField(max_length=20, default="pcs")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class RawMaterial(CompanyOwned):
    name = models.CharField(max_length=150)
    unit = models.CharField(max_length=20, default="kg")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    supplier = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.name


class BOM(CompanyOwned):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="boms")
    version = models.CharField(max_length=20, default="1.0")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"BOM {self.product.name} v{self.version}"


class BOMLine(CompanyOwned):
    bom = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name="lines")
    material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, related_name="bom_lines")
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    def __str__(self):
        return f"{self.bom} — {self.material.name}"


class ProductionPlan(CompanyOwned):
    STATUS = [("draft", "Draft"), ("approved", "Approved"), ("in_progress", "In Progress"), ("completed", "Completed")]
    plan_no = models.CharField(max_length=40)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="plans")
    planned_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="draft")

    def __str__(self):
        return self.plan_no


class ProductionOrder(CompanyOwned):
    STATUS = [("draft", "Draft"), ("released", "Released"), ("in_progress", "In Progress"),
              ("qc", "Quality Check"), ("completed", "Completed"), ("cancelled", "Cancelled")]
    order_no = models.CharField(max_length=40)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="production_orders")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    order_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="draft")

    def __str__(self):
        return self.order_no


class WorkCenter(CompanyOwned):
    name = models.CharField(max_length=120)
    center_type = models.CharField(max_length=80, blank=True)
    capacity_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[("active", "Active"), ("idle", "Idle"), ("maintenance", "Maintenance")], default="active")

    def __str__(self):
        return self.name


class Machine(CompanyOwned):
    name = models.CharField(max_length=120)
    work_center = models.ForeignKey(WorkCenter, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="machines")
    model = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=[("running", "Running"), ("idle", "Idle"), ("down", "Down")], default="idle")
    last_maintenance = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name


class MaterialIssue(CompanyOwned):
    issue_no = models.CharField(max_length=40)
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, related_name="material_issues")
    material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, related_name="issues")
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    issue_date = models.DateField()
    issued_by = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.issue_no


class QualityCheck(CompanyOwned):
    check_no = models.CharField(max_length=40)
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, related_name="quality_checks")
    check_date = models.DateField()
    inspector = models.CharField(max_length=120, blank=True)
    result = models.CharField(max_length=20, choices=[("pass", "Pass"), ("fail", "Fail"), ("rework", "Rework")], default="pass")
    defects_found = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.check_no


class Warehouse(CompanyOwned):
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=150, blank=True)
    manager = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.name


class Stock(CompanyOwned):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stock")
    item_type = models.CharField(max_length=20, choices=[("raw", "Raw Material"), ("finished", "Finished Good")], default="raw")
    item_name = models.CharField(max_length=150)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default="kg")

    def __str__(self):
        return f"{self.item_name} @ {self.warehouse.name}"


class Batch(CompanyOwned):
    batch_no = models.CharField(max_length=40)
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name="batches")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="batches")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    production_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[("in_production", "In Production"), ("qc", "QC Hold"), ("released", "Released"), ("expired", "Expired")], default="in_production")

    def __str__(self):
        return self.batch_no


class MaintenanceRecord(CompanyOwned):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name="maintenance")
    maintenance_type = models.CharField(max_length=20, choices=[("preventive", "Preventive"), ("corrective", "Corrective")], default="preventive")
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    technician = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=[("scheduled", "Scheduled"), ("in_progress", "In Progress"), ("done", "Done")], default="scheduled")

    def __str__(self):
        return f"{self.machine.name} — {self.scheduled_date}"
