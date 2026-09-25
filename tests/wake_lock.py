#!/usr/bin/env python3
# Screen wake-lock contract (Robin's IDEAS bugs line — phones black the screen
# during play / practice; the lock must hold while a melody plays or a practice
# session is genuinely running, drop on stop/pause/un-press, and re-request
# after the system/UA took it during a hidden tab). The suite drives the page
# with an injected fake `navigator.wakeLock` and asserts the request/release
# calls the module makes.
#
#   python3 tests/wake_lock.py         # headless & silent

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

# The fake is INSTALLED POST-BOOT via the setWakeLockSource seam inside the
# app's own module instance (dynamic import through the page's absolute URL
# resolves to the same module the app already loaded). navigator.wakeLock is a
# readonly WebIDL getter — a script assignment can NOT shadow it, which is
# exactly why the module carries the seam. The fake records every request /
# sentinel release and stands in for the UA permission surface.
INSTALL_FAKE = """
async () => {
  window.__wl = { log: [], sentinels: [] };
  const fake = {
    request: (type) => {
      __wl.log.push(["req", type]);
      const s = { type, released: false, handlers: [] };
      s.release = () => {
        if (s.released) return Promise.resolve();
        s.released = true;
        __wl.log.push(["srel"]);
        s.handlers.slice().forEach(fn => fn());
        return Promise.resolve();
      };
      s.addEventListener = (t, fn) => { if (t === "release") s.handlers.push(fn); };
      __wl.sentinels.push(s);
      return Promise.resolve(s);
    }
  };
  window.__fakeWakeLock = fake;
  const m = await import(new URL("js/wakelock.js", location.href).href);
  m.setWakeLockSource(() => fake);
  return m.wakeReasons() === 0;
}
"""


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


def counts(page):
    return page.evaluate(
        "() => ({ req: __wl.log.filter(e => e[0] === 'req').length,"
                " srel: __wl.log.filter(e => e[0] === 'srel').length })")


def visible(page, on):
    page.evaluate(
        "(on) => { Object.defineProperty(document, 'visibilityState',"
        " { configurable: true, get: () => on ? 'visible' : 'hidden' });"
        " document.dispatchEvent(new Event('visibilitychange')); }", on)


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS,
                                        args=["--autoplay-policy=no-user-gesture-required"])
            errs = []

            # --- the instrumented context -----------------------------------
            page = browser.new_page()
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(WAIT)
            if not page.evaluate(INSTALL_FAKE):
                failures.append("the wake-lock source seam must install clean")

            n0 = counts(page)
            if n0["req"] != 0 or n0["srel"] != 0:
                failures.append(f"an idle boot must hold no wake lock (got {n0})")

            # engage practice = a screen lock; the same button again is
            # DISENGAGE (paused, position retained — the transport contract),
            # which drops the lock like any other pause
            page.click("#mirrorPractice")
            page.wait_for_function("() => __wl.log.filter(e => e[0] === 'req').length >= 1")
            armed = counts(page)
            if armed["srel"] != 0:
                failures.append(f"engaged practice must hold the lock (got {armed})")
            page.click("#mirrorPractice")  # disengage (paused)
            page.wait_for_function("() => __wl.log.filter(e => e[0] === 'srel').length >= 1")
            paused = counts(page)
            if paused["req"] != 1:
                failures.append(f"pausing practice must NOT re-request (got {paused})")
            # a disengaged button re-engages from position: the lock returns
            page.click("#mirrorPractice")
            page.wait_for_function("() => __wl.log.filter(e => e[0] === 'req').length >= 2")
            resumed = counts(page)
            if resumed["srel"] != 1:
                failures.append(f"resumed practice must hold again ({resumed})")

            # full un-press is the PLAY button (swap): practice stops, the
            # melody takes over — the release and the melody's re-acquire ride
            # one user action
            page.click("#mirrorPlay")
            page.wait_for_function("() => __wl.log.filter(e => e[0] === 'req').length >= 3")
            played = counts(page)
            if played["srel"] < 2:
                failures.append(f"swapping play must release the practice lock (got {played})")

            # melody pause/resume drives the same lifecycle
            page.click("#mirrorPlay")  # pause
            page.wait_for_function("() => __wl.log.filter(e => e[0] === 'srel').length >= 3")
            page.click("#mirrorPlay")  # continue
            page.wait_for_function("() => __wl.log.filter(e => e[0] === 'req').length >= 4")

            # the UA took the lock while hidden (system release event); the
            # module must keep WANTING it (no reason dropped on hide) and
            # re-request unaided when visibility returns
            visible(page, False)
            page.evaluate(
                "() => { const s = __wl.sentinels[__wl.sentinels.length - 1];"
                " if (!s.released) s.release(); }")
            page.evaluate("() => __wl.log.length = 0")
            still_wants = page.evaluate(
                "async () => { const m = await import(new URL('js/wakelock.js', location.href).href); return m.wakeReasons(); }")
            if still_wants != 1:
                failures.append(f"a hidden tab must keep wanting the lock (got {still_wants})")
            visible(page, True)
            page.wait_for_function("() => __wl.log.filter(e => e[0] === 'req').length >= 1")
            back = counts(page)
            if back["srel"] != 0:
                failures.append(f"the re-acquire must not release again (got {back})")

            # melody stop while holding lets everything go
            page.click("#mirrorStop")
            page.wait_for_function("() => __wl.log.filter(e => e[0] === 'srel').length >= 1")
            stopped = counts(page)
            if stopped["req"] != 1:
                failures.append(f"stopping the melody must not re-request (got {stopped})")

            # --- bare context: no injected fake, no errors from the module --
            raw = browser.new_page()
            raw_errs = []
            raw.on("pageerror", lambda e: raw_errs.append(str(e)))
            console_errs = []
            raw.on("console", lambda m: console_errs.append(m.text) if m.type == "error" else None)
            raw.goto(base)
            raw.wait_for_function(WAIT)
            raw.click("#mirrorPlay")
            raw.wait_for_timeout(1200)
            raw.click("#mirrorPractice")
            raw.wait_for_timeout(1200)
            page_errors = raw_errs
            # the intentional manifest-declared tone.json 404s are the one
            # allowed console error class; anything else from the lock path fails
            unknown = [e for e in console_errs
                       if "tone.json" not in e and "Failed to load resource" not in e]
            if page_errors:
                failures.append(f"bare boot page errors: {page_errors}")
            if unknown:
                failures.append(f"bare boot console errors beyond the tone 404s: {unknown}")

            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: the wake lock follows play + practice exactly — engaged/playing "
          "holds it, stop/pause/un-press drops it, hidden tabs lose it and return "
          "to visibility re-requests it, and an unsupported browser boots clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
