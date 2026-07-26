part of 'portal_cubit.dart';

enum PortalStatus { initial, loading, ready, failure }

class PortalState extends Equatable {
  const PortalState({
    this.status = PortalStatus.initial,
    this.profile,
    this.busy = false,
    this.error,
  });

  final PortalStatus status;
  final Profile? profile;

  /// A sign-up (create driver/rider) is in flight.
  final bool busy;

  /// Last error message, or null. Always replaced (not merged) so it can clear.
  final String? error;

  PortalState copyWith({
    PortalStatus? status,
    Profile? profile,
    bool? busy,
    String? error,
  }) {
    return PortalState(
      status: status ?? this.status,
      profile: profile ?? this.profile,
      busy: busy ?? this.busy,
      error: error,
    );
  }

  @override
  List<Object?> get props => [status, profile, busy, error];
}
