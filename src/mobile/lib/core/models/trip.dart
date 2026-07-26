class Trip {
  const Trip({
    required this.id,
    required this.hashid,
    required this.driverId,
    required this.riderId,
    required this.status,
    required this.originId,
    required this.originAddress,
    required this.destinationId,
    required this.destinationAddress,
    this.originLat,
    this.originLng,
    this.destinationLat,
    this.destinationLng,
    this.date,
    this.customerNotes = '',
    this.driverNotes = '',
    this.dispatcherNotes = '',
  });

  final int id;
  final String hashid;
  final int driverId;
  final int riderId;
  final DateTime? date;
  final String originId;
  final String originAddress;
  final String destinationId;
  final String destinationAddress;
  // Geocoded ends. Null when the server hasn't resolved the place id to a
  // coordinate yet (e.g. no Google key, or a geocode miss) — the map treats a
  // missing end as "no route to draw".
  final double? originLat;
  final double? originLng;
  final double? destinationLat;
  final double? destinationLng;
  final String status;
  final String customerNotes;
  final String driverNotes;
  final String dispatcherNotes;

  factory Trip.fromJson(Map<String, dynamic> json) {
    return Trip(
      id: json['id'] as int,
      hashid: json['hashid'] as String,
      driverId: json['driver_id'] as int,
      riderId: json['rider_id'] as int,
      date: json['date'] != null && (json['date'] as String).isNotEmpty
          ? DateTime.parse(json['date'] as String)
          : null,
      originId: json['origin_id'] as String,
      originAddress: json['origin_address'] as String,
      destinationId: json['destination_id'] as String,
      destinationAddress: json['destination_address'] as String,
      originLat: (json['origin_lat'] as num?)?.toDouble(),
      originLng: (json['origin_lng'] as num?)?.toDouble(),
      destinationLat: (json['destination_lat'] as num?)?.toDouble(),
      destinationLng: (json['destination_lng'] as num?)?.toDouble(),
      status: json['status'] as String,
      customerNotes: (json['customer_notes'] ?? '') as String,
      driverNotes: (json['driver_notes'] ?? '') as String,
      dispatcherNotes: (json['dispatcher_notes'] ?? '') as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'hashid': hashid,
      'driver_id': driverId,
      'rider_id': riderId,
      'date': date?.toIso8601String(),
      'origin_id': originId,
      'origin_address': originAddress,
      'origin_lat': originLat,
      'origin_lng': originLng,
      'destination_id': destinationId,
      'destination_address': destinationAddress,
      'destination_lat': destinationLat,
      'destination_lng': destinationLng,
      'status': status,
      'customer_notes': customerNotes,
      'driver_notes': driverNotes,
      'dispatcher_notes': dispatcherNotes,
    };
  }

  @override
  String toString() {
    return 'Trip(id: '
        '$id, hashid: $hashid, driverId: $driverId, riderId: $riderId, '
        'date: ${date?.toIso8601String()}, origin: $originAddress, '
        'destination: $destinationAddress, status: $status)';
  }
}

// Ordered list of statuses; keep in sync with server core.models.TripStatus.
// NOTE: the server value is 'enroute' (no underscore) — must match exactly or
// status writes are rejected.
const kTripStatuses = <String>[
  'unassigned',
  'assigned',
  'enroute',
  'arrived',
  'in_progress',
  'completed',
  'canceled',
];

// The statuses a driver may set from the app, in the order they progress. The
// server restricts driver updates to everything except 'unassigned'
// (assignment is the dispatcher's job) — see app.api._DRIVER_SETTABLE_STATUSES.
const kDriverTripFlow = <String>[
  'enroute',
  'arrived',
  'in_progress',
  'completed',
];
const kTripCanceledStatus = 'canceled';

// The statuses during which a driver is actually on the road and should be
// sharing location: from 'enroute' through the ride itself. Before this
// ('assigned') there's nothing to track; after it ('completed'/'canceled') the
// trip is over. Drives [LocationTrackingBloc] start/stop.
const kTripTrackingStatuses = <String>['enroute', 'arrived', 'in_progress'];

/// Whether a trip in [status] should be sharing the driver's location.
bool tripSharesLocation(String status) => kTripTrackingStatuses.contains(status);

/// Human label for a status value, e.g. 'in_progress' -> 'In Progress'.
String tripStatusLabel(String status) {
  return status
      .split('_')
      .where((part) => part.isNotEmpty)
      .map((part) => part[0].toUpperCase() + part.substring(1))
      .join(' ');
}
