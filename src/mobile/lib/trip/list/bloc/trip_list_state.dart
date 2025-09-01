part of 'trip_list_bloc.dart';

enum TripListStatus { initial, loading, success, failure }

enum TripViewFilter {
  all,
  scheduled,
  assigned,
  enRoute,
  arrived,
  inProgress,
  completed,
  canceled,
}

extension TripViewFilterX on TripViewFilter {
  bool apply(Trip trip) {
    switch (this) {
      case TripViewFilter.all:
        return true;
      case TripViewFilter.scheduled:
        return trip.status == 'scheduled';
      case TripViewFilter.assigned:
        return trip.status == 'assigned';
      case TripViewFilter.enRoute:
        return trip.status == 'en_route';
      case TripViewFilter.arrived:
        return trip.status == 'arrived';
      case TripViewFilter.inProgress:
        return trip.status == 'in_progress';
      case TripViewFilter.completed:
        return trip.status == 'completed';
      case TripViewFilter.canceled:
        return trip.status == 'canceled';
    }
  }

  Iterable<Trip> applyAll(Iterable<Trip> trips) => trips.where(apply);
}

@immutable
class TripListState extends Equatable {
  const TripListState({
    this.status = TripListStatus.initial,
    this.trips = const [],
    this.filter = TripViewFilter.all,
  });

  final TripListStatus status;
  final List<Trip> trips;
  final TripViewFilter filter;

  Iterable<Trip> get filteredTrips => filter.applyAll(trips);

  TripListState copyWith({
    TripListStatus? status,
    List<Trip>? trips,
    TripViewFilter? filter,
  }) {
    return TripListState(
      status: status ?? this.status,
      trips: trips ?? this.trips,
      filter: filter ?? this.filter,
    );
  }

  @override
  List<Object?> get props => [status, trips, filter];
}
