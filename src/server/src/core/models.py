from decimal import Decimal, ROUND_HALF_UP

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


class DriverStatus(models.TextChoices):
    # Ordered unavailable-first so the default (a freshly created driver) reads
    # as "not dispatchable until an admin approves them" — mirrors
    # VehicleStatus, and matches the same gate on the driver's vehicle.
    unavailable = "unavailable", _("Unavailable")
    available = "available", _("Available")


class Driver(models.Model):
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="driver",
    )
    # Whether dispatch may put this driver on the road. Defaults to
    # `unavailable`: a new driver isn't dispatchable until an admin reviews them
    # and flips it to `available` — same posture as Vehicle.status.
    status = models.CharField(
        max_length=12,
        choices=DriverStatus.choices,
        default=DriverStatus.unavailable,
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
    # unassigned IS the "scheduled" state — a trip with no driver yet. Kept as
    # one status rather than two: every trip already implies it's scheduled by
    # virtue of existing, so the only thing worth naming is whether a driver
    # is on it.
    unassigned = "unassigned", _("Unassigned")
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
    TripStatus.unassigned,
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
# Statuses that only make sense once a driver is actively on the trip. A trip
# left without a driver (never assigned one, or had one unassigned) can't sit
# in any of these — Trip.save() forces it back to `unassigned` whenever
# driver_id is None, so "assigned"/"enroute"/etc always imply a real driver.
DRIVER_REQUIRED_STATUSES = [
    TripStatus.assigned,
    TripStatus.enroute,
    TripStatus.arrived,
    TripStatus.in_progress,
]


def _unassign_driver_on_delete(collector, field, sub_objs, using):
    """Trip.driver's on_delete: behaves like SET_NULL, but a delete cascade
    updates rows directly in the DB and never calls Trip.save() — so without
    this, a deleted driver's in-flight trips would keep a
    DRIVER_REQUIRED_STATUSES status with no driver. Revert those to
    `unassigned` first, then nullify, mirroring the invariant save() enforces
    for a single trip."""
    sub_objs.filter(status__in=DRIVER_REQUIRED_STATUSES).update(
        status=TripStatus.unassigned
    )
    models.SET_NULL(collector, field, sub_objs, using)


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


def _dec(value):
    """Coerce any numeric input (int, float, str, Decimal) to Decimal safely —
    float goes through str so 0.1 stays 0.1, not 0.1000000000000000055511…"""
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _money(value):
    """Round to cents, half-up (the customer-facing rounding)."""
    return _dec(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Zone(BaseModel):
    """A service area (city, region) that fares are priced within.

    `area` is the real PostGIS geometry for point-in-zone checks
    (Zone.objects.filter(area__contains=place.coordinate)). Nullable for now:
    zones arrive before the geometry wiring, so every trip is assumed in-zone
    and the seeded "Default Zone" is picked without a spatial test.
    """

    name = models.CharField(max_length=255, unique=True)
    area = models.MultiPolygonField(null=True, blank=True)

    def __str__(self):
        return self.name


class ServicePlan(BaseModel):
    """A named fare schedule for a zone: the rates the canonical pricing
    algorithm multiplies against a trip's measurements (rate × value, summed,
    then taxed).

    Access model:
      • is_default=True → the "Zone Default" plan, available to every rider
        booking in the zone. At most one per zone — a partial unique
        constraint in Postgres, so a zone's default can never be duplicated
        (and, being a row of this table, never a plan from another zone).
      • riders (M2M) → private plans list their members explicitly. Default
        plans leave it empty; membership rows exist only for the exceptions,
        so nothing is attached to rider profiles at signup.

    Pricing is two-phase, same formula both times:
      quote(trip)  — booking time. Waiting time is unknown until the driver
                     has actually waited, so it contributes nothing yet.
      charge(trip, waiting_min, fixed_price=None) — after completion: the
                     identical assessment plus waiting_rate × waiting_min,
                     materialized as the trip's Invoice.
    """

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="plans")
    name = models.CharField(max_length=255)
    base_fare = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    # Per-km and per-minute rates, multiplied against the trip's measurements.
    meter_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    duration_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    waiting_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    # A fraction, not a percent: 0.15 = 15% tax applied on top of the fare.
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    is_default = models.BooleanField(default=False)
    riders = models.ManyToManyField(Rider, blank=True, related_name="service_plans")

    class Meta(BaseModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["zone"],
                condition=models.Q(is_default=True),
                name="one_default_plan_per_zone",
            ),
            models.UniqueConstraint(
                fields=["zone", "name"], name="unique_plan_name_per_zone"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.zone.name})"

    @classmethod
    def available_to(cls, rider, zone):
        """Every plan this rider may pick in this zone, defaults first: the
        zone's default (open to everyone) plus any private plan whose member
        list includes the rider. One query; distinct() because a rider can be
        a member of the default plan too without duplicating it."""
        qs = cls.objects.filter(zone=zone)
        if rider is None:
            # New customer with no Rider row yet — only the open default applies.
            qs = qs.filter(is_default=True)
        else:
            qs = qs.filter(models.Q(is_default=True) | models.Q(riders=rider))
        return qs.distinct().order_by("-is_default", "name")

    def _fare(self, distance_km, duration_min, waiting_min):
        """The canonical algorithm: every rate × its measurement, summed, then
        taxed. Both pricing phases run exactly this — the quote simply passes
        zero waiting."""
        subtotal = (
            self.base_fare
            + self.meter_rate * _dec(distance_km)
            + self.duration_rate * _dec(duration_min)
            + self.waiting_rate * _dec(waiting_min)
        )
        subtotal = _money(subtotal)
        tax = _money(subtotal * self.tax_rate)
        return subtotal, tax

    def quote(self, trip):
        """Booking-time estimate over the trip's estimated distance/duration.
        Estimates are nullable (route metrics wiring comes later) and price as
        zero — a metric-less trip quotes to base fare + tax."""
        subtotal, tax = self._fare(
            trip.distance_km or 0, trip.duration_min or 0, 0
        )
        return _money(subtotal + tax)

    def charge(self, trip, waiting_min=0, fixed_price=None):
        """Completion-time assessment → the trip's Invoice.

        Re-runs the exact fare the quote ran, over the same trip measurements,
        now with the waiting time slapped on. `fixed_price` short-circuits the
        whole computation: a dispatcher-agreed flat amount IS the total (no
        tax added on top). Re-charging a trip overwrites its invoice in place,
        so corrections — an adjusted waiting time, a newly agreed fixed price
        — are just another call."""
        waiting_min = _dec(waiting_min)
        if fixed_price is not None:
            fixed_price = _money(fixed_price)
            subtotal, tax, total = fixed_price, Decimal("0.00"), fixed_price
        else:
            subtotal, tax = self._fare(
                trip.distance_km or 0, trip.duration_min or 0, waiting_min
            )
            total = _money(subtotal + tax)
        invoice, _ = Invoice.objects.update_or_create(
            trip=trip,
            defaults={
                "service_plan": self,
                "waiting_min": waiting_min,
                "fixed_price": fixed_price,
                "total": total,
                # The rates and measurements actually billed, frozen at charge
                # time — a later edit to the plan never rewrites this invoice.
                "breakdown": {
                    "subtotal": str(subtotal),
                    "tax": str(tax),
                    "base_fare": str(self.base_fare),
                    "meter_rate": str(self.meter_rate),
                    "duration_rate": str(self.duration_rate),
                    "waiting_rate": str(self.waiting_rate),
                    "tax_rate": str(self.tax_rate),
                    "distance_km": str(trip.distance_km or 0),
                    "duration_min": str(trip.duration_min or 0),
                    "waiting_min": str(waiting_min),
                },
            },
        )
        return invoice


class Trip(models.Model):
    # Nullable: a trip can be booked before a driver is picked, and an
    # assigned driver can later be unassigned (see save(), which forces the
    # status back to `unassigned` whenever driver is None). on_delete
    # unassigns rather than cascading the delete, so removing a Driver
    # doesn't wipe out trip history — see _unassign_driver_on_delete.
    driver = models.ForeignKey(
        Driver,
        on_delete=_unassign_driver_on_delete,
        null=True,
        blank=True,
        related_name="trips",
    )
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
        default=TripStatus.unassigned,
    )
    # Fare plumbing. The plan is what quote()/charge() price with (PROTECT: a
    # plan referenced by trips can't be deleted out from under its pricing
    # history). distance/duration are route estimates — null until the Google
    # Maps metrics wiring lands, and both phases price null as zero. The quoted
    # price is frozen at booking so later plan edits never move it.
    service_plan = models.ForeignKey(
        ServicePlan,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="trips",
    )
    distance_km = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    duration_min = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    quoted_price = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
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
        # `unassigned` is entirely driver-driven, never a dispatcher's manual
        # pick — the two rules below are the only way in or out of it:
        if self.driver_id is None:
            # A driver-less trip can't be in a status that implies one is
            # actively on it — force it back to `unassigned` whenever driver
            # is cleared, regardless of what set the status before this save.
            # Terminal statuses are exempt: a trip can be canceled without
            # ever getting a driver, and a completed trip keeps its history
            # even if its driver is later removed.
            if self.status in DRIVER_REQUIRED_STATUSES:
                self.status = TripStatus.unassigned
        elif self.status == TripStatus.unassigned:
            # A driver is on the trip now, so `unassigned` no longer
            # applies — promote to `assigned`. This only fires when the
            # status is still `unassigned` (a new trip's default, or a
            # dispatcher trying to hand-pick `unassigned` while a driver is
            # attached); reassigning the driver on a trip already further
            # along (en route, arrived, …) leaves that progress untouched.
            self.status = TripStatus.assigned
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.hashid:
            sqids = Sqids(
                min_length=10, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
            )
            # driver_id may be None (no driver assigned yet); Sqids only
            # encodes ints, so a driver-less trip falls back to 0.
            encoded = sqids.encode([self.pk, self.rider_id, self.driver_id or 0])  # type: ignore
            Trip.objects.filter(pk=self.pk).update(hashid=encoded)
            self.hashid = encoded

    def get_absolute_url(self):
        """Link to the shared trip detail drawer endpoint (core), keyed by hashid."""
        return reverse("core_trip_drawer", kwargs={"hashid": self.hashid})

    def clean(self):
        if self.driver_id is not None:
            if self.driver.account.uid == self.rider.account.uid:
                raise ValidationError(
                    "Driver cannot be assigned to a Trip when they are the Trip Rider."
                )
            # A driver dispatches in their vehicle — no vehicle, nothing to
            # dispatch. `vehicle` is the reverse OneToOne from Vehicle.driver;
            # hasattr is the existence check (see AccountAdmin.is_driver).
            if not hasattr(self.driver, "vehicle"):
                raise ValidationError(
                    "Driver cannot be assigned to a Trip without an associated vehicle."
                )

    def __str__(self):
        formatted_date = (
            self.date.strftime("%B %d, %Y") if self.date else "Unknown date"
        )
        return f"Trip for {self.rider} going from {self.origin} to {self.destination} on {formatted_date} at {self.date.strftime('%I:%M %p') if self.date else 'Unknown time'}"


class InvoiceStatus(models.TextChoices):
    unsettled = "unsettled", _("Unsettled")
    settled = "settled", _("Settled")


class Invoice(BaseModel):
    """A completed trip's bill — what ServicePlan.charge() materializes.

    One per trip (re-charging updates it in place). `fixed_price`, when set,
    is the dispatcher-agreed flat total that overrode the computed fare; the
    breakdown records the rates and measurements actually billed either way,
    so the invoice stays auditable after a plan's rates change. PROTECT on
    both FKs: billing records outlive trips-cleanup and plan deletion."""

    trip = models.OneToOneField(
        Trip, on_delete=models.PROTECT, related_name="invoice"
    )
    service_plan = models.ForeignKey(
        ServicePlan, on_delete=models.PROTECT, related_name="invoices"
    )
    waiting_min = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fixed_price = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    total = models.DecimalField(max_digits=8, decimal_places=2)
    breakdown = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=12,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.unsettled,
    )

    def __str__(self):
        return f"Invoice {self.trip.hashid} — {self.total} ({self.get_status_display()})"


class VehicleStatus(models.TextChoices):
    # Ordered unavailable-first so the default (a freshly added vehicle) reads
    # as "not road-ready until an admin approves it" — see Vehicle.status.
    unavailable = "unavailable", _("Unavailable")
    available = "available", _("Available")


class Vehicle(BaseModel):
    """A fleet vehicle, at most one per driver — and one driver per vehicle — at
    any time. The OneToOne enforces both directions of that rule; SET_NULL means
    removing a driver just detaches their vehicle rather than deleting it. The FK
    is nullable so a vehicle can sit driverless while it's being serviced or its
    documents are being renewed.

    `status` gates whether dispatch may put it on the road and defaults to
    `unavailable`: a newly added vehicle isn't road-ready until an admin has
    reviewed its documents and flipped it to `available` (the toggle lives on the
    admin detail page — see core.admin.VehicleAdmin.toggle_availability).

    `last_location` is the vehicle's *current* position, OVERWRITTEN on each ping
    from the driver app — never appended. Tracking a whole fleet is therefore one
    row UPDATE per vehicle per interval, not an ever-growing breadcrumb table, so
    the write volume stays trivial (a hundred vehicles pinging every 10s is ~10
    UPDATEs/sec). `location_updated_at` records when the fix arrived, so a stale
    timestamp tells dispatch a vehicle has gone dark."""

    driver = models.OneToOneField(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle",
    )
    make = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    color = models.CharField(max_length=50, blank=True)
    license_plate = models.CharField(max_length=32, blank=True)
    status = models.CharField(
        max_length=12,
        choices=VehicleStatus.choices,
        default=VehicleStatus.unavailable,
    )
    last_location = models.PointField(null=True, blank=True)
    location_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        # "2022 Toyota Camry (ABC-123)" — drop whichever identity parts are
        # blank, falling back to the plate, then the pk, so a bare vehicle still
        # renders something.
        name = " ".join(
            part
            for part in (str(self.year) if self.year else "", self.make, self.model)
            if part
        ).strip()
        if self.license_plate:
            return f"{name} ({self.license_plate})" if name else self.license_plate
        return name or f"Vehicle #{self.pk}"


class VehicleDocumentKind(models.TextChoices):
    insurance = "insurance", _("Insurance")
    license = "license", _("License")
    permit = "permit", _("Permit")
    other = "other", _("Other")


class VehicleDocument(BaseModel):
    """A file attached to a vehicle. `kind` names the three documents the fleet
    cares about (insurance / license / permit) while still allowing an arbitrary
    number of files per vehicle — extra copies, or anything else, filed as
    `other`. `expires_at` is optional; it's the hook a future background job can
    read to flip a vehicle to Unavailable once a document lapses (see
    Vehicle.status)."""

    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="documents"
    )
    kind = models.CharField(
        max_length=20,
        choices=VehicleDocumentKind.choices,
        default=VehicleDocumentKind.other,
    )
    file = models.FileField(upload_to="vehicles/documents/")
    expires_at = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_kind_display()} — {self.vehicle}"
