part of 'trip_list_bloc.dart';

@immutable
sealed class TripListEvent {}

final class TripListSubscriptionRequested extends TripListEvent {
  TripListSubscriptionRequested();
}

final class TripListFilterChanged extends TripListEvent {
  TripListFilterChanged(this.filter);

  final TripViewFilter filter;
}

final class TripListRefreshed extends TripListEvent {
  TripListRefreshed();
}
