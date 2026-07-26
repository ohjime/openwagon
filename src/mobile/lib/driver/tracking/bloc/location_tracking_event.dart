part of 'location_tracking_bloc.dart';

sealed class LocationTrackingEvent extends Equatable {
  const LocationTrackingEvent();

  @override
  List<Object?> get props => [];
}

/// Start sharing the driver's location (requests permission if needed).
class LocationTrackingStarted extends LocationTrackingEvent {
  const LocationTrackingStarted();
}

/// Stop sharing and tear down the background service.
class LocationTrackingStopped extends LocationTrackingEvent {
  const LocationTrackingStopped();
}

/// Internal: a new fix arrived from the repository's position stream.
class _LocationTrackingPositionReceived extends LocationTrackingEvent {
  const _LocationTrackingPositionReceived(this.position);

  final LatLng position;

  @override
  List<Object?> get props => [position];
}

/// Internal: a new upload outcome arrived from the repository's sync-event feed.
class _LocationTrackingSyncMessageReceived extends LocationTrackingEvent {
  const _LocationTrackingSyncMessageReceived(this.message);

  final String message;

  @override
  List<Object?> get props => [message];
}
