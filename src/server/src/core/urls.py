from django.urls import path

from core import views

# Core's trip-drawer htmx endpoints (the one shared drawer in the app). Mounted
# under `core/` by config.urls, so they resolve to /core/htmx/trip/... :
#   new/     – render the empty New Trip form into the drawer and open it
#   create/  – create the trip from that form, then close + refresh the table
#   <hashid> – open the existing trip's detail (keyed by its public hashid)
# The literal new/ and create/ routes MUST come before <str:hashid>, or the
# hashid pattern would swallow them. Features never reference these names — the
# detail drawer is opened via the <c-trip-drawer-button> component and the create
# flow via the app's nav actions, so features depend on core only, never on each
# other.
urlpatterns = [
    path("htmx/trip/new/", views.new_trip, name="core_trip_new"),
    path("htmx/trip/create/", views.create_trip, name="core_trip_create"),
    path("htmx/trip/<str:hashid>/", views.show_trip, name="core_trip_drawer"),
]
