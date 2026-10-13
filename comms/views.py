"""Notification inbox: JSON feed for the topbar bell + mark-read."""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from core.views import company_access_required

from shared.models import Notification


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


# ------------------------------------------------------------ communication hub
def _el(company, url_name, entity=None):
    from django.urls import reverse
    kw = {"company_slug": company.slug}
    if entity:
        kw["entity"] = entity
    return reverse(url_name, kwargs=kw)


@company_access_required
def dashboard(request, company_slug):
    from django.utils import timezone
    from core import dashboards as D
    from core.modules import build_sidebar
    from shared.models import Announcement, Notification
    from . import models as m

    c = request.company
    today = timezone.now().date()
    unread = Notification.objects.filter(company=c, user=request.user, is_read=False).count()
    open_tasks = m.Task.objects.filter(company=c).exclude(status="done")
    my_tasks = open_tasks.filter(assigned_to=request.user).count()
    upcoming = m.Meeting.objects.filter(company=c, start__date__gte=today).order_by("start")[:8]
    recent_ann = Announcement.objects.filter(company=c, is_active=True).order_by("-publish_date")[:5]
    kpis = [
        D.kpi("Unread Notifications", f"{unread}", "bell", "orange", sub="in your inbox"),
        D.kpi("Open Tasks", f"{open_tasks.count()}", "clipboard", "blue",
              sub=f"{my_tasks} assigned to me"),
        D.kpi("Upcoming Meetings", f"{m.Meeting.objects.filter(company=c, start__date__gte=today).count()}",
              "calendar", "green", sub="scheduled"),
    ]
    cfg = {
        "title": "Collaboration Hub", "subtitle": "Tasks, meetings & announcements",
        "kpis": kpis,
        "tables": [
            {"title": "My Open Tasks", "headers": ["Task", "Due", "Priority"],
             "rows": [[t.title, str(t.due_date or "—"), t.get_priority_display()]
                      for t in open_tasks.filter(assigned_to=request.user)[:8]],
             "link": _el(c, "comms_entity_list", "tasks"), "link_label": "All tasks"},
            {"title": "Upcoming Meetings", "headers": ["Meeting", "When", "Where"],
             "rows": [[mt.title, mt.start.strftime("%b %d %H:%M"), mt.location or "—"]
                      for mt in upcoming],
             "link": _el(c, "comms_entity_list", "meetings"), "link_label": "All meetings"},
            {"title": "Latest Announcements", "headers": ["Title", "Published"],
             "rows": [[a.title, str(a.publish_date)] for a in recent_ann],
             "link": _el(c, "comms_entity_list", "announcements"), "link_label": "All announcements"},
        ],
        "actions": [
            {"label": "New Task", "icon": "plus", "url": _el(c, "comms_entity_create", "tasks")},
            {"label": "Schedule Meeting", "icon": "plus", "url": _el(c, "comms_entity_create", "meetings")},
            {"label": "New Announcement", "icon": "plus", "url": _el(c, "comms_entity_create", "announcements")},
        ],
    }
    return D.render_module_dashboard(request, c, cfg)
