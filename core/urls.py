from django.urls import include, path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("", views.company_hub, name="company_hub"),
    path("companies/new/", views.company_create, name="company_create"),
    path("c/<slug:company_slug>/", views.workspace, name="workspace"),
    path("c/<slug:company_slug>/fleet/", include("fleet.urls")),
]
