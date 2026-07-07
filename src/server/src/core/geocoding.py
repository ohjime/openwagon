"""On-demand geocoding for Places.

A Place created from a Google autocomplete *prediction* carries only a
`place_id` and an address string — no coordinate (see `core.views`: the booking
form leaves `Place.coordinate` null, "backfill via geocoding later"). But the
mobile trip map needs real lat/lng: unlike the web map (which hands raw place
ids to the Google Directions JS API and lets Google resolve them), the Flutter
map draws on OpenStreetMap tiles and has nothing to resolve a place id.

This module is that backfill: resolve a Place's coordinate from its Google
place id via the Geocoding API and persist it, so the first trip fetch pays the
lookup once and every fetch after reads the stored point. It reuses the same
`GOOGLE_MAPS_API_KEY` + `googlemaps` client the seeding code uses.
"""

import os

from django.contrib.gis.geos import Point

try:  # optional dependency, mirrors core.fake
    import googlemaps
except ImportError:  # pragma: no cover - exercised only where the lib is absent
    googlemaps = None


def _client():
    """A Google Maps client, or None when geocoding isn't available.

    Returns None (rather than raising) when the package or key is missing so a
    trip fetch degrades to "no coordinate" instead of failing — the client
    handles a null coordinate by simply not framing that end.
    """
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not googlemaps or not key:
        return None
    try:
        return googlemaps.Client(key=key)
    except Exception:
        return None


def ensure_place_coordinate(place):
    """Resolve and persist `place.coordinate` from its Google place id.

    No-op when the coordinate is already set. Returns the Point, or None if it
    can't be resolved (no key/package, geocode miss, or malformed response) —
    callers must tolerate None.
    """
    if place.coordinate is not None:
        return place.coordinate
    client = _client()
    if client is None:
        return None
    try:
        results = client.geocode(place_id=place.id)  # type: ignore[attr-defined]
    except Exception:
        return None
    if not results:
        return None
    loc = results[0].get("geometry", {}).get("location", {})
    lat, lng = loc.get("lat"), loc.get("lng")
    if lat is None or lng is None:
        return None
    # PointField stores (x=lng, y=lat); mirror core.api's Vehicle.last_location.
    point = Point(lng, lat, srid=4326)
    place.coordinate = point
    place.save(update_fields=["coordinate"])
    return point
