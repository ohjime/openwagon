import 'dart:async';

import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:latlong2/latlong.dart';

import 'package:app/core/core.dart';

part 'location_tracking_event.dart';
part 'location_tracking_state.dart';

/// Owns the driver's background location-sharing lifecycle.
///
/// The tracking itself — GPS capture + upload to `/api/drivers/location` — runs
/// in the platform's native background service via [LocationRepository]/locus,
/// so it keeps flowing while the app is backgrounded or the trip screen is
/// popped. This bloc just switches that native service on/off in response to
/// trip state and mirrors its status for the UI.
///
/// It is provided ABOVE the app's router (see main.dart) so a single tracking
/// authority survives every route change. It stays [LocationTrackingStatus.idle]
/// until something dispatches [LocationTrackingStarted] — riders never do, so it
/// costs them nothing.
class LocationTrackingBloc
    extends Bloc<LocationTrackingEvent, LocationTrackingState> {
  LocationTrackingBloc({required LocationRepository locationRepository})
    : _locationRepository = locationRepository,
      super(const LocationTrackingState()) {
    on<LocationTrackingStarted>(_onStarted);
    on<LocationTrackingStopped>(_onStopped);
    on<_LocationTrackingPositionReceived>(_onPositionReceived);
    on<_LocationTrackingSyncMessageReceived>(_onSyncMessageReceived);
  }

  final LocationRepository _locationRepository;
  StreamSubscription<LatLng>? _positionSub;
  StreamSubscription<String>? _syncSub;

  Future<void> _onStarted(
    LocationTrackingStarted event,
    Emitter<LocationTrackingState> emit,
  ) async {
    // Already sharing — nothing to do. Keeps repeated starts (e.g. reopening a
    // trip that's already active) from re-prompting or restarting the service.
    if (state.status == LocationTrackingStatus.active) return;
    emit(state.copyWith(status: LocationTrackingStatus.requestingPermission));
    try {
      final granted = await _locationRepository.requestPermission();
      if (!granted) {
        emit(state.copyWith(status: LocationTrackingStatus.permissionDenied));
        return;
      }
      await _locationRepository.startTracking();
      await _positionSub?.cancel();
      _positionSub = _locationRepository.positions.listen(
        (position) => add(_LocationTrackingPositionReceived(position)),
      );
      await _syncSub?.cancel();
      _syncSub = _locationRepository.syncEvents.listen(
        (message) => add(_LocationTrackingSyncMessageReceived(message)),
      );
      emit(state.copyWith(status: LocationTrackingStatus.active));
    } catch (error) {
      emit(
        state.copyWith(
          status: LocationTrackingStatus.failure,
          errorMessage: '$error',
        ),
      );
    }
  }

  Future<void> _onStopped(
    LocationTrackingStopped event,
    Emitter<LocationTrackingState> emit,
  ) async {
    await _positionSub?.cancel();
    _positionSub = null;
    await _syncSub?.cancel();
    _syncSub = null;
    try {
      await _locationRepository.stopTracking();
    } catch (_) {
      // Best-effort teardown; the UI should return to idle regardless.
    }
    emit(state.copyWith(status: LocationTrackingStatus.idle));
  }

  void _onPositionReceived(
    _LocationTrackingPositionReceived event,
    Emitter<LocationTrackingState> emit,
  ) {
    emit(state.copyWith(lastPosition: event.position));
  }

  void _onSyncMessageReceived(
    _LocationTrackingSyncMessageReceived event,
    Emitter<LocationTrackingState> emit,
  ) {
    emit(state.copyWith(lastSyncMessage: event.message));
  }

  @override
  Future<void> close() {
    _positionSub?.cancel();
    _syncSub?.cancel();
    return super.close();
  }
}
