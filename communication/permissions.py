"""Messaging permission rules.

- Management (owner / admin / manager) may start a direct conversation
  with any staff member.
- Other users message through authorized channels: the department
  channel(s) of their own department, and group chats they are members of.
- Management can view every department and group channel; direct
  conversations stay private to their two participants.
"""
from django.db.models import Q

from .models import Channel, ChannelMember, ChatMessage, MessageRead

MANAGEMENT_ROLES = ["owner", "admin", "manager"]


def is_management(membership):
    return membership.role in MANAGEMENT_ROLES


def user_department_ids(company, user):
    from shared.models import Employee
    return set(
        Employee.objects.filter(company=company, user=user)
        .exclude(department__isnull=True)
        .values_list("department_id", flat=True)
    )


def accessible_channel_ids(company, user, membership):
    """IDs of channels the user may open."""
    mgmt = is_management(membership)
    direct_ids = set(
        ChannelMember.objects.filter(channel__company=company, user=user,
                                     channel__channel_type="direct")
        .values_list("channel_id", flat=True)
    )
    dept_ids = set(
        Channel.objects.filter(company=company, is_active=True,
                               channel_type="department")
        .values_list("id", flat=True)
    )
    if not mgmt:
        my_depts = user_department_ids(company, user)
        dept_ids = set(
            Channel.objects.filter(company=company, is_active=True,
                                   channel_type="department",
                                   department_id__in=my_depts)
            .values_list("id", flat=True)
        )
    group_ids = set(
        ChannelMember.objects.filter(channel__company=company, user=user,
                                     channel__channel_type="group")
        .values_list("channel_id", flat=True)
    )
    if mgmt:
        group_ids |= set(
            Channel.objects.filter(company=company, is_active=True,
                                   channel_type="group")
            .values_list("id", flat=True)
        )
    return direct_ids | dept_ids | group_ids


def get_channel_or_denied(company, user, membership, pk):
    from django.shortcuts import get_object_or_404
    channel = get_object_or_404(Channel, company=company, pk=pk, is_active=True)
    if channel.id not in accessible_channel_ids(company, user, membership):
        return None
    return channel


def can_post(channel, user, membership):
    return channel.id in accessible_channel_ids(
        channel.company, user, membership)


def can_create_direct(membership):
    return is_management(membership)


def can_manage_members(channel, user, membership):
    if is_management(membership):
        return True
    return ChannelMember.objects.filter(
        channel=channel, user=user, is_admin=True).exists()


def unread_counts(company, user, membership):
    """{channel_id: unread} for channels the user can access."""
    ids = accessible_channel_ids(company, user, membership)
    if not ids:
        return {}
    read_ids = set(
        MessageRead.objects.filter(user=user, message__channel_id__in=ids)
        .values_list("message_id", flat=True)
    )
    counts = {}
    msgs = (ChatMessage.objects.filter(channel_id__in=ids)
            .exclude(sender=user).only("id", "channel_id"))
    for m in msgs.iterator():
        if m.id not in read_ids:
            counts[m.channel_id] = counts.get(m.channel_id, 0) + 1
    return counts


def mark_channel_read(channel, user):
    unread = (ChatMessage.objects.filter(channel=channel)
              .exclude(sender=user)
              .exclude(reads__user=user))
    MessageRead.objects.bulk_create(
        [MessageRead(message=m, user=user) for m in unread.only("id")],
        ignore_conflicts=True,
    )


def notify_members(company, channel, sender, message):
    """Notify every participant except the sender about a new message."""
    from shared.models import Notification
    member_ids = channel.member_ids()
    if channel.channel_type == "department" and channel.department_id:
        from shared.models import Employee
        emp_user_ids = set(
            Employee.objects
            .filter(company=company, department_id=channel.department_id)
            .exclude(user__isnull=True).values_list("user_id", flat=True)
        )
        member_ids |= emp_user_ids
    link = f"/c/{company.slug}/comm/channel/{channel.pk}/"
    preview = (message.body[:80] + "…") if len(message.body) > 80 else message.body
    for uid in member_ids:
        if uid == sender.id:
            continue
        try:
            Notification.objects.get_or_create(
                company=company, user_id=uid,
                title=f"New message in {channel.name}",
                message=f"{sender.username}: {preview}",
                defaults={"link": link},
            )
        except Exception:
            pass
