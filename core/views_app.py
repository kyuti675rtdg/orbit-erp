"""Serves the Flutter PWA (mobile app) shell at /app/.

The Flutter web build lives in static/app/ (served by WhiteNoise at
/static/app/*). This view serves its index.html at the pretty /app/ URL
so the PWA installs with start_url/scope /app/. Additive only: no existing
routes, APIs, static files, or media files are touched.
"""
import os

from django.contrib.staticfiles import finders
from django.http import HttpResponse, Http404


def flutter_app(request):
    path = finders.find("app/index.html")
    if not path or not os.path.isfile(path):
        raise Http404("Flutter app not built yet")
    with open(path, "rb") as f:
        return HttpResponse(f.read(), content_type="text/html")
