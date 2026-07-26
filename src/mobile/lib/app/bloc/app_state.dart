part of 'app_bloc.dart';

/// Base class for all states in the [AppBloc].
///
/// This class is extended by specific states to represent different
/// stages of the application's lifecycle.
sealed class AppState extends Equatable {
  /// Default constructor for [AppState].
  const AppState();

  @override
  List<Object?> get props => []; // No fields to compare in the base class.
}

/// Represents the initial state of the application.
///
/// This state is used before any authentication or user data is loaded.
/// Typically, it is used to show a splash screen or loading indicator.
final class Starting extends AppState {
  /// Default constructor for [Starting].
  const Starting();
}

/// Represents the state when the user is not authenticated.
///
/// This state is used when the user is logged out or has not completed onboarding.
final class Unauthenticated extends AppState {
  /// Default constructor for [Unauthenticated].
  const Unauthenticated();
}

/// Base class for states where the user is authenticated.
///
/// This state carries the user's [credential] and is extended by more
/// specific authenticated states.
final class Authenticated extends AppState {
  /// Creates an [Authenticated] state with the given [credential].
  const Authenticated({required this.credential});

  /// The user's authentication credential.
  final core.AuthCredential credential;

  @override
  List<Object?> get props => [credential];
}

/// Represents the state when the user is authenticated but requires onboarding.
///
/// This state is used to redirect the user to the onboarding process.
final class Unregistered extends Authenticated {
  /// Creates an [Unregistered] state with the given [credential].
  const Unregistered({required super.credential});
}

/// Represents the state when the user is authenticated and has completed onboarding.
///
/// This state is used to redirect the user to the main application.
final class Onboarded extends Authenticated {
  /// Creates an [Onboarded] state with the given [credential].
  const Onboarded({required super.credential});
}
