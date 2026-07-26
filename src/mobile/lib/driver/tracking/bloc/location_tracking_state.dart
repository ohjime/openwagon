part of 'location_tracking_bloc.dart';

enum LocationTrackingStatus {
  /// Not sharing.
  idle,

  /// Waiting on the OS permission prompt.
  requestingPermission,

  /// Sharing — the background service is running.
  active,

  /// The user declined the location permission.
  permissionDenied,

  /// Something went wrong starting the service.
  failure,
}

class LocationTrackingState extends Equatable {
  const LocationTrackingState({
    this.status = LocationTrackingStatus.idle,
    this.lastPosition,
    this.errorMessage,
    this.lastSyncMessage,
  });

  final LocationTrackingStatus status;
  final LatLng? lastPosition;
  final String? errorMessage;

  /// Newest line from the native uploader's [HttpEvent] feed (e.g.
  /// "sync OK 200 sent=1" or "sync FAIL 0 sync_body_builder_failed"). Surfaced
  /// under the location banner so upload outcomes are visible on-device in a
  /// release build. Null until the first sync attempt.
  final String? lastSyncMessage;

  /// Whether we're actively sharing — drives the in-app "sharing" indicator.
  bool get isSharing => status == LocationTrackingStatus.active;

  LocationTrackingState copyWith({
    LocationTrackingStatus? status,
    LatLng? lastPosition,
    String? errorMessage,
    String? lastSyncMessage,
  }) {
    return LocationTrackingState(
      status: status ?? this.status,
      lastPosition: lastPosition ?? this.lastPosition,
      errorMessage: errorMessage,
      lastSyncMessage: lastSyncMessage ?? this.lastSyncMessage,
    );
  }

  @override
  List<Object?> get props => [
    status,
    lastPosition,
    errorMessage,
    lastSyncMessage,
  ];
}
