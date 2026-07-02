from core.dashboard import Dashboard

# The `app` dashboard shell. `app` is the concrete application — it owns the
# django-ninja API (api.py) and, since the old `app.dispatch` sub-app was merged
# up into it, the dispatcher dashboard itself. One instance fixes the header
# label / browser-tab name ("Dispatcher | Waygon") and the base template that
# wires this dashboard's nav into the core shell, so every view just names a
# template and hands it data — never a title, target, or base template.
dashboard = Dashboard(name="Dispatch Center", base_template="app/base.html")
