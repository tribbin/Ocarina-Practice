#!/usr/bin/env python3
# Practice pitch-worker contract: the autocorrelation detector runs in a
# dedicated worker (the tuner's ~2M multiply-adds per 66 ms frame leave the
# main thread), and the worker result is BIT-IDENTICAL to the classic
# main-thread detector because both are the same js/pitch-dsp.js source. When
# no Worker can be created, the async surface reports the fallback honestly
# and nothing breaks.
#
#   python3 tests/ac_worker.py      # headless & silent

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

# sr 48000 covers every shipped detector ceiling (C7's lag ~22.9).
FREQS = [220, 261.63, 293.66, 349.23, 392, 440, 523.25, 659.26, 880,
         1046.5, 1318.5, 1568, 2093]


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


COMBARE = """
(TEST_FREQS) => { return (async () => {
  const rows = [];
  for (const f of TEST_FREQS) {
    const sync = OCA_PRACTICE.testAC(f, 48000);
    const worker = await OCA_PRACTICE.testACAsync(f, 48000);
    rows.push({ f: f, sync: sync, worker: worker });
  }
  return { rows, usingWorker: OCA_PRACTICE.usingWorker() };
})(); }
"""


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS,
                                        args=["--autoplay-policy=no-user-gesture-required"])
            context = browser.new_context()
            errs = []
            page = context.new_page()
            page.on("pageerror", lambda e: errs.append(str(e)))

            # --- worker path: results identical to the sync detector ---
            page.goto(base)
            page.wait_for_function(WAIT)
            page.evaluate(COMBARE, FREQS)
            r = page.evaluate(COMBARE, FREQS)
            if not r["usingWorker"]:
                failures.append(
                    "after testACAsync the practice analysis must run in "
                    "the worker (usingWorker() false)")
            for row in r["rows"]:
                f, sw, hw = row["f"], row["sync"], row["worker"]
                if hw is None:
                    failures.append(
                        f"worker path unavailable for {f} Hz (resolved null)")
                    continue
                if abs(hw - sw) > 1e-9:
                    failures.append(
                        f"worker {hw} vs sync {sw} for {f} Hz — the two "
                        "threads run the same js/pitch-dsp.js and must be "
                        "bit-identical")
                if sw <= 0 or abs(sw - f) / f > 0.005:
                    failures.append(
                        f"sync detector misreads a clean tone: {sw} vs "
                        f"{f} Hz")
            # Concurrent requests keep their pairing (seq-tagged round trips).
            pair = page.evaluate("""
              () => { return Promise.all([
                OCA_PRACTICE.testACAsync(440, 48000),
                OCA_PRACTICE.testACAsync(880, 48000),
              ]).then(([a, b]) => ({ a: a, b: b })); }
            """)
            if not pair["a"] or not pair["b"]:
                failures.append(
                    "concurrent worker requests must both answer "
                    f"(got {pair})")
            elif pair["b"] <= pair["a"]:
                failures.append(
                    "concurrent worker results must pair with their "
                    f"requests (880 Hz must read higher than 440: {pair})")

            # --- no-worker environment: async surface reports the fallback ---
            page2 = browser.new_context().new_page()
            errs2 = []
            page2.on("pageerror", lambda e: errs2.append(str(e)))
            page2.add_init_script("window.Worker = undefined;")
            page2.goto(base)
            page2.wait_for_function(WAIT)
            p2 = page2.evaluate(
                "() => OCA_PRACTICE.testACAsync(440, 48000)"
                ".then(v => ({ v: v, usingWorker: OCA_PRACTICE.usingWorker() }))")
            if p2["v"] is not False and p2["v"] is not None:
                failures.append(
                    "without Workers the async surface must report the "
                    f"fallback (resolved {p2['v']})")
            if p2["usingWorker"]:
                failures.append(
                    "usingWorker() must be false when no worker was created")
            if errs2:
                failures.append(f"page errors {errs2}")

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
    print("\nPASS: pitch analysis runs in the worker, returns bit-identical "
          "results to the shared detector, pairs concurrent requests, and "
          "reports the sync fallback when workers are unavailable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
