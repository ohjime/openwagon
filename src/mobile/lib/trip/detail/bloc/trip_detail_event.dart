part of 'trip_detail_bloc.dart';

sealed class TripDetailEvent extends Equatable {
  const TripDetailEvent();

  @override
  List<Object?> get props => [];
}

class TripDetailInitialized extends TripDetailEvent {
  const TripDetailInitialized({required this.trip});
  final Trip trip;

  @override
  List<Object?> get props => [trip];
}

class TripDetailDriverNotesChanged extends TripDetailEvent {
  const TripDetailDriverNotesChanged(this.notes);
  final String notes;

  @override
  List<Object?> get props => [notes];
}

class TripDetailStatusChanged extends TripDetailEvent {
  const TripDetailStatusChanged(this.status);
  final String status;

  @override
  List<Object?> get props => [status];
}

class TripDetailSubmitted extends TripDetailEvent {
  const TripDetailSubmitted();
}
