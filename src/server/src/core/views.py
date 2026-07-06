import json

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.models import (
    Account,
    Driver,
    Place,
    Rider,
    ServicePlan,
    Trip,
    TripStatus,
    Vehicle,
    Zone,
)

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


def _trip_detail_context(trip, *, error=None):
    """Context for core/trip_detail.html, shared by show_trip (open the
    drawer) and update_trip's failure path (re-render it in place)."""
    return {
        "trip": trip,
        "status_choices": TripStatus.choices,
        "drivers": _drivers_qs(),
        # The customer's own pickup/destination history for the history button.
        "recent_pickups": _recent_places("origin", rider=trip.rider),
        "recent_destinations": _recent_places("destination", rider=trip.rider),
        "error": error,
    }


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
    response = render(request, "core/trip_detail.html", _trip_detail_context(trip))
    response["HX-Retarget"] = "#trip_drawer_content"
    response["HX-Reswap"] = "innerHTML"
    response["HX-Trigger-After-Swap"] = "show-drawer"
    return response


def _render_trip_detail(request, trip, *, error):
    """Re-render the trip detail drawer body with a validation error — the
    update_trip failure path. Same swap-into-drawer trick as
    _render_new_trip, but the drawer is already open so there's no
    show-drawer trigger to fire."""
    response = render(
        request, "core/trip_detail.html", _trip_detail_context(trip, error=error)
    )
    response["HX-Retarget"] = "#trip_drawer_content"
    response["HX-Reswap"] = "innerHTML"
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


def _default_zone():
    """The zone trips are priced in. Until the PostGIS point-in-zone wiring
    lands every trip is assumed in-zone, so this is simply the first (the
    seeded "Default Zone") row."""
    return Zone.objects.order_by("pk").first()


def _available_plans(email=None):
    """Service plans the New Trip form may offer for the rider identified by
    email: the zone's default plan plus that rider's private plans. A blank or
    unknown email (brand-new customer) gets just the defaults. Empty when no
    zone exists yet (fresh DB before the seed migration)."""
    zone = _default_zone()
    if zone is None:
        return ServicePlan.objects.none()
    rider = None
    if email:
        rider = Rider.objects.filter(account__email=email).first()
    return ServicePlan.available_to(rider, zone)


def _plan_options_context(email=None, selected_raw=None):
    """Context for the plan <option> list (core/plan_options.html): the plans
    offered for this email, and which one to mark selected. A previous pick is
    kept only while it's still in the offered set — switching to a rider who
    can't use it falls back to the zone default (the template selects the
    is_default row when selected_plan_id is None)."""
    plans = list(_available_plans(email))
    selected_id = (
        int(selected_raw) if selected_raw and selected_raw.isdigit() else None
    )
    if selected_id not in {p.pk for p in plans}:
        selected_id = None
    return {"plans": plans, "selected_plan_id": selected_id}


def _render_new_trip(request, *, error=None, form_data=None, open_drawer=False):
    """Render the New Trip form into #trip_drawer_content.

    Shared by new_trip (GET — open_drawer=True slides the drawer open) and the
    create_trip validation-error path (open_drawer=False — the drawer is already
    open, so we just swap the form back in with the error and the user's input).
    """
    form_data = form_data or {}
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
            # Service-plan dropdown. On the error re-render the rejected POST's
            # email/plan keep the dispatcher's picks; on a fresh form both are
            # blank and the zone default is offered/selected.
            **_plan_options_context(
                email=(form_data.get("email") or "").strip() or None,
                selected_raw=(form_data.get("service_plan") or "").strip(),
            ),
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


def trip_plans(request):
    """Re-render the New Trip form's service-plan <option>s (htmx GET).

    Fired when an existing customer is picked (the rider-picked event
    riderPicker.select dispatches — programmatic field fills emit no change
    event) or when the email field is edited by hand. Blank/unknown email
    offers just the zone defaults, so a brand-new customer sees exactly the
    open plans."""
    return render(
        request,
        "core/plan_options.html",
        _plan_options_context(
            email=request.GET.get("email", "").strip() or None,
            selected_raw=request.GET.get("service_plan", "").strip(),
        ),
    )


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

    # Validate up front. Email is the unique rider key; phone is always
    # collected too. A driver is optional — a trip can be booked before a
    # driver is picked (Trip.driver is nullable) — but if one was picked, it
    # must actually resolve to a real Driver.
    if not (first_name and last_name and email and phone):
        return _render_new_trip(
            request,
            error="Rider first name, last name, email and phone are required.",
            form_data=post,
        )
    driver = _drivers_qs().filter(pk=driver_id).first() if driver_id else None
    if driver_id and driver is None:
        return _render_new_trip(
            request, error="Selected driver not found.", form_data=post
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

        # Service plan: the submitted pick, but only if it's in the set this
        # rider is actually allowed (defaults + their private plans — the same
        # query the dropdown renders from, so a tampered/stale id can't buy a
        # plan the rider doesn't have). Anything else falls back to the zone
        # default rather than failing the booking.
        zone = _default_zone()
        plan = None
        if zone is not None:
            allowed = ServicePlan.available_to(rider, zone)
            plan_raw = post.get("service_plan", "").strip()
            if plan_raw.isdigit():
                plan = allowed.filter(pk=int(plan_raw)).first()
            if plan is None:
                plan = allowed.filter(is_default=True).first()

        # status defaults to unassigned; Trip.save() assigns the public hashid.
        trip = Trip.objects.create(
            driver=driver,
            rider=rider,
            origin=origin,
            destination=destination,
            date=date,
            service_plan=plan,
        )
        if plan is not None:
            # Freeze the booking-time estimate. Route metrics are still null
            # (Google Maps wiring pending), so today this is base fare + tax —
            # it firms up automatically once distance/duration get populated.
            trip.quoted_price = plan.quote(trip)
            trip.save(update_fields=["quoted_price"])
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


def update_trip(request, hashid):
    """Save edits made in the trip detail drawer: driver (nullable — this is
    where a dispatcher clears the assignment back to unassigned), pickup
    date, origin/destination, and status. The drawer carries no rider fields,
    so the rider FK is never touched here.
    """
    trip = get_object_or_404(
        Trip.objects.select_related(*TRIP_SELECT_RELATED), hashid=hashid
    )
    post = request.POST
    driver_id = post.get("driver", "").strip()
    origin_id = post.get("origin_id", "").strip()
    origin_address = post.get("origin_address", "").strip()
    destination_id = post.get("destination_id", "").strip()
    destination_address = post.get("destination_address", "").strip()
    status_raw = post.get("status", "").strip()

    # A blank driver clears the assignment; a non-blank id that doesn't
    # resolve is treated the same as a tampered pick on the New Trip form.
    driver = _drivers_qs().filter(pk=driver_id).first() if driver_id else None
    if driver_id and driver is None:
        return _render_trip_detail(request, trip, error="Selected driver not found.")
    if not (origin_id and destination_id):
        return _render_trip_detail(
            request, trip, error="Please pick both an origin and a destination."
        )

    # datetime-local is "YYYY-MM-DDTHH:MM" (seconds optional); blank → no date.
    date_raw = post.get("date", "").strip()
    date = parse_datetime(date_raw) if date_raw else None
    if date and timezone.is_naive(date):
        date = timezone.make_aware(date)

    origin, _ = Place.objects.get_or_create(
        id=origin_id, defaults={"address": origin_address}
    )
    destination, _ = Place.objects.get_or_create(
        id=destination_id, defaults={"address": destination_address}
    )

    trip.driver = driver
    trip.origin = origin
    trip.destination = destination
    trip.date = date
    if status_raw in TripStatus.values:
        trip.status = status_raw

    try:
        trip.clean()
    except ValidationError as e:
        return _render_trip_detail(request, trip, error=" ".join(e.messages))
    trip.save()

    # 204 + triggers: the drawer closes and the trips table refreshes its rows
    # (trips.html listens for trip-updated alongside trip-created).
    response = HttpResponse(status=204)
    response["HX-Trigger"] = json.dumps({"close-drawer": True, "trip-updated": True})
    return response


def driver_location(request):
    """JSON: a driver's current map position, for the trip map's live poll
    (c-trip.map). Position lives on the Vehicle (Vehicle.last_location,
    overwritten per GPS ping — never appended), reached through the driver's
    one-to-one vehicle. A PointField stores (x=lng, y=lat).

    Returns {"location": null} — and the map simply shows no dot — when the
    ?driver id is missing/unknown, the driver has no vehicle assigned, or that
    vehicle has never reported a fix. Read-only and cheap: one indexed lookup
    of a single row's point, so the poll can run every few seconds per open
    drawer without concern.
    """
    driver_id = request.GET.get("driver", "").strip()
    vehicle = None
    if driver_id.isdigit():
        vehicle = (
            Vehicle.objects.filter(driver_id=int(driver_id))
            .only("id", "last_location", "location_updated_at")
            .first()
        )
    if vehicle is None or vehicle.last_location is None:
        return JsonResponse({"location": None})
    point = vehicle.last_location
    return JsonResponse(
        {
            "location": {"lat": point.y, "lng": point.x},
            "updated_at": (
                vehicle.location_updated_at.isoformat()
                if vehicle.location_updated_at
                else None
            ),
        }
    )
