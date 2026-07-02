from django_tables2 import tables

from core.models import Driver

# django-tables2 table for the drivers list. As with TripTable the columns are
# cosmetic: the bound template (drivers/partials/drivers_table.html) fully
# overrides thead/tbody and renders each row by hand (driver card, contact, trip
# counts, availability), so this class just wires the queryset to that template
# and carries the shared table CSS classes.


class DriverTable(tables.Table):
    class Meta:
        show_header = True
        model = Driver
        fields = ("account",)
        template_name = "drivers/partials/drivers_table.html"
        attrs = {"class": "table table-pin-rows table-pin-cols !p-0"}
