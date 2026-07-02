from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, render
from django_tables2 import RequestConfig

from core.dashboard import swap_content
from core.models import OPEN_TRIP_STATUSES, Rider, TripStatus
from riders.tables import RiderTable

# The riders feature is content + htmx endpoints — NOT a dashboard of its own,
# exactly like `trips` and `drivers`. It owns the rider page content templates and
# the htmx views those templates call; the `app` dispatcher loads
# riders/pages/riders.html into its shell via nav_response.
#
# Selecting a rider does NOT open a drawer — it transitions the main content
# (#app_content) to the rider's detail PAGE. The only drawer in the app is the
# shared trip drawer (core_trip_drawer), which the detail page's recent-trip rows
# open — so this feature depends on core only, never on trips.

# A rider row needs the linked account (avatar / name / contact) in one query,
# so pull it via select_related rather than fanning out per row.
RIDER_SELECT_RELATED = ("account",)


def _rider_queryset():
    """Every rider with its account and the trip data the table/filter read.

    trips_total — all trips the rider has taken (drives the Active/Inactive
                  activity filter).
    trips_open  — trips still in flight (OPEN_TRIP_STATUSES).
    last_trip   — the most recent trip's date, shown in the Last Trip column.

    distinct=True on each Count keeps the filtered aggregates from multiplying
    each other across the joined trips rows.
    """
    return Rider.objects.select_related(*RIDER_SELECT_RELATED).annotate(
        trips_total=Count("trips", distinct=True),
        trips_open=Count(
            "trips", filter=Q(trips__status__in=OPEN_TRIP_STATUSES), distinct=True
        ),
        last_trip=Max("trips__date"),
    )


def build_riders_table(request, queryset=None):
    """Configured RiderTable over `queryset` (default: every rider).

    Exposed so the host dashboard can build the table for the initial full-page
    render without duplicating the query/pagination config — mirrors
    trips.views.build_trips_table.
    """
    if queryset is None:
        queryset = _rider_queryset()
    table = RiderTable(queryset)
    RequestConfig(request, paginate={"per_page": 80}).configure(table)  # type: ignore[arg-type]
    return table


def table(request):
    """htmx filter endpoint: re-render only the riders table fragment.

    The rider-filter component issues an htmx GET here as the search text or
    activity changes and swaps the response into #riders_table — so the page
    shell and filter bar stay put while just the rows refresh.
    """
    query = request.GET.get("search", "").strip()
    activity = request.GET.get("activity", "").strip()

    qs = _rider_queryset()

    # Text search — rider name, email, phone.
    if query:
        qs = qs.filter(
            Q(account__first_name__icontains=query)
            | Q(account__last_name__icontains=query)
            | Q(account__email__icontains=query)
            | Q(account__phone__icontains=query)
        )

    # Activity — whether the rider has ever taken a trip.
    if activity == "active":
        qs = qs.filter(trips_total__gt=0)
    elif activity == "inactive":
        qs = qs.filter(trips_total=0)

    return render(
        request,
        "riders/partials/riders_table.html",
        {"table": build_riders_table(request, qs)},
    )


def index(request):
    """htmx: re-render the riders list (filter + table) into #app_content.

    Backs the rider detail page's "Back to Riders" button so a feature page can
    return to its own list without referencing the host app's nav URL (app_riders)
    — keeping riders dependent on core only.
    """
    return swap_content(
        request,
        "riders/pages/riders.html",
        {"table": build_riders_table(request)},
    )


def detail(request, pk):
    """htmx: transition #app_content to the rider's detail PAGE (not a drawer).

    Selecting a rider swaps the main content to their profile + trip history. The
    recent-trips rows there open the one shared trip drawer via the core
    `core_trip_drawer` URL, so this feature never depends on trips.
    """
    rider = get_object_or_404(Rider.objects.select_related("account"), pk=pk)
    stats = rider.trips.aggregate(
        total=Count("id"),
        open=Count("id", filter=Q(status__in=OPEN_TRIP_STATUSES)),
        completed=Count("id", filter=Q(status=TripStatus.completed)),
    )
    recent_trips = rider.trips.select_related(
        "driver__account", "origin", "destination"
    ).order_by("-date")[:8]
    return swap_content(
        request,
        "riders/pages/rider_detail.html",
        {"rider": rider, "stats": stats, "recent_trips": recent_trips},
    )
