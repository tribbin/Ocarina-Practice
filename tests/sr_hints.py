#!/usr/bin/env python3
# Gesture-hint a11y contract: the affordances that used to exist only as
# title tooltips (token chips, piano keys, tan junk pills) point at one shared
# describedby hint block, so touch/AT users get the same explanation desktop
# hover gets; out-of-range chips additionally name their direction and the
# can't-play fact in the accessible label instead of title-only.
#
#   python3 tests/sr_hints.py      # headless & silent

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
            browser = p.chromium.launch(headless=HEADLESS,
                                        args=["--autoplay-policy=no-user-gesture-required"])
            errs = []
            page = browser.new_page()
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(WAIT)
            page.evaluate(
                "() => { const b = document.getElementById('playback');"
                " b.querySelector('.collapse-btn').click(); }")
            # Melody covers: playable chips (role=button), a bad junk chip,
            # and an out-of-range chip — the Pin melody on the default 12-hole
            # Alto C leaves most of that absent, so type a dedicated body.
            page.evaluate("""
              async () => {
                const ta = document.getElementById('src');
                ta.value = "# Hints\\n\\nB3 zz | G6/2";
                ta.dispatchEvent(new Event('input', { bubbles: true }));
                const t0 = Date.now();
                while (document.getElementById('title').textContent !== 'Hints' &&
                       Date.now() - t0 < 3000) {
                  await new Promise(r => setTimeout(r, 15));
                }
              }
            """)
            r = page.evaluate("""
              () => {
                const hint = document.getElementById('sr-gesture-hints');
                const text = hint ? hint.textContent : "";
                const described = (sel) => [...document.querySelectorAll(sel)]
                  .map(el => el.getAttribute('aria-describedby'));
                const oor = document.querySelector('#tokens .tok.oor');
                return {
                  hintPresent: !!hint,
                  hintVisibleText: !!(hint && text.includes('auditions')),
                  hintKeyText: !!(hint && text.includes('right-click')),
                  tokenDesc: described('#tokens .tok[role="button"]'),
                  badDesc: described('#tokens .tok.bad'),
                  keysDesc: described('#kb .key[role="button"]'),
                  oorLabel: oor ? oor.getAttribute('aria-label') : null,
                };
              }
            """)
            if not r["hintPresent"]:
                failures.append("the shared sr-gesture-hints block must exist")
            else:
                if not r["hintVisibleText"]:
                    failures.append(
                        "the hint block must explain the touch-hold audition")
                if not r["hintKeyText"]:
                    failures.append(
                        "the hint block must explain right-click to add")
            if not r["tokenDesc"] or any(d != "sr-gesture-hints" for d in r["tokenDesc"]):
                failures.append(
                    "every activatable token chip must describedby "
                    f"sr-gesture-hints (got {r['tokenDesc'][:4]!r})")
            if not r["keysDesc"] or any(d != "sr-gesture-hints" for d in r["keysDesc"]):
                failures.append(
                    "every playable piano key must describedby "
                    f"sr-gesture-hints (got {r['keysDesc'][:4]!r})")
            if not r["badDesc"] or any(d != "sr-gesture-hints" for d in r["badDesc"]):
                failures.append(
                    "junk pills must carry the shared hint (fix-or-remove is "
                    f"not title-only alphabet soup) — got {r['badDesc']!r}")
            if not r["oorLabel"] or "can't be played" not in r["oorLabel"] \
                    or not ("above" in r["oorLabel"] or "below" in r["oorLabel"]):
                failures.append(
                    "an out-of-range chip must name its direction and the "
                    f"can't-play fact in its label (got {r['oorLabel']!r})")

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
    print("\nPASS: token chips, piano keys and junk pills all describedby the "
          "shared gesture-hint block; out-of-range chips self-describe "
          "(direction + can't play) instead of title-only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
