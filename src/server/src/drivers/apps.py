from django.apps import AppConfig


class DriversConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Top-level feature module (sibling to `trips`, `riders`, `app`, `core`) — not
    # nested under `app`. Like `trips` it is NOT a dashboard: it ships the driver
    # content templates plus the htmx endpoints they call (drivers/urls.py), and a
    # host dashboard (`app`) loads its content. It has no models of its own — it
    # reads core.Driver. The label `drivers` namespaces this app's templates dir
    # (drivers/templates/drivers/) and its cotton components (templates/cotton/drivers/).
    name = "drivers"
