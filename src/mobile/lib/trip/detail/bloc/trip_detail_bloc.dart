import 'package:bloc/bloc.dart';
import 'package:app/core/repositories/trip_repository.dart';
import 'package:equatable/equatable.dart';
import 'package:app/core/models/trip.dart';

part 'trip_detail_event.dart';
part 'trip_detail_state.dart';

class TripDetailBloc extends Bloc<TripDetailEvent, TripDetailState> {
  TripDetailBloc({required TripRepository tripRepository})
    : _tripRepository = tripRepository,
      super(const TripDetailState()) {
    on<TripDetailInitialized>(_onInitialized);
    on<TripDetailDriverNotesChanged>(_onDriverNotesChanged);
    on<TripDetailStatusChanged>(_onStatusChanged);
    on<TripDetailSubmitted>(_onSubmitted);
  }

  final TripRepository _tripRepository;

  void _onInitialized(
    TripDetailInitialized event,
    Emitter<TripDetailState> emit,
  ) {
    emit(
      state.copyWith(
        status: TripDetailStatus.editing,
        trip: event.trip,
        driverNotes: event.trip.driverNotes,
        selectedStatus: event.trip.status,
      ),
    );
  }

  void _onDriverNotesChanged(
    TripDetailDriverNotesChanged event,
    Emitter<TripDetailState> emit,
  ) {
    emit(state.copyWith(driverNotes: event.notes));
  }

  void _onStatusChanged(
    TripDetailStatusChanged event,
    Emitter<TripDetailState> emit,
  ) {
    emit(state.copyWith(selectedStatus: event.status));
  }

  Future<void> _onSubmitted(
    TripDetailSubmitted event,
    Emitter<TripDetailState> emit,
  ) async {
    final trip = state.trip;
    if (trip == null) return;
    emit(state.copyWith(status: TripDetailStatus.submitting));
    try {
      final updated = await _tripRepository.updateTripAsDriver(
        tripId: trip.id,
        status: state.selectedStatus,
        driverNotes: state.driverNotes,
      );
      emit(
        state.copyWith(
          status: TripDetailStatus.success,
          trip: updated,
          selectedStatus: updated.status,
          driverNotes: updated.driverNotes,
        ),
      );
    } catch (e) {
      emit(
        state.copyWith(status: TripDetailStatus.failure, errorMessage: '$e'),
      );
    }
  }
}
