from django.urls import path

from . import views

# Explicit names for sidebar / workspace links, then generic entity routes.
urlpatterns = [
    path("", views.fleet_dashboard, name="fleet_dashboard"),
    path("tracking/", views.tracking, name="fleet_tracking"),
    path("tracking/feed/", views.tracking_feed, name="fleet_tracking_feed"),
    path("reports/", views.reports, name="fleet_reports"),
    path("trips/<int:pk>/action/", views.trip_action, name="fleet_trip_action"),
    path("invoices/<int:pk>/pay/", views.invoice_pay, name="fleet_invoice_pay"),
    path("payroll/run/", views.payroll_run, name="fleet_payroll_run"),
    # friendly aliases used by the nav
    path("trips/", views.entity_list, {"entity": "trips"}, name="fleet_trips"),
    path("dispatches/", views.entity_list, {"entity": "dispatches"}, name="fleet_dispatches"),
    path("deliveries/", views.entity_list, {"entity": "deliveries"}, name="fleet_deliveries"),
    path("vehicles/", views.entity_list, {"entity": "vehicles"}, name="fleet_vehicles"),
    path("vehicle-documents/", views.entity_list, {"entity": "vehicle-documents"}, name="fleet_vehicle-documents"),
    path("routes/", views.entity_list, {"entity": "routes"}, name="fleet_routes"),
    path("geofences/", views.entity_list, {"entity": "geofences"}, name="fleet_geofences"),
    path("drivers/", views.entity_list, {"entity": "drivers"}, name="fleet_drivers"),
    path("driver-documents/", views.entity_list, {"entity": "driver-documents"}, name="fleet_driver-documents"),
    path("employees/", views.entity_list, {"entity": "employees"}, name="fleet_employees"),
    path("attendance/", views.entity_list, {"entity": "attendance"}, name="fleet_attendance"),
    path("payrolls/", views.entity_list, {"entity": "payrolls"}, name="fleet_payrolls"),
    path("fuel/", views.entity_list, {"entity": "fuel"}, name="fleet_fuel"),
    path("services/", views.entity_list, {"entity": "services"}, name="fleet_services"),
    path("inspections/", views.entity_list, {"entity": "inspections"}, name="fleet_inspections"),
    path("parts/", views.entity_list, {"entity": "parts"}, name="fleet_parts"),
    path("workshop-jobs/", views.entity_list, {"entity": "workshop-jobs"}, name="fleet_workshop-jobs"),
    path("part-issues/", views.entity_list, {"entity": "part-issues"}, name="fleet_part-issues"),
    path("expenses/", views.entity_list, {"entity": "expenses"}, name="fleet_expenses"),
    path("advances/", views.entity_list, {"entity": "advances"}, name="fleet_advances"),
    path("invoices/", views.entity_list, {"entity": "invoices"}, name="fleet_invoices"),
    path("payments/", views.entity_list, {"entity": "payments"}, name="fleet_payments"),
    path("alerts/", views.entity_list, {"entity": "alerts"}, name="fleet_alerts"),
    # generic CRUD
    path("<slug:entity>/new/", views.entity_create, name="fleet_entity_create"),
    path("<slug:entity>/<int:pk>/", views.entity_detail, name="fleet_entity_detail"),
    path("<slug:entity>/<int:pk>/edit/", views.entity_update, name="fleet_entity_update"),
    path("<slug:entity>/<int:pk>/delete/", views.entity_delete, name="fleet_entity_delete"),
    path("<slug:entity>/", views.entity_list, name="fleet_entity_list"),
]
