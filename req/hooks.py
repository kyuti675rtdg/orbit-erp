"""Request workflow helpers: approver routing, notifications, activity log."""
from django.utils import timezone

APPROVER_ROLES = ["owner", "admin", "manager"]
_ROLE_RANK = {"owner": 0, "admin": 1, "manager": 2}


def _notify(company, user, title, message, link=""):
    if not user:
        return
    try:
        from shared.models import Notification
        Notification.objects.get_or_create(
            company=company, user=user, title=title, message=message,
            defaults={"link": link},
        )
    except Exception:
        pass


def pick_approver(company, requester):
    """First owner/admin/manager (by hierarchy) excluding the requester."""
    from core.models import Membership
    candidates = list(
        Membership.objects.filter(company=company, is_active=True)
        .exclude(user=requester)
        .select_related("user")
    )
    candidates.sort(key=lambda m: _ROLE_RANK.get(m.role, 99))
    return candidates[0].user if candidates else None


def approver_users(company, exclude=None):
    """All users able to decide on requests."""
    from core.models import Membership
    qs = Membership.objects.filter(
        company=company, is_active=True, role__in=APPROVER_ROLES
    ).select_related("user")
    if exclude:
        qs = qs.exclude(user=exclude)
    seen, out = set(), []
    for m in qs:
        if m.user_id not in seen:
            seen.add(m.user_id)
            out.append(m.user)
    return out


def can_decide(membership, req):
    """May this member approve/reject/return this request?"""
    if membership.role in APPROVER_ROLES:
        return True
    return bool(req.current_approver_id and req.current_approver_id == membership.user_id)


def log_event(company, req, actor, action, notes=""):
    from .models import RequestEvent
    return RequestEvent.objects.create(
        company=company, request=req, actor=actor, action=action, notes=notes or ""
    )


def on_submitted(company, req, actor):
    approver = pick_approver(company, req.requester)
    req.current_approver = approver
    req.save(update_fields=["current_approver"])
    log_event(company, req, actor, "submitted",
              f"Submitted for approval ({req.get_request_type_display()}).")
    link = f"/c/{company.slug}/req/requests/{req.pk}/"
    notified = set()
    for user in ([approver] if approver else []) + approver_users(company, exclude=req.requester):
        if user.id not in notified:
            notified.add(user.id)
            _notify(company, user, f"New request: {req.ref_no}",
                    f"{req.requester.username} submitted '{req.title}' "
                    f"({req.get_request_type_display()}).", link=link)


def on_decided(company, req, actor, action):
    req.decided_by = actor
    req.decided_at = timezone.now()
    req.save(update_fields=["decided_by", "decided_at"])
    log_event(company, req, actor, action, req.review_notes)
    link = f"/c/{company.slug}/req/requests/{req.pk}/"
    _notify(company, req.requester, f"Request {action}: {req.ref_no}",
            f"Your request '{req.title}' was {action}.", link=link)


def on_returned(company, req, actor):
    req.decided_by = actor
    req.decided_at = timezone.now()
    req.save(update_fields=["decided_by", "decided_at"])
    log_event(company, req, actor, "returned", req.review_notes)
    link = f"/c/{company.slug}/req/requests/{req.pk}/"
    _notify(company, req.requester, f"Changes requested: {req.ref_no}",
            f"'{req.title}' was returned for changes. Please revise and resubmit.",
            link=link)


def on_cancelled(company, req, actor):
    log_event(company, req, actor, "cancelled", "Request cancelled.")
    if req.current_approver and req.current_approver_id != req.requester_id:
        _notify(company, req.current_approver, f"Request cancelled: {req.ref_no}",
                f"'{req.title}' was cancelled by {actor.username}.")
