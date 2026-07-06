import json
import os

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.gis.db.models import MultiPolygonField, PointField
from django.contrib.gis.forms.widgets import OSMWidget
from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import date as format_date
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display
from unfold.sections import TemplateSection

from .models import (
    DEFAULT_LOCATION_POINT,
    Account,
    Driver,
    DriverStatus,
    Invoice,
    Place,
    Rider,
    ServicePlan,
    Trip,
    TripStatus,
    User,
    Vehicle,
    VehicleDocument,
    VehicleStatus,
    Zone,
)


def _person_header(account: Account) -> list:
    """[title, subtitle, initials, image] for an unfold `header=True` display
    column — the avatar-in-line-with-name treatment ported from the Unfold
    demo's driver list. Every Account always has a picture (a real upload or a
    generated placeholder — see Account.avatar_src), so the initials never
    actually render, but they're supplied as the documented fallback."""
    initials = f"{account.first_name[:1]}{account.last_name[:1]}".upper()
    return [
        f"{account.first_name} {account.last_name}".strip() or account.email,
        account.email,
        initials or "?",
        {"path": account.avatar_src, "height": 32, "width": 32},
    ]


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    pass


@admin.register(Account)
class AccountAdmin(ModelAdmin):
    list_display = ("display_header", "phone", "is_driver", "is_rider")
    search_fields = ("first_name", "last_name", "email", "phone", "uid")

    @display(description=_("Account"), header=True)
    def display_header(self, instance: Account):
        return _person_header(instance)

    @display(description=_("Driver"), boolean=True)
    def is_driver(self, instance: Account):
        return hasattr(instance, "driver")

    @display(description=_("Rider"), boolean=True)
    def is_rider(self, instance: Account):
        return hasattr(instance, "rider")


@admin.register(Driver)
class DriverAdmin(ModelAdmin):
    list_display = ("display_header", "display_status")
    list_filter = ("status",)
    search_fields = (
        "account__first_name",
        "account__last_name",
        "account__email",
        "account__phone",
    )

    @display(description=_("Driver"), header=True)
    def display_header(self, instance: Driver):
        return _person_header(instance.account)

    @display(
        description=_("Status"),
        label={
            DriverStatus.available: "success",
            DriverStatus.unavailable: "danger",
        },
    )
    def display_status(self, instance: Driver):
        return instance.status, instance.get_status_display()


@admin.register(Rider)
class RiderAdmin(ModelAdmin):
    list_display = ("display_header",)
    # Backs the autocomplete widget on ServicePlan.riders.
    search_fields = (
        "account__first_name",
        "account__last_name",
        "account__email",
        "account__phone",
    )

    @display(description=_("Rider"), header=True)
    def display_header(self, instance: Rider):
        return _person_header(instance.account)


class TripRouteMapSection(TemplateSection):
    """Row-expand preview: the origin -> destination route on Google Maps
    (directions/geocoding are within Google's terms — unlike the Zone
    boundary map, this isn't rendering our own polygon on a competing base
    layer)."""

    template_name = "core/admin/trip_route_map.html"

    def get_context_data(self, request, instance: Trip) -> dict:
        # The assigned driver's current position, if we have one: the driver's
        # vehicle last_location (reverse OneToOne — hasattr guards the no-vehicle
        # case). None when the trip has no driver, the driver has no vehicle, or
        # the vehicle has never reported a fix — the template just skips the
        # marker then.
        driver_location = None
        driver = instance.driver
        if driver is not None and hasattr(driver, "vehicle"):
            point = driver.vehicle.last_location
            if point is not None:
                driver_location = {
                    "lat": point.y,
                    "lng": point.x,
                    "label": str(driver),
                }
        return {
            "trip": instance,
            "maps_api_key": os.getenv("GOOGLE_MAPS_API_KEY", ""),
            "map_id": f"trip-map-{instance.pk}",
            "driver_location": driver_location,
        }


class TripRiderSection(TemplateSection):
    """Row-expand preview: who's riding, with their avatar, plus the trip's
    key facts at a glance."""

    template_name = "core/admin/trip_rider.html"

    def get_context_data(self, request, instance: Trip) -> dict:
        return {"trip": instance, "rider": instance.rider}


@admin.register(Trip)
class TripAdmin(ModelAdmin):
    list_display = (
        "display_rider",
        "display_date",
        "display_driver",
        "display_status",
    )
    # Every list row renders a rider/driver avatar+name, so preload both
    # accounts up front — otherwise each row would fire its own lookup.
    list_select_related = ("rider__account", "driver__account")
    list_sections = [TripRouteMapSection, TripRiderSection]
    list_sections_classes = "lg:grid-cols-2"
    # driver is nullable (a trip can be unassigned) — the plain <select> Django
    # renders by default buries the blank "---------" choice in a long driver
    # list. autocomplete_fields swaps it for a Select2 combobox with an explicit
    # × to clear the pick, same as DriverAdminMixin.editor/standing in the
    # unfold demo (bin/formula/admin.py). Requires DriverAdmin.search_fields,
    # which is already set below.
    autocomplete_fields = ("driver",)

    @display(description=_("Rider"), header=True)
    def display_rider(self, instance: Trip):
        return _person_header(instance.rider.account)

    @display(description=_("Date"), ordering="date")
    def display_date(self, instance: Trip):
        return format_date(instance.date, "M j, Y g:i A") if instance.date else "—"

    @display(description=_("Driver"), header=True)
    def display_driver(self, instance: Trip):
        if instance.driver_id is None:
            return ["Unassigned", None, None, None]
        return _person_header(instance.driver.account)

    @display(
        description=_("Status"),
        label={
            TripStatus.unassigned: "info",
            TripStatus.assigned: "primary",
            TripStatus.enroute: "warning",
            TripStatus.arrived: "warning",
            TripStatus.in_progress: "warning",
            TripStatus.completed: "success",
            TripStatus.canceled: "danger",
        },
    )
    def display_status(self, instance: Trip):
        return instance.status, instance.get_status_display()


@admin.register(Place)
class PlaceAdmin(ModelAdmin):
    pass


class ZoneMapWidget(OSMWidget):
    """Draw the zone polygon on an OpenStreetMap base layer (Django's built-in
    OpenLayers widget — no extra dependency; Google Maps stays for
    geocoding/directions, which is all its terms allow outside its own JS
    renderer anyway). Opens centered on the app's default service area.

    The Media CSS restores the map's dimensions: the stock admin sizes .dj_map
    in admin/css/widgets.css, which unfold's theme replaces wholesale. The
    Media JS bolts a place-search box onto the map and enforces one polygon per
    zone — a MultiPolygon field otherwise lets you paint several. A zone is a
    single service area; a genuinely disjoint area that must share one fare
    schedule (an airport enclave, an island) is rare and better modeled as a
    separate Zone row, so we don't expose multi-polygon drawing here."""

    default_lon = DEFAULT_LOCATION_POINT.x
    default_lat = DEFAULT_LOCATION_POINT.y
    default_zoom = 10

    class Media:
        css = {"all": ("core/zone_admin_map.css",)}
        js = ("core/zone_admin_map.js",)


@admin.register(Zone)
class ZoneAdmin(ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)
    formfield_overrides = {MultiPolygonField: {"widget": ZoneMapWidget}}


class ServicePlanZoneMapSection(TemplateSection):
    """Row-expand preview: the plan's zone boundary. Read-only, so it draws on
    an OSM base layer with OpenLayers (already vendored for ZoneMapWidget)
    rather than Google Maps — same reasoning as ZoneMapWidget above."""

    template_name = "core/admin/service_plan_zone_map.html"

    def get_context_data(self, request, instance: ServicePlan) -> dict:
        zone = instance.zone
        return {
            "zone": zone,
            "zone_geometry": json.loads(zone.area.geojson) if zone.area else None,
            "map_id": f"zone-map-{instance.pk}",
            "script_id": f"zone-geojson-{instance.pk}",
        }


class ServicePlanRatesSection(TemplateSection):
    """Row-expand preview: every rate the fare algorithm charges against, plus
    who the plan is available to."""

    template_name = "core/admin/service_plan_rates.html"

    def get_context_data(self, request, instance: ServicePlan) -> dict:
        return {
            "plan": instance,
            "tax_percent": instance.tax_rate * 100,
            "rider_count": instance.riders.count(),
        }


@admin.register(ServicePlan)
class ServicePlanAdmin(ModelAdmin):
    """Where the administration authors fare schedules. The one-default-per-
    zone rule is a DB constraint; the ModelForm's full_clean surfaces a
    violation as a normal field error instead of a 500."""

    list_display = (
        "name",
        "zone",
        "is_default",
        "base_fare",
        "meter_rate",
        "duration_rate",
        "waiting_rate",
        "tax_rate",
    )
    list_filter = ("zone", "is_default")
    search_fields = ("name",)
    autocomplete_fields = ("riders",)
    list_sections = [ServicePlanZoneMapSection, ServicePlanRatesSection]
    list_sections_classes = "lg:grid-cols-2"


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = (
        "trip",
        "service_plan",
        "total",
        "fixed_price",
        "waiting_min",
        "status",
        "created_at",
    )
    list_filter = ("status", "service_plan")
    # Billing math is frozen at charge time; admin edits status (settling),
    # not the numbers.
    readonly_fields = ("breakdown",)


class VehicleDocumentInline(TabularInline):
    """Upload an arbitrary number of files (insurance/license/permit/other)
    straight from the vehicle's detail page — one row per document."""

    model = VehicleDocument
    extra = 1
    fields = ("kind", "file", "expires_at")


class VehicleLocationMapWidget(OSMWidget):
    """Click-to-place editor for a vehicle's current position
    (Vehicle.last_location, a Point). Draws on the same OpenLayers/OSM base
    layer as ZoneMapWidget — Google Maps' terms don't allow rendering our own
    markers on a competing base map, and OSM keeps this consistent with the
    zone editor. The built-in widget already enforces a single point for a
    non-collection field: drawing a new pin replaces the old, and the "Delete
    all Features" link clears it. Opens centered on the app's default service
    area. The Media CSS restores the map's dimensions, which unfold's theme
    otherwise strips — same fix as ZoneMapWidget, see the stylesheet."""

    default_lon = DEFAULT_LOCATION_POINT.x
    default_lat = DEFAULT_LOCATION_POINT.y
    default_zoom = 11

    class Media:
        css = {"all": ("core/location_admin_map.css",)}
        # A non-collection PointField makes the stock widget place-once (it
        # disables drawing after the first point), so on the change form a
        # vehicle with an existing fix loads with clicking dead — only panning
        # works. This keeps drawing enabled and replaces the point on each
        # click; see the stylesheet's sibling for the full rationale.
        js = ("core/location_admin_map.js",)


@admin.register(Vehicle)
class VehicleAdmin(ModelAdmin):
    list_display = (
        "display_vehicle",
        "display_driver",
        "license_plate",
        "display_status",
    )
    # driver is nullable; select_related still LEFT-JOINs so the per-row driver
    # avatar/name never fans out into its own query.
    list_select_related = ("driver__account",)
    search_fields = (
        "make",
        "model",
        "license_plate",
        "driver__account__first_name",
        "driver__account__last_name",
        "driver__account__email",
    )
    list_filter = ("status",)
    # Select2 combobox with an explicit × to clear the pick — same treatment as
    # TripAdmin.driver. Requires DriverAdmin.search_fields (already set).
    autocomplete_fields = ("driver",)
    # Swap the raw WKT textarea Django renders for a PointField with a
    # click-to-place map, so an admin can set last_location by hand.
    formfield_overrides = {PointField: {"widget": VehicleLocationMapWidget}}
    # location_updated_at is system-recorded ("when the fix arrived" — see
    # Vehicle.last_location), so it's read-only in the form and stamped in
    # save_model whenever the pin moves, matching the driver app's GPS pings.
    readonly_fields = ("location_updated_at",)
    inlines = [VehicleDocumentInline]
    # Renders a button on the vehicle's detail page — see toggle_availability.
    actions_detail = ["toggle_availability"]

    def save_model(self, request, obj, form, change):
        """Stamp the fix time when an admin sets or moves the pin, and clear it
        when the pin is removed — so a manually placed location carries a fresh
        location_updated_at (dispatch reads a stale/empty one as "gone dark")
        while unrelated edits leave the existing timestamp untouched."""
        if "last_location" in form.changed_data:
            obj.location_updated_at = timezone.now() if obj.last_location else None
        super().save_model(request, obj, form, change)

    @display(description=_("Vehicle"))
    def display_vehicle(self, instance: Vehicle):
        return str(instance)

    @display(description=_("Driver"), header=True)
    def display_driver(self, instance: Vehicle):
        if instance.driver_id is None:
            return ["Unassigned", None, None, None]
        return _person_header(instance.driver.account)

    @display(
        description=_("Status"),
        label={
            VehicleStatus.available: "success",
            VehicleStatus.unavailable: "danger",
        },
    )
    def display_status(self, instance: Vehicle):
        return instance.status, instance.get_status_display()

    @action(description=_("Toggle availability"), icon="sync")
    def toggle_availability(self, request, object_id):
        """Flip the vehicle between Available and Unavailable — the one control
        the admin uses to take a vehicle off the road for maintenance/renewals
        or put it back on once it's cleared."""
        vehicle = get_object_or_404(Vehicle, pk=object_id)
        vehicle.status = (
            VehicleStatus.unavailable
            if vehicle.status == VehicleStatus.available
            else VehicleStatus.available
        )
        vehicle.save(update_fields=["status", "updated_at"])
        messages.success(
            request,
            _("Vehicle marked %(status)s.")
            % {"status": vehicle.get_status_display()},
        )
        return redirect(request.headers.get("referer"))
