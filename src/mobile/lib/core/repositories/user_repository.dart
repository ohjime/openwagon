import 'package:app/core/models/user.dart';

/// Repository for interfacing with user-related Firestore operations using domain models.
class UserRepository {
  UserRepository();

  /// Creates a new user document using the provided UID.
  Future<void> createUser(User user) async {
    try {
      await Future.delayed(const Duration(milliseconds: 500));
      return;
    } catch (e) {
      throw Exception('Failed to create user: ${e.toString()}');
    }
  }

  /// Retrieves a user document by UID and converts it to a [User] instance.
  Future<User> getUser(User user) async {
    try {
      await Future.delayed(const Duration(milliseconds: 500));
      return User.empty;
    } catch (e) {
      throw Exception('Failed to get user: ${e.toString()}');
    }
  }

  /// Updates a user document by converting the provided [User] to a map.
  Future<void> updateUser(User user) async {
    try {
      await Future.delayed(const Duration(milliseconds: 500));
      return;
    } catch (e) {
      throw Exception('Failed to update user: ${e.toString()}');
    }
  }

  /// Deletes a user document by UID.
  Future<void> deleteUser() async {
    try {
      await Future.delayed(const Duration(milliseconds: 500));
      return;
    } catch (e) {
      throw Exception('Failed to delete user: ${e.toString()}');
    }
  }

  /// Retrieves all users from the 'users' collection.
  Future<List<User>> getUsers() async {
    try {
      await Future.delayed(const Duration(milliseconds: 500));
      return [User.empty, User.empty];
    } catch (e) {
      throw Exception('Failed to get users: \\${e.toString()}');
    }
  }
}
