"""Dashboard shell helpers.

The reusable HTMX glue for the app shell that lives in `core` — any app can
build its dashboard UI on top of these without re-implementing the swap/drawer
plumbing. A view picks a template and a context; the helper handles every
swap/animation detail (where it lands, how it opens, how the navbar reacts).
Views never deal with HTML, targets, or events — they just say which template
to show. (Moved here from the old `shell.utils`.)

The host app creates ONE `Dashboard` instance, configured once with its display
name, the base template that wires in its nav, and (sharing a default) the
product name. The header label and browser-tab title are *fixed* for the whole
dashboard — they come from the instance, not the page — so moving between pages
never changes them; the active sidebar item (and the breadcrumb derived from it)
is the only thing that tracks location. The instance's methods are the same swap
helpers with the base template and names already baked in, so views stop
repeating them. (Core names no app/feature itself — the example below is just
illustrative.)

    # myapp/dashboard.py
    dashboard = Dashboard(name="Dispatcher", base_template="myapp/base.html")

    # myapp/views.py
    from myapp.dashboard import dashboard

    def index(request):
        return dashboard.nav_response(
            request, "myapp/pages/home.html", {"table": ...}, key="home")
"""

import json

from django.http import HttpResponse
from django.shortcuts import render


class Dashboard:
    """One feature's dashboard shell.

    `name` is the fixed header label and the first half of the browser-tab title
    ("<name> | <site_name>"); both stay put as you navigate within the feature,
    so the active sidebar item is the single source of truth for location.
    `base_template` is the feature's shell — one that extends core's
    `dashboard/base.html` and fills the `nav_items` / `nav_actions` blocks — so
    core never has to know an app's routes. `site_name` is the product brand,
    shared across features (default "Waygon").
    """

    def __init__(self, *, name, base_template, site_name="Waygon"):
        self.name = name
        self.base_template = base_template
        self.site_name = site_name

    def _context(self, context, key):
        """Merge the caller's context with the shell vars every full-shell
        render needs: the active nav key plus the fixed header/tab names."""
        return {
            **(context or {}),
            "active_nav": key,
            "dashboard_name": self.name,
            "site_name": self.site_name,
        }

    def page(self, request, content_template, context=None, *, key=""):
        """A static shell page — a landing/home view with nothing (or a fixed
        item) selected. Always the full shell; no htmx swap or pushed URL. The
        `content_template` itself extends this feature's base and fills the
        `content` block.

            def index(request):
                return dashboard.page(request, "app/home.html")
        """
        return render(request, content_template, self._context(context, key))

    def nav_response(self, request, content_template, context=None, *, key, push_url=None):
        """
        One helper for every navigable shell page. The *same view* serves two
        shapes and the request decides which — so a nav link and a typed-in URL
        hit the exact same endpoint. The active route is the single source of
        truth for what's selected; this helper just renders the right shape and
        tells the navbar which item to light up.

            def drivers(request):
                return dashboard.nav_response(
                    request, "drivers/pages/drivers.html", {"table": ...}, key="drivers")

        Full shell — a cold visit, a refresh, or htmx restoring a history entry
        (it swaps the whole <body>). Renders the feature's `base_template` with
        `content_template` already embedded in #app_content and the navbar's
        indicator pre-lit for `key`. Land on the URL directly and the page is
        complete, indicator and breadcrumb and all.

        Fragment — a live htmx nav click. Renders only `content_template` into
        #app_content, pushes `push_url` (default: the current full path) into the
        address bar + history, and fires `nav:active` so the navbar moves its
        indicator to `key` (plus `nav:close` to collapse the sidebar). The navbar
        re-derives the breadcrumb trail from `key` on its own — the view never
        names a title.

        `context` is passed straight through to `content_template` in BOTH shapes,
        so a view can forward extra params (anything off request.GET, say) without
        this helper having to know about them.
        """
        context = self._context(context, key)

        # Anything that isn't a live in-page swap gets the whole shell: a cold
        # URL visit (no HX-Request) or htmx asking for a full page to restore.
        if not request.htmx or request.htmx.history_restore_request:
            return render(
                request,
                self.base_template,
                {**context, "content_template": content_template},
            )

        # Live htmx swap: just the content region + the URL and indicator updates.
        response = render(request, content_template, context)
        response["HX-Retarget"] = "#app_content"
        response["HX-Reswap"] = "innerHTML"
        response["HX-Push-Url"] = push_url or request.get_full_path()
        response["HX-Trigger-After-Swap"] = json.dumps(
            {"nav:active": {"key": key}, "nav:close": True}
        )
        return response

    def swap_content(self, request, template, context=None, *, close_nav=True):
        """
        Render `template` into the main content region (#app_content). The swap-in
        animation is handled by CSS in dashboard/base.html (every fresh child of
        #app_content fades/slides in), so the template just renders its content.

            return dashboard.swap_content(request, "dashboard/pages/trips.html", {"trips": trips})

        By default this also fires `nav:close`, which the navbar listens for to
        animate shut. Pass close_nav=False to leave the navbar open.
        """
        response = render(request, template, context or {})
        response["HX-Retarget"] = "#app_content"
        response["HX-Reswap"] = "innerHTML"
        if close_nav:
            response["HX-Trigger-After-Swap"] = "nav:close"
        return response

    def close_drawer(self, request, template=None, context=None, reswap=None):
        """
        Close the trip drawer (#trip_drawer) by firing `close-drawer`. Optionally
        render a template whose body holds `hx-swap-oob` elements to update other
        parts of the page at the same time; `reswap` overrides the triggering
        element's hx-swap (defaults to "none" so the main swap is suppressed when
        OOB content is used).
        """
        if template:
            response = render(request, template, context or {})
        else:
            response = HttpResponse("")

        response["HX-Reswap"] = reswap or "none"
        response["HX-Trigger"] = "close-drawer"
        return response


def swap_content(request, template, context=None, *, close_nav=True):
    """Render `template` into the shell's main content region (#app_content).

    The instance-free counterpart to Dashboard.swap_content, for feature modules
    that swap their own content — e.g. a table row drilling into a detail page —
    without depending on a host app's Dashboard instance (so they depend on core
    only). Fires `nav:close` so the sidebar collapses, like a nav click.

        from core.dashboard import swap_content
        return swap_content(request, "drivers/pages/driver_detail.html", {...})

    There is intentionally NO instance-free drawer opener. The one drawer in the
    app — the trip detail drawer — is opened only by core.views.trip_drawer, which
    is hard-wired to a single core template. Without a generic "open any template
    in the drawer" helper, no feature can slide arbitrary content over the page.
    """
    response = render(request, template, context or {})
    response["HX-Retarget"] = "#app_content"
    response["HX-Reswap"] = "innerHTML"
    if close_nav:
        response["HX-Trigger-After-Swap"] = "nav:close"
    return response
