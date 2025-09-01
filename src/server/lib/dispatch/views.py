from django.shortcuts import render

# Create your views here.
from django_tables2 import RequestConfig
from core.models import Driver
from trip.models import Trip, Place
from .tables import TripTable
from django.shortcuts import render
from django.views.generic.detail import DetailView
from django.http import (
    HttpRequest,
    HttpResponseRedirect,
    HttpResponseBadRequest,
    HttpResponse,
)
from django.db.models import Q
from django.template.loader import render_to_string  # <-- add


def trips_index(request):
    table = TripTable(Trip.objects.all())
    RequestConfig(request, paginate={"per_page": 80}).configure(table)  # type: ignore
    if request.htmx:
        template_name = "dispatch/trips/partials/list.html"
    else:
        template_name = "dispatch/trips/trips.html"
    return render(request, template_name, {"table": table})


# 👇 REPLACE the previous version of this function with this one
def trip_driver_field_search(request):
    """
    Handles HTMX search requests for drivers and returns an HTML fragment.
    - With driver_id: returns the full driver summary block HTML (card + vehicle info).
    - With query: returns a list of dropdown items.
    """
    if not request.htmx:
        return HttpResponseBadRequest("This endpoint is for HTMX requests only.")

    driver_id = request.GET.get("driver_id")
    if driver_id:
        try:
            d = Driver.objects.select_related("account").get(pk=int(driver_id))
        except (Driver.DoesNotExist, ValueError):
            return HttpResponseBadRequest("Invalid driver_id")

        # Defaults mirroring the initial render in details.html
        default_vehicle_img = "https://d1mkhyrwwj7jji.cloudfront.net/wp-content/uploads/2020/06/17113405/sienna-png.png"
        default_vehicle_make_img = (
            "https://www.carlogos.org/car-logos/toyota-logo-1989-download.png"
        )
        default_avatar = (
            f"https://i.pravatar.cc/150?u={getattr(d.account, 'id', 'driver')}"
        )

        html = render_to_string(
            "cotton/driver_summary_card.html",
            {
                "driver_avatar": getattr(d.account, "avatar", default_avatar)
                or default_avatar,
                "driver_name": (
                    f"{getattr(d.account, 'first_name', '')} {getattr(d.account, 'last_name', '')}".strip()
                )
                or getattr(d.account, "email", "")
                or "Driver",
                "driver_identifier": getattr(
                    d, "identifier", f"D-{getattr(d.account, 'id', '')}"
                ),
                "driver_phone": getattr(d.account, "phone", "") or "",
                "vehicle_img": getattr(
                    getattr(d, "vehicle", None), "img", default_vehicle_img
                )
                or default_vehicle_img,
                "vehicle_make_img": getattr(
                    getattr(d, "vehicle", None), "make_img", default_vehicle_make_img
                )
                or default_vehicle_make_img,
                "vehicle_year": getattr(getattr(d, "vehicle", None), "year", 2025)
                or 2025,
                "vehicle_make": getattr(getattr(d, "vehicle", None), "make", "Toyota")
                or "Toyota",
                "vehicle_model": getattr(getattr(d, "vehicle", None), "model", "Sienna")
                or "Sienna",
                "vehicle_id": getattr(getattr(d, "vehicle", None), "id", "WAGON-15")
                or "WAGON-15",
                "vehicle_plate": getattr(getattr(d, "vehicle", None), "plate", "ABC123")
                or "ABC123",
                "vehicle_wheelchair_capacity": getattr(
                    getattr(d, "vehicle", None), "wheelchair_capacity", 1
                )
                or 1,
                "vehicle_seated_capacity": getattr(
                    getattr(d, "vehicle", None), "seated_capacity", 4
                )
                or 4,
            },
            request=request,
        )
        return HttpResponse(html)

    # Return the dropdown items for a search query
    query = request.GET.get("query", "").strip()
    if query:
        drivers = (
            Driver.objects.filter(
                Q(account__first_name__icontains=query)
                | Q(account__last_name__icontains=query)
                | Q(account__email__icontains=query)
            )
            .select_related("account")
            .only("id", "account__first_name", "account__last_name", "account__email")[
                :5
            ]
        )
    else:
        drivers = Driver.objects.none()

    if drivers.count() == 0:
        html = """
            <div class="p-4 text-center text-gray-500">No drivers found.</div>
            """
    else:
        html = "".join(
            render_to_string(
                "cotton/driver_dropdown_item.html",
                {
                    "driver_id": d.pk,
                    "driver_avatar": (
                        getattr(d.account, "avatar", default_avatar)
                        if False
                        else d.account.avatar
                    ),
                    "driver_name": f"{d.account.first_name} {d.account.last_name}".strip()
                    or d.account.email,
                    "vehicle_wheelchair_capacity": 1,
                    "vehicle_seating_capacity": 5,
                    "driver_status": "available",
                },
                request=request,
            )
            for d in drivers
        )
    return HttpResponse(html)


# Search/filtering of trips table
def table_htmx(request):
    import time
    from datetime import datetime

    time.sleep(1)
    query = request.GET.get("search", "").strip()
    date_filter = request.GET.get("date", "").strip()
    status_filter = request.GET.get("status", "").strip()

    qs = Trip.objects.all()

    # Text search filter - restrict to rider/driver names, addresses, and hashid
    if query:
        qs = qs.filter(
            Q(rider__account__first_name__icontains=query)
            | Q(rider__account__last_name__icontains=query)
            | Q(driver__account__first_name__icontains=query)
            | Q(driver__account__last_name__icontains=query)
            | Q(origin__address__icontains=query)
            | Q(destination__address__icontains=query)
            | Q(hashid__icontains=query)
        )

    # Date filter - filter trips on the selected date
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            qs = qs.filter(date__date=filter_date)
        except ValueError:
            # Handle invalid date format
            pass

    # Status filter
    if status_filter:
        qs = qs.filter(status=status_filter)

    table = TripTable(qs)
    RequestConfig(request, paginate={"per_page": 80}).configure(table)  # type: ignore
    return render(request, "dispatch/trips/partials/table.html", {"table": table})


def riders_index(request):
    if request.htmx:
        template_name = "dispatch/riders/partials/list.html"
    else:
        template_name = "dispatch/riders/riders.html"
    return render(request, template_name)


def drivers_index(request):
    if request.htmx:
        template_name = "dispatch/drivers/partials/list.html"
    else:
        template_name = "dispatch/drivers/drivers.html"
    return render(request, template_name)


def index(request):
    template_name = "dispatch/index.html"
    return render(request, template_name)


class TripDetailView(DetailView):
    model = Trip
    template_name = "dispatch/trip_detail.html"

    def get_template_names(self):
        request: HttpRequest = self.request  # type: ignore
        if getattr(request, "htmx", False):
            return ["dispatch/trips/partials/details.html"]
        return [self.template_name]

    def post(self, request: HttpRequest, *args, **kwargs):  # type: ignore
        self.object = self.get_object()
        origin_address = request.POST.get("origin_address", "").strip()
        destination_address = request.POST.get("destination_address", "").strip()
        origin_id = request.POST.get("origin_id", "").strip()
        destination_id = request.POST.get("destination_id", "").strip()

        # Upsert origin Place
        if origin_address and origin_id:
            origin_place, _ = Place.objects.update_or_create(
                place_id=origin_id,
                defaults={"address": origin_address},
            )
            self.object.origin = origin_place  # type: ignore

        # Upsert destination Place
        if destination_address and destination_id:
            destination_place, _ = Place.objects.update_or_create(
                place_id=destination_id,
                defaults={"address": destination_address},
            )
            self.object.destination = destination_place  # type: ignore

        # Optionally parse lat/lng to set coordinate if posted (not shown here)

        self.object.full_clean(exclude=["hashid"])  # validate model constraints
        self.object.save()

        if getattr(request, "htmx", False):
            context = self.get_context_data(object=self.object)
            return render(request, "dispatch/trips/partials/details.html", context)
        return HttpResponseRedirect(self.object.get_absolute_url())  # type: ignore
