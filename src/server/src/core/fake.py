import random
import factory
from datetime import timedelta
from django.utils import timezone

from factory.declarations import LazyFunction, SubFactory, LazyAttribute
from factory import post_generation  # type: ignore
from factory.faker import Faker
from core import models
from core.models import TripStatus

import os
import math
from uuid import uuid4
from django.contrib.gis.geos import Point

try:
    import googlemaps  # optional
except Exception:  # pragma: no cover
    googlemaps = None


def _unique_email() -> str:
    """Return an email not present in the DB, trying a few random candidates."""
    # Try a bunch of random numeric suffixes to avoid collisions with prior runs.
    for _ in range(1000):
        n = random.randint(0, 10**12)
        email = f"user{n}@example.com"
        if not models.Account.objects.filter(email=email).exists():
            return email
    # Absolute fallback using UUID to guarantee uniqueness
    return f"user-{uuid4()}@example.com"


def _unique_uid() -> str:
    """Return a UUID that's not already used in the DB (extremely unlikely collision)."""
    for _ in range(10):
        uid = str(uuid4())
        if not models.Account.objects.filter(uid=uid).exists():
            return uid
    return str(uuid4())


def _unique_phone() -> str:
    """Return a phone number not present in the DB (E.164 +1XXXXXXXXXX)."""
    for _ in range(1000):
        n = random.randint(0, 10**10 - 1)
        phone = "+1" + f"{n:010d}"
        if not models.Account.objects.filter(phone=phone).exists():
            return phone
    # Fallback with UUID-derived tail to guarantee uniqueness
    tail = str(uuid4().int % (10**10)).rjust(10, "0")
    return "+1" + tail


class AccountFactory(factory.django.DjangoModelFactory):
    """Base account used by Driver/Rider factories."""

    class Meta:  # type: ignore
        model = models.Account

    # Ensure UID doesn't collide with existing rows (super rare, but safe)
    uid = LazyFunction(_unique_uid)
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    # Ensure DB-unique emails across multiple runs
    email = LazyFunction(_unique_email)
    # Short E.164-style and DB-unique across runs
    phone = LazyFunction(_unique_phone)

    @factory.lazy_attribute  # type: ignore
    def avatar(self):
        return f"https://i.pravatar.cc/150?u={self.uid}"


class DriverFactory(factory.django.DjangoModelFactory):
    class Meta:  # type: ignore
        model = models.Driver

    account = SubFactory(AccountFactory)  # type: ignore


class RiderFactory(factory.django.DjangoModelFactory):
    class Meta:  # type: ignore
        model = models.Rider

    account = SubFactory(AccountFactory)  # type: ignore


# ---------------------------------------------------------------------------
# Address generation
# ---------------------------------------------------------------------------
# We want realistic-looking (but fake) Canadian / Edmonton style addresses of
# the form: 8934 179A AVE NW Edmonton AB
# Pattern pieces:
#   <civic_number> <street_number>[<optional_letter>] <street_type> <direction> Edmonton AB
# Example output: 523 82 AVE NE Edmonton AB
#                 10432 179A ST NW Edmonton AB

STREET_TYPES = ["AVE", "ST", "RD", "DR", "CT", "PL", "BLVD", "WAY", "TRAIL"]
CARDINALS = ["NW", "NE", "SW", "SE"]
LETTER_SUFFIXES = ["", "A", "B", "C"]  # appended to street number occasionally


def generate_address() -> str:
    civic_number = random.randint(1, 99999)  # Edmonton civic numbers can be large
    street_number = random.randint(1, 300)
    letter = random.choice(LETTER_SUFFIXES)
    # Lower probability for a letter suffix; keep only ~20% of the time
    if letter and random.random() > 0.2:
        letter = ""
    street_type = random.choice(STREET_TYPES)
    direction = random.choice(CARDINALS)
    return (
        f"{civic_number} {street_number}{letter} {street_type} {direction} Edmonton AB"
    )


def _random_time_window():
    """Return a timezone-aware datetime within +/- 3 days from now."""
    now = timezone.now()
    delta = timedelta(hours=random.randint(-72, 72), minutes=random.randint(0, 59))
    return now + delta


# Edmonton center for local random coordinates
EDMONTON_CENTER = (53.5461, -113.4938)  # (lat, lng)


def _random_point_near(lat: float, lng: float, max_km: float = 20.0) -> Point:
    """Return a random Point within max_km of the given lat/lng."""
    # Random distance and bearing
    distance_km = random.uniform(0, max_km)
    bearing = random.uniform(0, 2 * math.pi)

    R = 6371.0  # Earth radius (km)
    δ = distance_km / R
    φ1 = math.radians(lat)
    λ1 = math.radians(lng)

    φ2 = math.asin(
        math.sin(φ1) * math.cos(δ) + math.cos(φ1) * math.sin(δ) * math.cos(bearing)
    )
    λ2 = λ1 + math.atan2(
        math.sin(bearing) * math.sin(δ) * math.cos(φ1),
        math.cos(δ) - math.sin(φ1) * math.sin(φ2),
    )

    new_lat = math.degrees(φ2)
    new_lng = (math.degrees(λ2) + 540) % 360 - 180  # normalize to [-180, 180)
    return Point(new_lng, new_lat, srid=4326)


def _gmaps_client():
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not googlemaps:
        raise RuntimeError(
            "googlemaps package not available. Install it to use Google Places."
        )
    if not key:
        raise RuntimeError(
            "GOOGLE_MAPS_API_KEY is not set. Configure it to enable Google Places."
        )
    try:
        return googlemaps.Client(key=key)
    except Exception as e:
        raise RuntimeError("Failed to initialize Google Maps client") from e


def _random_place_google():
    """Fetch a nearby random place from Google Places (required)."""
    client = _gmaps_client()

    lat, lng = EDMONTON_CENTER
    # Query a random nearby POI type
    poi_types = ["restaurant", "cafe", "store", "park", "bar", "museum"]
    poi_type = random.choice(poi_types)
    try:
        resp = client.places_nearby(  # type: ignore[attr-defined]
            location=(lat, lng),
            radius=10000,  # 10km
            open_now=False,
            type=poi_type,
        )
        results = resp.get("results", [])
        if not results:
            raise RuntimeError("Google Places returned no results")
        picked = random.choice(results)
        place_id = picked.get("place_id")
        geom = picked.get("geometry", {}).get("location", {})
        plat, plng = geom.get("lat"), geom.get("lng")

        # Try to get a formatted address via Place Details; fallback to vicinity/name
        formatted_address = None
        if place_id:
            details = client.place(place_id=place_id, fields=["formatted_address"])  # type: ignore[attr-defined]
            formatted_address = details.get("result", {}).get("formatted_address")

        address = (
            formatted_address
            or picked.get("vicinity")
            or picked.get("name")
            or "Edmonton, AB"
        )
        if plat is None or plng is None:
            # If geometry missing (rare), fall back to a local random point
            point = _random_point_near(lat, lng)
        else:
            point = Point(plng, plat, srid=4326)

        return {
            "id": place_id or str(uuid4()),
            "address": address,
            "point": point,
        }
    except Exception as e:
        raise RuntimeError("Failed to fetch place from Google Places") from e


def _random_place_local():
    """Local-only fake Place: random coordinate near Edmonton + fake address."""
    point = _random_point_near(*EDMONTON_CENTER)
    return {
        "id": str(uuid4()),
        "address": generate_address(),
        "point": point,
    }


def _make_place_payload():
    """Produce a single coherent payload used by PlaceFactory fields."""
    # Require Google; do not fall back to local fake addresses
    return _random_place_google()


class PlaceFactory(factory.django.DjangoModelFactory):
    class Meta:  # type: ignore
        model = models.Place
        django_get_or_create = ("id",)  # dedupe by primary key

    class Params:
        payload = LazyFunction(_make_place_payload)

    id = LazyAttribute(lambda o: o.payload["id"])
    address = LazyAttribute(lambda o: o.payload["address"])
    coordinate = LazyAttribute(lambda o: o.payload["point"])


class TripFactory(factory.django.DjangoModelFactory):
    class Meta:  # type: ignore
        model = models.Trip

    driver = SubFactory(DriverFactory)  # type: ignore
    rider = SubFactory(RiderFactory)  # type: ignore
    date = LazyFunction(_random_time_window)
    origin = SubFactory(PlaceFactory)

    @staticmethod
    def _random_status():
        return random.choice(list(TripStatus))

    status = LazyFunction(_random_status)

    @factory.lazy_attribute  # type: ignore
    def destination(self):  # type: ignore
        # Ensure destination differs from origin; retry a few times
        for _ in range(5):
            place = PlaceFactory()
            if place.id != self.origin_id:  # type: ignore[attr-defined]
                return place
        return PlaceFactory()

    @post_generation  # type: ignore
    def ensure_distinct_accounts(self, create, extracted, **kwargs):  # type: ignore
        if not create:
            return
        if self.driver.account.uid == self.rider.account.uid:  # type: ignore[attr-defined]
            self.rider = RiderFactory()
            self.save(update_fields=["rider_id"])  # type: ignore[arg-type]

    @classmethod
    def bulk(cls, count: int, **overrides):
        """Efficiently create many trips with proper Place FKs."""
        created: list[models.Trip] = []
        for _ in range(count):
            driver = overrides.get("driver") or DriverFactory()
            rider = overrides.get("rider") or RiderFactory()
            if driver.account.uid == rider.account.uid:
                rider = RiderFactory()

            origin = overrides.get("origin") or PlaceFactory()
            dest = overrides.get("destination") or PlaceFactory()
            if origin.id == dest.id:
                dest = PlaceFactory()

            trip = models.Trip.objects.create(
                driver=driver,
                rider=rider,
                date=_random_time_window(),
                origin=origin,
                destination=dest,
                status=random.choice(list(TripStatus)),
            )
            created.append(trip)
        return created


# Convenience: create N trips with separate drivers/riders
def generate(count=25):
    return TripFactory.bulk(count)
