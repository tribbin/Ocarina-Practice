#!/usr/bin/env python3
# Media Session announce + hardware media keys (board §9 stop-media,
# scoped down 2026-09-30): the page DECLARES its own playback state —
# playbackState + MediaMetadata naming "Ocarina Practice — <song>" for the
# lock screen / media center — and the hardware play/pause/stop keys drive
# the SAME transport as the on-screen buttons. Stopping OTHER apps' media is
# infeasible from a web page (the API is declarative-only), so that half
# dropped per Robin's rule; next/prev stay unwired until their stepping
# target is picked. Everything gates on ("mediaSession" in navigator) and
# no-ops silently where unsupported.
#
# The legs spy on navigator.mediaSession through an add-init-script proxy
# (recorded metadata/playbackState writes + registered action handlers) in
# per-leg fresh contexts; the recorded handlers are invoked the way a
# headset keypress would, so the wiring itself is pinned.
#
#   python3 tests/media_session.py     # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv

from suite_server import start_server

# The #scale select fills only after boot's loadInstrument has fully
# resolved (the instruments_load settled rendezvous).
BOOT_WAIT = ("window.BUILTIN && document.getElementById('scale') && "
             "document.getElementById('scale').options.length > 0")

MS_PROXY = """
  window.__ms = { meta: [], state: [], actions: {} };
  const real = navigator.mediaSession;
  if (real) {
    const proxy = new Proxy(real, {
      set(t, k, v) {
        if (k === "metadata") window.__ms.meta.push(v ? v.title : null);
        if (k === "playbackState") window.__ms.state.push(v);
        try { t[k] = v; } catch (e) {}
        return true;
      },
      get(t, k) {
        if (k === "setActionHandler") {
          return (name, fn) => { window.__ms.actions[name] = fn; };
        }
        const v = t[k];
        return typeof v === "function" ? v.bind(t) : v;
      }
    });
    Object.defineProperty(navigator, "mediaSession",
                          { value: proxy, configurable: true });
  }
"""


def last_state(page):
    return page.evaluate("window.__ms.state[window.__ms.state.length - 1]")


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=HEADLESS,
                args=["--autoplay-policy=no-user-gesture-required"])

            # L1 — boot announces the home song and parks at "none"
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.add_init_script(MS_PROXY)
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            page.wait_for_function("window.__ms && window.__ms.meta.length > 0")
            meta = page.evaluate("window.__ms.meta")
            if meta[-1] != "Ocarina Practice \u2014 Song of Storms":
                failures.append(f"L1 boot metadata: {meta!r}")
            if "none" not in page.evaluate("window.__ms.state"):
                failures.append(
                    f"L1 the boot stop must announce 'none': "
                    f"{page.evaluate('window.__ms.state')!r}")
            if errs:
                failures.append(f"L1 page errors: {errs}")
            page.close()

            # L2 — song switch re-announces the metadata
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.add_init_script(MS_PROXY)
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            pick = page.evaluate("""() => {
                const sel = document.getElementById('scale');
                for (const o of sel.options) {
                    if (o.value === sel.value) continue;
                    if (o.value === "major" || o.value === "chromatic") continue;
                    return [o.value, o.textContent];
                }
                return null;
            }""")
            if not pick:
                failures.append("L2 no second library song to switch to")
            else:
                value, label = pick
                page.evaluate(
                    "(id) => { const s = document.getElementById('scale');"
                    " s.value = id;"
                    " s.dispatchEvent(new Event('change', { bubbles: true })); }",
                    value)
                page.wait_for_function(
                    "(n) => document.getElementById('title').textContent === n",
                    arg=label, timeout=10000)
                meta = page.evaluate("window.__ms.meta")
                if meta[-1] != "Ocarina Practice \u2014 " + label:
                    failures.append(
                        f"L2 metadata must follow the song switch: {meta!r}")
            if errs:
                failures.append(f"L2 page errors: {errs}")
            page.close()

            # L3 — the transport edges drive playbackState
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.add_init_script(MS_PROXY)
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            page.evaluate("playMelody()")
            page.wait_for_function(
                "(s) => window.__ms.state[window.__ms.state.length - 1] === s"
                " && isMelodyPlaying()",
                arg="playing", timeout=15000)
            page.evaluate("pauseMelody()")
            page.wait_for_function(
                "(s) => window.__ms.state[window.__ms.state.length - 1] === s"
                " && isMelodyPaused()",
                arg="paused", timeout=15000)
            page.evaluate("resumeMelody()")
            page.wait_for_function(
                "(s) => window.__ms.state[window.__ms.state.length - 1] === s"
                " && isMelodyPlaying()",
                arg="playing", timeout=15000)
            page.evaluate("stopMelody()")
            page.wait_for_function(
                "(s) => window.__ms.state[window.__ms.state.length - 1] === s"
                " && !isMelodyPlaying()",
                arg="none", timeout=15000)
            if errs:
                failures.append(f"L3 page errors: {errs}")
            page.close()

            # L4 — the hardware keys reach the transport (and only the
            # sensible ones are wired)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.add_init_script(MS_PROXY)
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            acts = page.evaluate("Object.keys(window.__ms.actions)")
            for wanted in ("play", "pause", "stop"):
                if wanted not in acts:
                    failures.append(f"L4 missing handler: {wanted} "
                                    f"(registered: {acts!r})")
            for unwired in ("nexttrack", "previoustrack"):
                if unwired in acts:
                    failures.append(
                        f"L4 {unwired} must stay unwired until its stepping "
                        f"target is picked")
            page.evaluate("window.__ms.actions['play']()")
            page.wait_for_function("isMelodyPlaying()", timeout=15000)
            page.evaluate("window.__ms.actions['pause']()")
            page.wait_for_function("isMelodyPaused()", timeout=15000)
            page.evaluate("window.__ms.actions['stop']()")
            page.wait_for_function(
                "!isMelodyPlaying() && !isMelodyPaused()")
            if last_state(page) != "none":
                failures.append(
                    f"L4 the stop key must announce 'none': "
                    f"{last_state(page)!r}")
            if errs:
                failures.append(f"L4 page errors: {errs}")
            page.close()

            browser.close()
    finally:
        httpd.shutdown()

    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: the Media Session announce holds — metadata names "
          "'Ocarina Practice \u2014 <song>' at boot and on song switch, the "
          "transport edges announce none/playing/paused/none, and the "
          "hardware play/pause/stop keys drive the real transport while "
          "next/prev stay unwired.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
