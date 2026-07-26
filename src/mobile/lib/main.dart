import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:firebase_core/firebase_core.dart';

import 'package:app/firebase_options.dart';
import 'package:app/core/core.dart';
import 'package:app/app/app.dart';
import 'package:app/home/home.dart';
import 'package:app/login/login.dart';
import 'package:app/signup/signup.dart';
import 'package:app/portal/portal.dart';
import 'package:app/driver/driver.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase.
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  // Initialize the Bloc Observer for our Application
  Bloc.observer = CoreObserver();

  // Initialize Authentication Repository and wait for the first user's
  // credentials to be emitted.
  final authenticationRepository = AuthenticationRepository();
  await authenticationRepository.credential.first;

  runApp(App(authenticationRepository: authenticationRepository));
}

class App extends StatelessWidget {
  const App({
    required AuthenticationRepository authenticationRepository,
    super.key,
  }) : _authenticationRepository = authenticationRepository;

  final AuthenticationRepository _authenticationRepository;
  Route<dynamic>? _onGenerateRoute(RouteSettings settings) {
    switch (settings.name) {
      case '/':
        return MaterialPageRoute(builder: (_) => const SplashPage());
      case '/welcome':
        return MaterialPageRoute(builder: (_) => const WelcomePage());
      case '/login':
        return MaterialPageRoute(builder: (_) => const LoginPage());
      case '/signup':
        return MaterialPageRoute(builder: (_) => const SignupPage());
      case '/home':
        return MaterialPageRoute(builder: (_) => HomePage());
      case '/portal':
        return MaterialPageRoute(builder: (_) => const PortalPage());
      case '/driver':
        return MaterialPageRoute(builder: (_) => const DriverHomePage());
      default:
        return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final brightness = MediaQuery.platformBrightnessOf(context);
    final isDark = brightness == Brightness.dark;
    final colorScheme = isDark ? darkTheme.colorScheme : lightTheme.colorScheme;

    SystemChrome.setSystemUIOverlayStyle(
      SystemUiOverlayStyle(
        statusBarColor: colorScheme.primary,
        systemNavigationBarColor: colorScheme.surface,
        statusBarIconBrightness: isDark ? Brightness.light : Brightness.dark,
        systemNavigationBarIconBrightness: isDark
            ? Brightness.light
            : Brightness.dark,
      ),
    );
    return MultiRepositoryProvider(
      providers: [
        RepositoryProvider.value(value: _authenticationRepository),
        RepositoryProvider<TripRepository>(create: (_) => TripRepository()),
        RepositoryProvider<ProfileRepository>(
          create: (_) => ProfileRepository(),
        ),
        RepositoryProvider<LocationRepository>(
          create: (_) => LocationRepository(),
        ),
      ],
      // LocationTrackingBloc lives above the router so a single tracking
      // authority survives every route change and app backgrounding. It's lazy
      // and inert until a driver's trip goes active (see TripDetailPage), so it
      // costs riders nothing.
      child: BlocProvider<LocationTrackingBloc>(
        create: (context) => LocationTrackingBloc(
          locationRepository: context.read<LocationRepository>(),
        ),
        child: AppView(onGenerateRoute: _onGenerateRoute),
      ),
    );
  }
}
