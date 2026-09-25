#!/usr/bin/env python3
# Zen note-bar never lags the notes (Robin, field 2026-09-25: on his phone's
# vertical screen the focus strip "moves too slowly toward center as a note
# highlights and even leaves the screen partially").
#
# Where the lag lived (session-15 diagnostic, throttled headless + his field
# report): the strip handed its centering to the browser-native smooth
# scroll (scrollTo behavior:"smooth"). UA smooth settles ~200 ms for a
# one-note step and ~500 ms for a jump; per-note re-issues restart the
# decelerating animation from wherever it stands, so the strip trails in
# time and the .now token can drift past the mask edge on a narrow phone
# strip. The sheet solved the same class long ago with the app's own
# bounded rAF glide ("never lag behind the playing notes", ui.js).
#
# The contract pinned (legs):
#   1. never hand the pace to the browser: no strip.scrollTo smooth call;
#   2. a centering call settles on target within <=260 ms (its own glide);
#   3. a far jump (loop-wrap class, delta past the strip width) snaps now;
#   4. sustained per-note advances (130 ms apart) keep the .now token
#      centered — the bar stays with the melody instead of trailing it;
#   5. a wheel grab stops a running glide (the user owns the strip).
#
#   .venv/bin/python3 tests/zen_notebar.py     # headless phone viewport

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
BOOT_WAIT = ("window.NOTES && window.NOTES.length"
             " && typeof parse === 'function'")

MEL = ("c4 d4 e4 f4 g4 a4 b4 c5 b4 a4 g4 f4 e4 d4 c4 d4 e4 f4 "
       "g4 a4 b4 c5 b4 a4 g4 f4 e4 d4 c4 c4 d4 e4 f4 g4 a4 b4 c5")

SETUP = """
async () => {
  document.getElementById('src').value = %r;
  render();
  document.getElementById('tabPanel').classList.add('focus');
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  const strip = document.getElementById('focusTokens');
  if (!strip) throw new Error("no #focusTokens");
  if (!strip.offsetParent) throw new Error("focus strip not visible");
  window.__smoothCalls = [];
  strip.scrollTo = (opt) => { window.__smoothCalls.push(opt); };
  return { width: strip.clientWidth,
           toks: strip.querySelectorAll('.tok[data-i]').length };
}
""" % MEL

HELPERS = """
window.__targetLeft = (i) => {
  const strip = document.getElementById('focusTokens');
  const el = strip.querySelector('.tok[data-i="' + i + '"]');
  if (!el) throw new Error('missing token ' + i);
  const s = strip.getBoundingClientRect(), c = el.getBoundingClientRect();
  return Math.max(0, strip.scrollLeft +
    (c.left + c.width / 2) - (s.left + s.width / 2));
};
window.__settle = () => new Promise(r => setTimeout(r, 340));
window.__watch = (ms) => {
  const strip = document.getElementById('focusTokens');
  return new Promise(res => {
    let last = strip.scrollLeft, stable = 0;
    const t0 = performance.now();
    const step = () => {
      const now = performance.now();
      const x = strip.scrollLeft;
      if (Math.abs(x - last) < 0.5) stable++; else stable = 0;
      last = x;
      if (stable >= 6 || now - t0 >= ms) {
        res(now - t0 - stable * 16);
      } else requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
};
"""


from suite_server import start_server


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            ctx = browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=3, is_mobile=True, has_touch=True)
            page = ctx.new_page()
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            page.evaluate(HELPERS)
            info = page.evaluate(SETUP)
            if info["toks"] < 30:
                failures.append(f"probe sanity: only {info['toks']} tokens")
            if not info["width"]:
                failures.append(
                    "probe sanity: #focusTokens has no width — the focus "
                    "class no longer displays it")
            width = info["width"]

            # Leg 1: never hand the pace to the browser's native scroll.
            page.evaluate(
                "const s = document.getElementById('focusTokens'); "
                "s.scrollLeft = 0; scrollFocusStripTo(4);")
            calls = page.evaluate("window.__smoothCalls")
            if calls:
                failures.append(
                    f"scrollFocusStripTo must not hand the pace to the "
                    f"browser's native scroll — it called "
                    f"strip.scrollTo({calls[0]!r})")
            page.evaluate("window.__settle()")

            # Leg 2: the app's own glide settles on target, bounded.
            page.evaluate(
                "const s = document.getElementById('focusTokens'); "
                "s.scrollLeft = 0;")
            page.evaluate("scrollFocusStripTo(4)")
            settle = page.evaluate("window.__watch(2500)")
            x = page.evaluate(
                "document.getElementById('focusTokens').scrollLeft")
            want = page.evaluate("window.__targetLeft(4)")
            if abs(x - want) > 3:
                failures.append(
                    f"glide landed off its centering target "
                    f"(x={x}, want {want})")
            if settle > 260:
                failures.append(
                    f"glide settled in {settle} ms — past the 260 ms bound; "
                    "the note bar can lag the notes again")
            page.evaluate("window.__settle()")

            # Leg 3: far jump snaps instantly (the loop-wrap class).
            want0 = page.evaluate("""() => {
              const s = document.getElementById('focusTokens');
              s.scrollLeft = window.__targetLeft(30);
              const w = window.__targetLeft(0);
              scrollFocusStripTo(0);
              return w;
            }""")
            x = page.evaluate(
                "document.getElementById('focusTokens').scrollLeft")
            if abs(x - want0) > 3:
                failures.append(
                    f"far jump must snap instantly to {want0}, landed at {x}")
            page.evaluate("window.__settle()")

            # Leg 4: sustained per-note advances keep the .now token
            # centered (the field symptom class).
            page.evaluate("""async () => {
              const s = document.getElementById('focusTokens');
              s.scrollLeft = window.__targetLeft(6);
              for (let i = 7; i <= 15; i++) {
                scrollFocusStripTo(i);
                await new Promise(r => setTimeout(r, 130));
              }
            }""")
            page.evaluate("window.__settle()")
            trail = page.evaluate("""() => {
              const s = document.getElementById('focusTokens');
              const c = s.querySelector('.tok[data-i="15"]')
                          .getBoundingClientRect();
              const b = s.getBoundingClientRect();
              return Math.round((c.left + c.width / 2)
                                - (b.left + b.width / 2));
            }""")
            if abs(trail) > 8:
                failures.append(
                    f"after per-note advances the strip trails the .now "
                    f"token by {trail}px (want |dx| <= 8) — the bar falls "
                    "behind the melody again")

            # Leg 5: a wheel grab stops a running glide.
            moved = page.evaluate("""async () => {
              const s = document.getElementById('focusTokens');
              s.scrollLeft = 0;
              scrollFocusStripTo(12);
              s.dispatchEvent(new WheelEvent('wheel', { deltaY: -60 }));
              const x1 = s.scrollLeft;
              await new Promise(r => requestAnimationFrame(() =>
                requestAnimationFrame(r)));
              const x2 = s.scrollLeft;
              await new Promise(r => requestAnimationFrame(r));
              return x2 !== x1;
            }""")
            if moved:
                failures.append(
                    "a wheel grab must stop a running glide — the strip "
                    "kept writing scrollLeft after the wheel")

            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print(f"\nFAIL (strip width {width}px):")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: the focus strip centers with the app's own bounded rAF "
          "glide — settles <=260 ms, far jumps snap, per-note advances keep "
          "the .now token centered, a wheel grab cancels the glide — and "
          "never asks the browser's native smooth scroll to pace it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
