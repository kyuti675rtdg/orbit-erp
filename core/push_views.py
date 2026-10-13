"""Web push subscription API + notification preferences UI."""
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .models import NotificationPreference, PushSubscription
from .push import vapid_configured


@require_GET
def vapid_key(request):
    return JsonResponse({"publicKey": getattr(settings, "VAPID_PUBLIC_KEY", ""),
                         "configured": vapid_configured()})


@login_required
@require_POST
def subscribe(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid JSON"}, status=400)
    endpoint = (data.get("endpoint") or "")[:500]
    keys = data.get("keys") or {}
    if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
        return JsonResponse({"error": "incomplete subscription"}, status=400)
    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={"user": request.user,
                  "p256dh": keys["p256dh"][:200],
                  "auth": keys["auth"][:100],
                  "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255]})
    return JsonResponse({"ok": True})


@login_required
@require_POST
def unsubscribe(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        data = {}
    endpoint = data.get("endpoint") or ""
    PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    return JsonResponse({"ok": True})


@login_required
@require_GET
def subscription_status(request):
    n = PushSubscription.objects.filter(user=request.user).count()
    try:
        pref = request.user.notification_pref
    except NotificationPreference.DoesNotExist:
        pref = None
    return JsonResponse({
        "devices": n,
        "vapid_configured": vapid_configured(),
        "prefs": ({c: getattr(pref, c, True)
                   for c, _ in NotificationPreference.CATEGORIES}
                  if pref else {}),
    })


@login_required
def preferences(request):
    pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        for cat, _ in NotificationPreference.CATEGORIES:
            setattr(pref, cat, request.POST.get(f"pref_{cat}") == "on")
        pref.quiet_hours_start = request.POST.get("quiet_start") or None
        pref.quiet_hours_end = request.POST.get("quiet_end") or None
        pref.save()
        from django.contrib import messages
        messages.success(request, "Notification preferences saved.")
        from django.shortcuts import redirect
        return redirect("push_preferences")
    from core.modules import build_sidebar
    sidebar = None
    company = getattr(request, "company", None)
    if company:
        try:
            sidebar = build_sidebar(request)
        except Exception:
            sidebar = None
    prefs = {cat: getattr(pref, cat, True) for cat, _ in NotificationPreference.CATEGORIES}
    return render(request, "core/push_preferences.html", {
        "pref": pref,
        "prefs": prefs,
        "categories": NotificationPreference.CATEGORIES,
        "sidebar": sidebar,
        "company": company,
        "membership": getattr(request, "membership", None),
        "my_companies": request.user.memberships.select_related("company").filter(
            is_active=True),
    })


def offline(request):
    return render(request, "core/offline.html")
