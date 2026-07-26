// Unit tests for the driver-portal domain helpers. These are pure-Dart (no
// Firebase / network), so they run without any platform bootstrap.

import 'package:flutter_test/flutter_test.dart';

import 'package:app/core/models/trip.dart';
import 'package:app/core/models/profile.dart';

void main() {
  group('tripStatusLabel', () {
    test('title-cases a multi-word status', () {
      expect(tripStatusLabel('in_progress'), 'In Progress');
    });

    test('title-cases a single-word status', () {
      expect(tripStatusLabel('enroute'), 'Enroute');
    });
  });

  group('trip status constants', () {
    test('use the server spelling "enroute", not "en_route"', () {
      // Must match core.models.TripStatus on the server or status writes fail.
      expect(kTripStatuses.contains('enroute'), isTrue);
      expect(kTripStatuses.contains('en_route'), isFalse);
    });

    test('driver flow excludes unassigned (dispatcher-only)', () {
      expect(kDriverTripFlow.contains('unassigned'), isFalse);
      expect(kDriverTripFlow, containsAllInOrder(<String>['enroute', 'completed']));
    });
  });

  group('Profile.fromJson', () {
    test('parses a driver with a vehicle and no rider', () {
      final profile = Profile.fromJson(<String, dynamic>{
        'account': <String, dynamic>{
          'uid': 'abc',
          'first_name': 'Ada',
          'last_name': 'Lovelace',
          'email': 'ada@example.com',
          'phone': '',
          'avatar': '',
        },
        'driver': <String, dynamic>{
          'id': 7,
          'status': 'available',
          'has_vehicle': true,
        },
        'rider': null,
      });

      expect(profile.hasDriver, isTrue);
      expect(profile.hasRider, isFalse);
      expect(profile.hasAnyRole, isTrue);
      expect(profile.driver!.id, 7);
      expect(profile.driver!.hasVehicle, isTrue);
      expect(profile.account.firstName, 'Ada');
    });

    test('parses an account with neither role', () {
      final profile = Profile.fromJson(<String, dynamic>{
        'account': <String, dynamic>{'uid': 'x', 'email': 'x@example.com'},
        'driver': null,
        'rider': null,
      });

      expect(profile.hasAnyRole, isFalse);
      expect(profile.driver, isNull);
      expect(profile.rider, isNull);
    });
  });
}
