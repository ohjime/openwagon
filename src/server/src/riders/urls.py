from django.urls import path

from riders import views

# The riders feature's htmx reactivity endpoints, collected under the `htmx/`
# prefix. config.urls mounts this module under `riders/`, so they resolve to
# /riders/htmx/table/ and /riders/htmx/detail/<pk>/. The rider content templates
# are pre-wired to these `name=`s, so a host dashboard that loads those templates
# gets all the reactivity for free — it never references a rider URL.
#
# As with trips there is deliberately no page route here: the navigable /riders/
# page is served by the host dashboard (app), which renders riders/pages/riders.html
# into its own shell. This module owns only the fragments the page calls back to.
urlpatterns = [
    path("htmx/table/", views.table, name="riders_htmx_table"),
    path("htmx/detail/<int:pk>/", views.detail, name="riders_htmx_detail"),
    path("htmx/list/", views.index, name="riders_htmx_index"),
]
