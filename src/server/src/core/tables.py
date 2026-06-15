from django_tables2 import tables
from .models import Trip


class TripTable(tables.Table):

    class Meta:
        show_header = True
        model = Trip
        fields = (
            "rider",
            "id",
            "datetime",
            "origin",
            "destination",
            "driver",
            "status",
        )
        template_name = "core/trips/partials/table.html"
        attrs = {"class": "table table-pin-rows table-pin-cols !p-0"}
