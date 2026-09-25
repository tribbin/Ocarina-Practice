#!/usr/bin/env python3
# Instrument-switch race: a slow loadInstrument for an OLD selection must not
# clobber a newer one that finished first. Reproduces the dropdown swap burst:
# user switches to instrument A (slow fetch), immediately to B (fast); when A's
# promise finally resolves it must NOT install its fingerings/template over B.
#
#   python3 tests/instrument_switch_race.py      # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
BOOT_WAIT = ("window.INSTRUMENTS && window.INSTRUMENTS.length"
             " && window.NOTES && window.NOTES.length"
             " && typeof switchInstrument === 'function'")

# Throttle every loadText path mentioning this folder id by DELAY ms.
SLOW_ID = "dummy-bass-c-double"
FAST_ID = "stein-double-alto-c"
DELAY_MS = 800

RACE_SCRIPT = """
async ([slowId, fastId, delayMs]) => {
  const real = window.loadText;
  window.loadText = (path) => path.indexOf(slowId) !== -1
    ? new Promise(res => setTimeout(() => res(real(path)), delayMs))
    : real(path);
  const slow = window.INSTRUMENTS.find(i => i.id === slowId);
  const fast = window.INSTRUMENTS.find(i => i.id === fastId);
  try {
    const stale = switchInstrument(slow);   // slow fetch, not awaited
    await switchInstrument(fast);           // fast one completes first
    const during = {
      inst: window.CURRENT_INSTRUMENT.id,
      first: window.NOTES[0],
      consistent: window.FING && window.NOTES[0] === window.FING.notes[0].id,
    };
    await stale;                            // let the slow one settle
    const settled = {
      inst: window.CURRENT_INSTRUMENT.id,
      first: window.NOTES[0],
      consistent: window.FING && window.NOTES[0] === window.FING.notes[0].id,
      firstUnchanged: window.NOTES[0] === during.first,
    };
    return { during, settled };
  } finally {
    window.loadText = real;
  }
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
            page.goto(f"{base}?inst={FAST_ID}")
            page.wait_for_function(BOOT_WAIT)
            r = page.evaluate(RACE_SCRIPT, [SLOW_ID, FAST_ID, DELAY_MS])

            during, settled = r["during"], r["settled"]
            if during["inst"] != FAST_ID:
                failures.append(
                    f"right after the fast switch the newer instrument must be "
                    f"installed, got {during['inst']!r}")
            if not settled["consistent"]:
                failures.append(
                    "FING/NOTES/COVER must stay aligned with the installed "
                    "instrument (settled)")
            if settled["inst"] != FAST_ID:
                failures.append(
                    f"the slow older switch must NOT clobber the newer install "
                    f"on settle, ended up on {settled['inst']!r}")
            if not settled["firstUnchanged"]:
                failures.append(
                    f"the slow older switch must NOT replace NOTES "
                    f"({during['first']!r} became {settled['first']!r})")
            if set((during["inst"], during["first"], settled["first"])) \
                    & {None, "", False}:
                failures.append(f"degenerate race state: {r}")

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
    print("\nPASS: a slow stale instrument switch can no longer clobber the "
          "newer install (fingerings/template stay consistent).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
