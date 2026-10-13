from django.urls import include, path

from . import push_views, views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("", views.company_hub, name="company_hub"),
    path("companies/new/", views.company_create, name="company_create"),
    path("offline/", push_views.offline, name="offline"),
    path("sw.js", push_views.service_worker, name="service_worker"),
    # Web push + notification preferences (PWA)
    path("push/vapid-key/", push_views.vapid_key, name="push_vapid_key"),
    path("push/subscribe/", push_views.subscribe, name="push_subscribe"),
    path("push/unsubscribe/", push_views.unsubscribe, name="push_unsubscribe"),
    path("push/status/", push_views.subscription_status, name="push_status"),
    path("notifications/preferences/", push_views.preferences, name="push_preferences"),
    path("", include("monitoring.urls")),
    # Flow: Login -> Select Company -> Company Dashboard -> Modules -> Submodules
    path("c/<slug:company_slug>/", views.company_dashboard, name="company_dashboard"),
    path("c/<slug:company_slug>/modules/", views.workspace, name="workspace"),
    path("c/<slug:company_slug>/fleet/", include("fleet.urls")),
    path("c/<slug:company_slug>/imports/", include("imports.urls")),
    path("c/<slug:company_slug>/exports/", include("exports.urls")),
    path("c/<slug:company_slug>/manufacturing/", include("manufacturing.urls")),
    path("c/<slug:company_slug>/rentals/", include("rentals.urls")),
    path("c/<slug:company_slug>/coffee/", include("coffee.urls")),
    # Enterprise modules (centralized HR / Finance / Admin / Comms / Executive)
    path("c/<slug:company_slug>/hr/", include("hr.urls")),
    path("c/<slug:company_slug>/finance/", include("finance.urls")),
    path("c/<slug:company_slug>/admin/", include("administration.urls")),
    path("c/<slug:company_slug>/comms/", include("comms.urls")),
    path("c/<slug:company_slug>/exec/", include("executive.urls")),
    # Request workflow + messaging modules
    path("c/<slug:company_slug>/req/", include("req.urls")),
    path("c/<slug:company_slug>/inbox/", include("inbox.urls")),
    path("c/<slug:company_slug>/chat/", include("orbitchat.urls")),
]
