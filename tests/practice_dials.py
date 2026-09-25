#!/usr/bin/env python3
# The playback-only dials dim while practice is engaged: practice runs from the
# song's own headers (tempo AND swing), so the playback tempo dial already dims
# (.dial-off = opacity .18 + pointer-events none) — the swing slider must join
# that same family (Robin's field defect: swing stayed live "not 'disabled'
# like tempo"). Engage practice in the non-Zen screen: tempo, focus-tempo and
# swing groups all dim inert; disengage: all restore; re-engage: dims again.
#
#   python3 tests/practice_dials.py    # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function' && window.OCA_PRACTICE")


from suite_server import start_server


GROUPS = ("tempoGrp", "focusTempoLab", "swingGrp")

SNAP = """
() => ["tempoGrp", "focusTempoLab", "swingGrp"].reduce((acc, id) => {
  const el = document.querySelector("#" + id);
  if (!el) { acc[id] = "MISSING"; return acc; }
  const cs = getComputedStyle(el);
  acc[id] = { off: el.classList.contains("dial-off"), op: cs.opacity,
              pe: cs.pointerEvents };
  return acc;
}, {})
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
            page.goto(base)
            page.wait_for_function(WAIT)

            def snap():
                return page.evaluate(SNAP)

            pre = snap()
            for g in GROUPS:
                s = pre[g]
                if s == "MISSING":
                    failures.append(f"boot: #{g} missing — the dim family needs it")
                elif s["off"]:
                    failures.append(f"boot: #{g} must not carry .dial-off before practice")

            # --- engage practice: the whole playback-dial family dims inert ---
            page.click("#mirrorPractice")
            page.wait_for_function("() => window.OCA_PRACTICE.active()")
            on = snap()
            for g in GROUPS:
                s = on[g]
                if s == "MISSING":
                    continue
                if not s["off"]:
                    failures.append(f"engage: #{g} must carry .dial-off while practice runs")
                elif float(s["op"]) > 0.3:
                    failures.append(f"engage: #{g} opacity {s['op']} is not the .18 dim")
                elif s["pe"] != "none":
                    failures.append(f"engage: #{g} must be inert (pointer-events "
                                    f"{s['pe']!r} ≠ none)")

            # --- disengage: every member restores ---
            page.click(".prac-panel .prac-close")
            page.wait_for_function("() => !window.OCA_PRACTICE.active()")
            off = snap()
            for g in GROUPS:
                s = off[g]
                if s == "MISSING":
                    continue
                if s["off"]:
                    failures.append(f"disengage: #{g} must drop .dial-off")

            # --- re-engage: dims again (no restore debt) ---
            page.click("#mirrorPractice")
            page.wait_for_function("() => window.OCA_PRACTICE.active()")
            again = snap()
            for g in GROUPS:
                s = again[g]
                if s == "MISSING":
                    continue
                if not s["off"]:
                    failures.append(f"re-engage: #{g} must carry .dial-off again")

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
    print("\nPASS: the swing dial joins the tempo's playback-only dim while "
          "practice runs (.dial-off on tempo/focus-tempo/swing, inert), and "
          "the family restores on disengage and dims again on re-engage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
