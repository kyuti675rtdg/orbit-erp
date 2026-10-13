"""Notification inbox: JSON feed for the topbar bell + mark-read."""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from core.views import company_access_required

from .models import Notification


@company_access_required
def notifications_feed(request, company_slug):
    items = (Notification.objects
             .filter(company=request.company, user=request.user)
             .order_by("-created_at")[:15])
    return JsonResponse({
        "unread": Notification.objects.filter(
            company=request.company, user=request.user, is_read=False).count(),
        "items": [{"id": n.id, "title": n.title, "message": n.message,
                   "link": n.link, "is_read": n.is_read,
                   "time": n.created_at.strftime("%b %d, %H:%M")} for n in items],
    })


@company_access_required
@require_POST
def notifications_read(request, company_slug):
    Notification.objects.filter(
        company=request.company, user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})


@company_access_required
@require_POST
def notification_open(request, company_slug, pk):
    n = get_object_or_404(Notification, company=request.company,
                          user=request.user, pk=pk)
    n.is_read = True
    n.save(update_fields=["is_read"])
    return JsonResponse({"ok": True, "link": n.link})
