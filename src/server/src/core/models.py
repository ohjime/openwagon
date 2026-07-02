from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from sqids import Sqids
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django.urls import reverse


class BaseModel(models.Model):
    """Abstract base with created/updated timestamps, shared by app/feature
    models. Lives in core (moved here from the old config.db) so any model can
    reuse it without depending on the project's config package — keeping core
    the foundation everything builds on, never the other way around."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-updated_at"]


class User(AbstractUser):
    pass


class Account(models.Model):
    uid = models.CharField(max_length=128, unique=True, db_index=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    # Optional + unique: an empty phone is stored as NULL (not ''), so multiple
    # accounts can have "no phone" without colliding on the unique constraint
    # (Postgres allows many NULLs but only one '').
    phone = models.CharField(
        max_length=255, blank=True, null=True, unique=True
    )
    avatar = models.URLField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        # Normalize blank phone to NULL so the unique constraint ignores it.
        if not self.phone:
            self.phone = None
        super().save(*args, **kwargs)

    @property
    def avatar_src(self) -> str:
        """What to render in an <img src>: the real photo if the account has one,
        otherwise a DiceBear glyph generated on the fly from the email.

        Mobile/Firebase users upload a photo at signup (stored in `avatar`), so
        they keep theirs. Dispatch-created guests never sign up and arrive with
        no photo — they get a stable, unique generated avatar instead. Templates
        render this, never `avatar` directly."""
        if self.avatar:
            return self.avatar
        # Local import avoids loading the dicebear style at model-import time.
        from core.utils import generate_avatar

        return generate_avatar(self.email)

    def __str__(self):
        return self.email


class Driver(models.Model):
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="driver",
    )

    def __str__(self):
        return self.account.first_name + " " + self.account.last_name


class Rider(models.Model):
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="rider",
    )

    def __str__(self):
        return self.account.first_name + " " + self.account.last_name


class TripStatus(models.TextChoices):
    scheduled = "scheduled", _("Scheduled")
    assigned = "assigned", _("Assigned")
    enroute = "enroute", _("En Route")
    arrived = "arrived", _("Arrived")
    in_progress = "in_progress", _("In Progress")
    completed = "completed", _("Completed")
    canceled = "canceled", _("Canceled")


# Trip-status groupings shared by the drivers/riders feature tables and filters
# (a single source of truth so "open" and "on trip" mean the same thing in every
# annotation). These are plain lists of TripStatus values — no DB field, no
# migration. "Open" = the trip is still in flight (anything not completed or
# canceled); "On trip" = the driver/rider is actively in a vehicle right now.
OPEN_TRIP_STATUSES = [
    TripStatus.scheduled,
    TripStatus.assigned,
    TripStatus.enroute,
    TripStatus.arrived,
    TripStatus.in_progress,
]
ONTRIP_TRIP_STATUSES = [
    TripStatus.enroute,
    TripStatus.arrived,
    TripStatus.in_progress,
]


DEFAULT_LOCATION_POINT = Point(-104.9903, 39.7392)


class Place(BaseModel):
    id = models.CharField(primary_key=True, max_length=255, unique=True, db_index=True)
    address = models.CharField(max_length=255)
    coordinate = models.PointField(blank=True, null=True)

    def __str__(self) -> str:
        return self.address

    @property
    def street(self) -> str:
        """The street address: everything before the first comma."""
        return self.address.split(",", 1)[0].strip()

    @property
    def locality(self) -> str:
        """The rest of the address (city, region, postal) after the first comma."""
        parts = self.address.split(",", 1)
        return parts[1].strip() if len(parts) > 1 else ""


class Trip(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="trips")
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="trips")
    date = models.DateTimeField(null=True, blank=True)
    origin = models.ForeignKey(
        Place, on_delete=models.PROTECT, related_name="trips_origin"
    )
    destination = models.ForeignKey(
        Place, on_delete=models.PROTECT, related_name="trips_destination"
    )
    hashid = models.CharField(max_length=32, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=TripStatus.choices,
        default=TripStatus.scheduled,
    )

    class Meta:
        # Composite indexes for the Recent-locations history query
        # (core.views._recent_places): group a trip end by place, keyed by the
        # latest date. The rider-scoped pair backs the per-customer history shown
        # on an existing trip; the place+date pair backs the global history on the
        # New Trip form. The <field>-then-date column order lets Postgres satisfy
        # the GROUP BY + Max(date) sort straight from the index.
        indexes = [
            models.Index(
                fields=["rider", "origin", "date"], name="trip_rider_origin_dt_idx"
            ),
            models.Index(
                fields=["rider", "destination", "date"], name="trip_rider_dest_dt_idx"
            ),
            models.Index(fields=["origin", "date"], name="trip_origin_dt_idx"),
            models.Index(fields=["destination", "date"], name="trip_dest_dt_idx"),
        ]

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.hashid:
            sqids = Sqids(
                min_length=10, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
            )
            encoded = sqids.encode([self.pk, self.rider_id, self.driver_id])  # type: ignore
            Trip.objects.filter(pk=self.pk).update(hashid=encoded)
            self.hashid = encoded

    def get_absolute_url(self):
        """Link to the shared trip detail drawer endpoint (core), keyed by hashid."""
        return reverse("core_trip_drawer", kwargs={"hashid": self.hashid})

    def clean(self):
        if self.driver.account.uid == self.rider.account.uid:
            raise ValidationError(
                "Driver cannot be assigned to a Trip when they are the Trip Rider."
            )

    def __str__(self):
        formatted_date = (
            self.date.strftime("%B %d, %Y") if self.date else "Unknown date"
        )
        return f"Trip for {self.rider} going from {self.origin} to {self.destination} on {formatted_date} at {self.date.strftime('%I:%M %p') if self.date else 'Unknown time'}"
