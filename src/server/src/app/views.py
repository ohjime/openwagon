from app.dashboard import dashboard
from drivers.views import build_drivers_table
from riders.views import build_riders_table
from trips.views import build_trips_table

# The `app` dashboard views (the dispatcher). Built on the core shell: each
# navigable page is a real URL served by the dashboard's
# nav_response (full shell on a direct hit, fragment on an htmx swap). The header
# label and tab title are fixed by the Dashboard instance, so views never pass a
# title — they pick a template and hand it data.
#
# The Drivers / Riders / Trips pages are all the same shape: `app` is a thin
# loader that builds the feature's initial table via the feature's own helper and
# hands the feature's content template to nav_response. The feature owns the
# template and every htmx endpoint it calls (mounted under <feature>/htmx/ in
# config.urls), so `app` never references a feature URL.


def index(request):
    """Landing page: the shell with nothing selected."""
    return dashboard.page(request, "app/home.html")


def drivers(request):
    """Load the drivers feature's content (table + filters) into the shell."""
    return dashboard.nav_response(
        request,
        "drivers/pages/drivers.html",
        {"table": build_drivers_table(request)},
        key="drivers",
    )


def riders(request):
    """Load the riders feature's content (table + filters) into the shell."""
    return dashboard.nav_response(
        request,
        "riders/pages/riders.html",
        {"table": build_riders_table(request)},
        key="riders",
    )


def trips(request):
    """Load the trips feature's content into the dispatcher shell."""
    return dashboard.nav_response(
        request,
        "trips/pages/trips.html",
        {"table": build_trips_table(request)},
        key="trips",
    )
