"""Communication views: department channels, group chats, direct messages."""
from django import forms
from django.contrib import messages
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core import dashboards as D
from core.crud import _audit
from core.models import Membership
from core.modules import build_sidebar
from core.views import company_access_required

from . import permissions as P
from .models import Channel, ChannelMember, ChatMessage


def _el(company, url_name, **kw):
    from django.urls import reverse
    k = {"company_slug": company.slug}
    k.update(kw)
    return reverse(url_name, kwargs=k)


@company_access_required
def dashboard(request, company_slug):
    c = request.company
    me = request.user
    ids = P.accessible_channel_ids(c, me, request.membership)
    channels = (Channel.objects.filter(id__in=ids, is_active=True)
                .annotate(last_msg=Max("messages__created_at"),
                          msg_count=Count("messages")))
    unread = P.unread_counts(c, me, request.membership)
    total_unread = sum(unread.values())
    direct = channels.filter(channel_type="direct").count()
    dept = channels.filter(channel_type="department").count()
    recent = (ChatMessage.objects.filter(channel_id__in=ids)
              .select_related("sender", "channel")
              .order_by("-created_at")[:10])

    kpis = [
        D.kpi("My Channels", f"{channels.count()}", "chat", "orange",
              sub="direct, department & groups"),
        D.kpi("Unread Messages", f"{total_unread}", "bell", "blue",
              sub="across your channels"),
        D.kpi("Direct Conversations", f"{direct}", "user", "green",
              sub="1-to-1 messages"),
        D.kpi("Department Channels", f"{dept}", "building", "purple",
              sub="team discussions"),
    ]
    cfg = {
        "title": "Communication", "subtitle": "Company-wide internal messaging",
        "kpis": kpis,
        "tables": [
            {"title": "Recent Messages", "headers": ["Channel", "From", "Message", "When"],
             "rows": [[m.channel.name, m.sender.username,
                       (m.body[:45] + "…") if len(m.body) > 45 else m.body,
                       m.created_at.strftime("%b %d %H:%M")] for m in recent],
             "link": _el(c, "comm_channels"), "link_label": "All channels"},
            {"title": "Channels With Unread",
             "headers": ["Channel", "Type", "Unread"],
             "rows": [[ch.name, ch.get_channel_type_display(), unread.get(ch.id, 0)]
                      for ch in channels if unread.get(ch.id)],
             "link": _el(c, "comm_channels"), "link_label": "All channels"},
        ],
        "actions": [
            {"label": "Browse Channels", "icon": "chat", "url": _el(c, "comm_channels")},
        ] + ([{"label": "New Direct Message", "icon": "plus",
               "url": _el(c, "comm_new_direct")}]
             if P.can_create_direct(request.membership) else []) + [
            {"label": "New Group Chat", "icon": "plus", "url": _el(c, "comm_new_group")},
        ],
    }
    return D.render_module_dashboard(request, c, cfg)


@company_access_required
def channel_list(request, company_slug):
    c = request.company
    me = request.user
    ids = P.accessible_channel_ids(c, me, request.membership)
    channels = (Channel.objects.filter(id__in=ids, is_active=True)
                .annotate(last_msg=Max("messages__created_at"))
                .order_by("-last_msg", "name"))
    unread = P.unread_counts(c, me, request.membership)
    for ch in channels:
        ch.unread_n = unread.get(ch.id, 0)
    directs = [ch for ch in channels if ch.channel_type == "direct"]
    departments = [ch for ch in channels if ch.channel_type == "department"]
    group_chats = [ch for ch in channels if ch.channel_type == "group"]
    ctx = {"company": c, "membership": request.membership,
           "directs": directs, "departments": departments,
           "group_chats": group_chats,
           "can_dm": P.can_create_direct(request.membership),
           "sidebar": build_sidebar(request)}
    return render(request, "communication/channel_list.html", ctx)


@company_access_required
def channel_detail(request, company_slug, pk):
    c = request.company
    channel = P.get_channel_or_denied(c, request.user, request.membership, pk)
    if not channel:
        messages.error(request, "You don't have access to that conversation.")
        return redirect(_el(c, "comm_channels"))
    P.mark_channel_read(channel, request.user)
    msgs = (channel.messages.select_related("sender")
            .order_by("-created_at")[:60])
    msgs = list(reversed(msgs))
    members = (ChannelMember.objects.filter(channel=channel)
               .select_related("user").order_by("user__username"))
    if channel.channel_type == "department" and channel.department_id:
        from shared.models import Employee
        dept_users = (Employee.objects.filter(company=c, department_id=channel.department_id)
                      .exclude(user__isnull=True).select_related("user"))
    else:
        dept_users = []
    ctx = {"company": c, "membership": request.membership, "channel": channel,
           "messages": msgs, "members": members, "dept_users": dept_users,
           "can_manage": P.can_manage_members(channel, request.user, request.membership),
           "sidebar": build_sidebar(request)}
    return render(request, "communication/channel_detail.html", ctx)


@company_access_required
@require_POST
def message_post(request, company_slug, pk):
    c = request.company
    channel = P.get_channel_or_denied(c, request.user, request.membership, pk)
    body = (request.POST.get("body") or "").strip()
    if not channel:
        messages.error(request, "You don't have access to that conversation.")
        return redirect(_el(c, "comm_channels"))
    if not body:
        messages.error(request, "Message cannot be empty.")
        return redirect(_el(c, "comm_channel", pk=pk))
    msg = ChatMessage.objects.create(company=c, channel=channel,
                                     sender=request.user, body=body)
    P.notify_members(c, channel, request.user, msg)
    _audit(request, "message posted", msg)
    return redirect(_el(c, "comm_channel", pk=pk))


class DirectForm(forms.Form):
    user = forms.ModelChoiceField(queryset=None, label="Message")

    def __init__(self, company, me, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = (
            Membership.objects.filter(company=company, is_active=True)
            .exclude(user=me).select_related("user").order_by("user__username")
        )
        self.fields["user"].label_from_instance = (
            lambda m: f"{m.user.username} ({m.get_role_display()})")


@company_access_required
def new_direct(request, company_slug):
    c = request.company
    if not P.can_create_direct(request.membership):
        messages.error(request,
                       "Only management can start direct conversations. "
                       "Please use your department or group channels.")
        return redirect(_el(c, "comm_channels"))
    form = DirectForm(c, request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        other = form.cleaned_data["user"].user
        # find an existing direct channel between the two
        mine = set(ChannelMember.objects.filter(
            user=request.user, channel__channel_type="direct",
            channel__company=c).values_list("channel_id", flat=True))
        theirs = set(ChannelMember.objects.filter(
            user=other, channel__channel_type="direct",
            channel__company=c).values_list("channel_id", flat=True))
        existing = mine & theirs
        channel = None
        for cid in existing:
            ch = Channel.objects.filter(pk=cid, is_active=True).first()
            if ch and ch.memberships.count() == 2:
                channel = ch
                break
        if not channel:
            channel = Channel.objects.create(
                company=c, name=f"{request.user.username} ↔ {other.username}",
                channel_type="direct", created_by=request.user)
            ChannelMember.objects.create(channel=channel, user=request.user,
                                         is_admin=True)
            ChannelMember.objects.create(channel=channel, user=other)
            _audit(request, "direct conversation started", channel)
        return redirect(_el(c, "comm_channel", pk=channel.pk))
    ctx = {"company": c, "membership": request.membership, "form": form,
           "sidebar": build_sidebar(request)}
    return render(request, "communication/new_direct.html", ctx)


class GroupForm(forms.Form):
    name = forms.CharField(max_length=120, label="Group name")
    description = forms.CharField(max_length=255, required=False,
                                  widget=forms.Textarea(attrs={"rows": 2}))
    members = forms.ModelMultipleChoiceField(
        queryset=None, required=False, label="Members",
        widget=forms.CheckboxSelectMultiple)

    def __init__(self, company, me, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["members"].queryset = (
            Membership.objects.filter(company=company, is_active=True)
            .exclude(user=me).select_related("user").order_by("user__username")
        )
        self.fields["members"].label_from_instance = (
            lambda m: f"{m.user.username} ({m.get_role_display()})")


@company_access_required
def new_group(request, company_slug):
    c = request.company
    form = GroupForm(c, request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        channel = Channel.objects.create(
            company=c, name=form.cleaned_data["name"],
            channel_type="group",
            description=form.cleaned_data["description"] or "",
            created_by=request.user)
        ChannelMember.objects.create(channel=channel, user=request.user,
                                     is_admin=True)
        for m in form.cleaned_data["members"]:
            ChannelMember.objects.get_or_create(channel=channel, user=m.user)
        _audit(request, "group chat created", channel)
        messages.success(request, f"Group '{channel.name}' created.")
        return redirect(_el(c, "comm_channel", pk=channel.pk))
    ctx = {"company": c, "membership": request.membership, "form": form,
           "sidebar": build_sidebar(request)}
    return render(request, "communication/new_group.html", ctx)


@company_access_required
@require_POST
def member_add(request, company_slug, pk):
    c = request.company
    channel = P.get_channel_or_denied(c, request.user, request.membership, pk)
    if not channel or channel.channel_type == "department":
        messages.error(request, "Members can't be added here.")
        return redirect(_el(c, "comm_channels"))
    if not P.can_manage_members(channel, request.user, request.membership):
        messages.error(request, "Only channel admins or management can add members.")
        return redirect(_el(c, "comm_channel", pk=pk))
    username = (request.POST.get("username") or "").strip()
    try:
        target = Membership.objects.get(company=c, is_active=True,
                                        user__username=username).user
    except Membership.DoesNotExist:
        messages.error(request, f"No active member '{username}'.")
        return redirect(_el(c, "comm_channel", pk=pk))
    if channel.channel_type == "direct" and not P.is_management(request.membership):
        messages.error(request, "Only management can add people to a direct conversation.")
        return redirect(_el(c, "comm_channel", pk=pk))
    ChannelMember.objects.get_or_create(channel=channel, user=target)
    messages.success(request, f"{target.username} added to {channel.name}.")
    return redirect(_el(c, "comm_channel", pk=pk))


@company_access_required
@require_POST
def member_remove(request, company_slug, pk, user_id):
    c = request.company
    channel = P.get_channel_or_denied(c, request.user, request.membership, pk)
    if not channel or not P.can_manage_members(channel, request.user, request.membership):
        messages.error(request, "You can't remove members here.")
        return redirect(_el(c, "comm_channel", pk=pk))
    ChannelMember.objects.filter(channel=channel, user_id=user_id).delete()
    messages.success(request, "Member removed.")
    return redirect(_el(c, "comm_channel", pk=pk))
