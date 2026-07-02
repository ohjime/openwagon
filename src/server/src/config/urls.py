from django.urls import include, path
from django.contrib import admin
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls, name="admin"),
    # Core's shared trip drawer endpoint (the one drawer in the app) →
    # /core/htmx/trip/<pk>/. Mounted before the app include so it resolves first.
    # Every feature that shows a trip points here, so they depend on core only.
    path("core/", include("core.urls")),
    # The trips / drivers / riders features' htmx endpoints, mounted under their
    # own prefixes → /trips/htmx/..., /drivers/htmx/..., /riders/htmx/... . Each
    # ships content + reactivity, not a shell; the navigable /trips/, /drivers/
    # and /riders/ pages are served by app's dashboard below — Django falls
    # through to it since these patterns only match the /htmx/* sub-paths. Must
    # precede the app include so those fragment URLs resolve here first.
    path("trips/", include("trips.urls")),
    path("drivers/", include("drivers.urls")),
    path("riders/", include("riders.urls")),
    # `app` owns the dispatcher dashboard plus the django-ninja API, united under
    # app.urls; config just mounts that one tree at the root. (Mounted at "" so
    # the API stays at /api/ — see app/urls.py.)
    path("", include("app.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
