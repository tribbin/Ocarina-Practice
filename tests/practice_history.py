#!/usr/bin/env python3
# Practice history contract: every COMPLETED run records {ts, wipes, cents,
# sec} under the song's id in localStorage ('oco-practice-history'), the
# panel's history line reads the current song's last run, and OCA_PRACTICE
# exposes the list for the dev panel. Driven with the same synthetic mic-frame
# player model the practice acceptance suite uses (TEST provider, no mic).
#
#   python3 tests/practice_history.py      # headless & silent

import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
TEST_WAIT = ("window.NOTES && window.NOTES.length"
             " && typeof parse === 'function' && window.OCA_PRACTICE")


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


RUN_DRIVER = """
(SRC) => new Promise(resolve => {
  const ta = document.getElementById('src');
  ta.value = SRC;
  render();
  const pets = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (P.state === "await" || P.state === "rest" || !P.bar) {
      window.__pracFrame = { hz: 0, rms: 0 };
    } else {
      const k = P.zonesNear >= 0 ? P.zonesNear : 0;
      window.__pracFrame = { hz: P.bar.zones[k], rms: 0.4 };
    }
  }, 30);
  OCA_PRACTICE.start();
  // Arbiter: only trust the inactive signal after engagement, twice in a row
  // (the practice suite's CI flake taught this).
  let started = false, idle = 0;
  const poll = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (OCA_PRACTICE.active() && !P.paused) started = true;
    if (!OCA_PRACTICE.active() || P.paused) {
      if (!started) { idle = 0; return; }
      if (++idle < 2) return;
      clearInterval(pets); clearInterval(poll);
      resolve({ completed: !!P.completed });
    }
  }, 100);
  setTimeout(() => {
    clearInterval(pets); clearInterval(poll);
    OCA_PRACTICE.stop();
    resolve({ completed: false, timeout: true });
  }, 24000);
})
"""


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS,
                                        args=["--autoplay-policy=no-user-gesture-required"])
            errs = []
            page = browser.new_page()
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base + "?practiceTest=1")
            page.wait_for_function(TEST_WAIT)

            MEL = "# Hist\n\nA4/4 C5/4 D5/4 E5/4"
            r1 = page.evaluate(RUN_DRIVER, MEL)
            if not r1["completed"]:
                failures.append(f"the case must complete (got {r1})")
            hist1 = page.evaluate("() => OCA_PRACTICE.history()")
            if not hist1.get("runs"):
                failures.append("a completed run must be recorded "
                                f"(history {hist1})")
            else:
                run = hist1["runs"][-1]
                for field in ("ts", "wipes", "sec"):
                    if field not in run:
                        failures.append(f"run record missing {field}: ({run})")
                if run["cents"] is not None and not (0 <= run["cents"] <= 50):
                    failures.append(f"cents mean out of band: {run}")
                if run["sec"] < 1:
                    failures.append(f"run seconds absurd: {run}")

            # second run appends (same song key)
            r2 = page.evaluate(RUN_DRIVER, MEL)
            if not r2["completed"]:
                failures.append(f"the second run must complete (got {r2})")
            hist2 = page.evaluate("() => OCA_PRACTICE.history()")
            if len(hist2.get("runs", [])) != 2:
                failures.append(f"two completed runs must be recorded "
                                f"(history {hist2})")

            stored = page.evaluate("""
              () => {
                try { return JSON.parse(localStorage.getItem('oco-practice-history') || '{}'); }
                catch (e) { return null; }
              }
            """)
            if not stored:
                failures.append("localStorage must carry the history JSON")
            # The panel line reflects the CURRENT song's last run.
            line = page.evaluate(
                "() => { const el = document.querySelector('.prac-history');"
                " return el ? el.textContent : null; }")
            if not line or "runs" not in line:
                failures.append(f"the panel history line must be written "
                                f"(got {line!r})")

            if errs:
                failures.append(f"page errors {errs}")
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: completed practice runs record wipes/mean-cents/duration "
          "per song, the second run appends, the panel line reads the last "
          "one, and the storage is guarded JSON.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
