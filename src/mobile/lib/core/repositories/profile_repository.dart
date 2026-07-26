import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart' as firebase_auth;

import '../config/api_config.dart';
import '../models/profile.dart';

/// Talks to the server's account/portal endpoints: fetch "who am I" and sign the
/// current account up for a driver or rider role. All calls carry the Firebase
/// ID token as a Bearer header (the server resolves it to the Account).
class ProfileRepository {
  ProfileRepository({firebase_auth.FirebaseAuth? firebaseAuth, Dio? dio})
    : _firebaseAuth = firebaseAuth ?? firebase_auth.FirebaseAuth.instance,
      _dio = dio ?? Dio();

  final firebase_auth.FirebaseAuth _firebaseAuth;
  final Dio _dio;

  Future<Options> _authOptions() async {
    final user = _firebaseAuth.currentUser;
    if (user == null) {
      throw Exception('Not authenticated');
    }
    final token = await user.getIdToken();
    if (token == null || token.isEmpty) {
      throw Exception('Unable to obtain id token');
    }
    return Options(
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );
  }

  /// GET /api/core/me — the account plus its driver/rider profiles (either may
  /// be null). Throws on a non-2xx (Dio raises), which the portal surfaces as a
  /// retryable error.
  Future<Profile> fetchMe() async {
    final resp = await _dio.get(
      '${ApiConfig.baseUrl}/api/core/me',
      options: await _authOptions(),
    );
    if (resp.statusCode == 200 && resp.data is Map<String, dynamic>) {
      return Profile.fromJson(resp.data as Map<String, dynamic>);
    }
    throw Exception('Failed to load profile: HTTP ${resp.statusCode}');
  }

  /// POST /api/drivers/create — idempotent on the server (get_or_create).
  Future<void> createDriver() async {
    final resp = await _dio.post(
      '${ApiConfig.baseUrl}/api/drivers/create',
      options: await _authOptions(),
    );
    if (resp.statusCode != 200) {
      throw Exception('Failed to sign up as driver: HTTP ${resp.statusCode}');
    }
  }

  /// POST /api/riders/create — idempotent on the server (get_or_create).
  Future<void> createRider() async {
    final resp = await _dio.post(
      '${ApiConfig.baseUrl}/api/riders/create',
      options: await _authOptions(),
    );
    if (resp.statusCode != 200) {
      throw Exception('Failed to sign up as rider: HTTP ${resp.statusCode}');
    }
  }
}
