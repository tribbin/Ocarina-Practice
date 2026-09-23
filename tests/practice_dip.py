#!/usr/bin/env python3
# Separate-note dip gate: two UNLINKED notes in practice must not be
# coverable by one continuous hold. When a completed bar's tone could keep
# sounding straight into the next bar's note (its pitch within the onset arm
# tolerance), the engine parks the next bar in "dip" until the air was cut
# once for dipMs (≈ two detection frames — a mic glitch cannot fake it).
#
#   A  hold-through: the long-then-short same-pitch pair (Song of Storms'
#      A5 A5 shape) must NOT complete on one uninterrupted hold.
#   B  dipping player: a full-silence dip completes the song, and the
#      full-stop "await" gate never fires after the first bar.
#   C  legato stays free: a different-pitch pair flows continuously, no dip
#      ever demanded (the generous note-to-note behavior is unchanged).
#   D  shallow duck: ducking to 75% of the hold level — above dipFrac —
#      must NOT open the gate (a wobble is not an articulation).
#   E  tongued dip: ducking to 40% — below the 50% dipFrac, never silence —
#      DOES open the gate and completes the pair with no silence at all.
#
# Single-page driver per case, ?practiceTest=1 synthetic mic frames, exactly
# the readFrame path the tuner uses while practicing.
#
#   python3 tests/practice_dip.py          # headless & silent

import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass


def start_server():
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), QuietHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


# OPT: { src, obey, notch: { frac, ms } | null, holdMs }
# obey  — the synthetic player tongued full silence when the engine demands
#         it (silent in dip); hold-through keeps the tone running instead.
# notch — when the gate first engages, the tone ducks to (holdRms × frac)
#         for `ms`, then resumes the hold: the tongued volume dip without
#         silence (frac 0.4 opens, 0.75 should not — the dip fraction).
# The driver resolves early once a hold-through has demonstrably NOT earned
# the gated bar (dip observed, held ≥ holdMs, no credit) — the assert then
# reads diagnosis off the resolution, not out of a wait.
DIP_DRIVER = """
(OPT) => new Promise((resolve, reject) => {
  document.getElementById('src').value =
    "# dip gate\\n# tempo 150\\n" + OPT.src;
  render();
  OCA_PRACTICE.start();
  let sawDip = false, dipSince = 0, notchLeft = 0, awaitLate = false;
  let silentAfterArm = false;
  let maxIdx = 0;
  const feed = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (P.state === "await" && P.idx > 0) awaitLate = true;
    if (P.idx > maxIdx) maxIdx = P.idx;
    if (P.state === "dip") {
      if (!sawDip) { sawDip = true; dipSince = performance.now();
                     notchLeft = OPT.notch ? Math.ceil(OPT.notch.ms / 30) : 0; }
      else if (notchLeft > 0) {
        notchLeft--;                            // duck, then resume the hold
        const ref = P.holdRms || 0.4;
        if (ref * OPT.notch.frac < 0.01) silentAfterArm = true;
        window.__pracFrame = { hz: P.bar.zones[0], rms: ref * OPT.notch.frac };
        return;
      }
    }
    const silent = (P.state === "await" && P.idx === 0) ||
                   P.state === "rest" ||
                   (P.state === "dip" && OPT.obey);
    if (silent) {
      if (!(P.state === "await" && P.idx === 0)) silentAfterArm = true;
      window.__pracFrame = { hz: 0, rms: 0 };
    }
    else {
      const k = P.zonesNear >= 0 ? P.zonesNear : 0;
      window.__pracFrame = { hz: P.bar.zones[k], rms: 0.4 };
    }
  }, 30);
  let started = false, idle = 0;
  const poll = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (OCA_PRACTICE.active() && !P.paused) started = true;
    if (sawDip && !OPT.obey && OPT.holdMs > 0 &&
        performance.now() - dipSince > OPT.holdMs) {
      // the gate has sat in dip through holdMs with the tone held: the bar
      // cannot have earned anything in that window (capture the credit
      // BEFORE the stop — stopPractice nulls the bar)
      const segNow = P.bar && P.state === "dip" ? P.bar.segs[0] : -1;
      clearInterval(feed); clearInterval(poll);
      OCA_PRACTICE.stop();
      resolve({ completed: false, sawDip: true, blocked: true,
                seg0: segNow, maxIdx: maxIdx, awaitLate: awaitLate,
                silentAfterArm: silentAfterArm });
      return;
    }
    if (!OCA_PRACTICE.active() || P.paused) {
      if (!started) { idle = 0; return; }      // engage still racing in
      if (++idle < 2) return;                   // one blip is not a stop
      clearInterval(feed); clearInterval(poll);
      resolve({ completed: !!P.completed, sawDip: sawDip, blocked: false,
                seg0: -1, maxIdx: maxIdx, awaitLate: awaitLate,
                silentAfterArm: silentAfterArm });
      return;
    }
  }, 100);
  setTimeout(() => {
    clearInterval(feed); clearInterval(poll);
    OCA_PRACTICE.stop();
    resolve({ completed: false, timeout: true, sawDip: sawDip,
              maxIdx: maxIdx, awaitLate: awaitLate,
              silentAfterArm: silentAfterArm });
  }, OPT.obey ? 20000 : 15000);
})
"""


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            cases = [
                ("hold-through must not cover two notes",
                 dict(src="A5/2 A5/2", obey=False, notch=None, holdMs=1200),
                 lambda r, f: (
                     (not r.get("sawDip")) and f("the gate never engaged (no dip state while holding through)"),
                     r.get("completed") and f("one continuous hold completed BOTH unlinked same-pitch notes "
                                              "(the score let the hold pass as two notes)"),
                     r.get("maxIdx", 0) < 1 and f("the first bar never completed upstream of the gate"),
                     r.get("awaitLate") and f("the full-stop await gate fired between notes"),
                     (not r.get("blocked")) and f("hold-through resolved without observing the blocked gate"),
                     r.get("seg0") not in (0, 0.0) and f(f"the gated note started crediting while the tone "
                                                         f"never broke (seg0 {r.get('seg0')!r})"),
                 )),
                ("silence dip completes",
                 dict(src="A5/2 A5/2", obey=True, notch=None, holdMs=0),
                 lambda r, f: (
                     (not r.get("completed")) and f("dipping between the two notes did not complete the song"),
                     (not r.get("sawDip")) and f("the dip gate never engaged on the same-pitch pair"),
                     r.get("awaitLate") and f("the full-stop await gate fired between notes"),
                 )),
                ("legato across pitches stays free",
                 dict(src="A5/2 C6/2", obey=False, notch=None, holdMs=0),
                 lambda r, f: (
                     (not r.get("completed")) and f("a different-pitch pair did not flow legato"),
                     r.get("sawDip") and f("the engine demanded a dip for a genuinely different pitch "
                                           "(the travel is the distinct step)"),
                     r.get("awaitLate") and f("the full-stop await gate fired between notes"),
                 )),
                ("a 75% duck is not the dip",
                 dict(src="A5/2 A5/2", obey=False, notch=dict(frac=0.75, ms=90), holdMs=1000),
                 lambda r, f: (
                     (not r.get("sawDip")) and f("the gate never engaged"),
                     r.get("completed") and f("an above-threshold duck opened the separate-note gate"),
                     r.get("seg0") not in (0, 0.0) and f(f"the duck's depth earned credit "
                                                          f"(seg0 {r.get('seg0')!r})"),
                 )),
                ("a 40% tongued dip opens without silence",
                 dict(src="A5/2 A5/2", obey=False, notch=dict(frac=0.4, ms=120), holdMs=0),
                 lambda r, f: (
                     (not r.get("completed")) and f("a below-threshold tongued dip did not complete the pair"),
                     r.get("silentAfterArm") and f("the gate opened only through full silence "
                                                   "(a volume dip must count)"),
                     r.get("awaitLate") and f("the full-stop await gate fired between notes"),
                 )),
            ]
            for name, opt, checks in cases:
                page = browser.new_page()
                errs = []
                page.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
                page.goto(base + "?practiceTest=1")
                page.wait_for_function(
                    "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                    " && window.NOTES && window.NOTES.length")
                r = page.evaluate(DIP_DRIVER, opt)
                page.close()
                print(f"== {name}: {r!r}", flush=True)
                if errs:
                    failures.append(f"{name}: page errors {errs}")
                for fail in checks(r, lambda msg: failures.append(f"{name}: {msg}")):
                    pass
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: unlinked same-pitch notes need a distinct dip (full "
          "silence or a ~50% volume notch), above-threshold ducks stay "
          "shut, dipping players pass, legato across real pitch travel "
          "stays free.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
