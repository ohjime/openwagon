import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'package:app/core/core.dart';
import 'package:app/trip/trip.dart';

/// The driver's home screen: a simple list of every trip assigned to the
/// signed-in driver, loaded from `/api/trips/driver/assigned`.
///
/// Reuses the shared [TripListBloc]/[TripRepository] and [TripListItem] (tapping
/// a trip opens its detail, where the driver advances status and shares
/// location). Pushed from the portal; [TripRepository] is provided at the app
/// root so it's available here.
class DriverHomePage extends StatelessWidget {
  const DriverHomePage({super.key});

  static Route<dynamic> route() {
    return MaterialPageRoute<dynamic>(builder: (_) => const DriverHomePage());
  }

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) =>
          TripListBloc(tripRepository: context.read<TripRepository>())
            ..add(TripListSubscriptionRequested()),
      child: const DriverHomeView(),
    );
  }
}

class DriverHomeView extends StatelessWidget {
  const DriverHomeView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Trips'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () =>
                context.read<TripListBloc>().add(TripListSubscriptionRequested()),
          ),
        ],
      ),
      body: BlocBuilder<TripListBloc, TripListState>(
        builder: (context, state) {
          switch (state.status) {
            case TripListStatus.initial:
            case TripListStatus.loading:
              return const Center(child: CupertinoActivityIndicator());
            case TripListStatus.failure:
              return const Center(child: Text('Failed to load your trips'));
            case TripListStatus.success:
              final trips = state.filteredTrips.toList(growable: false);
              if (trips.isEmpty) {
                return const Center(child: Text('No trips assigned to you'));
              }
              return RefreshIndicator(
                onRefresh: () async => context
                    .read<TripListBloc>()
                    .add(TripListSubscriptionRequested()),
                child: CupertinoScrollbar(
                  child: ListView.builder(
                    itemCount: trips.length,
                    itemBuilder: (context, index) =>
                        TripListItem(trip: trips[index]),
                  ),
                ),
              );
          }
        },
      ),
    );
  }
}
