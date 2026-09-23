#!/usr/bin/env python3
# Console-hygiene contract: a real page boot must leave the browser console
# CLEAN of everything except the documented, expected misses. Robin kept
# catching real page errors by hand in the F12 console while the unit suites
# printed green — the suites capture pageerrors but never look at
# console.error-level output, and a sick page with healthy unit probes is
# the worst failure mode (the AI reads green and moves on).
#
# Four real boots: the default home, the Hyrule/OoT look (?oot), the plain
# look (?plain) and the debug panel boot (?debug=1 — it exercises the
# panel-build path). Each must produce ZERO uncaught exceptions, ZERO
# unhandled rejections, and zero console errors except the 404s the
# manifest DECLARES: a tone entry whose file is intentionally absent
# ("no recordings yet") is a documented miss — any other console error
# fails.
#
#   python3 tests/console_hygiene.py          # headless & silent

import http.server
import socketserver
import json
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
BOOT_WAIT = ("typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
             " && window.NOTES && window.NOTES.length")
SETTLE_MS = 2000  # async stragglers: library fill, SW registration, tone misses


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


def declared_tone_paths():
    """The tone files the manifest WANTS — their 404s are the documented
    'no recordings yet' state, expected and allowed."""
    manifest = json.loads((ROOT / "instruments.json").read_text())
    paths = []
    for inst in manifest.get("instruments", []):
        tone = inst.get("tone")
        if isinstance(tone, str):
            paths.append(tone)
        elif isinstance(tone, dict):
            for v in tone.values():
                if isinstance(v, str):
                    paths.append(v)
    return paths


def main():
    failures = []
    allowed = declared_tone_paths()
    boots = ["", "?oot", "?plain", "?debug=1"]
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            for query in boots:
                tag = query or "default"
                page = browser.new_page()
                con_errors = []   # (text, url)
                page_errors = []
                rejections = []
                page.on("console", lambda m, q=con_errors:
                        (m.type == "error") and q.append((m.text, m.location["url"])))
                page.on("pageerror", lambda e, q=page_errors: q.append(str(e)))
                # unhandled rejections arrive on the page itself
                page.add_init_script(
                    "window.__rejections = [];"
                    "window.addEventListener('unhandledrejection',"
                    " e => window.__rejections.push(String(e && e.reason)));")
                page.goto(base + query)
                page.wait_for_function(BOOT_WAIT)
                page.wait_for_timeout(SETTLE_MS)
                rejections = page.evaluate("() => window.__rejections")
                page.close()

                print(f"== {tag}: {len(con_errors)} console errors,"
                      f" {len(page_errors)} page errors,"
                      f" {len(rejections)} rejections", flush=True)
                unexpected = [
                    f"console.error {text!r} @ {url}"
                    for (text, url) in con_errors
                    if not (url and "404" in text and
                            any(url.endswith(a) for a in allowed))
                ]
                if unexpected:
                    failures.append(f"{tag}: unexpected console errors: {unexpected}")
                if page_errors:
                    failures.append(f"{tag}: uncaught page errors: {page_errors}")
                if rejections:
                    failures.append(f"{tag}: unhandled rejections: {rejections}")
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL: the console is not clean — a boot surfaced real page"
              " errors the unit suites would have printed green around.")
        for f in failures:
            print("  - " + f)
        return 1
    print(f"\nPASS: {len(boots)} real boots are console-clean (allowed"
          f" misses: {len(allowed)} manifest-declared tone files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
