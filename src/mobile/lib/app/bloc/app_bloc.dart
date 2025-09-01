import 'dart:async';
import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:app/core/core.dart' as core;

part 'app_event.dart';
part 'app_state.dart';

/// [AppBloc] is the main Bloc for managing the application's state.
/// It handles authentication, onboarding, and logout events.
///
/// This Bloc listens to events such as [CredentialSubscriptionRequested],
/// [LogoutPressed], and [VerifyOnboardingStatus] to update the application state.
class AppBloc extends Bloc<AppEvent, AppState> {
  /// Creates an instance of [AppBloc].
  ///
  /// Requires an [authenticationRepository] to manage authentication
  /// and a [userRepository] to fetch user-related data.
  AppBloc({required core.AuthenticationRepository authenticationRepository})
    : _authenticationRepository = authenticationRepository,
      super(Starting()) {
    on<CredentialSubscriptionRequested>(_onCredentialSubscriptionRequested);
    on<LogoutPressed>(_onLogoutPressed);
  }

  /// Repository for managing authentication-related operations.
  final core.AuthenticationRepository _authenticationRepository;

  /// Handles the [CredentialSubscriptionRequested] event.
  ///
  /// Subscribes to the authentication repository's credential stream
  /// and updates the state based on the user's authentication and onboarding status.
  ///
  /// - Emits [Unauthenticated] if no valid credentials are found.
  /// - Emits [OnboardingRequired] if the user requires onboarding.
  /// - Emits [Onboarded] if the user is fully onboarded.
  ///
  /// Parameters:
  /// - [event]: The [CredentialSubscriptionRequested] event.
  /// - [emit]: The function to emit new states.
  Future<void> _onCredentialSubscriptionRequested(
    CredentialSubscriptionRequested event,
    Emitter<AppState> emit,
  ) async {
    return emit.onEach(
      _authenticationRepository.credential,
      onData: (credential) async {
        if (credential == core.AuthCredential.empty) {
          emit(const Unauthenticated());
        } else {
          try {
            await Future.delayed(const Duration(milliseconds: 500));
          } catch (_) {
            emit(const Unauthenticated());
          }
          emit(Authenticated(credential: credential));
        }
      },
      onError: (_, __) => emit(const Unauthenticated()),
    );
  }

  /// Handles the [LogoutPressed] event.
  ///
  /// Logs the user out by calling the authentication repository's logout method
  /// and updates the state to [Unauthenticated].
  ///
  /// Parameters:
  /// - [event]: The [LogoutPressed] event.
  /// - [emit]: The function to emit new states.
  void _onLogoutPressed(LogoutPressed event, Emitter<AppState> emit) {
    _authenticationRepository.logOut();
    emit(const Unauthenticated());
  }
}
