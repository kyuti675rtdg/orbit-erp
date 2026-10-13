"""Unified request intake: leave, loans, advances, purchases, expenses,
payments, stock transfers, maintenance and other business requests.

Every request flows through an approval workflow:
draft -> submitted -> approved / rejected / returned -> (resubmit) ...
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import CompanyOwned


class Request(CompanyOwned):
    TYPE_CHOICES = [
        ("leave", "Leave Request"),
        ("loan", "Loan Request"),
        ("advance", "Salary Advance"),
        ("purchase", "Purchase Request"),
        ("expense", "Expense Claim"),
        ("payment", "Payment Request"),
        ("stock_transfer", "Stock Transfer"),
        ("maintenance", "Maintenance Request"),
        ("travel", "Travel Request"),
        ("other", "Other Request"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("returned", "Returned for Changes"),
        ("cancelled", "Cancelled"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    ref_no = models.CharField(max_length=30, blank=True, help_text="Auto-generated")
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="erp_requests"
    )
    request_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="other")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    needed_by = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True, help_text="For leave / travel")
    end_date = models.DateField(null=True, blank=True, help_text="For leave / travel")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="draft")
    current_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="requests_to_approve",
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="requests_decided",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ref_no or 'REQ'} — {self.title}"

    def save(self, *args, **kwargs):
        if not self.ref_no and self.company_id:
            seq = Request.objects.filter(company_id=self.company_id).count() + 1
            self.ref_no = f"REQ-{timezone.now():%Y}-{seq:04d}"
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        return self.status in ("draft", "submitted", "returned")


class RequestEvent(CompanyOwned):
    """Activity history: every submit / decision / comment on a request."""

    ACTION_CHOICES = [
        ("created", "Created"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("returned", "Returned for Changes"),
        ("cancelled", "Cancelled"),
        ("comment", "Comment"),
        ("reassigned", "Reassigned"),
    ]
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="request_events"
    )
    action = models.CharField(max_length=15, choices=ACTION_CHOICES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.request.ref_no} {self.action} by {self.actor.username}"
