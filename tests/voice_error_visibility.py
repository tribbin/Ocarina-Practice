#!/usr/bin/env python3
# Voice-builder failure visibility: playNoteAt/playTickAt deliberately swallow
# any WebAudio failure so a bad synth call can never break the page — but a
# swallowed system-wide failure was INVISIBLE (an ocarina that silently plays
# nothing is the worst failure mode for a practice tool). This asserts a new
# OCA_DEBUG.voiceErrors() recorder catches real failures (forced AudioContext
# creation failure) for both voices, without breaking the calling page.
#
#   python3 tests/voice_error_visibility.py      # headless & silent

import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
BOOT_WAIT = ("typeof playNote === 'function'"
             " && typeof playTickAt === 'function'"
             " && window.OCA_DEBUG")

FORCE_FAIL = """
() => {
  // Fresh, gesture-less page: no existing AudioContext, so the constructor
  // lookup is forced to fail before any voice code runs.
  Object.defineProperty(window, "AudioContext", {
    get() { throw new Error("forced-ctx-fail"); }, configurable: true,
  });
  let note = null;
  try { playNote("C5", 0.2); note = "NO_THROW"; }
  catch (e) { note = "THREW:" + e.message; }
  const rec = (window.OCA_DEBUG && window.OCA_DEBUG.voiceErrors)
    ? window.OCA_DEBUG.voiceErrors() : null;
  let tickCount = null, tickLast = null;
  try { playTickAt(); } catch (e) {}
  if (rec !== null && window.OCA_DEBUG.voiceErrors) {
    const after = window.OCA_DEBUG.voiceErrors();
    tickCount = after.count;
    tickLast = after.last;
  }
  const unhandled = [];
  return { note, rec, tickCount, tickLast };
}
"""


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
            browser = p.chromium.launch(headless=HEADLESS)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            # Only capture unhandled rejections relevant to the forced-fail
            # window (the page may legitimately resume() later — we poison
            # the constructor, resume is never reached).
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            r = page.evaluate(FORCE_FAIL)

            if r["note"] != "NO_THROW":
                failures.append(
                    f"a voice-builder failure must never break the calling "
                    f"page, got {r['note']!r}")
            if r["rec"] is None:
                failures.append(
                    "OCA_DEBUG.voiceErrors() missing — voice-builder errors "
                    "are still invisible")
            else:
                if r["rec"]["count"] < 1:
                    failures.append(
                        "a forced voice failure was not recorded "
                        f"(count={r['rec']['count']})")
                if "playNoteAt" not in str(r["rec"]["last"]):
                    failures.append(
                        f"the recorder must name the failing site "
                        f"(playNoteAt…), got {r['rec']['last']!r}")
                if "forced-ctx-fail" not in str(r["rec"]["last"]):
                    failures.append(
                        f"the recorder must carry the underlying error, got "
                        f"{r['rec']['last']!r}")
                if r["tickCount"] != r["rec"]["count"] + 1:
                    failures.append(
                        f"playTickAt failure must be recorded too "
                        f"(count {r['rec']['count']} -> {r['tickCount']})")
                if "playTickAt" not in str(r["tickLast"]):
                    failures.append(
                        f"the last record must name playTickAt, got "
                        f"{r['tickLast']!r}")

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
    print("\nPASS: voice-builder failures are recorded (count + site + cause) "
          "in OCA_DEBUG.voiceErrors() without breaking the page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
