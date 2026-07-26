enum AppMode { driver, rider }

extension AppModeExtension on AppMode {
  bool get isDriver => this == AppMode.driver;
  bool get isRider => this == AppMode.rider;

  String get displayName {
    switch (this) {
      case AppMode.driver:
        return 'Driver Mode';
      case AppMode.rider:
        return 'Rider Mode';
    }
  }
}
