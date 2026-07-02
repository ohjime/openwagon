from django.urls import path

from app import views
from app.api import api_urls

# The `app` URL tree. `app` is the concrete application: it owns the django-ninja
# API (api.py) and the dispatcher dashboard (merged up from the old `app.dispatch`
# sub-app — there are no longer nested features inside `app`). config.urls mounts
# this whole tree at the site root, so the dashboard lives at "/" and "/users/".
#
# NOTE: the API stays at /api/ — the CORS rule (^/api/.*$) and the Flutter client
# both depend on that path. Keep `name=` in sync with the `key=` each view passes
# and the `key=` on its <c-dashboard.nav-item>/<c-dashboard.nav-child> in app/base.html.
urlpatterns = [
    path("api/", api_urls, name="api"),
    path("", views.index, name="app_index"),
    # The navigable Drivers / Riders / Trips pages — `app` loads each feature's
    # content template into this dashboard's shell. The feature htmx endpoints
    # live in <feature>.urls (mounted in config.urls under <feature>/htmx/), not
    # here. Django falls through to these page routes because those includes only
    # match the /htmx/* sub-paths.
    path("drivers/", views.drivers, name="app_drivers"),
    path("riders/", views.riders, name="app_riders"),
    path("trips/", views.trips, name="app_trips"),
]
