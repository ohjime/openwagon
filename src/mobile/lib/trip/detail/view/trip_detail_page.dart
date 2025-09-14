import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'package:app/core/core.dart';
import 'package:app/trip/trip.dart';

class TripDetailPage extends StatelessWidget {
  const TripDetailPage({super.key, required this.trip});

  final Trip trip;

  static Route<void> route({required Trip trip}) {
    return MaterialPageRoute(
      fullscreenDialog: true,
      builder: (context) => BlocProvider(
        create: (context) =>
            TripDetailBloc(tripRepository: context.read<TripRepository>())
              ..add(TripDetailInitialized(trip: trip)),
        child: TripDetailPage(trip: trip),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocListener<TripDetailBloc, TripDetailState>(
      listenWhen: (prev, curr) => prev.status != curr.status,
      listener: (context, state) {
        if (state.status == TripDetailStatus.success) {
          Navigator.of(context).pop();
        } else if (state.status == TripDetailStatus.failure) {
          final msg = state.errorMessage ?? 'Update failed';
          ScaffoldMessenger.of(context)
            ..hideCurrentSnackBar()
            ..showSnackBar(SnackBar(content: Text(msg)));
        }
      },
      child: const TripDetailView(),
    );
  }
}

class TripDetailView extends StatelessWidget {
  const TripDetailView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<TripDetailBloc>().state;
    final trip = state.trip;
    final submitting = state.status == TripDetailStatus.submitting;
    if (trip == null) return const SizedBox.shrink();

    return Scaffold(
      appBar: AppBar(
        title: Text('Trip ${trip.hashid}'),
        actions: [
          IconButton(
            onPressed: submitting
                ? null
                : () => context.read<TripDetailBloc>().add(
                    const TripDetailSubmitted(),
                  ),
            icon: submitting
                ? const SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.check),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TripRouteMap(),
              Text(trip.originAddress),
              const Icon(Icons.arrow_downward, size: 16),
              Text(trip.destinationAddress),
              TextFormField(
                initialValue: state.driverNotes,
                maxLines: 5,
                decoration: const InputDecoration(
                  labelText: 'Driver notes',
                  border: OutlineInputBorder(),
                ),
                onChanged: (text) => context.read<TripDetailBloc>().add(
                  TripDetailDriverNotesChanged(text),
                ),
              ),
              TextFormField(
                initialValue: state.driverNotes,
                maxLines: 5,
                decoration: const InputDecoration(
                  labelText: 'Driver notes',
                  border: OutlineInputBorder(),
                ),
                onChanged: (text) => context.read<TripDetailBloc>().add(
                  TripDetailDriverNotesChanged(text),
                ),
              ),
              TextFormField(
                initialValue: state.driverNotes,
                maxLines: 5,
                decoration: const InputDecoration(
                  labelText: 'Driver notes',
                  border: OutlineInputBorder(),
                ),
                onChanged: (text) => context.read<TripDetailBloc>().add(
                  TripDetailDriverNotesChanged(text),
                ),
              ),
              TextFormField(
                initialValue: state.driverNotes,
                maxLines: 5,
                decoration: const InputDecoration(
                  labelText: 'Driver notes',
                  border: OutlineInputBorder(),
                ),
                onChanged: (text) => context.read<TripDetailBloc>().add(
                  TripDetailDriverNotesChanged(text),
                ),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [Colors.transparent, Theme.of(context).colorScheme.surface],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            stops: const [0.0, 0.1],
          ),
        ),
        child: BottomAppBar(
          elevation: 0,
          child: TripStatusSwiper(
            statuses: kTripStatuses,
            current: trip.status,
            onChanged: (status) {
              context.read<TripDetailBloc>().add(
                TripDetailStatusChanged(status),
              );
            },
          ),
        ),
      ),
    );
  }
}
