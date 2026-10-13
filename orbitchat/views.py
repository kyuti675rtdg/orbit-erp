"""Orbit Chat views: full-page UI + live JSON APIs."""
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from core.models import Membership
from core.views import company_access_required
from shared.models import Notification

from .models import (ChatMember, ChatMessage, ChatPresence, ChatReaction,
                     ChatRoom, MessageRead, REACTIONS)

MGMT = {settings.ROLE_OWNER, settings.ROLE_ADMIN, settings.ROLE_MANAGER}


# ---------------------------------------------------------------- helpers
def _is_management(membership):
    return membership.role in MGMT


def _member_of(room, user):
    return ChatMember.objects.filter(room=room, user=user).first()


def _room_or_404(company, room_id, user):
    room = get_object_or_404(ChatRoom, pk=room_id, company=company, is_archived=False)
    mem = _member_of(room, user)
    if not mem:
        from django.http import Http404
        raise Http404("Not a member of this chat")
    return room, mem


def _presence_map(user_ids):
    cutoff = timezone.now() - timedelta(seconds=120)
    seen = set(ChatPresence.objects.filter(
        user_id__in=user_ids, last_seen__gte=cutoff).values_list("user_id", flat=True))
    return {uid: (uid in seen) for uid in user_ids}


def _avatar_url(u):
    try:
        p = u.profile
        return p.avatar.url if p.avatar else ""
    except Exception:
        return ""


def _user_dict(u, online=None):
    return {"id": u.id, "username": u.username,
            "name": u.get_full_name() or u.username,
            "initial": (u.get_full_name() or u.username or "?")[:1].upper(),
            "avatar": _avatar_url(u),
            "online": online}


def _room_dict(room, user):
    mem = _member_of(room, user)
    members = list(room.memberships.select_related("user"))
    online = _presence_map([m.user_id for m in members])
    last = room.last_message()
    if room.room_type == "dm":
        other = next((m.user for m in members if m.user_id != user.id), None)
        name = (other.get_full_name() or other.username) if other else "Direct Message"
        peer_online = online.get(other.id, False) if other else False
        peer_avatar = _avatar_url(other) if other else ""
    else:
        name, peer_online, peer_avatar = room.display_name(), None, ""
    return {
        "id": room.id, "type": room.room_type, "name": name,
        "description": room.description,
        "peer_online": peer_online,
        "peer_avatar": peer_avatar,
        "members": [_user_dict(m.user, online.get(m.user_id, False)) for m in members],
        "member_count": len(members),
        "unread": mem.unread_count() if mem else 0,
        "muted": mem.muted if mem else False,
        "is_admin": (mem.role == "admin") if mem else False,
        "last_message": ({"body": last.body or ("[file] " + (last.attachment_name or "")),
                           "sender_name": last.sender.get_full_name() or last.sender.username,
                           "at": last.created_at.isoformat()} if last else None),
        "updated_at": room.updated_at.isoformat(),
    }


def ensure_department_rooms(company):
    """Idempotent: one group room per department with all its employees."""
    try:
        from shared.models import Employee
    except Exception:
        return
    depts = (Employee.objects.filter(company=company, status="active")
             .exclude(department__isnull=True)
             .values_list("department__name", flat=True).distinct())
    for dept in depts:
        if not dept:
            continue
        room, created = ChatRoom.objects.get_or_create(
            company=company, room_type="department", ref_key=dept,
            defaults={"name": dept})
        emp_users = User.objects.filter(
            id__in=Employee.objects.filter(
                company=company, status="active", department__name=dept,
                user__isnull=False).values_list("user_id", flat=True))
        for u in emp_users:
            ChatMember.objects.get_or_create(room=room, user=u)
        if created and emp_users:
            ChatMessage.objects.create(
                company=company, room=room, sender=emp_users[0],
                body=f"Welcome to the {dept} channel.")


def _notify(company, room, message):
    """Notify members: DMs always; groups only on @mention."""
    body = (message.body or "").lower()
    mentioned = set(re.findall(r"@(\w+)", body))
    for mem in room.memberships.select_related("user").exclude(user=message.sender):
        if mem.muted:
            continue
        if room.room_type != "dm" and mem.user.username.lower() not in mentioned:
            continue
        Notification.objects.create(
            company=company, user=mem.user,
            title=f"New message from {message.sender.get_full_name() or message.sender.username}",
            message=(message.body or "[file]")[:160],
            link=f"/c/{company.slug}/chat/?room={room.id}")


# ---------------------------------------------------------------- page
@company_access_required
def chat_home(request, company_slug):
    c = request.company
    ensure_department_rooms(c)
    ChatPresence.objects.update_or_create(
        user=request.user, defaults={"last_seen": timezone.now()})
    from core.modules import build_sidebar
    return render(request, "orbitchat/chat.html", {
        "company": c, "membership": request.membership,
        "sidebar": build_sidebar(request),
        "is_management": _is_management(request.membership),
        "active_room": request.GET.get("room") or "",
    })


# ---------------------------------------------------------------- APIs
@company_access_required
def api_rooms(request, company_slug):
    c = request.company
    rooms = (ChatRoom.objects.filter(company=c, is_archived=False,
                                     memberships__user=request.user)
             .distinct().prefetch_related("memberships__user"))
    rooms = sorted(rooms, key=lambda r: r.updated_at, reverse=True)
    return JsonResponse({"rooms": [_room_dict(r, request.user) for r in rooms]})


@company_access_required
@require_POST
def api_dm(request, company_slug):
    """Get-or-create a DM with another company user (management starts)."""
    c, me = request.company, request.user
    try:
        other = User.objects.get(pk=int(request.POST.get("user_id", 0)))
    except (User.DoesNotExist, ValueError):
        return JsonResponse({"error": "User not found"}, status=404)
    if not Membership.objects.filter(user=other, company=c, is_active=True).exists():
        return JsonResponse({"error": "User is not in this company"}, status=403)
    if other == me:
        return JsonResponse({"error": "Cannot message yourself"}, status=400)
    existing = (ChatRoom.objects.filter(company=c, room_type="dm",
                                        memberships__user=me)
                .filter(memberships__user=other).distinct().first())
    if existing:
        return JsonResponse({"room": _room_dict(existing, me)})
    if not _is_management(request.membership):
        return JsonResponse(
            {"error": "Only managers can start new direct messages"}, status=403)
    room = ChatRoom.objects.create(company=c, room_type="dm", created_by=me)
    ChatMember.objects.create(room=room, user=me, role="admin")
    ChatMember.objects.create(room=room, user=other)
    return JsonResponse({"room": _room_dict(room, me)})


@company_access_required
@require_POST
def api_group_create(request, company_slug):
    c, me = request.company, request.user
    if not _is_management(request.membership):
        return JsonResponse({"error": "Only managers can create groups"}, status=403)
    name = (request.POST.get("name") or "").strip()
    if not name:
        return JsonResponse({"error": "Group name required"}, status=400)
    room = ChatRoom.objects.create(company=c, room_type="group", name=name,
                                   description=request.POST.get("description", ""),
                                   created_by=me)
    ChatMember.objects.create(room=room, user=me, role="admin")
    for uid in request.POST.getlist("member_ids"):
        try:
            u = User.objects.get(pk=int(uid))
        except (User.DoesNotExist, ValueError):
            continue
        if Membership.objects.filter(user=u, company=c, is_active=True).exists():
            ChatMember.objects.get_or_create(room=room, user=u)
    return JsonResponse({"room": _room_dict(room, me)})


@company_access_required
@require_GET
def api_messages(request, company_slug, room_id):
    c = request.company
    room, mem = _room_or_404(c, room_id, request.user)
    qs = room.messages.filter(is_deleted=False).select_related(
        "sender", "reply_to", "reply_to__sender").prefetch_related(
        "reactions", "reads__user")
    after = request.GET.get("after")
    before = request.GET.get("before")
    if after:
        qs = qs.filter(id__gt=int(after))
    if before:
        qs = qs.filter(id__lt=int(before))
    msgs = list(qs.order_by("-created_at")[:50])
    msgs.reverse()
    return JsonResponse({"messages": [m.to_dict() for m in msgs]})


@company_access_required
@require_POST
def api_send(request, company_slug, room_id):
    c = request.company
    room, mem = _room_or_404(c, room_id, request.user)
    body = (request.POST.get("body") or "").strip()
    f = request.FILES.get("file")
    if not body and not f:
        return JsonResponse({"error": "Empty message"}, status=400)
    reply_to = None
    if request.POST.get("reply_to"):
        try:
            reply_to = ChatMessage.objects.get(pk=int(request.POST["reply_to"]),
                                               room=room, is_deleted=False)
        except (ChatMessage.DoesNotExist, ValueError):
            pass
    msg = ChatMessage.objects.create(
        company=c, room=room, sender=request.user, body=body[:4000],
        reply_to=reply_to,
        attachment=f, attachment_name=(f.name if f else ""),
        record_link=request.POST.get("record_link", "")[:120],
        record_label=request.POST.get("record_label", "")[:160],
    )
    room.save(update_fields=["updated_at"])  # bump ordering
    _notify(c, room, msg)
    return JsonResponse({"message": msg.to_dict()})


@company_access_required
@require_POST
def api_react(request, company_slug, message_id):
    c = request.company
    msg = get_object_or_404(ChatMessage, pk=message_id, company=c, is_deleted=False)
    _room_or_404(c, msg.room_id, request.user)
    reaction = request.POST.get("reaction", "")
    if reaction not in REACTIONS:
        return JsonResponse({"error": "Invalid reaction"}, status=400)
    obj, created = ChatReaction.objects.get_or_create(
        message=msg, user=request.user, reaction=reaction)
    if not created:
        obj.delete()
    msg.refresh_from_db()
    return JsonResponse({"message": msg.to_dict()})


@company_access_required
@require_POST
def api_delete_message(request, company_slug, message_id):
    c = request.company
    msg = get_object_or_404(ChatMessage, pk=message_id, company=c, is_deleted=False)
    room, mem = _room_or_404(c, msg.room_id, request.user)
    if msg.sender != request.user and mem.role != "admin" \
            and not _is_management(request.membership):
        return JsonResponse({"error": "Not allowed"}, status=403)
    msg.is_deleted = True
    msg.body = ""
    msg.save(update_fields=["is_deleted", "body"])
    return JsonResponse({"ok": True})


@company_access_required
@require_POST
def api_mark_read(request, company_slug, room_id):
    c = request.company
    room, mem = _room_or_404(c, room_id, request.user)
    now = timezone.now()
    mem.last_read_at = now
    mem.save(update_fields=["last_read_at"])
    unread = (room.messages.filter(is_deleted=False)
              .exclude(sender=request.user).exclude(reads__user=request.user))
    MessageRead.objects.bulk_create(
        [MessageRead(message=m, user=request.user) for m in unread[:200]],
        ignore_conflicts=True)
    return JsonResponse({"ok": True})


@company_access_required
@require_GET
def api_contacts(request, company_slug):
    c = request.company
    memberships = (Membership.objects.filter(company=c, is_active=True)
                   .select_related("user"))
    users = [m.user for m in memberships if m.user_id != request.user.id]
    online = _presence_map([u.id for u in users])
    depts = {}
    try:
        from shared.models import Employee
        for e in Employee.objects.filter(
                company=c, user__in=users, department__isnull=False
                ).select_related("department"):
            depts[e.user_id] = e.department.name
    except Exception:
        pass
    contacts = [_user_dict(u, online.get(u.id, False)) for u in users]
    for ct in contacts:
        ct["department"] = depts.get(ct["id"], "")
        ct["role"] = next((m.role for m in memberships if m.user_id == ct["id"]), "")
    contacts.sort(key=lambda x: (not x["online"], x["name"].lower()))
    return JsonResponse({"contacts": contacts,
                         "can_start_dm": _is_management(request.membership)})


@company_access_required
@require_GET
def api_search(request, company_slug):
    c = request.company
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"messages": []})
    room_ids = ChatRoom.objects.filter(
        company=c, memberships__user=request.user).values_list("id", flat=True)
    msgs = (ChatMessage.objects.filter(
        room_id__in=room_ids, is_deleted=False, body__icontains=q)
        .select_related("sender", "room").order_by("-created_at")[:30])
    out = []
    for m in msgs:
        d = m.to_dict()
        d["room_name"] = m.room.display_name()
        out.append(d)
    return JsonResponse({"messages": out})


@company_access_required
@require_GET
def api_updates(request, company_slug):
    """Polling endpoint: new messages + presence since a timestamp."""
    c = request.company
    since = request.GET.get("since")
    room_ids = list(ChatRoom.objects.filter(
        company=c, memberships__user=request.user).values_list("id", flat=True))
    msgs = []
    if since:
        try:
            from django.utils.dateparse import parse_datetime
            ts = parse_datetime(since)
            if ts:
                qs = (ChatMessage.objects.filter(
                    room_id__in=room_ids, created_at__gt=ts)
                    .select_related("sender", "reply_to", "reply_to__sender")
                    .prefetch_related("reactions", "reads__user")
                    .order_by("created_at")[:100])
                msgs = [m.to_dict() for m in qs]
        except Exception:
            pass
    total_unread = 0
    for mem in ChatMember.objects.filter(user=request.user, room_id__in=room_ids):
        total_unread += mem.unread_count()
    # typing indicators
    typing = {}
    for p in ChatPresence.objects.filter(
            typing_room_id__in=room_ids,
            typing_at__gte=timezone.now() - timedelta(seconds=6)
            ).select_related("user", "typing_room").exclude(user=request.user):
        typing.setdefault(p.typing_room_id, []).append(
            p.user.get_full_name() or p.user.username)
    return JsonResponse({
        "messages": msgs,
        "total_unread": total_unread,
        "typing": typing,
        "now": timezone.now().isoformat(),
    })


@company_access_required
@require_POST
def api_heartbeat(request, company_slug):
    room_id = request.POST.get("typing_in")
    vals = {"last_seen": timezone.now()}
    if room_id:
        try:
            rid = int(room_id)
            if ChatRoom.objects.filter(pk=rid, company=request.company,
                                       is_archived=False).exists():
                vals["typing_room_id"] = rid
                vals["typing_at"] = timezone.now()
        except (ValueError, TypeError):
            pass
    ChatPresence.objects.update_or_create(user=request.user, defaults=vals)
    return JsonResponse({"ok": True})


@company_access_required
@require_POST
def api_room_members(request, company_slug, room_id):
    c = request.company
    room, mem = _room_or_404(c, room_id, request.user)
    if mem.role != "admin" and not _is_management(request.membership):
        return JsonResponse({"error": "Only admins can manage members"}, status=403)
    action = request.POST.get("action")
    try:
        u = User.objects.get(pk=int(request.POST.get("user_id", 0)))
    except (User.DoesNotExist, ValueError):
        return JsonResponse({"error": "User not found"}, status=404)
    if action == "add":
        if not Membership.objects.filter(user=u, company=c, is_active=True).exists():
            return JsonResponse({"error": "User is not in this company"}, status=403)
        ChatMember.objects.get_or_create(room=room, user=u)
    elif action == "remove":
        if u == request.user:
            return JsonResponse({"error": "Cannot remove yourself"}, status=400)
        ChatMember.objects.filter(room=room, user=u).delete()
    else:
        return JsonResponse({"error": "Invalid action"}, status=400)
    return JsonResponse({"room": _room_dict(room, request.user)})


@company_access_required
def api_profile(request, company_slug):
    """Get/update own chat profile (avatar + title)."""
    from core.models import UserProfile
    prof, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        if "avatar" in request.FILES:
            f = request.FILES["avatar"]
            if f.size > 2 * 1024 * 1024:
                return JsonResponse({"error": "Image too large (max 2MB)"}, status=400)
            prof.avatar.save(f"user_{request.user.id}/{f.name}", f, save=True)
        title = request.POST.get("title")
        if title is not None:
            prof.title = title[:80]
            prof.save()
    return JsonResponse({
        "name": request.user.get_full_name() or request.user.username,
        "username": request.user.username,
        "title": prof.title,
        "avatar": prof.avatar.url if prof.avatar else "",
    })
