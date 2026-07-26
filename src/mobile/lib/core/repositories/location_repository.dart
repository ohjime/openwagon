import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart' as firebase_auth;
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:latlong2/latlong.dart';
import 'package:locus/locus.dart';

import 'package:app/firebase_options.dart';
import '../config/api_config.dart';

/// Shares the driver's GPS position with the backend, including while the app is
/// backgrounded or terminated.
///
/// This is a thin wrapper over the `locus` SDK, which does the hard part
/// natively: it captures fixes and uploads them from a platform background
/// service, so tracking survives the app leaving the foreground (a plain Dart
/// `Timer` cannot — the OS suspends the isolate). We keep the server design the
/// Vehicle model documents: the app POSTs fixes to `/api/drivers/location` and
/// the server OVERWRITES `Vehicle.last_location` (never appends).
///
/// Delivery is durable: locus queues fixes in SQLite and drains them — batched —
/// when connectivity returns, so a tunnel or dead zone no longer silently drops
/// positions the way the old fire-and-forget loop did.
///
/// Identity is carried by the Firebase ID token in the `Authorization` header,
/// refreshed per-sync (tokens expire hourly), NOT by anything in the body — the
/// server binds the write to the authenticated driver. See app.api.
class LocationRepository {
  LocationRepository({firebase_auth.FirebaseAuth? firebaseAuth})
    : _firebaseAuth = firebaseAuth ?? firebase_auth.FirebaseAuth.instance;

  final firebase_auth.FirebaseAuth _firebaseAuth;
  bool _configured = false;

  /// DEBUG-ONLY. Drives a periodic forced GPS capture so tracking can be tested
  /// from a standstill (see [_startDebugForcedFixes]). Never runs in release.
  Timer? _debugFixTimer;

  /// Human-readable, on-DEVICE feed of the native uploader's outcomes.
  ///
  /// This is the diagnostic the "we can't read logs" problem needed: locus
  /// emits an [HttpEvent] on EVERY sync attempt — success, HTTP status, network
  /// error, and the pre-POST abort reasons `sync_body_builder_failed` /
  /// `pre_sync_validator_rejected` — plus pause/resume transitions. We fan those
  /// into readable strings the UI can render, so a plain RELEASE build over
  /// Wi-Fi reveals exactly what the uploader is doing without a debug attach.
  final StreamController<String> _syncLogController =
      StreamController<String>.broadcast();
  StreamSubscription<HttpEvent>? _httpSub;
  StreamSubscription<SyncPauseState>? _pauseSub;

  /// Latest sync outcomes as display strings. Subscribe from the tracking bloc
  /// to surface the newest line in the in-app location banner.
  Stream<String> get syncEvents => _syncLogController.stream;

  void _emitSync(String message) {
    debugPrint('[locus] $message');
    if (!_syncLogController.isClosed) _syncLogController.add(message);
  }

  /// Live position updates for foreground UI (e.g. the "sharing" indicator or a
  /// map). Mapped to `latlong2` so callers never see the locus type.
  Stream<LatLng> get positions => Locus.location.stream.map(
    (l) => LatLng(l.coords.latitude, l.coords.longitude),
  );

  /// Requests the location permission locus needs for background tracking
  /// (drives the platform's multi-step "Always" flow). Returns whether it was
  /// granted.
  Future<bool> requestPermission() => Locus.requestPermission();

  /// Begin sharing. Idempotent: safe to call when already tracking.
  Future<void> startTracking() async {
    await _configure();
    await Locus.start();

    // Force locus out of its initial STATIONARY state.
    //
    // On iOS, `start()` arms tracking but the recorder stays paused until motion
    // is detected — a device sitting still (or a driver idling at a curb) emits
    // NO fixes, so the backlog never fills and the uploader never POSTs. That is
    // exactly the "forced fix pending=0, no sync ever" symptom. A dispatch app
    // wants position even while stopped, so we kick it into the moving state
    // immediately; `disableStopDetection`/`stopOnStationary:false` (see config)
    // keep it there.
    await Locus.location.changePace(true);
    final state = await Locus.getState();
    debugPrint(
      '[locus] state after start: enabled=${state.enabled} '
      'isMoving=${state.isMoving}',
    );

    // Clear any *persisted* transport pause before we start relying on autoSync.
    //
    // locus latches sync into a paused state on an HTTP 401/403 and that pause
    // SURVIVES app restarts (it's stored natively). Recovery is not automatic —
    // it needs an explicit resume(). Without this, a single stale-token sync
    // early in development (e.g. a fix uploaded before the driver's Vehicle
    // existed, or with an expired Firebase token) silently blocks EVERY future
    // upload — the queue fills but nothing is ever POSTed — until reinstall.
    // Our headers callback already refreshes the token per-sync, so resuming on
    // each start is safe: if auth is genuinely bad it'll just re-pause.
    final backlog = await Locus.dataSync.getBacklog();
    debugPrint(
      '[locus] start: tracking=${await Locus.isTracking()} '
      'paused=${backlog.isPaused} pending=${backlog.pendingLocationCount} '
      'reason=${Locus.dataSync.pauseReason}',
    );
    if (backlog.isPaused) {
      final resumed = await Locus.dataSync.resume();
      debugPrint('[locus] cleared persisted sync pause -> resumed=$resumed');
    }

    _startDebugForcedFixes();
  }

  /// TEMPORARY TEST FLAG — REVERT BEFORE COMMIT/SHIP.
  ///
  /// Set true so the forced-fix loop below runs in RELEASE builds too. Wireless
  /// DEBUG attach on iOS 26 is too flaky to observe logs, but a RELEASE build
  /// installs reliably over Wi-Fi and runs standalone — so we let it drive the
  /// loop and confirm uploads purely via the prod server access log. MUST be set
  /// back to false (loop → debug-only) before this is committed or released,
  /// otherwise every driver's app spams a fix every 8s.
  static const bool _kForcedFixTestMode = true;

  /// Diagnostic loop. The `tracking` preset's `distanceFilter: 10` means a
  /// stationary device emits no fresh CoreLocation fixes, so the live
  /// capture→sync path never fires — you'd have to physically drive to test
  /// uploads. This loop sidesteps that.
  ///
  /// NOTE (iOS): the previous version relied on `getCurrentPosition(persist:
  /// true)`. That is a no-op on iOS — the native `getCurrentPosition` handler
  /// ignores the `persist`/`samples` arguments entirely (it just calls
  /// `requestLocation()`), so `persist:true` never queued anything. What DOES
  /// work is the side effect: while tracking is enabled, the fix that
  /// `getCurrentPosition()` produces flows through the same
  /// `didUpdateLocations → emitLocationEvent → syncNow` path as a normal fix,
  /// which persists it and triggers a POST. So we just request a position and
  /// let that path do the upload; the real outcome shows up on [syncEvents]
  /// (the [HttpEvent] feed), not in the backlog count.
  ///
  /// Runs only in debug, unless [_kForcedFixTestMode] is set; torn down in
  /// [stopTracking].
  void _startDebugForcedFixes() {
    if (!kDebugMode && !_kForcedFixTestMode) return;
    _debugFixTimer?.cancel();
    _debugFixTimer = Timer.periodic(const Duration(seconds: 8), (_) async {
      try {
        final loc = await Locus.location.getCurrentPosition(samples: 1);
        final backlog = await Locus.dataSync.getBacklog();
        final state = await Locus.getState();
        _emitSync(
          'fix ${loc.coords.latitude.toStringAsFixed(5)},'
          '${loc.coords.longitude.toStringAsFixed(5)} '
          'enabled=${state.enabled} moving=${state.isMoving} '
          'pending=${backlog.pendingLocationCount} paused=${backlog.isPaused}',
        );
      } catch (error) {
        _emitSync('forced fix failed: $error');
      }
    });
  }

  /// Stop sharing and tear down the native background service.
  Future<void> stopTracking() {
    _debugFixTimer?.cancel();
    _debugFixTimer = null;
    return Locus.stop();
  }

  Future<bool> isTracking() => Locus.isTracking();

  /// Releases the sync-event subscriptions and the log stream. The repository
  /// is app-lifetime, so this mainly matters for tests.
  Future<void> dispose() async {
    await _httpSub?.cancel();
    await _pauseSub?.cancel();
    await _syncLogController.close();
  }

  /// One-time SDK setup: the uploader endpoint, the per-sync auth header, and
  /// the request body shaped to the server's contract. Guarded so repeated
  /// [startTracking] calls don't re-register callbacks.
  Future<void> _configure() async {
    if (_configured) return;

    // Fresh Firebase ID token on every sync — tokens expire after ~1h, so a
    // header captured once at ready() would start returning 401 mid-shift.
    await Locus.setHeadersCallback(() async {
      final token = await _firebaseAuth.currentUser?.getIdToken();
      if (token == null || token.isEmpty) {
        debugPrint('[locus] headers: NO Firebase token — sending unauthed');
        return <String, String>{};
      }
      debugPrint('[locus] headers: attaching Bearer token');
      return {'Authorization': 'Bearer $token'};
    });

    // locus posts a batch; the server reads the newest fix from it. We send only
    // coordinates + timestamp — never any device/driver id, so the write can
    // only ever be attributed to the token's driver.
    await Locus.setSyncBodyBuilder((locations, extras) async {
      // Fires only when native is actually attempting a sync — the single most
      // useful signal for "is anything being uploaded?". If you never see this
      // while driving, no sync is being attempted (queue empty or paused); if
      // you see it but the server logs nothing, the request is failing in
      // transit (URL/DNS/TLS/auth).
      debugPrint(
        '[locus] sync attempt: posting ${locations.length} fix(es) '
        'to ${ApiConfig.baseUrl}/api/drivers/location',
      );
      return _buildLocationSyncBody(locations);
    });

    // Terminated/background syncs run in a headless Dart isolate that cannot see
    // the closures above — they need top-level entry-point functions. Without
    // these, uploads stop the moment the OS kills the app mid-trip, silently
    // defeating stopOnTerminate:false / startOnBoot:true / enableHeadless:true.
    await Locus.registerHeadlessSyncBodyBuilder(locusHeadlessSyncBody);
    await Locus.registerHeadlessHeadersCallback(locusHeadlessHeaders);

    // The HTTP-outcome feed. locus emits one HttpEvent per sync attempt with
    // the exact result; this is what makes a release build over Wi-Fi
    // self-diagnosing (see [syncEvents]). Guarded so repeat starts don't stack
    // listeners.
    _httpSub ??= Locus.dataSync.events.listen((e) {
      _emitSync(
        e.ok
            ? 'sync OK ${e.status} sent=${e.recordsSent ?? '?'}'
            : 'sync FAIL ${e.status} ${e.responseText ?? '(no body)'}',
      );
    });
    _pauseSub ??= Locus.dataSync.pauseChanges.listen((s) {
      _emitSync(s.isPaused ? 'sync PAUSED reason=${s.reason}' : 'sync resumed');
    });

    // locus's HTTP sync layer REQUIRES a "route context" on every fix or it
    // silently QUARANTINES it — the fix is never batched (no POST) and isn't
    // even counted in the backlog (`pending` stays 0), so nothing is ever
    // uploaded and no HttpEvent fires. The native side derives that context
    // from five `extras` keys, ALL of which must be present and non-empty:
    // owner_id, driver_id, task_id, tracking_session_id, started_at
    // (see SyncManager.extractRouteContext). This app previously set no extras
    // at all, which is why not one fix ever reached the server.
    //
    // These are DEVICE-SIDE ONLY: the custom sync body builder sends just
    // lat/lng/ts and drops extras, and the server binds the write to the token's
    // driver — so these values never leave the phone. They exist purely to let
    // locus group and drain the queue; any stable, non-empty set works.
    final uid = _firebaseAuth.currentUser?.uid ?? 'unknown-driver';
    final startedAt = DateTime.now().toUtc().toIso8601String();

    await Locus.ready(
      ConfigPresets.tracking.copyWith(
        url: '${ApiConfig.baseUrl}/api/drivers/location',
        extras: {
          'owner_id': 'waygon',
          'driver_id': uid,
          'task_id': 'active-trip',
          'tracking_session_id': '$uid:$startedAt',
          'started_at': startedAt,
        },
        // Sync each fix promptly while online (autoSyncThreshold: 1), but drain
        // an offline backlog in batches of up to maxBatchSize per request.
        autoSync: true,
        batchSync: true,
        autoSyncThreshold: 1,
        maxBatchSize: 50,
        // Send raw JSON. locus defaults to gzipping request bodies over ~1 KB
        // (Content-Encoding: gzip), but the django-ninja endpoint does a plain
        // json.loads on request.body with no gzip decoding, so a compressed
        // batch fails with "400 Cannot parse request body". A multi-fix batch
        // crosses the 1 KB threshold, so this bites as soon as the backlog
        // grows. Fixes are tiny; compression saves nothing here.
        compressRequests: false,
        // Persist every fix to the native SQLite backlog. With batchSync the
        // uploader drains from that store, so this must be on for anything to
        // be sent; the tracking preset leaves it unset (iOS defaults to
        // "none"), so set it explicitly.
        persistMode: PersistMode.location,
        // Keep recording while the vehicle is stopped. locus otherwise pauses
        // the recorder when it detects the device is stationary — but dispatch
        // still needs the position of a driver idling at a curb or red light.
        disableStopDetection: true,
        stopOnStationary: false,
        // iOS reliability for vehicle tracking:
        //  - pausesLocationUpdatesAutomatically defaults to TRUE, which lets
        //    iOS silently stop delivering fixes when it thinks you're parked —
        //    exactly the standstill case dispatch still needs. Force it off.
        //  - keep the app alive between fixes so heartbeat/upload survive.
        //  - show the blue background-location indicator (also nudges iOS to
        //    keep updates flowing).
        pausesLocationUpdatesAutomatically: false,
        preventSuspend: true,
        showsBackgroundLocationIndicator: true,
        // Keep sharing if the OS kills or reboots the app mid-trip.
        stopOnTerminate: false,
        startOnBoot: true,
        enableHeadless: true,
        // Android foreground-service notification (required for background
        // location on Android); mirrors the in-app "sharing" banner.
        notification: const NotificationConfig(
          title: 'Waygon',
          text: 'Sharing your location with dispatch',
        ),
      ),
    );

    _configured = true;
  }
}

/// Shapes locus's pending fixes into the server's `LocationBatch` contract
/// (`app.api.update_driver_location`). Shared by the foreground closure and the
/// headless entry point so both send an identical body. Coordinates + timestamp
/// only — identity comes from the auth header, never the body.
Map<String, dynamic> _buildLocationSyncBody(List<Location> locations) {
  return {
    'fixes': [
      for (final l in locations)
        {
          'lat': l.coords.latitude,
          'lng': l.coords.longitude,
          'ts': l.timestamp.toIso8601String(),
        },
    ],
  };
}

/// Headless sync-body builder. MUST be a top-level function marked as a VM
/// entry point: locus invokes it from a background isolate when syncing while
/// the app is terminated, where the foreground closure is unreachable.
@pragma('vm:entry-point')
Future<Map<String, dynamic>> locusHeadlessSyncBody(
  SyncBodyContext context,
) async {
  return _buildLocationSyncBody(context.locations);
}

/// Headless auth-header provider. Runs in the background isolate on a sync
/// (e.g. locus recovering from a 401 while the app is terminated), where
/// Firebase is NOT yet initialized — so we bootstrap it before reading the ID
/// token. Best-effort: on any failure we return no header and let native fall
/// back to its last cached one rather than crash the sync.
@pragma('vm:entry-point')
Future<Map<String, String>> locusHeadlessHeaders() async {
  try {
    if (Firebase.apps.isEmpty) {
      await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform,
      );
    }
    final token =
        await firebase_auth.FirebaseAuth.instance.currentUser?.getIdToken();
    if (token == null || token.isEmpty) return <String, String>{};
    return {'Authorization': 'Bearer $token'};
  } catch (error) {
    debugPrint('[locus] headless headers failed: $error');
    return <String, String>{};
  }
}
