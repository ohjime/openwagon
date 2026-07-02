from django.urls import path

from trips import views

# The trips feature's htmx reactivity endpoints, collected under the `htmx/`
# prefix. config.urls mounts this module under `trips/`, so they resolve to
# /trips/htmx/table/ and /trips/htmx/detail/<pk>/. The trip content templates are
# pre-wired to these `name=`s, so a host dashboard that loads those templates
# gets all the reactivity for free — it never references a trip URL itself.
#
# There is deliberately no page route here: the navigable trips page is served
# by the host dashboard (app), which renders trips/pages/trips.html into its own
# shell. This module owns only the fragments the page calls back to.
urlpatterns = [
    path("htmx/table/", views.table, name="trips_htmx_table"),
    path("htmx/counts/", views.counts, name="trips_htmx_counts"),
]
