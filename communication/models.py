"""Company-wide internal messaging.

Channel types:
- direct: 1-to-1 conversation. Only management (owner/admin/manager) may
  start a direct conversation with any staff member; other users take part
  only when invited.
- department: bound to an HR department. Every employee of that department
  (plus management) can read and post — membership is derived from the
  employee's department, no invites needed.
- group: free-form group chat with an explicit member list, for
  department-to-department and cross-team discussions.
"""
from django.conf import settings
from django.db import models

from core.models import CompanyOwned


class Channel(CompanyOwned):
    CHANNEL_TYPES = [
        ("direct", "Direct Message"),
        ("department", "Department Channel"),
        ("group", "Group Chat"),
    ]
    name = models.CharField(max_length=120)
    channel_type = models.CharField(max_length=15, choices=CHANNEL_TYPES, default="group")
    department = models.ForeignKey(
        "shared.Department", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="chat_channels",
    )
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="channels_created",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"

    def member_ids(self):
        return set(self.memberships.values_list("user_id", flat=True))


class ChannelMember(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="channel_memberships")
    is_admin = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("channel", "user")]

    def __str__(self):
        return f"{self.user.username} in {self.channel.name}"


class ChatMessage(CompanyOwned):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="chat_messages")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username}: {self.body[:40]}"


class MessageRead(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="message_reads")
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("message", "user")]
