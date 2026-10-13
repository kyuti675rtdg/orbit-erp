from django.urls import include, path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("", views.company_hub, name="company_hub"),
    path("companies/new/", views.company_create, name="company_create"),
    # Flow: Login -> Select Company -> Company Dashboard -> Modules -> Submodules
    path("c/<slug:company_slug>/", views.company_dashboard, name="company_dashboard"),
    path("c/<slug:company_slug>/modules/", views.workspace, name="workspace"),
    path("c/<slug:company_slug>/fleet/", include("fleet.urls")),
    path("c/<slug:company_slug>/imports/", include("imports.urls")),
    path("c/<slug:company_slug>/exports/", include("exports.urls")),
    path("c/<slug:company_slug>/manufacturing/", include("manufacturing.urls")),
    path("c/<slug:company_slug>/rentals/", include("rentals.urls")),
    path("c/<slug:company_slug>/shared/", include("shared.urls")),
]
