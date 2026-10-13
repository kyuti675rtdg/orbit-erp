"""Record login sessions for security monitoring."""
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import LoginSession


@receiver(user_logged_in)
def record_login(sender, request, user, **kwargs):
    try:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = (xff.split(",")[0].strip() if xff else None) or request.META.get("REMOTE_ADDR")
        LoginSession.objects.create(
            user=user, ip_address=ip or None,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255])
    except Exception:
        pass
