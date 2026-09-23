#!/usr/bin/env python3
# Practice session keeps its seat across view-mode changes: while a practice
# session is running, the live tab's card must name the tone the tuner is
# CURRENTLY expecting — not the song's first note. A zen exit (mode falls
# back) and zen return (back to single) rebuilds the card between practice's
# own highlight calls; without practice-aware seeding the rebuild fell back
# to firstSoundIdx and displayed "start over" while P.idx stayed advanced.
#
#   python3 tests/practice_zen_return.py          # headless & silent

import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
SONG = "# seat test\n# tempo 150\nC5/2 D5/2 E5/2 F5/2 G5/2"


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


# Advances practice through the song's first bars with the closed-loop
# player (identical to the acceptance suite's zone model), then flips the
# display mode out of single and back twice, reading the live card and the
# tuner's expectation both times. The feeding interval keeps running through
# the flips — practice stays active exactly like a real session would.
SEAT_DRIVER = """
(SRC) => new Promise((resolve, reject) => {
  const ta = document.getElementById('src');
  ta.value = SRC;
  render();
  let firstSound = null;
  const feed = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (P.state === "await" || P.state === "dip" || P.state === "rest" || !P.bar) {
      window.__pracFrame = { hz: 0, rms: 0 };
    } else {
      const k = P.zonesNear >= 0 ? P.zonesNear : 0;
      window.__pracFrame = { hz: P.bar.zones[k], rms: 0.4 };
    }
  }, 30);
  OCA_PRACTICE.start();
  let started = false;
  const poll = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (OCA_PRACTICE.active() && !P.paused) started = true;
    if (!started) return;
    if (P.idx >= 2) {
      // mid-song (third note's bar): exit the single view and come back
      setDisplayMode('scroll');          // the zen-exit fallback mode
      setDisplayMode('single');          // the zen return
      const card = document.querySelector('#sheet .card.live');
      const active = { card: card ? card.dataset.i : null,
                       spot: OCA_PRACTICE.spot(),
                       idx: P.idx };
      // with the session stopped, the first note owns the card again
      OCA_PRACTICE.stop();
      window.__pracFrame = { hz: 0, rms: 0 };
      setDisplayMode('scroll');
      setDisplayMode('single');
      const idleCard = document.querySelector('#sheet .card.live');
      clearInterval(feed); clearInterval(poll);
      resolve({ active: active,
                idleCard: idleCard ? idleCard.dataset.i : null,
                firstSound: firstSound });
      return;
    }
  }, 60);
  setTimeout(() => { clearInterval(feed); clearInterval(poll);
    OCA_PRACTICE.stop();
    reject(new Error('practice never reached the third note')); }, 20000);
})
"""


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base + "?practiceTest=1")
            page.wait_for_function(
                "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                " && window.NOTES && window.NOTES.length")
            r = page.evaluate(SEAT_DRIVER, SONG)
            page.close()
            print(f"== mid-song seat: {r['active']!r}  idle card: {r['idleCard']!r}", flush=True)
            if errs:
                failures.append(f"page errors {errs}")
            card = r["active"]["card"]
            spot = r["active"]["spot"]
            if card is None:
                failures.append("no live card after the mode round-trip")
            elif r["active"]["idx"] < 2:
                failures.append(f"practice never advanced (idx {r['active']['idx']})")
            elif card != str(spot):
                failures.append(
                    f"the rebuilt card shows token {card!r} while the tuner "
                    f"expects token {spot!r} — a mid-song session must keep "
                    "its seat across a zen exit/return (card falls back to "
                    "the first note while the engine stays advanced)")
            elif r["idleCard"] not in (None, "0", str(spot)):
                failures.append(
                    f"with practice stopped the card should name the song's "
                    f"first note, got {r['idleCard']!r}")
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: an active practice session owns the live card across view "
          "rebuilds (zen exit/return), and a stopped session falls back to "
          "the first note as before.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
