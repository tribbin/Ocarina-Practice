#!/usr/bin/env python3
# Theme toggle contract: a saved "oco-theme" choice persists across reloads,
# the toggle flips data-theme (Hyrule ↔ classic light) and re-renders, and the
# ?plain / ?oot link parameters keep outranking the saved choice (old shared
# links, ??plain detours, stay truthful).
#
#   python3 tests/theme_toggle.py      # headless & silent

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

            # fresh browser: the Hyrule look, glyph names the TARGET? no — it
            # names the ACTIVE look ("Hyrule" while the Hyrule look is on).
            page.goto(base)
            page.wait_for_function(WAIT)
            first = page.evaluate(
                "() => ({ theme: document.documentElement.getAttribute('data-theme'),"
                        " label: document.getElementById('themeBtn').textContent })")
            if first["theme"] != "oot" or first["label"] != "Hyrule":
                failures.append(f"fresh visit must boot on the Hyrule look "
                                f"(got {first})")

            # click: flips to plain, persists, cards still render
            page.click("#themeBtn")
            page.wait_for_function(
                "() => !document.documentElement.hasAttribute('data-theme')")
            flipped = page.evaluate("""
              () => ({ label: document.getElementById('themeBtn').textContent,
                       saved: localStorage.getItem('oco-theme'),
                       cards: document.querySelectorAll('#sheet svg').length })
            """)
            if flipped["label"] != "Plain" or flipped["saved"] != "":
                failures.append(f"the toggle must flip to plain + save "
                                f"(got {flipped})")
            if not flipped["cards"]:
                failures.append("cards must still render on the plain theme")

            # reload: the saved choice rules (the label read waits for the
            # boot's glyph sync rather than trusting a bare boot-wait)
            page.reload()
            page.wait_for_function(
                "() => document.getElementById('themeBtn') &&"
                " document.getElementById('themeBtn').textContent === 'Plain'")
            kept = page.evaluate(
                "() => ({ theme: document.documentElement.getAttribute('data-theme'),"
                        " label: document.getElementById('themeBtn').textContent })")
            if kept["theme"] is not None or kept["label"] != "Plain":
                failures.append(f"the saved plain look must survive reload "
                                f"(got {kept})")

            # link parameters outrank the saved choice, both directions
            page.goto(base + "?oot")
            page.wait_for_function(WAIT)
            forced = page.evaluate(
                "() => document.documentElement.getAttribute('data-theme')")
            if forced != "oot":
                failures.append("?oot must force the Hyrule look for old links")
            page.evaluate("() => localStorage.setItem('oco-theme', 'oot')")
            page.goto(base + "?plain")
            page.wait_for_function(WAIT)
            detour = page.evaluate(
                "() => ({ theme: document.documentElement.getAttribute('data-theme'),"
                        " saved: localStorage.getItem('oco-theme') })")
            if detour["theme"] is not None:
                failures.append("?plain must detour to the light look even with "
                                f"a saved Hyrule choice (got {detour})")
            if detour["saved"] != "oot":
                failures.append("a link detour must not rewrite the saved choice")

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
    print("\nPASS: the theme toggle flips and persists data-theme, link "
          "parameters keep outranking the saved choice, and cards render in "
          "both looks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
