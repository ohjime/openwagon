from typing import List, Optional
from datetime import datetime

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError

import firebase_admin
from firebase_admin import auth, credentials
from pathlib import Path

from core.models import Account, Driver
from .models import Trip, TripStatus


# Ensure Firebase Admin is initialized once (reuse config from core.api style)
try:
    firebase_admin.get_app()
except ValueError:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    cred_path = BASE_DIR / "server/env" / "fbsvc.json"
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred)


router = Router(tags=["trips"])


class TripDriverAssignedSchema(Schema):
    id: int
    hashid: str
    driver_id: int
    rider_id: int
    date: Optional[datetime] = None
    origin_id: str
    origin_address: str
    destination_id: str
    destination_address: str
    status: str
    customer_notes: str = ""
    driver_notes: str = ""
    dispatcher_notes: str = ""


class TripDriverUpdateSchema(Schema):
    """Payload allowed for a Driver to update a Trip.

    Only status and driver_notes are updatable by the driver.
    """

    status: Optional[str] = None
    driver_notes: Optional[str] = None


@router.get("/driver/assigned", response=List[TripDriverAssignedSchema])
def list_driver_assigned_trips(request: HttpRequest):
    """
    Return all trips assigned to the authenticated Firebase user (as Driver).

    Requires Authorization: Bearer <Firebase ID Token>
    """

    # 1) Authorization header
    auth_header = request.headers.get("Authorization") or request.META.get(
        "HTTP_AUTHORIZATION"
    )
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HttpError(401, "Missing or invalid Authorization header.")

    # 2) Token validation
    token = auth_header.split(" ", 1)[1].strip()
    try:
        decoded = auth.verify_id_token(token)
    except Exception:
        raise HttpError(401, "Invalid or expired token.")

    # 3) UID extraction
    uid = decoded.get("uid")
    if not uid:
        raise HttpError(400, "Token payload missing uid.")

    # 4) Resolve Driver for this uid
    try:
        account = Account.objects.get(uid=uid)
    except Account.DoesNotExist:
        # If the account doesn't exist, there can be no trips
        return []

    try:
        driver = Driver.objects.get(account=account)
    except Driver.DoesNotExist:
        return []

    # 5) Query trips and format response
    trips = (
        Trip.objects.select_related("origin", "destination").filter(driver=driver).all()
    )

    return [
        {
            "id": t.pk,
            "hashid": t.hashid,
            "driver_id": t.driver_id,  # type: ignore[attr-defined]
            "rider_id": t.rider_id,  # type: ignore[attr-defined]
            "date": t.date,
            "origin_id": str(t.origin_id),  # type: ignore[attr-defined]
            "origin_address": t.origin.address,
            "destination_id": str(t.destination_id),  # type: ignore[attr-defined]
            "destination_address": t.destination.address,
            "status": t.status,
            "customer_notes": t.customer_notes or "",
            "driver_notes": t.driver_notes or "",
            "dispatcher_notes": t.dispatcher_notes or "",
        }
        for t in trips
    ]


@router.patch("/{trip_id}/driver", response=TripDriverAssignedSchema)
def update_trip_as_driver(
    request: HttpRequest, trip_id: int, payload: TripDriverUpdateSchema
):
    """
    Update a trip as the assigned Driver. Only allows updating:
    - status
    - driver_notes

    Requires Authorization: Bearer <Firebase ID Token>
    """

    # Authorization header
    auth_header = request.headers.get("Authorization") or request.META.get(
        "HTTP_AUTHORIZATION"
    )
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HttpError(401, "Missing or invalid Authorization header.")

    # Token validation
    token = auth_header.split(" ", 1)[1].strip()
    try:
        decoded = auth.verify_id_token(token)
    except Exception:
        raise HttpError(401, "Invalid or expired token.")

    # UID extraction
    uid = decoded.get("uid")
    if not uid:
        raise HttpError(400, "Token payload missing uid.")

    # Resolve Driver for this uid
    try:
        account = Account.objects.get(uid=uid)
    except Account.DoesNotExist:
        raise HttpError(403, "Account not found for token uid.")

    try:
        driver = Driver.objects.get(account=account)
    except Driver.DoesNotExist:
        raise HttpError(403, "Driver not found for account.")

    # Load trip
    try:
        trip = Trip.objects.select_related("origin", "destination").get(id=trip_id)
    except Trip.DoesNotExist:
        raise HttpError(404, "Trip not found.")

    # Ensure driver owns trip
    if trip.driver_id != driver.pk:  # type: ignore[attr-defined]
        raise HttpError(403, "You are not authorized to modify this trip.")

    # Apply updates if provided
    to_update = False
    if payload.status is not None:
        allowed_statuses = {choice for choice, _ in TripStatus.choices}
        if payload.status not in allowed_statuses:
            raise HttpError(400, "Invalid status value.")
        trip.status = payload.status
        to_update = True

    if payload.driver_notes is not None:
        trip.driver_notes = payload.driver_notes
        to_update = True

    if to_update:
        fields = []
        if payload.status is not None:
            fields.append("status")
        if payload.driver_notes is not None:
            fields.append("driver_notes")
        trip.save(update_fields=fields)

    return {
        "id": trip.pk,
        "hashid": trip.hashid,
        "driver_id": trip.driver_id,  # type: ignore[attr-defined]
        "rider_id": trip.rider_id,  # type: ignore[attr-defined]
        "date": trip.date,
        "origin_id": str(trip.origin_id),  # type: ignore[attr-defined]
        "origin_address": trip.origin.address,
        "destination_id": str(trip.destination_id),  # type: ignore[attr-defined]
        "destination_address": trip.destination.address,
        "status": trip.status,
        "customer_notes": trip.customer_notes or "",
        "driver_notes": trip.driver_notes or "",
        "dispatcher_notes": trip.dispatcher_notes or "",
    }
