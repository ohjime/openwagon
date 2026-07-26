import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import 'package:app/core/core.dart';
import 'package:app/driver/tracking/tracking.dart';

/// The trip's route map: a straight-line path between origin and destination
/// with pinned ends, framed to show both, plus a live driver pin.
///
/// Coordinates come from the [Trip] (the server geocodes the Google place ids
/// into lat/lng). The driver pin is driven by [LocationTrackingBloc.lastPosition]
/// — the fix captured on-device right before locus uploads it — so the pin
/// tracks the driver with no server round-trip. It's absent until sharing yields
/// a fix, and the map still shows the route without it.
///
/// The camera frames the origin/destination once the map is ready (that's the
/// "centered / pre-zoomed" ask); it deliberately does NOT re-frame as the driver
/// moves, so the view doesn't jerk on every fix — the pin just glides within.
///
/// When either end lacks a coordinate (the server hasn't geocoded it yet) there
/// is no route to frame, so a neutral placeholder is shown instead.
class TripRouteMap extends StatefulWidget {
  const TripRouteMap({required this.trip, super.key});

  final Trip trip;

  @override
  State<TripRouteMap> createState() => _TripRouteMapState();
}

class _TripRouteMapState extends State<TripRouteMap> {
  final MapController _controller = MapController();

  LatLng? get _origin {
    final lat = widget.trip.originLat;
    final lng = widget.trip.originLng;
    return (lat != null && lng != null) ? LatLng(lat, lng) : null;
  }

  LatLng? get _destination {
    final lat = widget.trip.destinationLat;
    final lng = widget.trip.destinationLng;
    return (lat != null && lng != null) ? LatLng(lat, lng) : null;
  }

  /// Frame the camera to show both ends with padding so the pins clear the
  /// edges. Called once the map is ready (both ends are known by then — the
  /// build guards on it).
  void _frameRoute(LatLng origin, LatLng destination) {
    _controller.fitCamera(
      CameraFit.coordinates(
        coordinates: [origin, destination],
        padding: const EdgeInsets.all(48),
        maxZoom: 16,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final origin = _origin;
    final destination = _destination;

    // No route to draw without both ends — show a neutral placeholder rather
    // than an unframed world map.
    if (origin == null || destination == null) {
      return const _MapPlaceholder();
    }

    final theme = Theme.of(context);
    // The driver's latest local fix (null until sharing yields one). Rebuilds
    // only when the position actually changes.
    final driver = context.select(
      (LocationTrackingBloc bloc) => bloc.state.lastPosition,
    );

    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: AspectRatio(
        aspectRatio: 16 / 9,
        child: FlutterMap(
          mapController: _controller,
          options: MapOptions(
            initialCenter: origin,
            initialZoom: 12,
            onMapReady: () => _frameRoute(origin, destination),
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'ca.waygon.app',
            ),
            PolylineLayer(
              polylines: [
                Polyline(
                  points: [origin, destination],
                  strokeWidth: 4,
                  color: theme.colorScheme.primary,
                ),
              ],
            ),
            MarkerLayer(
              markers: [
                _endMarker(origin, Icons.trip_origin, Colors.green.shade700),
                _endMarker(
                  destination,
                  Icons.location_on,
                  Colors.red.shade700,
                ),
                if (driver != null) _driverMarker(driver, theme),
              ],
            ),
            const RichAttributionWidget(
              attributions: [
                TextSourceAttribution(
                  '© OpenStreetMap contributors',
                  onTap: null,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Marker _endMarker(LatLng point, IconData icon, Color color) {
    return Marker(
      point: point,
      width: 40,
      height: 40,
      alignment: Alignment.topCenter,
      child: Icon(icon, size: 32, color: color),
    );
  }

  /// The driver's live position — a car in a colored chip, echoing the web map's
  /// car pin so the two surfaces read the same.
  Marker _driverMarker(LatLng point, ThemeData theme) {
    return Marker(
      point: point,
      width: 40,
      height: 40,
      child: Container(
        decoration: BoxDecoration(
          color: theme.colorScheme.primary,
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white, width: 3),
          boxShadow: const [
            BoxShadow(color: Colors.black26, blurRadius: 4, offset: Offset(0, 2)),
          ],
        ),
        child: Icon(
          Icons.local_taxi,
          size: 20,
          color: theme.colorScheme.onPrimary,
        ),
      ),
    );
  }
}

/// Shown when the trip's ends aren't geocoded yet, so there's no route to frame.
class _MapPlaceholder extends StatelessWidget {
  const _MapPlaceholder();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: AspectRatio(
        aspectRatio: 16 / 9,
        child: Container(
          color: theme.colorScheme.surfaceContainerHighest,
          alignment: Alignment.center,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.map_outlined,
                size: 32,
                color: theme.colorScheme.onSurfaceVariant,
              ),
              const SizedBox(height: 8),
              Text(
                'Route preview unavailable',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
