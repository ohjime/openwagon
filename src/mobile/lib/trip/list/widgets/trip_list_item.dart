import 'package:app/core/models/trip.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

class TripListItem extends StatelessWidget {
  const TripListItem({super.key, required this.trip});

  final Trip trip;

  String _formatDate(DateTime? dt) {
    if (dt == null) return 'TBD';
    final fmt = DateFormat('MMM d, yyyy h:mm a');
    return fmt.format(dt.toLocal());
  }

  @override
  Widget build(BuildContext context) {
    final title = '${trip.originAddress} → ${trip.destinationAddress}';
    final subtitle = '${trip.status} • ${_formatDate(trip.date)}';

    return ListTile(
      key: Key('tripListItem_${trip.id}_${trip.hashid}'),
      title: Text(
        title,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(subtitle),
      leading: const Icon(Icons.directions_car_rounded),
      dense: false,
    );
  }
}
