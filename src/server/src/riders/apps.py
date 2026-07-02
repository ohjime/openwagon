from django.apps import AppConfig


class RidersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Top-level feature module (sibling to `trips`, `drivers`, `app`, `core`) — not
    # nested under `app`. Like `trips` it is NOT a dashboard: it ships the rider
    # content templates plus the htmx endpoints they call (riders/urls.py), and a
    # host dashboard (`app`) loads its content. It has no models of its own — it
    # reads core.Rider. The label `riders` namespaces this app's templates dir
    # (riders/templates/riders/) and its cotton components (templates/cotton/riders/).
    name = "riders"
