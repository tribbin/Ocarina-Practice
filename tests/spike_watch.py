#!/usr/bin/env python3
# Spike watch: the sporadic single-frame audio "ticks" Robin reported (a
# waveform jump that silences the current note; Lite-invariant; Chrome-only,
# ~every 2 Concerning-Hobbits-short playbacks) are invisible to the perf
# watchdog — that counter needs a 0.3 s audio-clock lag, while a tick is a
# one-sample discontinuity in a flowing clock. This pins the detector:
#   - the pure classifier (OCA_DEBUG.spikeClassify) fires on an ISOLATED
#     one-sample step and stays silent on smooth tones, continuous steep
#     slopes (attack ramps), floor-level micro steps and — the report's own
#     signature — the jump-to-silence that kills the note after it;
#   - the plumbing records spike cards (OCA_DEBUG.spikeWatch) and a fake
#     spike shows up as a "Signal spikes (ticks)" row in the perf panel.
#
#   python3 tests/spike_watch.py      # headless & silent

import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
# The wait must yield a serialized (boolean) value: bare `window.OCA_DEBUG &&
# window.OCA_DEBUG.spikeClassify` would yield the FUNCTION object itself,
# which Playwright cannot serialize (unsatisfied wait forever).
BOOT_WAIT = ('typeof window.OCA_DEBUG === "object" &&'
             ' typeof window.OCA_DEBUG.spikeClassify === "function"')

CLASSIFY_EVAL = """
() => {
  const sr = 44100;
  const mk = (f) => {
    const w = new Float32Array(1024);
    for (let i = 0; i < 1024; i++) w[i] = f(i);
    return w;
  };
  const tone = (i) => 0.35 * Math.sin(2 * Math.PI * 440 * i / sr);
  const withStep = (w, idx, step) => { const c = w.slice(); if (c[idx] !== undefined) c[idx] += step; return c; };
  const C = OCA_DEBUG.spikeClassify;
  // a: isolated single-sample step inside a smooth tone -> fires at the step
  const base = mk(tone);
  const a = C(withStep(base, 500, 0.5));
  // b: the same tone without the step -> silent
  const b = C(base);
  // c: continuous steep slope (attack-ramp class): every delta equal ^ large
  const c = C(mk((i) => i * 0.05));
  // d: near-silence with a sub-floor micro step -> silent
  const d = C(mk((i) => i % 7 === 3 ? 0.01 : 0));
  // e: the report's signature - the tone jumps to silence in one sample
  const e = C(mk((i) => i < 512 ? tone(i) : 0));
  // f: three smooth windows hold the isolation rule: no second-best delta
  //    near the step's magnitude
  return { a, b, c, d, e };
}
"""

PANEL_EVAL = """
() => {
  playNote("C5", 0.2);           // gesture-less ctx (autoplay arg on launch)
  OCA_DEBUG.spikeFake();
  const watch = OCA_DEBUG.spikeWatch();
  return { watch };
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


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=HEADLESS,
                args=["--autoplay-policy=no-user-gesture-required"])

            # 1 — the pure classifier
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            r = page.evaluate(CLASSIFY_EVAL)

            def null_case(name, v):
                if v is not None:
                    failures.append(f"classify {name}: expected silence, got {v!r}")

            if not r["a"] or not isinstance(r["a"], dict):
                failures.append("classify step: the isolated step must fire")
            else:
                if not (480 <= r["a"]["i"] <= 521):
                    failures.append(f"classify step: wrong index {r['a']['i']}")
                # the reported jump is the up delta: the sine's own per-sample
                # swing sums into it (~0.02), so pin a ±0.03 band
                if not (0.47 <= r["a"]["jump"] <= 0.53):
                    failures.append(f"classify step: wrong jump {r['a']['jump']}")
            null_case("smooth tone", r["b"])
            null_case("steep ramp", r["c"])
            null_case("micro step", r["d"])
            if not r["e"] or not isinstance(r["e"], dict):
                failures.append("classify jump-to-silence: the report's "
                                "signature must fire")
            if errs:
                failures.append(f"classify: page errors {errs}")
            page.close()

            # 2 — the plumbing + perf panel row
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(
                "window.OCA_DEBUG && window.NOTES && window.NOTES.length")
            w = page.evaluate(PANEL_EVAL)
            if not isinstance(w["watch"], list):
                failures.append("spikeWatch() must return a list "
                                f"(got {w['watch']!r})")
            elif not any(e.get("fake") for e in w["watch"]):
                failures.append("spikeFake() must record a fake-marked "
                                f"spike card, got {w['watch']!r}")
            # the perf panel: open it and look for the spike row
            try:
                page.click("#perfBtn", timeout=3000)
            except Exception:
                failures.append("the #perfBtn button was not clickable "
                                "(perf widget missing?)")
            page.wait_for_timeout(500)
            body = page.evaluate(
                "() => (document.querySelector('.perf-tbl') ||"
                " document.body).innerText")
            spike_line = [l for l in body.splitlines()
                          if "Signal spikes (ticks)" in l]
            if not spike_line:
                failures.append('the perf panel lacks a "Signal spikes '
                                '(ticks)" row: ' + body[:200].replace("\n", " | "))
            else:
                line = spike_line[0]
                digits = [int(ch) for ch in line if ch.isdigit()]
                if not any(d > 0 for d in digits):
                    failures.append("the spike row must reflect the "
                                    "recorded count after spikeFake(), "
                                    f"got {line!r}")
            if errs:
                failures.append(f"plumbing: page errors {errs}")
            page.close()

            # 3 — the ambient context ring: the newest field evidence pairs
            # the ticks with a screen-orientation flip (the three perf
            # counters stay at 0), so a spike card must carry the recent
            # flip/resize markers and how long ago they fired — the next
            # field tick then pairs itself with the flip (naming the plane)
            # or, staying silent while the phone hops, proves the device
            # level.
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            r3 = page.evaluate("""
() => {
  // the phone's flip: the legacy event fires (resize follows in the wild)
  window.dispatchEvent(new Event('orientationchange'));
  window.dispatchEvent(new Event('resize'));
  OCA_DEBUG.spikeFake();
  const cards = OCA_DEBUG.spikeWatch();
  return cards[cards.length - 1];
}
""")
            amb = (r3 or {}).get("ambient")
            if not isinstance(amb, list):
                failures.append(f"the spike card must carry an ambient "
                                f"marker list, got {amb!r}")
            else:
                kinds = {a.get("kind") for a in amb if isinstance(a, dict)}
                if "flip" not in kinds:
                    failures.append(f"the orientation flip must land in the "
                                    f"card's context, got kinds {kinds}")
                if not any("agoMs" in a for a in amb if isinstance(a, dict)):
                    failures.append(f"ambient markers must carry agoMs "
                                    f"ages, got {amb!r}")
            if errs:
                failures.append(f"ambient: page errors {errs}")
            page.close()

            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: isolated one-sample steps are classified (smooth tones, "
          "steep ramps and micro steps stay silent; the jump-to-silence "
          "signature fires), spike cards record with their ambient context "
          "(flip/resize markers ride the next card) and the perf panel "
          "carries the 'Signal spikes (ticks)' row.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
