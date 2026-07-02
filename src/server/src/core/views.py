import json

from django.db import IntegrityError
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.models import Account, Driver, Place, Rider, Trip, TripStatus

# Core owns exactly ONE drawer: the trip detail drawer. It is deliberately the
# only thing in the whole app that opens the shell's base drawer (#trip_drawer) —
# there is no generic "open any template in a drawer" helper, so a feature can
# never slide arbitrary content over the page.
#
# Features never wire the drawer themselves: they drop a <c-trip-drawer-button>
# (a core cotton component) which is the single place that knows this view's URL
# and the drawer's target. So the trips table and the drivers/riders detail pages
# open a trip just by passing a hashid to that component — depending on core only,
# never on each other.

# Pull every relation the trip drawer renders in one query (rider/driver accounts
# for the cards, origin/destination places for the route), so opening the drawer
# is a single round-trip.
TRIP_SELECT_RELATED = (
    "rider__account",
    "driver__account",
    "origin",
    "destination",
)


def show_trip(request, hashid):
    """Render the trip detail into the shell's base drawer and slide it open.

    The sole drawer opener. Keyed by the trip's public hashid (the T-… id shown
    in the UI), not a sequential pk. It retargets #trip_drawer_content and fires
    `show-drawer`, but is hard-wired to the one core template — there is no
    template-path parameter, so nothing can open a drawer with other content.
    """
    trip = get_object_or_404(
        Trip.objects.select_related(*TRIP_SELECT_RELATED), hashid=hashid
    )
    response = render(
        request,
        "core/trip_detail.html",
        {
            "trip": trip,
            "status_choices": TripStatus.choices,
            "drivers": _drivers_qs(),
            # The customer's own pickup/destination history for the history button.
            "recent_pickups": _recent_places("origin", rider=trip.rider),
            "recent_destinations": _recent_places("destination", rider=trip.rider),
        },
    )
    response["HX-Retarget"] = "#trip_drawer_content"
    response["HX-Reswap"] = "innerHTML"
    response["HX-Trigger-After-Swap"] = "show-drawer"
    return response


# The New Trip drawer — the second body the shared #trip_drawer can hold. Unlike
# show_trip, which only displays an existing trip, these two views CREATE one:
# new_trip renders the empty form into the drawer; create_trip turns a submission
# into a Trip. The create flow resolves the rider by email (these guests never
# sign up through Firebase/mobile, so the email IS their uid — there is no
# Firebase uid — and they have no photo, so their avatar is a DiceBear glyph
# generated from the email at render time; see Account.avatar_src), resolves the
# picked driver and the origin/destination Places, makes the Trip, then closes
# the drawer and refreshes the trips table via the trip-created event. It is
# still hard-wired to one template — there is no template-path parameter, same as
# show_trip.


def _recent_places(field, *, rider=None, limit=8):
    """Most-recently-used distinct Places at one trip end, newest first.

    `field` is "origin" or "destination". Scoped to a rider when given (a
    customer's own pickup/destination history — what the history button shows on
    an existing trip), else global (the New Trip form, where no rider is picked
    yet).

    Efficiency: a single indexed GROUP BY collapses many trips to the distinct
    place used at that end, keyed by the latest trip date, then takes the top N
    place ids. A second `in_bulk` loads exactly those N Places (no N+1), and we
    re-order to match the recency ranking. Backed by a composite index on
    Trip(rider, <field>, date) so the group + sort is index-only — it never
    walks the full trips table. Two queries total, independent of trip volume.
    """
    trips = Trip.objects.all()
    if rider is not None:
        trips = trips.filter(rider=rider)
    rows = (
        trips.filter(date__isnull=False)
        .values(field)  # GROUP BY origin_id / destination_id
        .annotate(last_used=Max("date"))
        .order_by("-last_used")[:limit]
    )
    place_ids = [row[field] for row in rows]
    by_id = Place.objects.in_bulk(place_ids)
    return [by_id[pid] for pid in place_ids if pid in by_id]


def _drivers_qs():
    """Drivers for the form's combobox — account preloaded, name-ordered."""
    return Driver.objects.select_related("account").order_by(
        "account__first_name", "account__last_name"
    )


def _riders_qs():
    """Riders for the form's existing-customer search — account preloaded,
    name-ordered. Picking one fills the rider fields client-side; on submit the
    create flow reuses the matching Account by its (unique) email."""
    return Rider.objects.select_related("account").order_by(
        "account__first_name", "account__last_name"
    )


def _render_new_trip(request, *, error=None, form_data=None, open_drawer=False):
    """Render the New Trip form into #trip_drawer_content.

    Shared by new_trip (GET — open_drawer=True slides the drawer open) and the
    create_trip validation-error path (open_drawer=False — the drawer is already
    open, so we just swap the form back in with the error and the user's input).
    """
    response = render(
        request,
        "core/trip_new.html",
        {
            "drivers": _drivers_qs(),
            "riders": _riders_qs(),
            "status_choices": TripStatus.choices,
            "error": error,
            "form_data": form_data,
            # No rider is picked yet on the New Trip form, so the history button
            # shows the most-recent locations across all trips.
            "recent_pickups": _recent_places("origin"),
            "recent_destinations": _recent_places("destination"),
        },
    )
    response["HX-Retarget"] = "#trip_drawer_content"
    response["HX-Reswap"] = "innerHTML"
    if open_drawer:
        response["HX-Trigger-After-Swap"] = "show-drawer"
    return response


def new_trip(request):
    """Render the empty New Trip form into the drawer and slide it open."""
    return _render_new_trip(request, open_drawer=True)


def create_trip(request):
    """Create a Trip from the New Trip form, then close the drawer and refresh
    the trips table. On missing/invalid input, re-render the form (in the drawer)
    with an error instead of returning the 204.
    """
    post = request.POST
    first_name = post.get("first_name", "").strip()
    last_name = post.get("last_name", "").strip()
    email = post.get("email", "").strip()
    phone = post.get("phone", "").strip()
    driver_id = post.get("driver", "").strip()
    origin_id = post.get("origin_id", "").strip()
    origin_address = post.get("origin_address", "").strip()
    destination_id = post.get("destination_id", "").strip()
    destination_address = post.get("destination_address", "").strip()

    # Validate up front. The driver field is a hidden input, and browsers skip
    # constraint validation on hidden inputs, so its `required` can't enforce a
    # pick client-side — this is the real guard. Email is the unique rider key;
    # phone is always collected too.
    if not (first_name and last_name and email and phone):
        return _render_new_trip(
            request,
            error="Rider first name, last name, email and phone are required.",
            form_data=post,
        )
    driver = _drivers_qs().filter(pk=driver_id).first() if driver_id else None
    if driver is None:
        return _render_new_trip(
            request, error="Please select a driver from the list.", form_data=post
        )
    if not (origin_id and destination_id):
        return _render_new_trip(
            request,
            error="Please pick both an origin and a destination.",
            form_data=post,
        )

    # datetime-local is "YYYY-MM-DDTHH:MM" (seconds optional); blank → no date.
    date_raw = post.get("date", "").strip()
    date = parse_datetime(date_raw) if date_raw else None
    if date and timezone.is_naive(date):
        date = timezone.make_aware(date)

    try:
        # Rider: reuse the Account by email if it exists, else create one. These
        # guests never go through Firebase/mobile signup, so there is no Firebase
        # uid — the email IS the uid. They also have no photo; their avatar is a
        # DiceBear glyph generated from the email on render (Account.avatar_src),
        # so nothing avatar-related is stored here.
        account = Account.objects.filter(email=email).first()
        if account is None:
            account = Account(
                uid=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone or None,
            )
            account.save()
        else:
            # Reuse the existing account, backfilling whatever the dispatcher just
            # supplied that the row was missing — older guest rows can have a blank
            # name/phone (the "no name" bug). Only fill empty fields so we never
            # clobber data the rider set themselves on mobile.
            updates = []
            if not account.first_name and first_name:
                account.first_name = first_name
                updates.append("first_name")
            if not account.last_name and last_name:
                account.last_name = last_name
                updates.append("last_name")
            if not account.phone and phone:
                account.phone = phone
                updates.append("phone")
            if updates:
                account.save(update_fields=updates)
        rider, _ = Rider.objects.get_or_create(account=account)

        # Origin/destination Places keyed by Google place_id. Predictions carry
        # no lat/lng, so coordinate stays null (backfill via geocoding later).
        origin, _ = Place.objects.get_or_create(
            id=origin_id, defaults={"address": origin_address}
        )
        destination, _ = Place.objects.get_or_create(
            id=destination_id, defaults={"address": destination_address}
        )

        # status defaults to scheduled; Trip.save() assigns the public hashid.
        Trip.objects.create(
            driver=driver,
            rider=rider,
            origin=origin,
            destination=destination,
            date=date,
        )
    except IntegrityError:
        # e.g. the phone is already taken by a different account (phone is
        # unique). Re-render the form with the input preserved.
        return _render_new_trip(
            request,
            error=(
                "Could not create the trip — a rider with that phone "
                "number may already exist."
            ),
            form_data=post,
        )

    # 204 + triggers: the drawer closes (#trip_drawer listens for close-drawer)
    # and the trips page refreshes its rows (trips.html listens for trip-created).
    response = HttpResponse(status=204)
    response["HX-Trigger"] = json.dumps({"close-drawer": True, "trip-created": True})
    return response
