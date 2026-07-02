from django.urls import path

from drivers import views

# The drivers feature's htmx reactivity endpoints, collected under the `htmx/`
# prefix. config.urls mounts this module under `drivers/`, so they resolve to
# /drivers/htmx/table/ and /drivers/htmx/detail/<pk>/. The driver content
# templates are pre-wired to these `name=`s, so a host dashboard that loads those
# templates gets all the reactivity for free — it never references a driver URL.
#
# As with trips there is deliberately no page route here: the navigable /drivers/
# page is served by the host dashboard (app), which renders drivers/pages/drivers.html
# into its own shell. This module owns only the fragments the page calls back to.
urlpatterns = [
    path("htmx/table/", views.table, name="drivers_htmx_table"),
    path("htmx/detail/<int:pk>/", views.detail, name="drivers_htmx_detail"),
    path("htmx/list/", views.index, name="drivers_htmx_index"),
]
