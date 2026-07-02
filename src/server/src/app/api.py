import os
from pathlib import Path

import firebase_admin
from firebase_admin import auth, credentials
from django.http import HttpRequest
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from pydantic import EmailStr, HttpUrl

from core.models import Account


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


api = NinjaAPI()


class AccountCreatePayload(Schema):
    # Intentionally exclude uid from the payload; trust the token's uid only.
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    avatar: HttpUrl


@api.post("/core/create", tags=["core"])
def create_account(request: HttpRequest, payload: AccountCreatePayload):
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

    # 3) UID extraction (canonical uid from the verified token)
    uid = decoded.get("uid")
    if not uid:
        raise HttpError(400, "Token payload missing uid.")

    # 4) get_or_create the Account
    try:
        account, created = Account.objects.get_or_create(
            uid=uid,
            email=str(payload.email),
            defaults={
                "first_name": payload.first_name,
                "last_name": payload.last_name,
                # Empty phone -> NULL so the unique constraint allows many.
                "phone": payload.phone or None,
                "avatar": str(payload.avatar),
            },
        )
    except Exception as e:
        raise HttpError(500, f"Failed to create account: {e}")

    # 5) Success
    return {"status": "ok", "uid": account.uid, "created": created}


# Resolve the NinjaAPI's URLs exactly once. django-ninja refuses to attach the
# same NinjaAPI instance twice (ConfigError on a duplicate namespace), so any
# extra mount point (e.g. an api.* subdomain in a future config/urls_api.py)
# must reuse this single tuple rather than `api.urls` again.
api_urls = api.urls
