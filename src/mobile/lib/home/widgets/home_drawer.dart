// A simple menu screen widget
import 'package:app/core/core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_zoom_drawer/flutter_zoom_drawer.dart';

class HomeDrawer extends StatelessWidget {
  const HomeDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surfaceBright,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.only(left: 16, bottom: 26, top: 16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Padding(
                padding: const EdgeInsets.only(
                  right: 20,
                  left: 16,
                  bottom: 16,
                  top: 20,
                ),
                child: Image.asset(
                  'assets/images/shared/logo.png',
                  color: Theme.of(
                    context,
                  ).colorScheme.onPrimaryContainer.withAlpha(150),
                ),
              ),
              Divider(
                height: 26,
                indent: 5,
                thickness: 5,
                radius: BorderRadius.circular(20),
                color: Theme.of(context).colorScheme.surfaceContainerHigh,
              ),
              Expanded(
                child: ListView(
                  reverse: true,
                  children: <Widget>[
                    ListTile(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                      leading: Icon(
                        Icons.logout_rounded,
                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                      title: Text(
                        'Sign Out',
                        style: TextStyle(
                          color: Theme.of(
                            context,
                          ).colorScheme.onPrimaryContainer,
                        ),
                      ),
                      onTap: () {
                        ZoomDrawer.of(context)?.close();
                        showDialog(
                          context: context,
                          builder: (context) => AlertDialog(
                            content: SizedBox(
                              child: IntrinsicHeight(
                                child: Center(
                                  child: Column(
                                    spacing: 20,
                                    children: [
                                      Text(
                                        'Are you sure you want to sign out?',
                                      ),
                                      Row(
                                        mainAxisAlignment:
                                            MainAxisAlignment.center,
                                        children: [
                                          TextButton(
                                            onPressed: () {
                                              Navigator.of(
                                                context,
                                              ).pop(); // Close the dialog
                                            },
                                            child: Text('Cancel'),
                                          ),
                                          TextButton(
                                            onPressed: () {
                                              context
                                                  .read<
                                                    AuthenticationRepository
                                                  >()
                                                  .logOut();
                                            },
                                            child: Text('Sign Out'),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                        );
                      },
                    ),
                    ListTile(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                      leading: Icon(
                        Icons.support_agent,
                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                      title: Text(
                        'Contact Support',
                        style: TextStyle(
                          color: Theme.of(
                            context,
                          ).colorScheme.onPrimaryContainer,
                        ),
                      ),
                      onTap: () async {
                        ZoomDrawer.of(context)?.close();
                        await Future.delayed(const Duration(milliseconds: 300));
                        Navigator.of(
                          // ignore: use_build_context_synchronously
                          context,
                        ).pushNamed('support'); // Navigate to Support Page
                      },
                    ),
                    ListTile(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                      leading: Icon(
                        Icons.admin_panel_settings,
                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                      title: Text(
                        'Admin Tools',
                        style: TextStyle(
                          color: Theme.of(
                            context,
                          ).colorScheme.onPrimaryContainer,
                        ),
                      ),
                      onTap: () async {
                        ZoomDrawer.of(context)?.close();
                        await Future.delayed(const Duration(milliseconds: 300));
                        Navigator.of(
                          // ignore: use_build_context_synchronously
                          context,
                        ).pushNamed('admin'); // Navigate to Admin Page
                      },
                    ),
                    ListTile(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                      leading: Icon(
                        Icons.settings,
                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                      title: Text(
                        'Settings',
                        style: TextStyle(
                          color: Theme.of(
                            context,
                          ).colorScheme.onPrimaryContainer,
                        ),
                      ),
                      onTap: () async {
                        ZoomDrawer.of(context)?.close();
                        await Future.delayed(const Duration(milliseconds: 300));
                        Navigator.of(
                          // ignore: use_build_context_synchronously
                          context,
                        ).pushNamed('/settings'); // Navigate to Settings Page
                      },
                    ),
                    ListTile(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                      leading: Icon(
                        Icons.bug_report,
                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                      title: Text(
                        'Notification Debug',
                        style: TextStyle(
                          color: Theme.of(
                            context,
                          ).colorScheme.onPrimaryContainer,
                        ),
                      ),
                      onTap: () async {
                        ZoomDrawer.of(context)?.close();
                        await Future.delayed(const Duration(milliseconds: 300));

                        Navigator.of(
                          // ignore: use_build_context_synchronously
                          context,
                        ).pushNamed(
                          '/notification_debug', // Navigate to Notification Debug
                        );
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
