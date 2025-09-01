part of 'app_bloc.dart';

/// Base class for all events in the [AppBloc].
///
/// This class is extended by specific events to handle different actions
/// within the application.
sealed class AppEvent {
  /// Default constructor for [AppEvent].
  const AppEvent();
}

/// Event to request a subscription to the authentication repository's credential stream.
///
/// This event triggers the [_onCredentialSubscriptionRequested] method in [AppBloc].
final class CredentialSubscriptionRequested extends AppEvent {
  /// Default constructor for [CredentialSubscriptionRequested].
  const CredentialSubscriptionRequested();
}

/// Event to handle user logout.
///
/// This event triggers the [_onLogoutPressed] method in [AppBloc].
final class LogoutPressed extends AppEvent {
  /// Default constructor for [LogoutPressed].
  const LogoutPressed();
}
