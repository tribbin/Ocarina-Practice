#!/usr/bin/env python3
# Offline (PWA) contract: after one connected visit, a reload in airplane
# mode boots the app from the service worker cache — shell, data, and the
# chosen ocarina's fingerings/template — with full practice capable flows:
# the melody renders, and swapping instruments still works offline. The
# install-time cache is derived from instruments.json, so a new ocarina in
# the manifest is covered without touching sw.js.
#
#   python3 tests/offline_pwa.py      # headless & silent

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
            context = browser.new_context()
            errs = []
            page = context.new_page()
            page.on("pageerror", lambda e: errs.append(str(e)))

            # --- first (connected) visit: app boots, SW installs, cache primes ---
            page.goto(base)
            page.wait_for_function(WAIT)
            page.wait_for_function(
                "() => navigator.serviceWorker"
                " && navigator.serviceWorker.controller")
            # The install derives the instrument files from the manifest;
            # give that settle so the offline leg has its data in cache.
            page.wait_for_function(
                "() => caches.match('instruments.json').then(Boolean)",
                timeout=15000)
            page.wait_for_function(
                "() => caches.match('songs.json').then(Boolean)",
                timeout=15000)
            got = page.evaluate(
                "() => ({ inst: window.CURRENT_INSTRUMENT &&"
                        " window.CURRENT_INSTRUMENT.id,"
                        " chips: document.querySelectorAll('#tokens .tok')"
                        ".length })")
            if not got["inst"]:
                failures.append("boot must land with an instrument installed")
            if not got["chips"]:
                failures.append("boot must render the token strip")
            offline_errors = []

            # --- airplane-mode reload: the shell must boot from cache ---
            context.set_offline(True)
            page.reload()
            page.wait_for_function(WAIT, timeout=20000)
            off = page.evaluate(
                "() => ({ inst: window.CURRENT_INSTRUMENT &&"
                        " window.CURRENT_INSTRUMENT.id,"
                        " notes: (window.NOTES || []).length,"
                        " cards: document.querySelectorAll('#sheet .card')"
                        ".length })")
            if not off["inst"] or not off["notes"]:
                failures.append(
                    "an offline reload must still mount the instrument from "
                    f"cache (got {off})")
            if not off["cards"]:
                failures.append("the offline song must render its chart")

            # --- offline instrument swap: derived cache must cover it ---
            page.select_option("#instSel", "ico-oak-leaf-bass-c-triple")
            page.wait_for_function(
                "() => window.CURRENT_INSTRUMENT &&"
                " window.CURRENT_INSTRUMENT.id ==="
                " 'ico-oak-leaf-bass-c-triple'", timeout=20000)
            swapped = page.evaluate(
                "() => ({ notes: (window.NOTES || []).length,"
                        " cards: document.querySelector('#sheet')"
                        ".children.length })")
            if not swapped["notes"]:
                failures.append(
                    "an offline instrument swap must install the other "
                    "ocarina's fingerings from cache")
            if swapped["cards"] < 1:
                failures.append(
                    "an offline instrument swap must render the sheet")

            context.set_offline(False)

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
    print("\nPASS: after one connected visit the app boots offline — shell, "
          "data, the home ocarina and even an instrument swap all come from "
          "the service worker cache.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
