part of 'trip_detail_bloc.dart';

enum TripDetailStatus { initial, editing, submitting, success, failure }

class TripDetailState extends Equatable {
  const TripDetailState({
    this.status = TripDetailStatus.initial,
    this.trip,
    this.driverNotes = '',
    this.selectedStatus,
    this.errorMessage,
  });

  final TripDetailStatus status;
  final Trip? trip;
  final String driverNotes;
  final String? selectedStatus;
  final String? errorMessage;

  TripDetailState copyWith({
    TripDetailStatus? status,
    Trip? trip,
    String? driverNotes,
    String? selectedStatus,
    String? errorMessage,
  }) {
    return TripDetailState(
      status: status ?? this.status,
      trip: trip ?? this.trip,
      driverNotes: driverNotes ?? this.driverNotes,
      selectedStatus: selectedStatus ?? this.selectedStatus,
      errorMessage: errorMessage,
    );
  }

  @override
  List<Object?> get props => [
    status,
    trip,
    driverNotes,
    selectedStatus,
    errorMessage,
  ];
}
