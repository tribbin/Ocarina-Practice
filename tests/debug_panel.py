#!/usr/bin/env python3
# Debug panel contract: the dev panel is a first-open-only build — a plain
# visit must not create any of its DOM, console/?debug=1 opening builds it,
# DEBUG=0 hides it again, and the single public handle is window.OCA_DEBUG
# (the legacy OCO_DEBUG alias is retired).
#
#   python3 tests/debug_panel.py      # headless & silent

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
