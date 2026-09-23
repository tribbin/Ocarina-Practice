#!/usr/bin/env python3
# Scheduler grid pin: the melody position the scheduler keeps (the number the
# swing-parity test reads) is an EXACT integer grid of 96ths of a beat — the
# notation lattice that covers dyadic durations, dots and triplets. Keeping it
# integer means no additive float drift can ever bend the swing parity on long
# songs. Numbers arrive via OCA_DEBUG.melodyPos96() while a triplet+half-beat
# melody loops under real playback with swing engaged.
#
#   python3 tests/swing_grid.py      # headless & silent

import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function'")


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
            page.goto(base)
            page.wait_for_function(WAIT)
            page.evaluate("""
              () => {
                // Triplet eighths (1/3-flavored beats) against half-beat
                // notes, swing engaged, looping — every position class the
                // parity test sees.
                document.getElementById('src').value =
                  "# swing 33\\n\\n" +
                  Array(8).fill("| C4/8t C4/8t C4/8t C5/2").join(" ") + " |";
                render();
                loopOn();
                playMelody(0);
              }
            """)
            r = page.evaluate("""
              async () => {
                const samples = [];
                const t0 = performance.now();
                while (performance.now() - t0 < 2600) {
                  const v = window.OCA_DEBUG.melodyPos96();
                  samples.push(v);
                  await new Promise(r2 => setTimeout(r2, 15));
                }
                return samples;
              }
            """)
            if len(r) < 60:
                failures.append(
                    f"scheduler must advance during the window (got only {len(r)} samples)")
            if all(s == 0 for s in r):
                failures.append("melody position must move (all samples 0)")
            for i, v in enumerate(r):
                if not float(v).is_integer():
                    failures.append(
                        f"melody position must sit exactly on the integer "
                        f"96th grid at sample {i}, got {v!r} "
                        f"({v % 1:+g} off) — additive drift must not bend "
                        f"the swing parity")
                    break

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
    print("\nPASS: the scheduler keeps its melody position exactly on the "
          "integer 96th-of-a-beat grid while swing-parity reads it — no "
          "additive drift.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
