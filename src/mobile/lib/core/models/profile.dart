import 'package:equatable/equatable.dart';

import 'user.dart';

/// The signed-in account's driver profile, if one exists. Mirrors the server's
/// `/api/core/me` → `driver` object.
class DriverProfile extends Equatable {
  const DriverProfile({
    required this.id,
    required this.status,
    required this.hasVehicle,
  });

  final int id;

  /// `available` / `unavailable` — whether dispatch may put them on the road.
  final String status;

  /// A driver can only broadcast GPS once a vehicle is attached (the position
  /// lives on the Vehicle server-side), so the trip screen uses this to decide
  /// whether location sharing can work.
  final bool hasVehicle;

  factory DriverProfile.fromJson(Map<String, dynamic> json) {
    return DriverProfile(
      id: json['id'] as int,
      status: (json['status'] ?? '') as String,
      hasVehicle: (json['has_vehicle'] ?? false) as bool,
    );
  }

  @override
  List<Object?> get props => [id, status, hasVehicle];
}

/// The signed-in account's rider profile, if one exists. Mirrors `/api/core/me`
/// → `rider`.
class RiderProfile extends Equatable {
  const RiderProfile({required this.id});

  final int id;

  factory RiderProfile.fromJson(Map<String, dynamic> json) {
    return RiderProfile(id: json['id'] as int);
  }

  @override
  List<Object?> get props => [id];
}

/// The full result of `/api/core/me`: the account plus whichever role profiles
/// exist. A null [driver]/[rider] is the signal the portal uses to offer
/// "Sign up as Driver/Rider".
class Profile extends Equatable {
  const Profile({required this.account, this.driver, this.rider});

  final User account;
  final DriverProfile? driver;
  final RiderProfile? rider;

  bool get hasDriver => driver != null;
  bool get hasRider => rider != null;
  bool get hasAnyRole => hasDriver || hasRider;

  factory Profile.fromJson(Map<String, dynamic> json) {
    final driver = json['driver'];
    final rider = json['rider'];
    return Profile(
      account: User.fromJson((json['account'] ?? const {}) as Map<String, dynamic>),
      driver: driver is Map<String, dynamic>
          ? DriverProfile.fromJson(driver)
          : null,
      rider: rider is Map<String, dynamic> ? RiderProfile.fromJson(rider) : null,
    );
  }

  @override
  List<Object?> get props => [account, driver, rider];
}
