"""Communication & Collaboration entity registry."""
from shared import models as sm

from . import models as m

E = lambda **kw: kw  # noqa: E731

ENTITIES = {
    "conversations": E(
        title="Conversations", singular="Conversation", icon="chat",
        model=m.Conversation,
        list_display=[("Title", "title"), ("Type", "conversation_type"), ("Created", "created_at")],
        search=["title"],
        form_fields=["title", "conversation_type", "department", "participants", "is_active"],
        detail_related=[
            ("Messages", "messages", [("Sender", "sender__username"), ("Body", "body")]),
        ],
    ),
    "messages": E(
        title="Messages", singular="Message", icon="chat",
        model=m.Message,
        list_display=[("Conversation", "conversation__title"), ("Sender", "sender__username"),
                      ("Sent", "created_at")],
        search=["body"],
        form_fields=["conversation", "sender", "body"],
    ),
    "announcements": E(
        title="Announcements", singular="Announcement", icon="bell",
        model=sm.Announcement,
        list_display=[("Title", "title"), ("Publish Date", "publish_date"),
                      ("Audience", "audience"), ("Active", "is_active")],
        search=["title", "body"],
        form_fields=["title", "body", "publish_date", "audience", "is_active"],
    ),
    "tasks": E(
        title="Tasks & Assignments", singular="Task", icon="clipboard",
        model=m.Task,
        list_display=[("Title", "title"), ("Assigned To", "assigned_to__username"),
                      ("Due", "due_date"), ("Priority", "priority"), ("Status", "status")],
        search=["title", "description"],
        form_fields=["title", "description", "assigned_to", "due_date", "priority", "status"],
        workflow={
            "status_field": "status",
            "transitions": [
                {"name": "start", "label": "Start", "from": ["todo"], "to": "in_progress",
                 "roles": ["owner", "admin", "manager", "dispatcher", "accountant", "viewer"]},
                {"name": "review", "label": "Send to Review", "from": ["in_progress"], "to": "review",
                 "roles": ["owner", "admin", "manager", "dispatcher", "accountant", "viewer"]},
                {"name": "done", "label": "Mark Done", "from": ["todo", "in_progress", "review"],
                 "to": "done", "roles": ["owner", "admin", "manager", "dispatcher", "accountant", "viewer"]},
            ],
        },
    ),
    "meetings": E(
        title="Meetings & Events", singular="Meeting", icon="calendar",
        model=m.Meeting,
        list_display=[("Title", "title"), ("Start", "start"),
                      ("Location", "location")],
        search=["title", "agenda"],
        form_fields=["title", "agenda", "start", "end", "location", "attendees", "minutes"],
    ),
    "notifications": E(
        title="Notifications", singular="Notification", icon="bell", readonly=True,
        model=sm.Notification,
        list_display=[("Title", "title"), ("User", "user__username"),
                      ("Read", "is_read"), ("Created", "created_at")],
        search=["title", "message"],
        form_fields=[],
    ),
    "documents": E(
        title="Document Library", singular="Document", icon="file",
        model=sm.CompanyDocument,
        list_display=[("Title", "title"), ("Category", "category"), ("Version", "version"),
                      ("Reference", "reference_no"), ("Uploaded By", "uploaded_by")],
        search=["title", "reference_no", "description"],
        form_fields=["title", "category", "description", "version", "reference_no", "file", "uploaded_by"],
    ),
}
