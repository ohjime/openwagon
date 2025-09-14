import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart' as firebase_auth;

import '../models/trip.dart';

class TripRepository {
  TripRepository({firebase_auth.FirebaseAuth? firebaseAuth, Dio? dio})
    : _firebaseAuth = firebaseAuth ?? firebase_auth.FirebaseAuth.instance,
      _dio = dio ?? Dio();

  final firebase_auth.FirebaseAuth _firebaseAuth;
  final Dio _dio;

  static const String _apiBaseUrl =
      'http://localhost:8000'; // Adjust to your server address
  static const String _assignedTripsEndpoint = '/api/trips/driver/assigned';
  static const String _driverUpdateEndpoint = '/api/trips';

  Future<List<Trip>> getAssignedTrips() async {
    final user = _firebaseAuth.currentUser;
    if (user == null) {
      // Not signed in; return empty list
      return [];
    }

    final idToken = await user.getIdToken();
    if (idToken == null || idToken.isEmpty) {
      return [];
    }

    final resp = await _dio.get(
      '$_apiBaseUrl$_assignedTripsEndpoint',
      options: Options(headers: {'Authorization': 'Bearer $idToken'}),
    );

    if (resp.statusCode == 200 && resp.data is List) {
      final list = resp.data as List<dynamic>;
      return list
          .whereType<Map<String, dynamic>>()
          .map((json) => Trip.fromJson(json))
          .toList();
    }

    throw Exception('Failed to fetch trips: HTTP ${resp.statusCode}');
  }

  Future<Trip> updateTripAsDriver({
    required int tripId,
    String? status,
    String? driverNotes,
  }) async {
    final user = _firebaseAuth.currentUser;
    if (user == null) {
      throw Exception('Not authenticated');
    }

    final idToken = await user.getIdToken();
    if (idToken == null || idToken.isEmpty) {
      throw Exception('Unable to obtain id token');
    }

    final payload = <String, dynamic>{};
    if (status != null) payload['status'] = status;
    if (driverNotes != null) payload['driver_notes'] = driverNotes;

    final resp = await _dio.patch(
      '$_apiBaseUrl$_driverUpdateEndpoint/$tripId/driver',
      data: payload,
      options: Options(
        headers: {
          'Authorization': 'Bearer $idToken',
          'Content-Type': 'application/json',
        },
      ),
    );

    if (resp.statusCode == 200 && resp.data is Map<String, dynamic>) {
      return Trip.fromJson(resp.data as Map<String, dynamic>);
    }

    throw Exception('Failed to update trip: HTTP ${resp.statusCode}');
  }
}
