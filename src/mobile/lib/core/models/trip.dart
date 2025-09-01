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
      'destination_id': destinationId,
      'destination_address': destinationAddress,
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
