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
import time
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
            # The Chromium offline→online transition leaves service-worker
            # fetches rejected for a stretch (observed: the data-freshness
            # legs below failed right after set_offline(False) while a later
            # fetch succeeded — the network-first fallback had answered their
            # requests from the cached copies). The legs' real rendezvous is
            # a fresh fetch succeeding through the worker.
            page.wait_for_function(
                "() => fetch('songs.json').then(r => r.ok)", timeout=30000)

            # --- data freshness legs (Robin, 2026-09-28: deployed songs had
            # to ride a SECOND reload under stale-while-revalidate, and a
            # phone-app resume never re-checked anything) ---
            songs_path = ROOT / "songs.json"
            pristine = songs_path.read_bytes()
            try:
                # (a) an online RELOAD lands the deployed data on the FIRST
                # reload: the same installed worker now serves the released
                # data before its cached copy (network-first with cached
                # fallback), instead of stale-while-revalidate's one-reload
                # lag.
                def with_sentinel(key):
                    import json as _json
                    data = _json.loads(pristine.decode("utf-8"))
                    data[key] = {
                        "name": "PWA Freshness Sentinel",
                        "group": "Other", "tempo": 97,
                        "body": "C4 D4 E4 | r/2.",
                    }
                    songs_path.write_text(
                        _json.dumps(data, separators=(",", ":")),
                        encoding="utf-8")
                with_sentinel("pwa-freshness-sentinel-a")
                page.reload()
                page.wait_for_function(WAIT)
                try:
                    page.wait_for_function(
                        "() => Object.keys(window.BUILTIN)"
                        ".includes('pwa-freshness-sentinel-a')", timeout=15000)
                except Exception:
                    failures.append(
                        "an online reload must land the released data on "
                        "the FIRST reload (stale-while-revalidate lag)")

                # (b) a RESUME (visibility back to visible, nothing running)
                # re-fetches the data network-first and swaps the library
                # when the bytes changed.
                # The server's conditional revalidation compares mtime at
                # whole-SECOND precision, and the sentinel rewrite lands
                # within the same wall-second as the previous serve — the
                # revalidation would answer 304 with the cached pre-mutation
                # body and the legs would race their own freshness clock.
                # One real clock-second separates the serve before any
                # rewrite.
                time.sleep(1.1)
                with_sentinel("pwa-freshness-sentinel-b")
                page.evaluate(
                    "() => document.dispatchEvent"
                    "(new Event('visibilitychange'))")
                try:
                    page.wait_for_function(
                        "() => Object.keys(window.BUILTIN)"
                        ".includes('pwa-freshness-sentinel-b')", timeout=15000)
                except Exception:
                    failures.append(
                        "an app resume must re-fetch songs.json and swap "
                        "the library when the bytes changed")
            finally:
                songs_path.write_bytes(pristine)

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
