import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:meta/meta.dart';

import 'package:app/core/repositories/trip_repository.dart';
import 'package:app/core/models/trip.dart';

part 'trip_list_event.dart';
part 'trip_list_state.dart';

class TripListBloc extends Bloc<TripListEvent, TripListState> {
  TripListBloc({required TripRepository tripRepository})
      : _tripRepository = tripRepository,
        super(const TripListState()) {
    on<TripListSubscriptionRequested>(_onSubscriptionRequested);
    on<TripListFilterChanged>(_onFilterChanged);
    on<TripListRefreshed>(_onRefreshed);
  }

  final TripRepository _tripRepository;

  Future<void> _onSubscriptionRequested(
    TripListSubscriptionRequested event,
    Emitter<TripListState> emit,
  ) async {
    emit(state.copyWith(status: TripListStatus.loading));
    try {
      final trips = await _tripRepository.getAssignedTrips();
      emit(state.copyWith(status: TripListStatus.success, trips: trips));
    } catch (e) {
      emit(state.copyWith(status: TripListStatus.failure));
    }
  }

  Future<void> _onRefreshed(
    TripListRefreshed event,
    Emitter<TripListState> emit,
  ) async {
    try {
      final trips = await _tripRepository.getAssignedTrips();
      emit(state.copyWith(status: TripListStatus.success, trips: trips));
    } catch (e) {
      emit(state.copyWith(status: TripListStatus.failure));
    }
  }

  void _onFilterChanged(
    TripListFilterChanged event,
    Emitter<TripListState> emit,
  ) {
    emit(state.copyWith(filter: event.filter));
  }
}
