import 'package:app/app/view/unknown_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:app/app/app.dart';
import 'package:app/core/core.dart';

// Document AppView class
class AppView extends StatefulWidget {
  const AppView({super.key, required this.onGenerateRoute});
  // Document the onGenerateRoute parameter
  final Route? Function(RouteSettings settings) onGenerateRoute;

  @override
  State<AppView> createState() => _AppViewState();
}

class _AppViewState extends State<AppView> {
  // Document the _bloc variable
  late final AppBloc _bloc;
  // Document the _navigatorKey
  final _navigatorKey = GlobalKey<NavigatorState>();
  // Document the _navigator getter
  NavigatorState get _navigator => _navigatorKey.currentState!;

  @override
  void initState() {
    super.initState();
    _bloc = AppBloc(
      authenticationRepository: context.read<AuthenticationRepository>(),
    );
    // Delay the subscription request until after build
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _bloc.add(CredentialSubscriptionRequested());
    });
  }

  @override
  void dispose() {
    _bloc.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return BlocProvider.value(
      // Providing the AppBloc to the widget tree
      value: _bloc,
      child: MaterialApp(
        // MaterialApp Properties
        debugShowCheckedModeBanner: false,
        theme: lightTheme,
        darkTheme: darkTheme,
        navigatorKey: _navigatorKey,
        initialRoute: '/',
        // Providing the onGenerateRoute function
        onGenerateRoute: widget.onGenerateRoute,
        onUnknownRoute: (settings) {
          // Handling unknown routes
          return MaterialPageRoute(
            builder: (_) => const UnknownPage(),
            settings: settings,
          );
        },
        builder: (context, child) {
          // AppView completely rebuilds anytime the AppBloc emits a new state.
          // Since AppView is at the root of the widget tree, rebuilds here will cause the
          // entire widget tree to rebuild.
          return BlocListener<AppBloc, AppState>(
            listener: (context, state) {
              switch (state) {
                case Unauthenticated():
                  // If the user is unauthenticated, navigate to the welcome screen
                  _navigator.pushNamedAndRemoveUntil('/welcome', (_) => false);
                // There are two cases for authenticated users:
                case Authenticated():
                  // If the user is authenticated, but does not have a user account in our system,
                  // We need to onboard them. This can happen if the user canceled the onboarding
                  // process, logged in via google, with out completing the onboarding process, etc.
                  _navigator.pushNamedAndRemoveUntil('/home', (_) => false);
                  break;
                // In the future, you may want to handle other authenticated states here, such as
                // disabled, inactive, etc.
                default:
                  // go back to the welcome screen if state is not handled
                  _navigator.pushNamedAndRemoveUntil('/welcome', (_) => false);
              }
            },
            child: child,
          );
        },
      ),
    );
  }
}
