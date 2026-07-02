from datetime import datetime

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render
from django_tables2 import RequestConfig

from core.models import Trip
from trips.tables import TripTable

# The trips feature is content + htmx endpoints — NOT a dashboard of its own. It
# owns the trip page content templates and the htmx views those templates call;
# the `app` dispatcher loads trips/pages/trips.html into its shell via nav_response.
#
# This module owns only the table + its filter endpoint. The trip *detail drawer*
# is NOT here: it's a core capability (the one shared drawer), opened via the
# core `core_trip_drawer` URL — the trips table, and the drivers/riders detail
# pages, all point there, so no feature depends on another feature.

# Pull every relation the trips table touches in one query — rider/driver names,
# their accounts (avatar), and the origin/destination places — so rendering a
# page of rows doesn't fan out into per-row lookups.
TRIP_SELECT_RELATED = (
    "rider__account",
    "driver__account",
    "origin",
    "destination",
)


def build_trips_table(request, queryset=None):
    """Configured TripTable over `queryset` (default: every trip).

    Exposed so a host dashboard can build the table for the initial full-page
    render without duplicating the trips query/pagination config — the host just
    calls this and hands the result to trips/pages/trips.html.
    """
    if queryset is None:
        queryset = Trip.objects.select_related(*TRIP_SELECT_RELATED)
    table = TripTable(queryset)
    RequestConfig(request, paginate={"per_page": 80}).configure(table)  # type: ignore[arg-type]
    return table


def table(request):
    """htmx filter endpoint: re-render only the table fragment.

    The trip-filter component issues an htmx GET here as the search text, date,
    or status changes and swaps the response into #trips_table — so the page
    shell and filter bar stay put while just the rows refresh.
    """
    query = request.GET.get("search", "").strip()
    date_filter = request.GET.get("date", "").strip()
    status_filter = request.GET.get("status", "").strip()

    qs = Trip.objects.select_related(*TRIP_SELECT_RELATED)

    # Text search — rider/driver names, origin/destination addresses, hashid.
    if query:
        qs = qs.filter(
            Q(rider__account__first_name__icontains=query)
            | Q(rider__account__last_name__icontains=query)
            | Q(driver__account__first_name__icontains=query)
            | Q(driver__account__last_name__icontains=query)
            | Q(origin__address__icontains=query)
            | Q(destination__address__icontains=query)
            | Q(hashid__icontains=query)
        )

    # Date — trips on the selected calendar day.
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            qs = qs.filter(date__date=filter_date)
        except ValueError:
            pass

    # Status — exact match against TripStatus values.
    if status_filter:
        qs = qs.filter(status=status_filter)

    return render(
        request,
        "trips/partials/trips_table.html",
        {"table": build_trips_table(request, qs)},
    )


def counts(request):
    """JSON map of {YYYY-MM-DD: trip_count} for the requested day window.

    The date-filter chip strip (c-trips.trip-filter) fetches this for its
    visible window so each day chip can show a badge with how many trips fall on
    that day. Only days that actually have trips appear in the response — the
    component treats a missing key as zero (no badge).

    Query params `start` and `end` bound the window inclusively (both YYYY-MM-DD).
    A missing/invalid bound is simply dropped, so the worst case is an unbounded
    count rather than an error.
    """
    qs = Trip.objects.all()

    for param, lookup in (("start", "date__date__gte"), ("end", "date__date__lte")):
        raw = request.GET.get(param, "").strip()
        if raw:
            try:
                qs = qs.filter(**{lookup: datetime.strptime(raw, "%Y-%m-%d").date()})
            except ValueError:
                pass

    rows = (
        qs.annotate(day=TruncDate("date"))
        .values("day")
        .annotate(n=Count("id"))
        .filter(day__isnull=False)
    )
    return JsonResponse({row["day"].isoformat(): row["n"] for row in rows})
