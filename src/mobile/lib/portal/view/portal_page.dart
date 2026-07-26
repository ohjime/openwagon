import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'package:app/core/core.dart';
import 'package:app/driver/driver.dart';
import 'package:app/portal/cubit/portal_cubit.dart';

/// The multi-user portal shown right after authentication.
///
/// Fetches the account's role profiles and presents each existing role as a
/// tappable option; for any role the account doesn't have yet it offers a
/// "Sign up as …" button. With neither role it shows the empty-state prompt.
class PortalPage extends StatelessWidget {
  const PortalPage({super.key});

  static Route<dynamic> route() {
    return MaterialPageRoute<dynamic>(builder: (_) => const PortalPage());
  }

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) =>
          PortalCubit(profileRepository: context.read<ProfileRepository>())
            ..load(),
      child: const PortalView(),
    );
  }
}

class PortalView extends StatelessWidget {
  const PortalView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Choose your portal'),
        actions: [
          IconButton(
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout_rounded),
            onPressed: () => context.read<AuthenticationRepository>().logOut(),
          ),
        ],
      ),
      body: BlocConsumer<PortalCubit, PortalState>(
        listenWhen: (prev, curr) =>
            curr.error != null && prev.error != curr.error,
        listener: (context, state) {
          ScaffoldMessenger.of(context)
            ..hideCurrentSnackBar()
            ..showSnackBar(SnackBar(content: Text(state.error!)));
        },
        builder: (context, state) {
          switch (state.status) {
            case PortalStatus.initial:
            case PortalStatus.loading:
              return const Center(child: CupertinoActivityIndicator());
            case PortalStatus.failure:
              return _PortalError(
                onRetry: () => context.read<PortalCubit>().load(),
              );
            case PortalStatus.ready:
              return _PortalReady(state: state);
          }
        },
      ),
    );
  }
}

class _PortalError extends StatelessWidget {
  const _PortalError({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_rounded, size: 48),
            const SizedBox(height: 12),
            const Text(
              "Couldn't load your account.",
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            AppButton.primary(text: 'Try again', onPressed: onRetry),
          ],
        ),
      ),
    );
  }
}

class _PortalReady extends StatelessWidget {
  const _PortalReady({required this.state});

  final PortalState state;

  @override
  Widget build(BuildContext context) {
    final profile = state.profile!;
    final account = profile.account;
    final theme = Theme.of(context);
    final name = account.firstName.isNotEmpty
        ? account.firstName
        : (account.email.isNotEmpty ? account.email : 'there');

    return AbsorbPointer(
      absorbing: state.busy,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text('Welcome, $name', style: theme.textTheme.headlineSmall),
          const SizedBox(height: 4),
          Text(
            'How would you like to continue?',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 24),

          // Existing roles as entry options.
          if (profile.hasDriver)
            _RoleCard(
              icon: Icons.local_taxi_rounded,
              title: 'Driver',
              subtitle: profile.driver!.hasVehicle
                  ? 'Status: ${profile.driver!.status}'
                  : 'No vehicle assigned yet',
              onTap: () => Navigator.of(context).push(DriverHomePage.route()),
            ),
          if (profile.hasRider)
            _RoleCard(
              icon: Icons.person_pin_circle_rounded,
              title: 'Rider',
              subtitle: 'Book and track your trips',
              onTap: () => Navigator.of(context).push(_riderPlaceholderRoute()),
            ),

          // Empty state when the account has neither role.
          if (!profile.hasAnyRole) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(
                  Icons.info_outline_rounded,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'No driver or rider account found.',
                    style: theme.textTheme.titleMedium,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Sign up for a role to get started.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],

          // Sign-up buttons for any role the account is missing.
          if (!profile.hasDriver) ...[
            const SizedBox(height: 20),
            AppButton.primary(
              text: 'Sign up as Driver',
              isLoading: state.busy,
              onPressed: () => context.read<PortalCubit>().signUpAsDriver(),
            ),
          ],
          if (!profile.hasRider) ...[
            const SizedBox(height: 12),
            AppButton.tertiary(
              text: 'Sign up as Rider',
              isLoading: state.busy,
              onPressed: () => context.read<PortalCubit>().signUpAsRider(),
            ),
          ],
        ],
      ),
    );
  }
}

class _RoleCard extends StatelessWidget {
  const _RoleCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(
        elevation: 0,
        color: theme.colorScheme.surfaceContainerHighest,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 8,
          ),
          leading: CircleAvatar(
            backgroundColor: theme.colorScheme.primaryContainer,
            child: Icon(icon, color: theme.colorScheme.onPrimaryContainer),
          ),
          title: Text(title, style: theme.textTheme.titleMedium),
          subtitle: Text(subtitle),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: onTap,
        ),
      ),
    );
  }
}

/// Placeholder destination for the rider role — the rider experience isn't built
/// yet, so the option is present but lands on a simple "coming soon" screen.
Route<dynamic> _riderPlaceholderRoute() {
  return MaterialPageRoute<dynamic>(
    builder: (_) => Scaffold(
      appBar: AppBar(title: const Text('Rider')),
      body: const Center(child: Text('Rider experience coming soon.')),
    ),
  );
}
