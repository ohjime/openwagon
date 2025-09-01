from typing import List, Optional
from datetime import datetime

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError

import firebase_admin
from firebase_admin import auth, credentials
from pathlib import Path

from core.models import Account, Driver
from .models import Trip


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
        Trip.objects.select_related("origin", "destination")
        .filter(driver=driver)
        .all()
    )

    return [
        TripDriverAssignedSchema(
            id=t.id,
            hashid=t.hashid,
            driver_id=t.driver_id,
            rider_id=t.rider_id,
            date=t.date,
            origin_id=str(t.origin_id),
            origin_address=t.origin.address,
            destination_id=str(t.destination_id),
            destination_address=t.destination.address,
            status=t.status,
            customer_notes=t.customer_notes or "",
            driver_notes=t.driver_notes or "",
            dispatcher_notes=t.dispatcher_notes or "",
        )
        for t in trips
    ]
