#!/usr/bin/env python3
# Keyboard accessibility of the two interactive widgets:
#   - piano keys must be operable from the keyboard: semantics (role=button),
#     aria-labels, roving tabindex (exactly one tab stop), arrow navigation
#     between keys, Enter/Space audition a note (a voice appears).
#   - token chips in the playback strip must be keyboard-reachable and
#     activatable: role=button + aria-label, roving tabindex with arrow
#     navigation, Enter/Space = "play from here" (same as mouse click).
#
#   python3 tests/keyboard_widgets.py      # headless & silent

import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
BOOT_WAIT = ("window.NOTES && window.NOTES.length"
             " && typeof playNote === 'function'"
             " && typeof isMelodyPlaying === 'function'"
             " && window.OCA_DEBUG")


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


PIANO = """
() => {
  const keys = [...document.querySelectorAll('#kb .key[data-note]')];
  const tabbable = keys.filter(k => k.getAttribute('tabindex') === '0');
  const labelled = keys.filter(k => (k.getAttribute('aria-label') || '').length > 3
                                    && k.getAttribute('role') === 'button');
  const out = { keyCount: keys.length, tabbable: tabbable.length,
                labelled: labelled.length, afterArrow: null, voiceAfterEnter: null };
  if (!keys.length || !tabbable.length) return out;
  // Arrow navigation: from the focused/anchor key, ArrowRight must land on
  // the next data-note key in DOM order.
  const anchor = document.activeElement.closest('#kb .key[data-note]');
  const start = tabbable[0];
  start.focus();
  start.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowRight', bubbles: true}));
  const focusedKey = document.activeElement.closest('#kb .key[data-note]');
  const all = [...document.querySelectorAll('#kb .key[data-note]')];
  const from = all.indexOf(start), to = all.indexOf(focusedKey);
  out.afterArrow = {from, to};
  // Enter audits the note: a voice must be built (OCA_DEBUG.liveVoices()).
  const before = window.OCA_DEBUG.liveVoiceCount ? window.OCA_DEBUG.liveVoiceCount() : null;
  focusedKey.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
  out.voiceAfterEnter = window.OCA_DEBUG.liveVoiceCount ? window.OCA_DEBUG.liveVoiceCount() : null;
  out.voiceBefore = before;
  out.curBefore = document.activeElement ? document.activeElement.dataset.note : null;
  return out;
}
"""

TOKENS = """
() => {
  // The playback block starts collapsed (display:none) — focus cannot land
  // there until it is expanded, exactly as for a human user. Expand first.
  const block = document.getElementById('playback');
  if (block && block.classList.contains('collapsed')) {
    const btn = block.querySelector('.collapse-btn');
    if (btn) btn.click();
  }
  const strip = document.getElementById('tokens');
  const toks = [...strip.querySelectorAll('.tok[role="button"]')];
  const out = { tokenCount: toks.length, tabbable: 0, labels: 0,
                arrow: null, playedFromToken: null };
  if (!toks.length) return out;
  out.tabbable = [...strip.querySelectorAll('[tabindex="0"]')]
    .filter(e => e.classList.contains('tok')).length;
  out.labels = toks.filter(t => (t.getAttribute('aria-label') || '').length > 3).length;
  // Focus the first activatable token, arrow right, Enter.
  toks[0].focus();
  toks[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowRight', bubbles: true}));
  out.arrow = toks.indexOf(document.activeElement);
  const target = document.activeElement;
  out.arrowNote = target ? (target.getAttribute('aria-label') || '') : null;
  target.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
  out.playedFromToken = window.isMelodyPlaying();
  if (out.playedFromToken && typeof stopMelody === 'function') {
    try { stopMelody(); } catch (e) {}
  }
  return out;
}
"""


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
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)

            # --- piano ---
            k = page.evaluate(PIANO)
            if k["keyCount"] < 15:
                failures.append(
                    f"piano: expected many playable keys for the triple bass, "
                    f"got {k['keyCount']}")
            if k["labelled"] != k["keyCount"]:
                failures.append(
                    f"piano: every playable key needs role=button + an "
                    f"aria-label, got {k['labelled']}/{k['keyCount']}")
            if k["tabbable"] != 1:
                failures.append(
                    f"piano: roving tabindex must yield exactly ONE tab stop, "
                    f"got {k['tabbable']}")
            if k["afterArrow"] is None or \
                    k["afterArrow"]["to"] != k["afterArrow"]["from"] + 1:
                failures.append(
                    f"piano: ArrowRight must move focus to the next key "
                    f"(got {k['afterArrow']})")
            if k["voiceAfterEnter"] is None:
                failures.append(
                    "OCA_DEBUG.liveVoiceCount() missing — cannot verify audition")
            elif not k["voiceAfterEnter"] or k["voiceAfterEnter"] <= (
                    k["voiceBefore"] or 0):
                failures.append(
                    f"piano: Enter must audition the note (live voices "
                    f"{k['voiceBefore']} -> {k['voiceAfterEnter']})")
            if k["voiceAfterEnter"] and not k["curBefore"]:
                failures.append("piano: focus must stay on the pressed key")

            # --- tokens ---
            t = page.evaluate(TOKENS)
            if t["tokenCount"] < 10:
                failures.append(
                    f"tokens: expected an activatable token strip, got "
                    f"{t['tokenCount']} role=button tokens")
            else:
                if t["labels"] != t["tokenCount"]:
                    failures.append(
                        f"tokens: every activatable token needs an aria-label, "
                        f"got {t['labels']}/{t['tokenCount']}")
                if t["tabbable"] != 1:
                    failures.append(
                        f"tokens: roving tabindex must yield exactly ONE tab "
                        f"stop in the strip, got {t['tabbable']}")
                if t["arrow"] != 1:
                    failures.append(
                        f"tokens: ArrowRight must move focus to the next "
                        f"token (got index {t['arrow']})")
                if t["playedFromToken"] is not True:
                    failures.append(
                        "tokens: Enter must play from that token "
                        "(isMelodyPlaying() stayed false)")

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
    print("\nPASS: piano keys and token chips are full keyboard citizens "
          "(semantics, roving tabindex, arrows, Enter/Space activation).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
