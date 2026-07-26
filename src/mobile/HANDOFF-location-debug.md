# Handoff — Driver location not uploading to server

**Date:** 2026-07-07
**Status:** UNRESOLVED. Root cause not yet identified. Investigation blocked by inability to read on-device logs (see "Why we're stuck").

---

## ⚠️ Read first: uncommitted temporary hack to revert

`lib/core/repositories/location_repository.dart` contains a **temporary test flag that MUST be reverted before commit/ship**:

```dart
static const bool _kForcedFixTestMode = true;   // REVERT TO false (or delete the loop)
```

With it `true`, a debug-only diagnostic loop (`_startDebugForcedFixes`) runs **in release builds too**, forcing a GPS capture + upload every 8 seconds. If this ships, every driver's app spams the server. Set it back to `false` (loop becomes debug-only) or remove the forced-fix loop entirely once debugging is done.

The **release build currently installed on the iPhone** was built WITH this flag = true, so the installed app and the source match right now.

---

## The symptom (confirmed by observation)

The driver app talks to the **production** server `https://waygon.dev` (that's the default; `ApiConfig.baseUrl` in `lib/core/config/api_config.dart:31`). In the prod access log we repeatedly see the app working:

- `GET /api/core/me` → 200
- `GET /api/trips/driver/assigned` → 200
- `PATCH /api/trips/1/driver` → 200 (many — user cycling trip status)

…but **never a single `POST /api/drivers/location`** — not even a failed `401`/`403`/`409`. Across every test. So the app is alive, authenticated, and reaching the same host fine; only the location upload never leaves the device (or never even attempts).

## The one on-device data point we captured (confirmed)

Exactly one debug session attached successfully and printed:

```
[locus] headers: attaching Bearer token
[locus] start: tracking=true paused=false pending=0 reason=null
```

Interpretation (grounded):
- **Auth is fine** — a Firebase Bearer token is obtained and attached.
- **locus reports `tracking=true`** — the native tracking service started.
- **`paused=false`** — sync is NOT in a paused state.
- **`pending=0`** — zero fixes queued *at the instant tracking started* (expected at t=0; tells us nothing about whether fixes accumulate later).

⚠️ NOTE: this session was on a build that did NOT yet contain the forced-fix loop. We have **never** observed a `[locus] forced fix …` or `[locus] sync attempt …` line on a device. We do not know if the forced-fix loop actually runs, records, or uploads.

## Theories tried and their status

| Theory | Status | Evidence |
|---|---|---|
| App pointed at wrong/local server | **DISPROVEN** | me/trips/PATCH all reach `waygon.dev`; location would use same base URL |
| Auth token missing → rejected | **DISPROVEN** | `headers: attaching Bearer token` logged; also a 401 would still SHOW as a POST in the log (it doesn't) |
| locus stuck in persisted 401/403 sync pause | **DISPROVEN** | `start:` showed `paused=false, reason=null`. The `resume()` code I added is harmless but was NOT the fix |
| Stationary + `distanceFilter:10` suppresses recording | **UNCONFIRMED / likely a real factor** | Plausible, but we never observed the queue to confirm. The forced-fix loop was built to bypass it but was never observed working |
| locus native uploader never fires at all | **OPEN — most likely** | Zero POSTs ever, in any build/mode = the native HTTP sync may have never worked in this integration |

## Why we're stuck (the actual blocker)

**We cannot read the client's logs.**
- `flutter run --release` does not stream `debugPrint` on iOS.
- `flutter logs` returns nothing on iOS release over Wi-Fi.
- `flutter run --debug` (which WOULD stream logs) requires the wireless Dart VM Service handshake, which on **iOS 26 over Wi-Fi is unreliable** — it failed 3 of 4 attempts (VM service "not discovered after 75s", then `CoreDeviceError 3 / Mercury 1001: connection invalidated`). Flutter's own output repeatedly says: *"consider using a wired (USB) connection."*
- The server is **remote production** in Docker (`web-1`, `172.18.0.5`); there is **no docker CLI on this Mac**, so this session cannot tail the prod log. Only the human (who has prod log access) can observe it.

Net: every prod-log test shows "no POST," but we can't see *why* because we can't see the client. That is the core problem to solve next, and it's a tooling problem, not (yet) a code diagnosis.

## Recommended next steps (in priority order)

1. **Plug the iPhone into the Mac with a USB cable and run `flutter run --debug -d 00008101-000A0CE02202001E`.**
   This is the single highest-value action. Wired makes the debug attach reliable and streams the `[locus]` lines directly. With that, the following become immediately visible and will localize the bug in one run:
   - Does `[locus] start:` fire, and does the `_LocationBanner` show "Sharing your location…" (state `active`)? → confirms tracking actually started.
   - Do `[locus] forced fix … pending=N` lines appear every 8s?
     - `pending` climbing, no server POST → **native uploader isn't draining the queue** (locus config/native problem).
     - `forced fix failed: <error>` → **capture/permission problem** in `getCurrentPosition`.
     - never logs → **tracking not active / loop not entered**.

2. **Add two missing native-state diagnostics** (we never checked these) right after `Locus.ready(...)` in `_configure()` (`location_repository.dart`):
   ```dart
   debugPrint('[locus] isSyncReady=${await Locus.dataSync.isSyncReady()}');
   debugPrint('[locus] state=${await Locus.getState()}');
   ```
   `isSyncReady()` returns whether the native side actually has the URL configured and sync enabled. If this is `false`, autoSync will never POST regardless of anything else — a strong candidate we have not ruled out.

3. **Check iOS location permission level on the phone:** Settings → (the app) → Location. Must be granted; "Always" is needed for background. If it's "While Using" and the app was backgrounded during a test, iOS blocks capture.

4. **Suspect the custom sync-body path.** `_configure()` calls `Locus.setSyncBodyBuilder((locations, extras) => …)` (a closure). This makes native call back into Dart (`buildSyncBody` method channel) before every sync. If that round-trip is misconfigured/failing, the native uploader may stall before issuing HTTP. Worth testing: temporarily REMOVE the custom body builder and let locus POST its default body to a throwaway endpoint (e.g. webhook.site) to isolate whether locus's uploader works at all in this app. If the default body reaches webhook.site but our endpoint never sees anything, the problem is the body-builder/endpoint contract, not locus.

5. Once the cause is found: **revert `_kForcedFixTestMode` to false** and decide whether to keep the diagnostics/forced-fix loop or strip them.

## Files touched this session (all in `lib/core/repositories/location_repository.dart`)

- `resume()`-on-start for a persisted sync pause — **kept, but proven not the cause** (paused=false). Harmless; consider removing.
- Headless top-level callbacks `locusHeadlessSyncBody` / `locusHeadlessHeaders` + registration in `_configure()` — for background/terminated uploads. Reasonable to keep; unverified.
- `[locus]`-tagged `debugPrint` diagnostics in the headers callback, sync-body builder, and `startTracking()`.
- `_startDebugForcedFixes()` forced-fix loop + `_kForcedFixTestMode` flag (**temporary — revert**).

No server-side changes. `POST /api/drivers/location` handler is `src/server/src/app/api.py:264` (writes `Vehicle.last_location`; 409 if the driver has no Vehicle). Tracking is dispatched from `lib/trip/detail/view/trip_detail_page.dart:56` when trip status ∈ `enroute|arrived|in_progress` (`lib/core/models/trip.dart:107`).

## Background tasks / build state at handoff

- A `flutter run --release` (with the forced-fix build) was launched and the app installed + launched on the phone.
- Xcode `DerivedData` and Flutter `build/` were cleared this session (~14 GB reclaimed); the next build is a full/clean compile (~6 min). `iOS DeviceSupport` (5.5 GB) and `CoreSimulator` (2.8 GB) were left in place.
- Device: `iPhone Mini (wireless) • 00008101-000A0CE02202001E • iOS 26.5`.
