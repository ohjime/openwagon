from django_tables2 import tables

from core.models import Rider

# django-tables2 table for the riders list. As with TripTable/DriverTable the
# columns are cosmetic: the bound template (riders/partials/riders_table.html)
# fully overrides thead/tbody and renders each row by hand (rider card, contact,
# trip counts, last trip), so this class just wires the queryset to that template
# and carries the shared table CSS classes.


class RiderTable(tables.Table):
    class Meta:
        show_header = True
        model = Rider
        fields = ("account",)
        template_name = "riders/partials/riders_table.html"
        attrs = {"class": "table table-pin-rows table-pin-cols !p-0"}
