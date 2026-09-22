#!/usr/bin/env python3
# Keyboard accessibility of the two interactive widgets:
#   - piano keys must be operable from the keyboard: semantics (role=button),
#     aria-labels, roving tabindex (exactly one tab stop), arrow navigation
#     between keys, Enter audits a note.
#   - token chips in the playback strip must be keyboard-reachable and
#     activatable: role=button + aria-label, roving tabindex with arrow
#     navigation, Enter = "play from here" (same as mouse click).
#   - Space is NEVER captured locally by either widget: it is the global
#     Pause/Continue shortcut everywhere (a token/key click on Space used to
#     mash with the global handler and leak a short faint note).
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
                labelled: labelled.length, afterArrow: null, voiceAfterEnter: null,
                spacePaused: null, spaceClicked: null, spaceVoices: null };
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
  // Enter audits the note: a voice must be built (OCA_DEBUG.liveVoiceCount()).
  const before = window.OCA_DEBUG.liveVoiceCount ? window.OCA_DEBUG.liveVoiceCount() : null;
  focusedKey.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
  out.voiceAfterEnter = window.OCA_DEBUG.liveVoiceCount ? window.OCA_DEBUG.liveVoiceCount() : null;
  out.voiceBefore = before;
  out.curBefore = document.activeElement ? document.activeElement.dataset.note : null;
  // Space must NOT audition, must NOT click the key: it belongs to the global
  // play/pause shortcut (pause/continue), consistently everywhere.
  if (typeof stopMelody === 'function') { try { stopMelody(); } catch (e) {} }
  if (typeof playMelody === 'function') playMelody(0);
  let spaceClicked = false;
  const spy = () => { spaceClicked = true; };
  focusedKey.addEventListener('click', spy, { once: true, capture: true });
  const voicesBefore = window.OCA_DEBUG.liveVoiceCount();
  focusedKey.dispatchEvent(new KeyboardEvent('keydown', {key: ' ', bubbles: true}));
  out.spaceClicked = spaceClicked;
  out.spaceVoices = window.OCA_DEBUG.liveVoiceCount();
  out.spacePaused = typeof isMelodyPaused === 'function' ? isMelodyPaused() : null;
  out.spacePlaying = typeof isMelodyPlaying === 'function' ? isMelodyPlaying() : null;
  out.voicesBefore = voicesBefore;
  if (typeof stopMelody === 'function') { try { stopMelody(); } catch (e) {} }
  return out;
}
"""

TOKENS = """
async () => {
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
  // Arrow-walk mirrors hovering: passing over a playable note must go
  // through the hover-preview path (stub recordable even in headless,
  // where the context stays suspended and the audible half stays silent).
  const hpCalls = [];
  const realHover = window.hoverPreview;
  window.hoverPreview = (i, t) => { hpCalls.push({ i, id: t && t.id }); if (realHover) realHover(i, t); };
  toks[0].focus();
  toks[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowRight', bubbles: true}));
  out.arrow = toks.indexOf(document.activeElement);
  const target = document.activeElement;
  out.arrowNote = target ? (target.getAttribute('aria-label') || '') : null;
  out.hpCalls = hpCalls;
  out.hadPreview = target ? target.classList.contains('now') : false;
  window.hoverPreview = realHover;
  target.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
  out.playedFromToken = window.isMelodyPlaying();
  if (out.playedFromToken && typeof stopMelody === 'function') {
    try { stopMelody(); } catch (e) {}
  }
  // Space must NOT click the token: the global play/pause shortcut owns it.
  if (typeof playMelody === 'function') playMelody(0);
  let spaceClicked = false;
  target.addEventListener('click', () => { spaceClicked = true; }, { once: true, capture: true });
  target.dispatchEvent(new KeyboardEvent('keydown', {key: ' ', bubbles: true}));
  out.spaceClicked = spaceClicked;
  out.spacePaused = typeof isMelodyPaused === 'function' ? isMelodyPaused() : null;
  if (typeof stopMelody === 'function') { try { stopMelody(); } catch (e) {} }
  // --- dwell: hover and arrow-walk must DELAY the note, not fire on touch ---
  out.audio = window.OCA_DEBUG.audioState ? window.OCA_DEBUG.audioState() : null;
  if (out.audio === 'running') {
    const realPn = window.playNote;
    window.__pn = [];
    window.playNote = (...args) => { window.__pn.push(args[0]); return realPn(...args); };
    const rest = (ms) => new Promise(r => setTimeout(r, ms));
    // The gesture click raised the hover quiet-window (hushHovers); settle
    // it out so the probe measures the dwell delay, not the quiet window.
    await rest(500);
    // mouseenter = highlight now, note only after the dwell delay
    toks[1].dispatchEvent(new MouseEvent('mouseenter'));
    out.pnImmediate = window.__pn.length;
    await new Promise(r => setTimeout(r, 450));
    out.pnAfterDwell = window.__pn.length;
    out.pnFirstId = window.__pn[0] || null;
    // graze-and-leave must cancel the pending note (no sound)
    toks[2].dispatchEvent(new MouseEvent('mouseenter'));
    toks[2].dispatchEvent(new MouseEvent('mouseleave'));
    await new Promise(r => setTimeout(r, 400));
    out.pnAfterSkim = window.__pn.length;
    window.playNote = realPn;
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
            # Real user gesture FIRST (click on inert space): unlocks the
            # context so the token-dwell probes can actually audition.
            page.mouse.click(3, 3)
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
            if k["spaceClicked"]:
                failures.append(
                    "piano: Space must not click/audition the key — it is the "
                    "global pause/continue shortcut")
            if k["spaceVoices"] != k["voicesBefore"]:
                failures.append(
                    f"piano: Space must not build a voice "
                    f"({k['voicesBefore']} -> {k['spaceVoices']})")
            if k["spacePaused"] is not True or k["spacePlaying"] is not False:
                failures.append(
                    f"piano: Space must toggle to paused via the global "
                    f"shortcut (paused={k['spacePaused']}, "
                    f"playing={k['spacePlaying']})")

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
                if not t["hadPreview"]:
                    failures.append(
                        "tokens: arrowing over a playable note must light it "
                        "up (focus highlight)")
                hp = t["hpCalls"] or []
                if not hp or hp[0]["i"] != 1:
                    failures.append(
                        f"tokens: arrowing over a playable note must enter "
                        f"the hover-preview path (audition), got {hp!r}")
                if t["playedFromToken"] is not True:
                    failures.append(
                        "tokens: Enter must play from that token "
                        "(isMelodyPlaying() stayed false)")
                if t["spaceClicked"]:
                    failures.append(
                        "tokens: Space must not click the token — the global "
                        "pause/continue shortcut owns Space")
                if t["spacePaused"] is not True:
                    failures.append(
                        f"tokens: Space must pause playback via the global "
                        f"shortcut (paused={t['spacePaused']})")
                if t["audio"] != "running":
                    failures.append(
                        f"tokens: audio context must be running after a real "
                        f"gesture, got {t['audio']!r} (dwell assertions skip)")
                else:
                    if t["pnImmediate"] != 0:
                        failures.append(
                            "tokens: hovering must NOT fire the note "
                            "immediately — it must wait out the dwell delay")
                    if t["pnAfterDwell"] != 1 or \
                            t["pnFirstId"] != t["arrowNote"].replace("Play from ", ""):
                        failures.append(
                            f"tokens: resting on a note must eventually "
                            f"audition it once, got {t['pnAfterDwell']} calls "
                            f"(first {t['pnFirstId']!r})")
                    if t["pnAfterSkim"] != t["pnAfterDwell"]:
                        failures.append(
                            "tokens: grazing a token and leaving must cancel "
                            "the pending note")

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
    print("\nPASS: piano keys and token chips are keyboard citizens; Space is "
          "exclusively the global Pause/Continue shortcut.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
