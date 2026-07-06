from django.urls import path

from core import views

# Core's trip-drawer htmx endpoints (the one shared drawer in the app). Mounted
# under `core/` by config.urls, so they resolve to /core/htmx/trip/... :
#   new/           – render the empty New Trip form into the drawer and open it
#   create/        – create the trip from that form, then close + refresh the table
#   plans/         – re-render the New Trip form's service-plan <option>s for the
#                    rider identified by ?email=… (defaults + their private plans)
#   <hashid>/      – open the existing trip's detail (keyed by its public hashid)
#   <hashid>/save/ – save edits made in that detail drawer, then close + refresh
# The literal new/, create/ and plans/ routes MUST come before <str:hashid>, or
# the hashid pattern would swallow them; <hashid>/save/ is safe after <hashid>/
# since Django tries patterns in order and neither is a prefix-only match of the
# other. Features never reference these names — the detail drawer is opened via
# the <c-trip-drawer-button> component and the create flow via the app's nav
# actions, so features depend on core only, never on each other.
urlpatterns = [
    path("htmx/trip/new/", views.new_trip, name="core_trip_new"),
    path("htmx/trip/create/", views.create_trip, name="core_trip_create"),
    path("htmx/trip/plans/", views.trip_plans, name="core_trip_plans"),
    path("htmx/trip/<str:hashid>/save/", views.update_trip, name="core_trip_update"),
    path("htmx/trip/<str:hashid>/", views.show_trip, name="core_trip_drawer"),
    # Live driver position for the trip map's poll (c-trip.map). Keyed by
    # ?driver=<id>; its own /htmx/driver-location/ path never collides with the
    # trip routes above.
    path(
        "htmx/driver-location/",
        views.driver_location,
        name="core_driver_location",
    ),
]
