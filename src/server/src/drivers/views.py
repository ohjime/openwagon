from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django_tables2 import RequestConfig

from core.dashboard import swap_content
from core.models import (
    ONTRIP_TRIP_STATUSES,
    OPEN_TRIP_STATUSES,
    Driver,
    TripStatus,
)
from drivers.tables import DriverTable

# The drivers feature is content + htmx endpoints — NOT a dashboard of its own,
# exactly like `trips`. It owns the driver page content templates and the htmx
# views those templates call; the `app` dispatcher loads drivers/pages/drivers.html
# into its shell via nav_response, so the host stays a thin loader.
#
# Selecting a driver does NOT open a drawer — it transitions the main content
# (#app_content) to the driver's detail PAGE. The only drawer in the app is the
# shared trip drawer (core_trip_drawer), which the detail page's recent-trip rows
# open — so this feature depends on core only, never on trips.

# A driver row needs the linked account (avatar / name / contact) in one query,
# so pull it via select_related rather than fanning out per row.
DRIVER_SELECT_RELATED = ("account",)


def _driver_queryset():
    """Every driver with its account and the trip counts the table/filter read.

    trips_total  — all trips the driver is on.
    trips_open   — trips still in flight (OPEN_TRIP_STATUSES).
    trips_active — trips where the driver is in a vehicle right now
                   (ONTRIP_TRIP_STATUSES); this drives the Available/On-Trip
                   status badge and the availability filter.

    distinct=True on each Count keeps the three filtered aggregates from
    multiplying each other across the joined trips rows.
    """
    return Driver.objects.select_related(*DRIVER_SELECT_RELATED).annotate(
        trips_total=Count("trips", distinct=True),
        trips_open=Count(
            "trips", filter=Q(trips__status__in=OPEN_TRIP_STATUSES), distinct=True
        ),
        trips_active=Count(
            "trips", filter=Q(trips__status__in=ONTRIP_TRIP_STATUSES), distinct=True
        ),
    )


def build_drivers_table(request, queryset=None):
    """Configured DriverTable over `queryset` (default: every driver).

    Exposed so the host dashboard can build the table for the initial full-page
    render without duplicating the query/pagination config — mirrors
    trips.views.build_trips_table.
    """
    if queryset is None:
        queryset = _driver_queryset()
    table = DriverTable(queryset)
    RequestConfig(request, paginate={"per_page": 80}).configure(table)  # type: ignore[arg-type]
    return table


def table(request):
    """htmx filter endpoint: re-render only the drivers table fragment.

    The driver-filter component issues an htmx GET here as the search text or
    availability changes and swaps the response into #drivers_table — so the page
    shell and filter bar stay put while just the rows refresh.
    """
    query = request.GET.get("search", "").strip()
    availability = request.GET.get("availability", "").strip()

    qs = _driver_queryset()

    # Text search — driver name, email, phone.
    if query:
        qs = qs.filter(
            Q(account__first_name__icontains=query)
            | Q(account__last_name__icontains=query)
            | Q(account__email__icontains=query)
            | Q(account__phone__icontains=query)
        )

    # Availability — derived from whether the driver is on a trip right now.
    if availability == "on_trip":
        qs = qs.filter(trips_active__gt=0)
    elif availability == "available":
        qs = qs.filter(trips_active=0)

    return render(
        request,
        "drivers/partials/drivers_table.html",
        {"table": build_drivers_table(request, qs)},
    )


def index(request):
    """htmx: re-render the drivers list (filter + table) into #app_content.

    Backs the driver detail page's "Back to Drivers" button so a feature page can
    return to its own list without referencing the host app's nav URL (app_drivers)
    — keeping drivers dependent on core only.
    """
    return swap_content(
        request,
        "drivers/pages/drivers.html",
        {"table": build_drivers_table(request)},
    )


def detail(request, pk):
    """htmx: transition #app_content to the driver's detail PAGE (not a drawer).

    Selecting a driver swaps the main content to their profile + trip history. The
    recent-trips rows there open the one shared trip drawer via the core
    `core_trip_drawer` URL, so this feature never depends on trips.
    """
    driver = get_object_or_404(Driver.objects.select_related("account"), pk=pk)
    stats = driver.trips.aggregate(
        total=Count("id"),
        open=Count("id", filter=Q(status__in=OPEN_TRIP_STATUSES)),
        completed=Count("id", filter=Q(status=TripStatus.completed)),
    )
    recent_trips = driver.trips.select_related(
        "rider__account", "origin", "destination"
    ).order_by("-date")[:8]
    return swap_content(
        request,
        "drivers/pages/driver_detail.html",
        {"driver": driver, "stats": stats, "recent_trips": recent_trips},
    )
