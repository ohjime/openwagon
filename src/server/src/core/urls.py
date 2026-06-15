from django.urls import path
from core.views import (
    trips_index,
    riders_index,
    drivers_index,
    index,
    TripDetailView,
    table_htmx,
)


urlpatterns = [
    path("", index, name="core_index"),
    path("trips/", trips_index, name="trips_index"),
    path("riders/", riders_index, name="riders_index"),
    path("drivers/", drivers_index, name="drivers_index"),
    # Restrict to integer primary keys so non-numeric paths like '/favicon.ico' don't resolve here
    path("<int:pk>/", TripDetailView.as_view(), name="trip_detail"),
    path("trips/table-htmx/", table_htmx, name="table_htmx"),
]
