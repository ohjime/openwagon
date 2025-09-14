from typing import Optional

try:
    from .models import TripStatus  # type: ignore
except Exception:  # pragma: no cover - fallback if TripStatus not available here
    from enum import Enum

    class TripStatus(str, Enum):  # minimal fallback; prefer existing TripStatus
        planned = "planned"
        en_route = "en_route"
        arrived = "arrived"
        completed = "completed"
        cancelled = "cancelled"

from pydantic import BaseModel


class TripDriverUpdate(BaseModel):
    status: Optional[TripStatus] = None
    driver_notes: Optional[str] = None

