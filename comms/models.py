"""Collaboration: tasks, meetings.

Works alongside shared.Announcement / shared.Notification /
shared.CompanyDocument.

Works alongside shared.Announcement / shared.Notification /
shared.CompanyDocument."""
from django.conf import settings
from django.db import models

from core.models import CompanyOwned


class Task(CompanyOwned):
    STATUS_CHOICES = [("todo", "To Do"), ("in_progress", "In Progress"),
                      ("review", "In Review"), ("done", "Done")]
    PRIORITY_CHOICES = [("low", "Low"), ("normal", "Normal"),
                        ("high", "High"), ("urgent", "Urgent")]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="assigned_tasks")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="created_tasks")
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="normal")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="todo")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date", "-created_at"]

    def __str__(self):
        return self.title


class Meeting(CompanyOwned):
    title = models.CharField(max_length=200)
    agenda = models.TextField(blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=150, blank=True)
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                       related_name="meetings", blank=True)
    minutes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start"]

    def __str__(self):
        return f"{self.title} ({self.start:%b %d %H:%M})"
