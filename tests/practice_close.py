#!/usr/bin/env python3
# The practice layout pair (Robin's IDEAS LAYOUT lines): the floating tuner's
# top-right close button un-presses practice in full (the mode ENDS — not the
# transport's pause-many-disengage), and the practice transport buttons carry
# a microphone glyph instead of the "♪" note (the new-user hint: this button
# wants you to play into the mic).
#
#   python3 tests/practice_close.py    # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function' && window.OCA_PRACTICE")


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
            page.goto(base)
            page.wait_for_function(WAIT)

            # --- the close button: top-right of the floating tuner ----------
            page.click("#mirrorPractice")
            page.wait_for_selector(".prac-panel:not([hidden])", timeout=15000)
            visible = page.evaluate(
                "() => ({ act: window.OCA_PRACTICE.active(),"
                        " cls: document.querySelector('.prac-panel').className,"
                        " n: document.querySelectorAll('.prac-panel .prac-close').length })")
            if not visible["act"]:
                failures.append("practice must engage for the close-button leg")
            if visible["n"] != 1:
                failures.append(f"the floating tuner must carry exactly one "
                                f"close button (got {visible['n']})")

            page.click(".prac-panel .prac-close")
            page.wait_for_function("() => !window.OCA_PRACTICE.active()")
            after = page.evaluate(
                "() => ({ hidden: document.querySelector('.prac-panel').hidden,"
                        " pressed: document.getElementById('mirrorPractice').getAttribute('aria-pressed') })")
            if not after["hidden"]:
                failures.append("closing practice must hide the tuner panel")
            if after["pressed"] != "false":
                failures.append(f"closing practice must un-press the transport button "
                                f"(arc pressed={after['pressed']})")

            # re-engage still works after a close (no dead panel, no stale state)
            page.click("#mirrorPractice")
            page.wait_for_function("() => window.OCA_PRACTICE.active()")
            re_engaged = page.evaluate(
                "() => document.querySelectorAll('.prac-panel .prac-close').length")
            if re_engaged != 1:
                failures.append(f"the rebuilt tuner still carries one close "
                                f"button (got {re_engaged})")

            # --- the mic glyph: the transports speak practice's language ----
            page.click(".prac-panel .prac-close")
            page.wait_for_function("() => !window.OCA_PRACTICE.active()")
            glyphs = page.evaluate("""
              () => ['mirrorPractice', 'practiceFocusBtn'].map(id => {
                const b = document.getElementById(id);
                return { id, mic: b.querySelectorAll('svg.g-mic').length,
                         text: (b.textContent || '').trim(),
                         title: b.title };
              })
            """)
            for g in glyphs:
                if g["mic"] != 1:
                    failures.append(f"#{g['id']} must carry the mic glyph (got {g['mic']})")
                if g["text"]:
                    failures.append(f"#{g['id']} must not keep the note glyph text "
                                    f"beside it (got {g['text']!r})")
                if "Practice mode" not in g["title"]:
                    failures.append(f"#{g['id']} must keep the Practice-mode title "
                                    f"(got {g['title']!r})")
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
    print("\nPASS: the floating tuner closes practice in full from its top-right "
          "close button and re-engages clean, and the practice transport buttons "
          "carry the microphone glyph with the note text retired.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
