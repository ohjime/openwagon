import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';

import 'package:app/core/core.dart';

part 'portal_state.dart';

/// Drives the post-login portal: fetch the account's role profiles, and sign the
/// account up as a driver or rider on request.
///
/// The account row itself is created by [AuthenticationRepository] during
/// sign-in/sign-up, so by the time the portal loads `/me` the account exists;
/// this cubit only reads which *roles* are attached and lets the user add one.
class PortalCubit extends Cubit<PortalState> {
  PortalCubit({required ProfileRepository profileRepository})
    : _profileRepository = profileRepository,
      super(const PortalState());

  final ProfileRepository _profileRepository;

  /// Load (or reload) the account's profiles from the server.
  Future<void> load() async {
    emit(state.copyWith(status: PortalStatus.loading, error: null));
    try {
      final profile = await _profileRepository.fetchMe();
      emit(state.copyWith(status: PortalStatus.ready, profile: profile));
    } catch (e) {
      emit(state.copyWith(status: PortalStatus.failure, error: '$e'));
    }
  }

  Future<void> signUpAsDriver() => _signUp(_profileRepository.createDriver);

  Future<void> signUpAsRider() => _signUp(_profileRepository.createRider);

  /// Create a role, then reload so the new profile shows as an option.
  Future<void> _signUp(Future<void> Function() create) async {
    emit(state.copyWith(busy: true, error: null));
    try {
      await create();
      final profile = await _profileRepository.fetchMe();
      emit(
        state.copyWith(
          status: PortalStatus.ready,
          profile: profile,
          busy: false,
        ),
      );
    } catch (e) {
      emit(state.copyWith(busy: false, error: '$e'));
    }
  }
}
