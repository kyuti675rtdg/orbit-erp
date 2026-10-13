"""Orbit Chat — Telegram-inspired messaging, native to the ERP.

Real-time delivery uses short-polling against live JSON APIs (works on the
existing gunicorn/Postgres stack with no extra infrastructure). Presence is
maintained by client heartbeats.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import CompanyOwned

ROOM_TYPES = [
    ("dm", "Direct Message"),
    ("group", "Group Chat"),
    ("department", "Department"),
    ("project", "Project"),
]

REACTIONS = ["like", "love", "laugh", "wow", "sad"]


class ChatRoom(CompanyOwned):
    room_type = models.CharField(max_length=15, choices=ROOM_TYPES, default="group")
    name = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="chat_rooms_created")
    # for department rooms: the department name; for project rooms: a label
    ref_key = models.CharField(max_length=120, blank=True,
                               help_text="Department name or project label")
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.display_name()

    def display_name(self):
        if self.room_type == "dm":
            return self.name or "Direct Message"
        return self.name or self.get_room_type_display()

    def last_message(self):
        return self.messages.filter(is_deleted=False).order_by("-created_at").first()


class ChatMember(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="chat_memberships")
    role = models.CharField(max_length=10, choices=[("admin", "Admin"), ("member", "Member")],
                            default="member")
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    muted = models.BooleanField(default=False)

    class Meta:
        unique_together = [("room", "user")]

    def unread_count(self):
        qs = self.room.messages.filter(is_deleted=False)
        if self.last_read_at:
            qs = qs.filter(created_at__gt=self.last_read_at)
        return qs.exclude(sender=self.user).count()


class ChatMessage(CompanyOwned):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="chat_messages")
    body = models.TextField(blank=True)
    reply_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="replies")
    attachment = models.FileField(upload_to="orbitchat/%Y/%m/", blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    # optional link to a business record: "app_label:ModelName:pk"
    record_link = models.CharField(max_length=120, blank=True)
    record_label = models.CharField(max_length=160, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"#{self.room_id} {self.sender}: {(self.body or '[file]')[:40]}"

    def to_dict(self, viewer=None):
        from django.urls import reverse
        d = {
            "id": self.id,
            "room": self.room_id,
            "sender": self.sender_id,
            "sender_name": (self.sender.get_full_name() or self.sender.username),
            "sender_username": self.sender.username,
            "body": self.body,
            "created_at": self.created_at.isoformat(),
            "edited": bool(self.edited_at),
            "reply_to": ({"id": self.reply_to_id,
                           "sender_name": (self.reply_to.sender.get_full_name()
                                           or self.reply_to.sender.username),
                           "body": (self.reply_to.body or "[file]")[:120]}
                          if self.reply_to else None),
            "attachment": (self.attachment.url if self.attachment else None),
            "attachment_name": self.attachment_name,
            "record": ({"label": self.record_label, "link": self.record_link}
                       if self.record_link else None),
            "reactions": {},
            "seen_by": [],
        }
        for r in self.reactions.all():
            d["reactions"].setdefault(r.reaction, []).append(r.user.username)
        d["seen_by"] = [r.user.username for r in
                        self.reads.select_related("user").all()
                        if r.user_id != self.sender_id]
        return d


class ChatReaction(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE,
                                related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=10, choices=[(r, r) for r in REACTIONS])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("message", "user", "reaction")]


class MessageRead(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE,
                                related_name="reads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("message", "user")]


class ChatPresence(models.Model):
    """Heartbeat-based online status (one row per user)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="chat_presence")
    last_seen = models.DateTimeField(default=timezone.now)

    def is_online(self):
        return (timezone.now() - self.last_seen).total_seconds() < 120
