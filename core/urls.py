from django.urls import include, path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("", views.company_hub, name="company_hub"),
    path("companies/new/", views.company_create, name="company_create"),
    path("", include("monitoring.urls")),
    # Flow: Login -> Select Company -> Company Dashboard -> Modules -> Submodules
    path("c/<slug:company_slug>/", views.company_dashboard, name="company_dashboard"),
    path("c/<slug:company_slug>/modules/", views.workspace, name="workspace"),
    path("c/<slug:company_slug>/fleet/", include("fleet.urls")),
    path("c/<slug:company_slug>/imports/", include("imports.urls")),
    path("c/<slug:company_slug>/exports/", include("exports.urls")),
    path("c/<slug:company_slug>/manufacturing/", include("manufacturing.urls")),
    path("c/<slug:company_slug>/rentals/", include("rentals.urls")),
    # Enterprise modules (centralized HR / Finance / Admin / Comms / Executive)
    path("c/<slug:company_slug>/hr/", include("hr.urls")),
    path("c/<slug:company_slug>/finance/", include("finance.urls")),
    path("c/<slug:company_slug>/admin/", include("administration.urls")),
    path("c/<slug:company_slug>/comms/", include("comms.urls")),
    path("c/<slug:company_slug>/exec/", include("executive.urls")),
    # Request workflow + messaging modules
    path("c/<slug:company_slug>/req/", include("req.urls")),
    path("c/<slug:company_slug>/inbox/", include("inbox.urls")),
    path("c/<slug:company_slug>/comm/", include("communication.urls")),
]
