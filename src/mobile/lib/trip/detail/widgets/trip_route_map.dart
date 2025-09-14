import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

class TripRouteMap extends StatelessWidget {
  const TripRouteMap({super.key});

  @override
  Widget build(BuildContext context) {
    // Pick a random-ish, but deterministic location for now (e.g., London fallback)
    final rnd = Random();
    final lat = 51.509364 + (rnd.nextDouble() * 0.1 - 0.05); // ~London area
    final lng = -0.128928 + (rnd.nextDouble() * 0.1 - 0.05);
    final center = LatLng(lat, lng);

    // Constrain height since this sits inside a Column
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: AspectRatio(
        aspectRatio: 16 / 9,
        child: FlutterMap(
          options: MapOptions(initialCenter: center, initialZoom: 12),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              // IMPORTANT: Set to your real package ID to comply with OSM policy
              userAgentPackageName: 'com.ohjime.wagon',
            ),
            MarkerLayer(
              markers: [
                Marker(
                  point: center,
                  width: 40,
                  height: 40,
                  child: const Icon(
                    Icons.location_pin,
                    size: 40,
                    color: Colors.red,
                  ),
                ),
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
}
