from ninja import Router, Schema
from pydantic import EmailStr, HttpUrl
from django.http import HttpRequest
import firebase_admin
from firebase_admin import auth, credentials
import os
from pathlib import Path

from .models import Account


# Ensure Firebase Admin is initialized once
try:
    firebase_admin.get_app()
except ValueError:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    cred_path = BASE_DIR / "server/env" / "fbsvc.json"
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred)


router = Router(tags=["core"])


class AccountCreatePayload(Schema):
    # Intentionally exclude uid from payload; trust token uid only
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    avatar: HttpUrl


@router.post("/create")
def create_account(request: HttpRequest, payload: AccountCreatePayload):
    from ninja.errors import HttpError

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
    except Exception as e:
        raise HttpError(401, "Invalid or expired token.")

    # 3) UID extraction (canonical uid)
    uid = decoded.get("uid")
    if not uid:
        raise HttpError(400, "Token payload missing uid.")

    # 4) Model creation
    try:
        account, created = Account.objects.get_or_create(
            uid=uid,
            email=str(payload.email),
            defaults={
                "first_name": payload.first_name,
                "last_name": payload.last_name,
                "phone": payload.phone,
                "avatar": str(payload.avatar),
            },
        )
    except Exception as e:
        print(e)
        raise HttpError(500, f"Failed to create account: {e}")

    # 5) Success
    return {"status": "ok", "uid": account.uid, "created": created}
