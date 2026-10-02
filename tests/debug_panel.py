#!/usr/bin/env python3
# Debug panel contract: the dev panel is a first-open-only build — a plain
# visit must not create any of its DOM, console/?debug=1 opening builds it,
# DEBUG=0 hides it again, and the single public handle is window.OCA_DEBUG
# (the legacy OCO_DEBUG alias is retired).
#
#   python3 tests/debug_panel.py      # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function'")


from suite_server import start_server


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

            # --- plain visit: no panel DOM at all ---
            page.goto(base)
            page.wait_for_function(WAIT)
            probe = page.evaluate("""
              () => ({
                panel: !!document.getElementById('dbgPanel'),
                notes: !!(window.NOTES || []).length,
                api: typeof window.OCA_DEBUG,
                apiToggle: typeof (window.OCA_DEBUG || {}).toggle,
                legacy: 'OCO_DEBUG' in window,
              })
            """)
            if probe["panel"]:
                failures.append(
                    "a plain visit must not create the debug panel DOM "
                    "(#dbgPanel exists before it was ever opened)")
            if probe["api"] != "object" or probe["apiToggle"] != "function":
                failures.append(
                    "window.OCA_DEBUG must expose the panel handle "
                    "(toggle missing)")
            if probe["legacy"]:
                failures.append(
                    "the retired OCO_DEBUG alias must not exist on window")

            # --- console open: DEBUG=1 builds and opens it ---
            page.evaluate("() => { window.DEBUG = 1; }")
            probe2 = page.evaluate("""
              () => ({
                panel: !!document.getElementById('dbgPanel'),
                open: document.getElementById('dbgPanel') &&
                  document.getElementById('dbgPanel').classList.contains('open'),
                notes: document.querySelectorAll('#dbgNotes .dbg-note').length,
                sliderRows: document.querySelectorAll('#dbgGroups .dbg-group').length > 0,
              })
            """)
            if not probe2["panel"] or not probe2["open"]:
                failures.append(
                    "window.DEBUG = 1 must build and open the panel")
            if not probe2["notes"]:
                failures.append(
                    "the open panel must show its reference test notes "
                    "(NOTES arrived before open)")
            if not probe2["sliderRows"]:
                failures.append("the open panel must have its slider groups")
            voice_line = page.evaluate("""() => {
              const el = document.getElementById('dbgVoice');
              return el ? el.textContent : '';
            }""")
            if "v3k-chamber" not in (voice_line or ""):
                failures.append(
                    "the open panel must show the running voice stamp "
                    f"(#dbgVoice, got {voice_line!r})")

            # --- console hide: DEBUG=0 closes it (panel stays built) ---
            page.evaluate("() => { window.DEBUG = 0; }")
            still = page.evaluate(
                "() => document.getElementById('dbgPanel').classList"
                ".contains('open')")
            if still:
                failures.append("window.DEBUG = 0 must hide the panel")

            # --- ?debug=1 opens it from the start ---
            page2 = browser.new_page()
            page2.on("pageerror", lambda e2: errs.append(str(e2)))
            page2.goto(f"{base}?debug=1")
            page2.wait_for_function(WAIT)
            opened = page2.evaluate(
                "() => { const el = document.getElementById('dbgPanel');"
                " return el && el.classList.contains('open'); }")
            if not opened:
                failures.append("?debug=1 must open the panel on load")

            # --- instrument-loudness dial: five rows, dB shape, session-only ---
            dial = page2.evaluate("""
              () => {
                const rows = [...document.querySelectorAll('#dbgGroups .dbg-row')];
                const byKey = {};
                rows.forEach(r => {
                  const lab = r.querySelector('.dbg-lab');
                  const k = (lab && lab.title || '').split(' ')[0];
                  const rng = r.querySelector('input[type=range]');
                  byKey[k] = { min: +rng.min, max: +rng.max, step: +rng.step, val: +rng.value };
                });
                const groupSum = [...document.querySelectorAll('#dbgGroups summary')]
                  .map(s => s.textContent).join(' | ');
                return {
                  oot: byKey.instOotDb, stein: byKey.instSteinDb,
                  oak: byKey.instOakDb, contra: byKey.instContraDb,
                  dummy: byKey.instDummyDb,
                  groupSum, 
                  savedLen: (localStorage.getItem('oco-debug-audio') || '').length,
                };
              }
            """)
            for name in ("oot", "stein", "oak", "contra", "dummy"):
                row = dial.get(name)
                if not row:
                    failures.append(f"the dial row inst{name}Db is missing")
                    continue
                if row != {"min": -3.0, "max": 9.0, "step": 0.1, "val": 0.0}:
                    failures.append(f"the dial row inst{name}Db reads {row} — "
                                    "expected min -3 max 9 step 0.1 default 0")
            if "session-only" not in dial["groupSum"]:
                failures.append("the dial group must announce session-only")

            # — the dial's read side: the loaded instrument's own dB —
            math = page2.evaluate("""
              () => {
                const P = window.OCA_DEBUG.params;
                const gain = () => window.OCA_DEBUG.instLevelGain();
                window.CURRENT_INSTRUMENT = { id: 'ico-contrabass-11-c' };
                const at0 = gain();
                P.instContraDb = 6;   const at6 = gain();
                P.instContraDb = -3;  const atM3 = gain();
                P.instContraDb = 9;   const at9 = gain();
                P.instContraDb = 0;
                window.CURRENT_INSTRUMENT = { id: 'not-an-ocarina' };
                const foreign = gain();
                window.CURRENT_INSTRUMENT = null;
                const none = gain();
                window.CURRENT_INSTRUMENT = { id: 'oot-alto-c-12' };
                P.instOotDb = -3;     const ootM3 = gain();
                P.instOotDb = 0;
                return [at0, at6, atM3, at9, foreign, none, ootM3];
              }
            """)
            exp = [1.0, 10 ** (6 / 20), 10 ** (-3 / 20), 10 ** (9 / 20), 1.0, 1.0, 10 ** (-3 / 20)]
            for got, want, tag in zip(math, exp,
                    "at0 at+6 at-3 at+9 foreign-inst none oot-3".split()):
                if abs(got - want) > 1e-3:
                    failures.append(f"dial gain {tag}: {got} — expected {want}")

            # — session-only contract: dial edits never persist; plain edits do —
            page2.evaluate("""
              () => {
                const rows = [...document.querySelectorAll('#dbgGroups .dbg-row')];
                const setNum = (key, v) => {
                  for (const r of rows) {
                    const lab = r.querySelector('.dbg-lab');
                    if (((lab && lab.title) || '').split(' ')[0] !== key) continue;
                    const num = r.querySelector('.dbg-num');
                    num.value = String(v);
                    num.dispatchEvent(new Event('change'));
                    return true;
                  }
                  return false;
                };
                window.__dialSet = setNum;
              }
            """)
            if not page2.evaluate("() => window.__dialSet('instOotDb', 4.2)"):
                failures.append("the dial row's number input is not drivable")
            if not page2.evaluate("() => window.__dialSet('masterLevel', 0.5)"):
                failures.append("the masterLevel row's number input is not drivable")
            ok = False
            for _ in range(20):   # the 300 ms save debounce; poll, never sleep-blind
                page2.wait_for_timeout(100)
                if page2.evaluate(
                        "() => { const s = localStorage.getItem('oco-debug-audio') || '';"
                        " return !s.includes('instOotDb') && s.includes('masterLevel'); }"):
                    ok = True
                    break
            if not ok:
                failures.append("session-only contract: a dial edit must never enter "
                                "'oco-debug-audio' while a plain row edit persists")

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
    print("\nPASS: the debug panel builds on first open only, opens from "
          "?debug=1 and the console toggle, hides again, and OCA_DEBUG is "
          "the one public handle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
