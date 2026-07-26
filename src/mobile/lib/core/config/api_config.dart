/// Single source of truth for the backend origin every repository talks to.
///
/// Defaults to **production** so builds hit the real backend without extra
/// flags. To debug against a local dev server you must switch this manually —
/// either pass `--dart-define=API_BASE=...` (preferred, no code change) or
/// temporarily point [baseUrl]'s fallback at [_localDevHost] below.
class ApiConfig {
  ApiConfig._();

  /// Production backend origin. This is the default target for every
  /// `/api/...` call (the django-ninja API is served from the apex domain).
  static const String _production = 'https://waygon.dev';

  /// Local dev server origin — used ONLY when manually debugging against a
  /// machine running `make server`. On a physical device this must be the host
  /// machine's LAN IP (not `localhost`, which is the phone itself); update it to
  /// match `ipconfig getifaddr en0` / the runserver bind. Not used unless you
  /// wire it into [baseUrl] or pass it via `--dart-define`.
  // ignore: unused_field
  static const String _localDevHost = 'http://192.168.1.75:8000';

  /// Optional compile-time override. Pass e.g.
  /// `--dart-define=API_BASE=http://192.168.1.75:8000` to point every
  /// `/api/...` call at the LAN dev server for debugging without editing code.
  /// Empty by default, in which case [_production] is used.
  static const String _override = String.fromEnvironment('API_BASE');

  /// Base origin for all `/api/...` calls. Order: the `--dart-define` override
  /// wins when provided; otherwise defaults to [_production]. To force local
  /// debugging in code, replace `_production` here with [_localDevHost].
  static String get baseUrl => _override.isNotEmpty ? _override : _production;
}
