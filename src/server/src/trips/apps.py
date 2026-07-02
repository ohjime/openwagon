from django.apps import AppConfig


class TripsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Top-level feature module (sibling to `app`, `drivers`, `riders`, `core`) —
    # not nested under `app`. It is NOT a dashboard: it ships the trip content
    # templates plus the htmx endpoints they call (trips/urls.py), and a host
    # dashboard loads its content. The label `trips` namespaces this app's
    # templates dir (trips/templates/trips/) and its cotton components
    # (templates/cotton/trips/).
    name = "trips"
