/* Makes GeoDjango's OSM point widget on the Vehicle admin (Vehicle.last_location)
   click-to-(re)place instead of place-once.

    Django exposes the widget's MapWidget instance as a global named after the
    field — `last_location` -> `geodjango_last_location` — and loads OpenLayers 7
    as the global `ol`. The widget's init runs inline in the body, so both exist
    by DOMContentLoaded; we wait for that (mirroring core/zone_admin_map.js).

    Why this is needed: last_location is a PointField, i.e. a *non-collection*
    geometry. The stock OLMapWidget treats that as "one feature, ever" — after a
    point is added it calls disableDrawing(), and it also disables on load when
    the field already has a value. From then on map clicks only pan; the pin can
    be nudged with a drag or wiped via the "Delete all Features" link (which sits
    below the map, easily off-screen), but a plain click won't move it. On the
    change form of a vehicle that already has a fix the widget therefore loads
    with drawing already off, which reads as "the map moves but won't set a pin."

    The Zone widget doesn't hit this: Zone.area is a MultiPolygon (a collection),
    so its widget never auto-disables — it only needs to enforce one polygon. A
    point needs both: keep drawing enabled AND replace the previous point, so
    that setting or moving the location is a single click in every state. */
'use strict';
(function () {
    var MODULE = 'geodjango_last_location';

    function onReady(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    // The inline init normally runs before DOMContentLoaded, but poll briefly
    // in case media ordering delays it, then give up quietly.
    function withWidget(cb, tries) {
        var widget = window[MODULE];
        if (widget && widget.map && widget.ready) {
            cb(widget);
        } else if ((tries || 0) < 40) {
            window.setTimeout(function () { withWidget(cb, (tries || 0) + 1); }, 50);
        }
    }

    onReady(function () {
        withWidget(enableClickToReplace);
    });

    function enableClickToReplace(widget) {
        var draw = widget.interactions && widget.interactions.draw;
        var features = widget.featureCollection;
        if (!draw || !features) { return; }

        // Each new point replaces the previous one. OpenLayers dispatches
        // `drawend` *before* it pushes the finished feature into the collection,
        // so clearing here drops the old point and leaves only the new one;
        // serializeFeatures() then runs on the subsequent 'add' and writes the
        // single Point to the hidden field. Same trick as zone_admin_map.js.
        draw.on('drawend', function () { features.clear(); });

        // MapWidget's own 'add' handler calls disableDrawing() for a
        // non-collection field. Ours is registered after it and fires in the
        // same dispatch, so drawing ends each placement re-enabled — the admin
        // can keep clicking to reposition the pin.
        features.on('add', function () { widget.enableDrawing(); });

        // Undo the disable that ran during construction: the change form of a
        // vehicle that already has a location loads with drawing off.
        widget.enableDrawing();
    }
})();
