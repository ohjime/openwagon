from django_tables2 import tables

from core.models import Trip

# django-tables2 table for the trips list. The columns are largely cosmetic: the
# bound template (trips/partials/trips_table.html) fully overrides
# thead/tbody and renders each row by hand, so this class mainly wires the
# queryset to that template and carries the table's CSS classes. Ported from the
# old core.tables.TripTable.


class TripTable(tables.Table):
    class Meta:
        show_header = True
        model = Trip
        fields = (
            "rider",
            "driver",
            "date",
            "origin",
            "destination",
            "status",
        )
        template_name = "trips/partials/trips_table.html"
        attrs = {"class": "table table-pin-rows table-pin-cols !p-0"}
