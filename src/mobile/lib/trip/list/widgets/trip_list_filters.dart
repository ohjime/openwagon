import 'package:app/trip/list/bloc/trip_list_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

class TripFiltersButton extends StatelessWidget {
  const TripFiltersButton({super.key});

  String _labelFor(TripViewFilter f) {
    switch (f) {
      case TripViewFilter.all:
        return 'All';
      case TripViewFilter.scheduled:
        return 'Scheduled';
      case TripViewFilter.assigned:
        return 'Assigned';
      case TripViewFilter.enRoute:
        return 'En Route';
      case TripViewFilter.arrived:
        return 'Arrived';
      case TripViewFilter.inProgress:
        return 'In Progress';
      case TripViewFilter.completed:
        return 'Completed';
      case TripViewFilter.canceled:
        return 'Canceled';
    }
  }

  @override
  Widget build(BuildContext context) {
    final active = context.select((TripListBloc b) => b.state.filter);
    return PopupMenuButton<TripViewFilter>(
      initialValue: active,
      tooltip: 'Filter',
      onSelected: (filter) => context
          .read<TripListBloc>()
          .add(TripListFilterChanged(filter)),
      itemBuilder: (context) {
        return [
          for (final f in TripViewFilter.values)
            PopupMenuItem(
              value: f,
              child: Text(_labelFor(f)),
            ),
        ];
      },
      icon: const Icon(Icons.filter_list_rounded),
    );
  }
}
