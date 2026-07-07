import os
from datetime import datetime
from pathlib import Path

import firebase_admin
from firebase_admin import auth, credentials
from django.contrib.gis.geos import Point
from django.http import HttpRequest
from django.utils import timezone
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.security import HttpBearer
from pydantic import EmailStr, HttpUrl

from core.geocoding import ensure_place_coordinate
from core.models import Account, Driver, Rider, Trip, TripStatus


def _resolve_credentials_path() -> str:
    """Locate the Firebase service-account key.

    Honors the FIREBASE_CREDENTIALS env var, otherwise walks up from this file
    looking for an `env/fbsvc.json` (it lives at the repo root, outside the
    Django source tree, and is gitignored).
    """
    override = os.environ.get("FIREBASE_CREDENTIALS")
    if override:
        return override
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "env" / "fbsvc.json"
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        "Firebase service-account key not found. Set FIREBASE_CREDENTIALS or "
        "place the key at <repo>/env/fbsvc.json."
    )


# Ensure Firebase Admin is initialized exactly once for the process.
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(credentials.Certificate(_resolve_credentials_path()))


class Principal:
    """The authenticated caller, resolved once per request by [FirebaseAuth] and
    exposed to every endpoint as `request.auth`.

    `uid`/`email` come straight off the verified Firebase token and always
    exist. `account` is the matching [Account] row, or None when the token is
    valid but no account has been created yet — that gap is legitimate: the very
    first call a new user makes is `/core/create`, which runs *before* any
    account exists. Every other endpoint requires `account` and 404s without it.
    """

    def __init__(self, uid: str, email: str | None, account: Account | None):
        self.uid = uid
        self.email = email
        self.account = account


class FirebaseAuth(HttpBearer):
    """Verifies the `Authorization: Bearer <firebase-id-token>` header on every
    request and hands the endpoint a [Principal].

    Returning None makes django-ninja answer 401, so an absent/garbage/expired
    token is rejected before any view code runs. A *valid* token with no Account
    yet still authenticates (Principal.account is None) — see Principal."""

    def authenticate(self, request: HttpRequest, token: str) -> "Principal | None":
        try:
            decoded = auth.verify_id_token(token)
        except Exception:
            return None
        uid = decoded.get("uid")
        if not uid:
            return None
        account = Account.objects.filter(uid=uid).first()
        return Principal(uid=uid, email=decoded.get("email"), account=account)


# One NinjaAPI for the whole mobile surface, authenticated by default: every
# operation below inherits FirebaseAuth, so none of them re-parse the header.
api = NinjaAPI(auth=FirebaseAuth())


def _require_account(request: HttpRequest) -> Account:
    """The caller's Account, or 404 if the token is valid but no account exists
    yet. Every endpoint except /core/create goes through this."""
    account = request.auth.account
    if account is None:
        raise HttpError(404, "No account exists for this user yet.")
    return account


def _require_driver(request: HttpRequest) -> Driver:
    """The caller's Driver profile, or 403 if they don't have one. Accessing the
    reverse one-to-one `account.driver` raises RelatedObjectDoesNotExist, which
    subclasses AttributeError — so `getattr(..., None)` yields None when absent
    (the same existence check the model layer uses via hasattr)."""
    account = _require_account(request)
    driver = getattr(account, "driver", None)
    if driver is None:
        raise HttpError(403, "This account is not a driver.")
    return driver


# ---------------------------------------------------------------------------
# Serializers — plain dicts shaped to the Flutter client's fromJson factories
# (see src/mobile/lib/core/models/*.dart). Kept as functions, not ninja Schemas,
# because the client shape doesn't line up 1:1 with the ORM rows (e.g. driver_id
# is non-null on the client and falls back to 0; the notes fields have no column
# yet). One place to evolve when the model gains those columns.
# ---------------------------------------------------------------------------


def _account_dict(account: Account) -> dict:
    return {
        "uid": account.uid,
        "first_name": account.first_name,
        "last_name": account.last_name,
        "email": account.email,
        "phone": account.phone or "",
        "avatar": account.avatar_src,
    }


def _driver_dict(driver: Driver) -> dict:
    vehicle = getattr(driver, "vehicle", None)
    return {
        "id": driver.id,
        "status": driver.status,
        "has_vehicle": vehicle is not None,
    }


def _rider_dict(rider: Rider) -> dict:
    return {"id": rider.id}


def _place_latlng(place) -> tuple[float | None, float | None]:
    """(lat, lng) for a Place, geocoding+persisting its coordinate on first read.

    The mobile map needs real coordinates to pin the ends and frame the route.
    Real Places start with a null coordinate (booking predictions carry no
    lat/lng), so backfill it here — the lookup happens once, then reads the
    stored point. Returns (None, None) when it can't be resolved; the client
    treats a missing end as "no route to draw" rather than erroring.
    """
    coord = place.coordinate or ensure_place_coordinate(place)
    if coord is None:
        return None, None
    return coord.y, coord.x  # PointField stores x=lng, y=lat


def _trip_dict(trip: Trip) -> dict:
    origin_lat, origin_lng = _place_latlng(trip.origin)
    destination_lat, destination_lng = _place_latlng(trip.destination)
    return {
        "id": trip.id,
        "hashid": trip.hashid,
        # The client model types driver_id as a non-null int; an unassigned trip
        # never reaches a driver's list, but fall back to 0 to honor the shape.
        "driver_id": trip.driver_id or 0,
        "rider_id": trip.rider_id,
        "date": trip.date.isoformat() if trip.date else "",
        "origin_id": trip.origin_id,
        "origin_address": trip.origin.address,
        # Geocoded ends (null until Google resolves the place id) — the mobile
        # map pins these and frames the route between them.
        "origin_lat": origin_lat,
        "origin_lng": origin_lng,
        "destination_id": trip.destination_id,
        "destination_address": trip.destination.address,
        "destination_lat": destination_lat,
        "destination_lng": destination_lng,
        "status": trip.status,
        # No columns for these yet; the client defaults them to '' anyway.
        "customer_notes": "",
        "driver_notes": "",
        "dispatcher_notes": "",
    }


# ---------------------------------------------------------------------------
# core — account bootstrap + the portal's "who am I" probe
# ---------------------------------------------------------------------------


class AccountCreatePayload(Schema):
    # Intentionally exclude uid from the payload; trust the token's uid only.
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    avatar: HttpUrl


@api.post("/core/create", tags=["core"])
def create_account(request: HttpRequest, payload: AccountCreatePayload):
    """Idempotently ensure an Account exists for the signed-in Firebase user.

    Keyed on the token's uid alone (the client never sends it): a repeat call
    from an existing user is a no-op get, so it's safe to run on every sign-in.
    """
    uid = request.auth.uid
    try:
        account, created = Account.objects.get_or_create(
            uid=uid,
            defaults={
                "first_name": payload.first_name,
                "last_name": payload.last_name,
                "email": str(payload.email),
                # Empty phone -> NULL so the unique constraint allows many.
                "phone": payload.phone or None,
                "avatar": str(payload.avatar),
            },
        )
    except Exception as e:
        raise HttpError(500, f"Failed to create account: {e}")
    return {"status": "ok", "uid": account.uid, "created": created}


@api.get("/core/me", tags=["core"])
def me(request: HttpRequest):
    """The portal's entry probe: the account plus which role profiles exist.

    `driver`/`rider` are null when the account has no such profile — that's the
    signal the app uses to show "No driver/rider account found — sign up?".
    """
    account = _require_account(request)
    driver = getattr(account, "driver", None)
    rider = getattr(account, "rider", None)
    return {
        "account": _account_dict(account),
        "driver": _driver_dict(driver) if driver is not None else None,
        "rider": _rider_dict(rider) if rider is not None else None,
    }


# ---------------------------------------------------------------------------
# drivers — profile sign-up + GPS ingest
# ---------------------------------------------------------------------------


@api.post("/drivers/create", tags=["drivers"])
def create_driver(request: HttpRequest):
    """Sign the current account up as a driver (get_or_create → idempotent).

    A new Driver defaults to `unavailable`: dispatch can't put them on the road
    until an admin reviews them and (with a vehicle attached) flips them to
    available. The app can still show the driver home meanwhile.
    """
    account = _require_account(request)
    driver, created = Driver.objects.get_or_create(account=account)
    return {"status": "ok", "driver": _driver_dict(driver), "created": created}


@api.post("/riders/create", tags=["riders"])
def create_rider(request: HttpRequest):
    """Sign the current account up as a rider (get_or_create → idempotent)."""
    account = _require_account(request)
    rider, created = Rider.objects.get_or_create(account=account)
    return {"status": "ok", "rider": _rider_dict(rider), "created": created}


class LocationFix(Schema):
    lat: float
    lng: float
    # Client capture time (ISO 8601). Optional and currently informational — the
    # batch is drained oldest-first, so ordering already identifies the newest.
    ts: datetime | None = None


class LocationBatch(Schema):
    """A batch of GPS fixes uploaded by the driver app.

    The app (locus) queues fixes locally and drains them in batches, so an
    offline stretch arrives in a single request when connectivity returns. The
    body carries ONLY coordinates — never a driver/device id; identity comes from
    the verified Firebase token (see update_driver_location).
    """

    fixes: list[LocationFix]


@api.post("/drivers/location", tags=["drivers"])
def update_driver_location(request: HttpRequest, payload: LocationBatch):
    """Overwrite the driver's current position from a batch of GPS fixes.

    This is the write side of core.views.driver_location (which the dispatcher
    map polls). Position lives on the driver's Vehicle and is OVERWRITTEN in
    place — never appended — so only the *newest* fix in the batch matters; a
    whole batch is one row UPDATE (see the Vehicle model docstring). A PointField
    stores (x=lng, y=lat).

    Security: the write is bound to the caller's own Vehicle, resolved from the
    verified Firebase token via _require_driver — a driver can only ever update
    their own location, regardless of the request body.
    """
    if not payload.fixes:
        raise HttpError(400, "No location fixes provided.")
    # locus drains its queue oldest-first, so the last fix is the newest.
    newest = payload.fixes[-1]
    if not (-90.0 <= newest.lat <= 90.0 and -180.0 <= newest.lng <= 180.0):
        raise HttpError(400, "lat/lng out of range.")
    driver = _require_driver(request)
    vehicle = getattr(driver, "vehicle", None)
    if vehicle is None:
        # 409: the driver is real but has no vehicle to attach a position to.
        # The app treats this as "tracking unavailable", not an auth failure.
        raise HttpError(409, "No vehicle is assigned to this driver.")
    vehicle.last_location = Point(newest.lng, newest.lat)
    vehicle.location_updated_at = timezone.now()
    vehicle.save(update_fields=["last_location", "location_updated_at"])
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# trips — the driver's assigned list + status updates
# ---------------------------------------------------------------------------


@api.get("/trips/driver/assigned", tags=["trips"])
def driver_assigned_trips(request: HttpRequest):
    """Every trip assigned to the signed-in driver, earliest date first.

    Returns all of them (history included) — the driver home renders the list
    and filters client-side. An account with no driver profile gets an empty
    list rather than an error, so the portal can show it before sign-up.
    """
    account = _require_account(request)
    driver = getattr(account, "driver", None)
    if driver is None:
        return []
    trips = (
        Trip.objects.filter(driver=driver)
        .select_related("origin", "destination")
        .order_by("date")
    )
    return [_trip_dict(trip) for trip in trips]


# Statuses a driver may set from the app. Everything except `unassigned` —
# assignment/unassignment is the dispatcher's job; a driver only advances (or
# cancels) a trip they're already on.
_DRIVER_SETTABLE_STATUSES = {
    s for s in TripStatus.values if s != TripStatus.unassigned
}


class DriverTripUpdate(Schema):
    status: str | None = None
    # Accepted for forward-compat with the client, ignored until Trip grows a
    # driver_notes column (there's no field to write it to today).
    driver_notes: str | None = None


@api.patch("/trips/{trip_id}/driver", tags=["trips"])
def driver_update_trip(request: HttpRequest, trip_id: int, payload: DriverTripUpdate):
    """Let the assigned driver advance a trip's status.

    Scoped to trips assigned to *this* driver (404 otherwise), and to the
    driver-settable statuses (400 otherwise). Trip.save() keeps its own
    invariants — e.g. a driver is attached here, so the status can legitimately
    leave `unassigned`.
    """
    driver = _require_driver(request)
    try:
        trip = Trip.objects.select_related("origin", "destination").get(
            id=trip_id, driver=driver
        )
    except Trip.DoesNotExist:
        raise HttpError(404, "Trip not found or not assigned to you.")

    if payload.status is not None:
        if payload.status not in _DRIVER_SETTABLE_STATUSES:
            raise HttpError(400, f"A driver cannot set status '{payload.status}'.")
        trip.status = payload.status
        trip.save(update_fields=["status"])

    return _trip_dict(trip)


# Resolve the NinjaAPI's URLs exactly once. django-ninja refuses to attach the
# same NinjaAPI instance twice (ConfigError on a duplicate namespace), so any
# extra mount point (e.g. an api.* subdomain in a future config/urls_api.py)
# must reuse this single tuple rather than `api.urls` again.
api_urls = api.urls
