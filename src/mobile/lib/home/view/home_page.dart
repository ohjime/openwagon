import 'package:app/trip/list/view/trip_list_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_zoom_drawer/flutter_zoom_drawer.dart';

import 'package:app/home/home.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  static Route<dynamic> route() {
    return MaterialPageRoute<dynamic>(builder: (_) => HomePage());
  }

  @override
  HomePageState createState() => HomePageState();
}

class HomePageState extends State<HomePage> {
  final _drawerController = ZoomDrawerController();

  @override
  Widget build(BuildContext context) {
    return ZoomDrawer(
      mainScreenScale: 0.1,
      controller: _drawerController,
      menuScreen: const HomeDrawer(),
      mainScreen: TripListPage(),
      showShadow: true,
      boxShadow: [
        BoxShadow(
          color: Theme.of(context).colorScheme.shadow.withValues(alpha: 0.2),
          blurRadius: 20,
          offset: const Offset(0, 2),
        ),
      ],
      borderRadius: 30,
      angle: 0,
      drawerShadowsBackgroundColor: Theme.of(context).colorScheme.primary,
      slideWidth: MediaQuery.of(context).size.width * 0.7,
      menuBackgroundColor: Theme.of(context).colorScheme.surfaceBright,
      mainScreenTapClose: true,
      menuScreenWidth: 220,
    );
  }
}
