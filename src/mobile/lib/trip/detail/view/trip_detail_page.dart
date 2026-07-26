import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'package:app/core/core.dart';
import 'package:app/driver/tracking/tracking.dart';
import 'package:app/trip/trip.dart';

/// The driver's trip screen.
///
/// Two jobs: (1) let the driver advance the trip's status with a tap, and (2)
/// keep the driver's location flowing to dispatch while the trip is active.
///
/// Sharing is NOT tied to this screen being open: it's driven by the trip's
/// (server-confirmed) status via the app-level [LocationTrackingBloc] — sharing
/// starts when the trip enters an active status ([tripSharesLocation]) and stops
/// when it's completed/canceled. That's what lets tracking survive the app being
/// backgrounded or this screen being popped mid-trip. This is a StatefulWidget
/// only to run the one-time initial status→tracking sync after first frame.
class TripDetailPage extends StatefulWidget {
  const TripDetailPage({super.key});

  static Route<void> route({required Trip trip}) {
    return MaterialPageRoute(
      fullscreenDialog: true,
      builder: (context) => BlocProvider(
        create: (context) =>
            TripDetailBloc(tripRepository: context.read<TripRepository>())
              ..add(TripDetailInitialized(trip: trip)),
        child: const TripDetailPage(),
      ),
    );
  }

  @override
  State<TripDetailPage> createState() => _TripDetailPageState();
}

class _TripDetailPageState extends State<TripDetailPage> {
  @override
  void initState() {
    super.initState();
    // Sync tracking to the trip's initial status once the tree is ready. The
    // BlocListener below only fires on subsequent changes, so this covers the
    // status TripDetailInitialized already set before we mounted.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _syncTracking(context.read<TripDetailBloc>().state.trip?.status);
    });
  }

  /// Turn location sharing on/off to match the trip's server-confirmed status.
  /// Driven by `trip.status` (not the optimistic `selectedStatus`) so a swipe
  /// the server rejects doesn't wrongly start or stop sharing.
  void _syncTracking(String? status) {
    final tracking = context.read<LocationTrackingBloc>();
    if (status != null && tripSharesLocation(status)) {
      tracking.add(const LocationTrackingStarted());
    } else {
      tracking.add(const LocationTrackingStopped());
    }
  }

  @override
  Widget build(BuildContext context) {
    return MultiBlocListener(
      listeners: [
        // Keep sharing in step with the confirmed trip status.
        BlocListener<TripDetailBloc, TripDetailState>(
          listenWhen: (prev, curr) => prev.trip?.status != curr.trip?.status,
          listener: (context, state) => _syncTracking(state.trip?.status),
        ),
        // Surface status-update success/failure to the driver.
        BlocListener<TripDetailBloc, TripDetailState>(
          listenWhen: (prev, curr) => prev.status != curr.status,
          listener: (context, state) {
            final messenger = ScaffoldMessenger.of(context);
            if (state.status == TripDetailStatus.success) {
              messenger
                ..hideCurrentSnackBar()
                ..showSnackBar(
                  SnackBar(
                    content: Text(
                      'Status: ${tripStatusLabel(state.trip?.status ?? '')}',
                    ),
                  ),
                );
            } else if (state.status == TripDetailStatus.failure) {
              messenger
                ..hideCurrentSnackBar()
                ..showSnackBar(
                  SnackBar(
                    content: Text(state.errorMessage ?? 'Update failed'),
                  ),
                );
            }
          },
        ),
      ],
      child: const TripDetailView(),
    );
  }
}

class TripDetailView extends StatelessWidget {
  const TripDetailView({super.key});

  /// Set the trip's status on the server. Fires the local change then the
  /// submit; the bloc processes them in order, so submit sees the new value.
  void _updateStatus(BuildContext context, String status) {
    final bloc = context.read<TripDetailBloc>();
    bloc
      ..add(TripDetailStatusChanged(status))
      ..add(const TripDetailSubmitted());
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<TripDetailBloc>().state;
    final trip = state.trip;
    if (trip == null) return const SizedBox.shrink();
    final submitting = state.status == TripDetailStatus.submitting;
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: Text('Trip ${trip.hashid}')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TripRouteMap(trip: trip),
          const SizedBox(height: 16),
          _RouteLine(
            origin: trip.originAddress,
            destination: trip.destinationAddress,
          ),
          const SizedBox(height: 16),
          const _LocationBanner(),
          const SizedBox(height: 20),
          Row(
            children: [
              Text('Current status', style: theme.textTheme.labelLarge),
              const Spacer(),
              Chip(label: Text(tripStatusLabel(trip.status))),
            ],
          ),
          const SizedBox(height: 12),
          Text('Update status', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final status in kDriverTripFlow)
                _StatusButton(
                  label: tripStatusLabel(status),
                  selected: trip.status == status,
                  onPressed: submitting || trip.status == status
                      ? null
                      : () => _updateStatus(context, status),
                ),
            ],
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: submitting || trip.status == kTripCanceledStatus
                ? null
                : () => _updateStatus(context, kTripCanceledStatus),
            icon: const Icon(Icons.cancel_outlined),
            label: const Text('Cancel trip'),
            style: OutlinedButton.styleFrom(
              foregroundColor: theme.colorScheme.error,
            ),
          ),
          if (submitting) ...[
            const SizedBox(height: 16),
            const Center(child: CircularProgressIndicator()),
          ],
        ],
      ),
    );
  }
}

class _RouteLine extends StatelessWidget {
  const _RouteLine({required this.origin, required this.destination});

  final String origin;
  final String destination;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.trip_origin, size: 18),
            const SizedBox(width: 8),
            Expanded(child: Text(origin)),
          ],
        ),
        const Padding(
          padding: EdgeInsets.only(left: 3),
          child: Icon(Icons.more_vert, size: 18),
        ),
        Row(
          children: [
            const Icon(Icons.location_on, size: 18),
            const SizedBox(width: 8),
            Expanded(child: Text(destination)),
          ],
        ),
      ],
    );
  }
}

/// A small location-sharing indicator that reflects the real state of the
/// app-level [LocationTrackingBloc]: a calm banner while sharing, an error-toned
/// one if permission was denied or the service failed, and nothing when idle.
class _LocationBanner extends StatelessWidget {
  const _LocationBanner();

  @override
  Widget build(BuildContext context) {
    final status = context.select(
      (LocationTrackingBloc bloc) => bloc.state.status,
    );
    // Latest native-uploader outcome (e.g. "sync OK 200 sent=1"). Shown as a
    // second line while sharing so upload success/failure is visible on-device
    // in a release build — no debug attach or server log needed.
    final syncMessage = context.select(
      (LocationTrackingBloc bloc) => bloc.state.lastSyncMessage,
    );
    final theme = Theme.of(context);

    final (IconData icon, String message, bool isError)? content =
        switch (status) {
          LocationTrackingStatus.active => (
            Icons.my_location_rounded,
            'Sharing your location with dispatch',
            false,
          ),
          LocationTrackingStatus.requestingPermission => (
            Icons.my_location_rounded,
            'Starting location sharing…',
            false,
          ),
          LocationTrackingStatus.permissionDenied => (
            Icons.location_disabled_rounded,
            'Location permission denied — dispatch can’t see you',
            true,
          ),
          LocationTrackingStatus.failure => (
            Icons.location_disabled_rounded,
            'Location sharing is unavailable',
            true,
          ),
          LocationTrackingStatus.idle => null,
        };

    if (content == null) return const SizedBox.shrink();
    final (icon, message, isError) = content;
    final background = isError
        ? theme.colorScheme.errorContainer
        : theme.colorScheme.secondaryContainer;
    final foreground = isError
        ? theme.colorScheme.onErrorContainer
        : theme.colorScheme.onSecondaryContainer;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: foreground),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  message,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: foreground,
                  ),
                ),
                if (!isError && syncMessage != null)
                  Text(
                    syncMessage,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: foreground.withValues(alpha: 0.75),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusButton extends StatelessWidget {
  const _StatusButton({
    required this.label,
    required this.selected,
    required this.onPressed,
  });

  final String label;
  final bool selected;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    if (selected) {
      return FilledButton(onPressed: onPressed, child: Text(label));
    }
    return FilledButton.tonal(onPressed: onPressed, child: Text(label));
  }
}
