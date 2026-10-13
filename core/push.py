"""Web push delivery for Orbit ERP (VAPID via pywebpush)."""
import json
import logging
from datetime import datetime

from django.conf import settings

log = logging.getLogger(__name__)


def vapid_configured():
    return bool(getattr(settings, "VAPID_PUBLIC_KEY", "")
                and getattr(settings, "VAPID_PRIVATE_KEY", ""))


def _in_quiet_hours(pref):
    if not (pref.quiet_hours_start and pref.quiet_hours_end):
        return False
    now = datetime.now().time()
    s, e = pref.quiet_hours_start, pref.quiet_hours_end
    return (s <= now <= e) if s <= e else (now >= s or now <= e)


def push_enabled_for(user, category="system"):
    """Check the user's preference + quiet hours for a category."""
    from .models import NotificationPreference
    try:
        pref = user.notification_pref
    except NotificationPreference.DoesNotExist:
        return True
    if not pref.enabled(category):
        return False
    return not _in_quiet_hours(pref)


def send_push(user, title, body="", url="/", category="system", tag=None):
    """Send a web push to all of the user's subscribed devices.

    Respects per-category preferences and quiet hours. Dead endpoints
    (410/404) are removed automatically. Returns number delivered.
    """
    from .models import PushSubscription
    if not vapid_configured():
        return 0
    if not push_enabled_for(user, category):
        return 0
    subs = list(PushSubscription.objects.filter(user=user))
    if not subs:
        return 0
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        log.warning("pywebpush not installed")
        return 0
    payload = json.dumps({
        "title": title, "body": (body or "")[:180],
        "url": url, "tag": tag or f"orbit-{category}",
    })
    vapid_claims = {"sub": getattr(settings, "VAPID_EMAIL", "mailto:admin@orbit.et")}
    sent = 0
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=vapid_claims,
            )
            sent += 1
        except Exception as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):
                sub.delete()
                log.info("removed dead push subscription %s", sub.pk)
            else:
                log.warning("push failed for %s: %s", sub.pk, e)
    return sent
