#!/usr/bin/env python3
# Practice acceptance test: drives the REAL js/practice.js engine in a real
# Chromium page with the pitches the 'play' transport would output, using the
# page's built-in synthetic mic provider (?practiceTest=1 →
# window.__pracFrame = { hz, rms } replaces capture; js/practice.js readFrame).
#
# Two modes:
#   - schedule: the exact play output timeline (each note's sounding hold via
#     soundingGridBeats, ties carried, tempo headers honored) fed open-loop.
#     Only valid for slide-free melodies: strict play acceptance is the
#     property under test.
#   - zones: closed-loop player model — the driver sounds whichever pitch the
#     tuner currently demands (P.bar.zones[P.zonesNear]) and goes silent
#     whenever the engine demands a fresh attack. Used for ~ chain songs:
#     the pure play timeline feeds each hop for exactly its notated tone,
#     but the detector's smoothing needs a couple of ticks to read a new
#     pitch in-tune after a step change, so a real player (like the driver)
#     holds each pitch until the reading line advances — the per-zone
#     75%-of-own-tone rule then absorbs that settle lag via every zone's
#     freed quarter.
#
# Assertions per case: the song completes, the reading line never moves
# backwards, and "await" (the restart gate) never occurs after the first
# bar — i.e. consecutive notes flow without any forced silence.
#
#   pip install playwright && playwright install chromium
#   python3 tests/practice_accepts_melody.py          # runs headless & silent
#   python3 tests/practice_accepts_melody.py --headed # watch it in a window


import http.server
import socketserver
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TICK_FEED_MS = 30
FIRST_BAR_SAFE_IDX = 5  # past the first bar (fresh-entry await is allowed there)
HEADLESS = "--headed" not in sys.argv

CASES = [
    dict(name="C major scale — strict play-output schedule",
         query="", mode="schedule", src=None),
    dict(name="Ties · dots · staccato · rests · triplets · inline tempo — strict",
         query="", mode="schedule",
         src=( "# T · ties dots staccato rests triplets tempo\n"
               "# tempo 120\n"
               "E5/1 -/1 D5/2t E5/2t F5/2t\n"
               "C6/4! D6/4! E6/2 r/4 F6/1\n"
               "# tempo 90\n"
               "A5/2. -/2 G5/1")),
    dict(name="Dense triplet-16ths + tie chains — player model",
         query="", mode="zones",
         src=( "# T · dense triplets\n"
               "E5/16t F5/16t G5/16t A5/16t G5/16t F5/16t\n"
               "E5/8 -/8 D5/2 -/4 r/4 E5/2.")),
    dict(name="Song of Storms (Double Alto C) — chain songs, player model",
         query="inst=stein-double-alto-c&song=song-of-storms-alto", mode="zones", src=None),
]

SCHEDULE_DRIVER = """
SRC => new Promise(resolve => {
  if (SRC) { document.getElementById("src").value = SRC; render(); }
  const toks = parse(document.getElementById("src").value);
  if (toks.some(t => t.type === "note" && t.slide)) { resolve({ skip: "has ~ slides" }); return; }
  let q = quarterSec();
  const evs = []; let t = 0;
  const PAD = 0.25; // silence lead: the fresh entry needs its gapMs
  for (let i = 0; i < toks.length; i++) {
    const tok = toks[i];
    if (tok.type === "tempo") { q = quarterSecFor(tok.bpm); continue; }
    if (tok.type === "bar") continue;
    if (tok.type === "rest") { t += tokenGridBeats(tok) * q; continue; }
    if (tok.type === "tie") continue; // span already covered by its holder
    if (tok.type === "note" && NOTES.includes(tok.id)) {
      const hold = Math.max(0.09, soundingGridBeats(toks, i) * q);
      evs.push({ t0: PAD + t, t1: PAD + t + hold, hz: freqOf(tok.id) });
      t += hold;
    }
  }
  const songSec = PAD + t + 1.0;
  const t0 = performance.now();
  const feed = setInterval(() => {
    const now = (performance.now() - t0) / 1000;
    const ev = evs.find(e => now >= e.t0 && now < e.t1);
    window.__pracFrame = ev ? { hz: ev.hz, rms: 0.4 } : { hz: 0, rms: 0 };
  }, 30);
  OCA_PRACTICE.start();
  let awaitLate = false;
  // The arbiter waits for the session to be SEEN engaged before the stop
  // signal means anything: on a slow CI box the first poll tick can race the
  // engage (pick '?song' renders, transport syncs) and read inactive — a
  // 0-completion instant stop that is a measurement artifact, not a case fail
  // (bit a CI run to flake exactly like this). Two consecutive inactive
  // reads AFTER engagement are the only end-of-case signal.
  let started = false, idleStreak = 0;
  const poll = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (P.state === "await" && P.idx > 5) awaitLate = true;
    if (OCA_PRACTICE.active() && !P.paused) { started = true; }
    if (!OCA_PRACTICE.active() || P.paused) {
      if (!started) { idleStreak = 0; return; }   // engage still racing in
      if (++idleStreak < 2) return;               // one blip is not a stop
      clearInterval(feed); clearInterval(poll);
      resolve({ completed: !!P.completed, awaitLate, idx: P.idx,
                total: P.tokens.length, timeout: false });
    }
  }, 100);
  setTimeout(() => { clearInterval(feed); clearInterval(poll);
                     resolve({ completed: false, awaitLate, timeout: true,
                               idx: OCA_PRACTICE._p.idx }); },
             (songSec + 20) * 1000);
})
"""

ZONES_DRIVER = """
SRC => new Promise(resolve => {
  if (SRC) { document.getElementById("src").value = SRC; render(); }
  // Player model: silence when the engine demands a re-attack ("await"),
  // otherwise sound the pitch the tuner currently demands.
  OCA_PRACTICE.start();
  let awaitLate = false, wentBack = false, lastIdx = 0;
  const feed = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (P.state === "await" && P.idx > 5) awaitLate = true;
    if (P.idx < lastIdx) wentBack = true;
    lastIdx = Math.max(lastIdx, P.idx);
    if (P.state === "await" || P.state === "rest" || !P.bar) {
      window.__pracFrame = { hz: 0, rms: 0 };
    } else {
      const k = P.zonesNear >= 0 ? P.zonesNear : 0;
      window.__pracFrame = { hz: P.bar.zones[k], rms: 0.4 };
    }
  }, 30);
  let started = false, idleStreak = 0;
  const poll = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (OCA_PRACTICE.active() && !P.paused) { started = true; }
    if (!OCA_PRACTICE.active() || P.paused) {
      if (!started) { idleStreak = 0; return; }
      if (++idleStreak < 2) return;
      clearInterval(feed); clearInterval(poll);
      resolve({ completed: !!P.completed, awaitLate, wentBack, timeout: false });
    }
  }, 100);
  setTimeout(() => { clearInterval(feed); clearInterval(poll);
                     resolve({ completed: false, awaitLate, wentBack,
                               timeout: true }); }, 120000);
})
"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):  # silence the per-request console spam
        pass


def start_server():
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), QuietHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            for case in CASES:
                page = browser.new_page()
                errs = []
                page.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
                page.goto(f"{base}?practiceTest=1" +
                          (("&" + case["query"]) if case["query"] else ""))
                # Wait for the app's REAL readiness, not just the practice
                # module: OCA_PRACTICE exists at script-parse time, but
                # window.NOTES (fingerings the schedule driver needs) is
                # installed asynchronously by boot() after its JSON fetches —
                # racing it in CI's cold cache threw early evals.
                page.wait_for_function(
                    "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                    " && window.NOTES && window.NOTES.length")
                driver = SCHEDULE_DRIVER if case["mode"] == "schedule" else ZONES_DRIVER
                print(f"\n== {case['name']}"
                      f"\n   feeding mic frames in real time — no audio, no"
                      f" window; this takes ~15-45 s per case…", flush=True)
                t_case = time.monotonic()
                result = page.evaluate(driver, case.get("src") or "")
                print(f"   done in {time.monotonic() - t_case:.1f} s"
                      f"\n   " + repr(result), flush=True)
                page.close()
                if errs:
                    failures.append(f"{case['name']}: page errors: {errs}")
                if result.get("skip"):
                    continue
                if not result.get("completed"):
                    failures.append(f"{case['name']}: did not complete the song")
                if result.get("timeout"):
                    failures.append(f"{case['name']}: timed out")
                if result.get("awaitLate"):
                    failures.append(f"{case['name']}: forced a stop between notes "
                                    "(await after the first bar)")
                if case["mode"] == "zones" and result.get("wentBack"):
                    failures.append(f"{case['name']}: reading line moved backwards")
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: play output accepted by practice; no forced stops between notes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
