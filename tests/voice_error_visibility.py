#!/usr/bin/env python3
# Voice-builder failure visibility: playNoteAt/playTickAt deliberately swallow
# any WebAudio failure so a bad synth call can never break the page — but a
# swallowed system-wide failure was INVISIBLE (an ocarina that silently plays
# nothing is the worst failure mode for a practice tool). This asserts a new
# OCA_DEBUG.voiceErrors() recorder catches real failures (forced AudioContext
# creation failure) for both voices, without breaking the calling page.
#
#   python3 tests/voice_error_visibility.py      # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
BOOT_WAIT = ("typeof playNote === 'function'"
             " && typeof playTickAt === 'function'"
             " && window.OCA_DEBUG")

FORCE_FAIL = """
() => {
  // Fresh, gesture-less page: no existing AudioContext, so the constructor
  // lookup is forced to fail before any voice code runs.
  Object.defineProperty(window, "AudioContext", {
    get() { throw new Error("forced-ctx-fail"); }, configurable: true,
  });
  let note = null;
  try { playNote("C5", 0.2); note = "NO_THROW"; }
  catch (e) { note = "THREW:" + e.message; }
  const rec = (window.OCA_DEBUG && window.OCA_DEBUG.voiceErrors)
    ? window.OCA_DEBUG.voiceErrors() : null;
  let tickCount = null, tickLast = null;
  try { playTickAt(); } catch (e) {}
  if (rec !== null && window.OCA_DEBUG.voiceErrors) {
    const after = window.OCA_DEBUG.voiceErrors();
    tickCount = after.count;
    tickLast = after.last;
  }
  const unhandled = [];
  return { note, rec, tickCount, tickLast };
}
"""


from suite_server import start_server


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            # Only capture unhandled rejections relevant to the forced-fail
            # window (the page may legitimately resume() later — we poison
            # the constructor, resume is never reached).
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            r = page.evaluate(FORCE_FAIL)

            if r["note"] != "NO_THROW":
                failures.append(
                    f"a voice-builder failure must never break the calling "
                    f"page, got {r['note']!r}")
            if r["rec"] is None:
                failures.append(
                    "OCA_DEBUG.voiceErrors() missing — voice-builder errors "
                    "are still invisible")
            else:
                if r["rec"]["count"] < 1:
                    failures.append(
                        "a forced voice failure was not recorded "
                        f"(count={r['rec']['count']})")
                if "playNoteAt" not in str(r["rec"]["last"]):
                    failures.append(
                        f"the recorder must name the failing site "
                        f"(playNoteAt…), got {r['rec']['last']!r}")
                if "forced-ctx-fail" not in str(r["rec"]["last"]):
                    failures.append(
                        f"the recorder must carry the underlying error, got "
                        f"{r['rec']['last']!r}")
                if r["tickCount"] != r["rec"]["count"] + 1:
                    failures.append(
                        f"playTickAt failure must be recorded too "
                        f"(count {r['rec']['count']} -> {r['tickCount']})")
                if "playTickAt" not in str(r["tickLast"]):
                    failures.append(
                        f"the last record must name playTickAt, got "
                        f"{r['tickLast']!r}")

            if errs:
                failures.append(f"page errors {errs}")

            # --- global error net: window errors + unhandled rejections
            # land in #err APPENDED, never clobbering the messages
            # render()/boot() put there.
            page2 = browser.new_page()
            errs2 = []
            page2.on("pageerror", lambda e: errs2.append(str(e)))
            page2.goto(base)
            page2.wait_for_function(BOOT_WAIT)
            page2.evaluate("() => { const e = document.getElementById('err');"
                           " e.textContent = 'precious'; }")
            # Rejection from a timer so evaluate() never awaits it -> truly
            # unhandled; thrower likewise (a deliberate, expected pageerror).
            page2.evaluate("setTimeout(() => { Promise.reject"
                           "(new Error('probe-rejection')); }, 0)")
            page2.evaluate("setTimeout(() => { throw new Error"
                           "('probe-window'); }, 0)")
            page2.wait_for_timeout(300)
            errText = page2.evaluate(
                "() => document.getElementById('err').textContent")
            if "precious" not in errText:
                failures.append(
                    "global handlers clobber #err (render/boot messages can "
                    "be wiped): 'precious' gone, got " + errText[:120])
            if "probe-rejection" not in errText:
                failures.append(
                    "an unhandled promise rejection was not surfaced in "
                    "#err, got " + errText[:120])
            if "probe-window" not in errText:
                failures.append(
                    "a window.onerror crash was not surfaced in #err, got "
                    + errText[:120])
            # The two probe errors ARE the expected pageerror entries.
            unexpected = [e for e in errs2
                          if "probe-window" not in e and "probe-rejection"
                          not in e]
            if unexpected:
                failures.append(f"page errors {unexpected}")
            page2.close()

            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: voice-builder failures are recorded (count + site + cause) "
          "in OCA_DEBUG.voiceErrors() without breaking the page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
