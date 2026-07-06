/* Augments GeoDjango's OSM drawing widget on the Zone admin (Zone.area).

    Django exposes the widget's MapWidget instance as a global named after the
    field — `area` -> `geodjango_area` — and loads OpenLayers 7 as the global
    `ol`. The widget's init runs inline in the body, so both exist by
    DOMContentLoaded; we wait for that, then bolt on three things the stock
    widget lacks:

     1. A place search box, so an admin can jump to a city instead of
        hand-panning and zooming. Geocoding uses OSM Nominatim (keyless,
        CORS-enabled, and consistent with the OSM base layer); the app's Google
        Maps key stays where it already is — geocoding, Places, directions.
         2. Single-polygon enforcement. Zone.area is a MultiPolygon, so the stock
                widget happily paints several rings into one value; a zone is one
                service area, so each finished polygon replaces the previous one. See
                the note in core/admin.py for where multiple polygons would belong.
      3. A clear action plus Escape-to-cancel, so admins can remove the current
          shape or abandon a half-drawn sketch without reaching for the stock
          OpenLayers controls. */
'use strict';
(function () {
    var MODULE = 'geodjango_area';

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
        withWidget(function (widget) {
            enforceSinglePolygon(widget);
            addSearchBox(widget);
        });
    });

    // --- Single polygon -----------------------------------------------------
    function enforceSinglePolygon(widget) {
        var draw = widget.interactions && widget.interactions.draw;
        if (!draw) { return; }
        draw.on('drawend', function () {
            // OpenLayers dispatches `drawend` *before* it pushes the finished
            // feature into the collection, so clearing here drops the previous
            // polygon and leaves only the new one. serializeFeatures() then
            // runs on the subsequent 'add' and writes a single-member
            // MultiPolygon to the hidden field.
            widget.featureCollection.clear();
        });
    }

    // --- City / address search ---------------------------------------------
    function addSearchBox(widget) {
        var map = widget.map;
        var wrapper = document.getElementById(widget.options.id + '_div_map');
        var mapEl = document.getElementById(widget.options.map_id);
        if (!wrapper || !mapEl) { return; }

        // A <div>, not a <form>: the widget lives inside the admin change form,
        // and a nested <form> (or a submit button / bare Enter) would submit
        // that outer form and save a half-drawn zone.
        var box = document.createElement('div');
        box.className = 'zone-map-search';

        var input = document.createElement('input');
        input.type = 'search';
        input.placeholder = 'Search for a city or address…';
        input.setAttribute('aria-label', 'Search the map for a place');
        input.className = 'zone-map-search__input';

        var button = document.createElement('button');
        button.type = 'button';
        button.textContent = 'Search';
        button.className = 'zone-map-search__button';

        var clearButton = document.createElement('button');
        clearButton.type = 'button';
        clearButton.textContent = 'Remove shape';
        clearButton.className = 'zone-map-search__button';
        clearButton.disabled = true;

        var status = document.createElement('span');
        status.className = 'zone-map-search__status';
        status.setAttribute('role', 'status');

        box.appendChild(input);
        box.appendChild(button);
        box.appendChild(clearButton);
        box.appendChild(status);
        wrapper.insertBefore(box, mapEl);

        function refreshClearButton() {
            clearButton.disabled = !widget.featureCollection ||
                widget.featureCollection.getLength() === 0;
        }

        refreshClearButton();

        function run() {
            var query = input.value.trim();
            if (query) { search(query, map, button, status); }
        }
        clearButton.addEventListener('click', function () {
            if (!widget.featureCollection) { return; }
            widget.featureCollection.clear();
            refreshClearButton();
            status.textContent = 'Shape removed.';
        });
        button.addEventListener('click', run);
        input.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // don't submit the admin change form
                run();
            } else if (event.key === 'Escape') {
                event.preventDefault();
                if (widget.interactions && widget.interactions.draw &&
                        widget.interactions.draw.abortDrawing) {
                    widget.interactions.draw.abortDrawing();
                    status.textContent = 'Drawing cancelled.';
                }
                input.blur();
            }
        });

        if (widget.featureCollection && widget.featureCollection.on) {
            widget.featureCollection.on('add', refreshClearButton);
            widget.featureCollection.on('remove', refreshClearButton);
            widget.featureCollection.on('clear', refreshClearButton);
        }

        if (widget.interactions && widget.interactions.draw &&
                widget.interactions.draw.on) {
            widget.interactions.draw.on('drawend', refreshClearButton);
        }

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && widget.interactions &&
                    widget.interactions.draw && widget.interactions.draw.abortDrawing) {
                event.preventDefault();
                widget.interactions.draw.abortDrawing();
                status.textContent = 'Drawing cancelled.';
            }
        });
    }

    function search(query, map, button, status) {
        var url = 'https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=' +
            encodeURIComponent(query);
        button.disabled = true;
        status.textContent = 'Searching…';
        fetch(url, {headers: {'Accept': 'application/json'}})
            .then(function (resp) {
                if (!resp.ok) { throw new Error('HTTP ' + resp.status); }
                return resp.json();
            })
            .then(function (results) {
                if (!results || !results.length) {
                    status.textContent = 'No match found.';
                    return;
                }
                status.textContent = '';
                fitToResult(results[0], map);
            })
            .catch(function () {
                status.textContent = 'Search unavailable — try again.';
            })
            .finally(function () {
                button.disabled = false;
            });
    }

    function fitToResult(result, map) {
        var view = map.getView();
        var projection = view.getProjection();
        // Nominatim's boundingbox is [south, north, west, east] as strings;
        // fitting to it frames the whole city instead of a bare center point.
        var bbox = result.boundingbox;
        if (bbox && bbox.length === 4) {
            var south = parseFloat(bbox[0]);
            var north = parseFloat(bbox[1]);
            var west = parseFloat(bbox[2]);
            var east = parseFloat(bbox[3]);
            var extent = ol.proj.transformExtent(
                [west, south, east, north], 'EPSG:4326', projection);
            view.fit(extent, {maxZoom: 14, duration: 400});
            return;
        }
        var center = ol.proj.transform(
            [parseFloat(result.lon), parseFloat(result.lat)], 'EPSG:4326', projection);
        view.setCenter(center);
        view.setZoom(12);
    }
})();
