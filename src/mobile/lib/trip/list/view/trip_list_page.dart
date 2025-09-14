import 'package:app/core/models/trip.dart' as model;
import 'package:app/core/repositories/trip_repository.dart';
import 'package:app/trip/list/bloc/trip_list_bloc.dart';
import 'package:app/trip/list/widgets/trip_list_filters.dart';
import 'package:app/trip/list/widgets/trip_list_item.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

class TripListPage extends StatelessWidget {
  const TripListPage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) =>
          TripListBloc(tripRepository: context.read<TripRepository>())
            ..add(TripListSubscriptionRequested()),
      child: const TripListView(),
    );
  }
}

class TripListView extends StatelessWidget {
  const TripListView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Trips'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<TripListBloc>().add(
              TripListSubscriptionRequested(),
            ),
          ),
          const TripFiltersButton(),
        ],
      ),
      body: BlocBuilder<TripListBloc, TripListState>(
        builder: (context, state) {
          switch (state.status) {
            case TripListStatus.initial:
            case TripListStatus.loading:
              return const Center(child: CupertinoActivityIndicator());
            case TripListStatus.failure:
              return const Center(child: Text('Failed to load trips'));
            case TripListStatus.success:
              final trips = state.filteredTrips.toList(growable: false);
              if (trips.isEmpty) {
                return const Center(child: Text('No trips found'));
              }
              return CupertinoScrollbar(
                child: ListView.builder(
                  itemCount: trips.length,
                  itemBuilder: (context, index) {
                    final model.Trip trip = trips[index];
                    return TripListItem(trip: trip);
                  },
                ),
              );
          }
        },
      ),
    );
  }
}
