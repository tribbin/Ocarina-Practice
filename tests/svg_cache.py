#!/usr/bin/env python3
# SVG-clone coordinates pin: the sheet card clones (ocarinaSVG) must be a pure
# function of their inputs — covered hole set, chamber, big-holes view and the
# installed template — with no hidden dependence on when/how they were
# rendered. Written to guard the upcoming per-note SVG reuse refactor: any
# cache or clone-memoization must invalidate on exactly these keys.
#
# Probed as rendered output (never inspecting the app's internals):
#   1. re-typing the same melody reproduces the identical card SVG
#   2. the Enlarge-small-holes view enlarges them, and toggling back restores
#   3. an instrument swap re-renders different hole states, and swapping back
#      reproduces the first instrument's SVG exactly
#
#   python3 tests/svg_cache.py      # headless & silent

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


TYPE = """
async (SRC) => {
  const expect = String(SRC).split("\\n").find(l => /^#([^\\s])/.test(l));
  const wantTitle = expect ? expect.replace(/^#\\s*/, "") : "";
  const ta = document.getElementById('src');
  ta.value = SRC;
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  const t0 = Date.now();
  while (document.getElementById('title').textContent !== wantTitle &&
         Date.now() - t0 < 3000) {
    await new Promise(r => setTimeout(r, 15));
  }
  const card = document.querySelector('#sheet .card[data-i="0"] svg')
    || document.querySelector('#sheet svg');
  return card ? card.outerHTML : null;
}
"""

TOGGLE_BIG = """
() => {
  const big = document.getElementById('bigSmall');
  big.click();
  const card = document.querySelector('#sheet .card[data-i="0"] svg')
    || document.querySelector('#sheet svg');
  return card ? card.outerHTML : null;
}
"""


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    MELODY = "# SVG pin\n\nA4 C5 A4 C5"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS,
                                        args=["--autoplay-policy=no-user-gesture-required"])
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            # Boot on the 12-hole Alto C explicitly: its calibrated chamber
            # look is the baseline, and the Triple Bass used below covers the
            # same melody on a different body template.
            page.goto(f"{base}?inst=oot-alto-c-12")
            page.wait_for_function(WAIT)
            page.evaluate(
                "() => { const b = document.getElementById('playback');"
                " b.querySelector('.collapse-btn').click(); }")

            svg1 = page.evaluate(TYPE, MELODY)
            if not svg1:
                failures.append("no card svg rendered for the melody")
            svg2 = page.evaluate(TYPE, MELODY)
            if svg1 != svg2:
                failures.append(
                    "re-typing the same melody must reproduce the identical "
                    "card svg (clone output is not a pure function of its "
                    "inputs)")

            # Enlarge-small-holes enters the output: radii grow.
            svgBig = page.evaluate(TOGGLE_BIG)
            if svgBig is None or svgBig == svg2:
                failures.append(
                    "big-holes view must change the rendered card svg")
            svgBack = page.evaluate(TOGGLE_BIG)
            if svgBack != svg2:
                failures.append(
                    "toggling big-holes back off must restore the exact "
                    "previous card svg")

            # Instrument swap: different hole set/template, then back.
            page.select_option("#instSel", "ico-oak-leaf-bass-c-triple")
            page.wait_for_function(
                "() => document.getElementById('instSel').value ==="
                " 'ico-oak-leaf-bass-c-triple'")
            svgBass = page.evaluate(TYPE, MELODY)
            if not svgBass:
                failures.append("no card svg after the instrument swap")
            elif svgBass == svg2:
                failures.append(
                    "a different instrument must render different card svgs")
            page.select_option("#instSel", "oot-alto-c-12")
            page.wait_for_function(
                "() => document.getElementById('instSel').value ==="
                " 'oot-alto-c-12'")
            svgBackI = page.evaluate(TYPE, MELODY)
            if svgBackI != svg2:
                failures.append(
                    "swapping back to the first instrument must reproduce its "
                    "original card svg exactly")

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
    print("\nPASS: card svgs are a pure function of holes/chamber/big-view/"
          "template across re-renders and instrument swaps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
