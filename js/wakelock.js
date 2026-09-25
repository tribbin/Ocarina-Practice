// Screen Wake Lock (Robin's IDEAS bugs line 2026-09-25: phones black the
// screen while someone is playing a song or practicing — the browser must keep
// the page on, the way a video player does). One sentinel behind a Set of
// labeled reasons ("melody", "practice"); a sealed consumer calls hold/drop,
// the module owns the acquire/release/re-acquire choreography:
//   - any reason while the page is visible  -> request("screen")
//   - no reasons                            -> release
//   - the UA takes the lock on tab hide     -> its release event clears us,
//     returning to visibility re-requests unaided (the spec's own pattern).
// Unsupported browsers are a no-op: the whole surface is feature-detected and
// every rejection is swallowed (console-hygiene: nothing here may growl).

let sentinel = null;
const reasons = new Set();
// Test seam (the setNoteSink/setHoverProbe pattern): tests install a stand-in
// provider for the UA surface; null restores the real navigator.wakeLock.
// The real property is a readonly WebIDL getter — no script assignment can
// replace it, which is why the seam must live here.
let wakeLockSource = null;

function currentWakeLock() {
  if (wakeLockSource) return wakeLockSource();
  if (typeof navigator === "undefined") return null;
  return navigator.wakeLock || null;
}

function wakeWanted() {
  try {
    return (reasons.size > 0
            && currentWakeLock()
            && document.visibilityState === "visible");
  } catch (e) { return false; }
}

async function wakeSync() {
  try {
    if (wakeWanted()) {
      if (!sentinel) {
        sentinel = await currentWakeLock().request("screen");
        sentinel.addEventListener("release", onSentinelRelease);
      }
    } else if (sentinel) {
      const s = sentinel;
      sentinel = null;
      // The UA-triggered release event is handled at the listener and MUST
      // run before the explicit release() resolves (the event dispatch is
      // synchronous there) — s.release() would otherwise double-fire it.
      await s.release();
    }
  } catch (e) { /* denied/unsupported/benign race: stay unlocked, stay quiet */ }
}

// Released from OUR side after sentinel reassignment, or by the UA (hidden
// tab / window minimized): both funnel here, re-acquiring only if a reason
// still asks for the light and the page is visible again.
function onSentinelRelease() {
  sentinel = null;
  if (wakeWanted()) wakeSync();
}

export function wakeHold(reason) {
  reasons.add(reason);
  wakeSync();
}

export function wakeDrop(reason) {
  reasons.delete(reason);
  wakeSync();
}

export function wakeReasons() {
  return reasons.size;
}

export function setWakeLockSource(fn) {
  wakeLockSource = fn || null;
}

if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    // Coming back visible: the UA has already released the (hidden) lock and
    // fired its event — one sync pass decides whether to re-request.
    wakeSync();
  });
}
