#!/usr/bin/env python3
# Song .txt round-trip with all attributes (board §9 2026-09-30): Save File
# exports the loaded song as .txt carrying title / tempo / swing + the
# #track blocks + the metronome opt-out, and Load File (or a paste straight
# into #src) brings the session back:
#
#   - the leading "# <title> / # tempo N / # swing N" header block round-
#     trips byte-for-byte and re-drives the dials;
#   - the tick attribute is ASYMMETRIC (Robin, 2026-09-30): ticking is the
#     default, so only "# tick off" is a declaration — the export writes it
#     only when the metronome is off, a load/paste flips #tickMel back off,
#     it is a per-song session override that never writes the user
#     preference, and "# tick on" is neither written nor enforced;
#   - the melody body and every #track block survive verbatim, so parse()
#     and parseTracks() see identical tokens on the way back.
#
# Per-leg fresh page (the boot-tail race, suite convention).
#
#   python3 tests/song_txt_roundtrip.py     # headless & silent

import json
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
TICK_KEY = "oco-bass-c-tick"

from suite_server import start_server

# The #scale select fills only after boot's loadInstrument has fully
# resolved (the instruments_load settled rendezvous).
BOOT_WAIT = ("window.BUILTIN && document.getElementById('scale') && "
             "document.getElementById('scale').options.length > 0")

SONG_BODY = ("A5/4 D5/4 | A5/2\n"
             "#track bass audible 80\n"
             "C2/4 D2/4 | C2/2\n")

SONG_ON = "# Round Trip Song\n# tempo 132\n# swing 25\n" + SONG_BODY
SONG_OFF = "# Round Trip Song\n# tempo 132\n# swing 25\n# tick off\n" + SONG_BODY
MELODY_SIG = "note/A5 note/D5 bar/- note/A5"


def type_song(page, text):
    page.evaluate("""(text) => {
        const ta = document.getElementById('src');
        ta.value = text;
        ta.dispatchEvent(new Event('input'));
    }""", text)


def wait_sig(page, sig):
    # The 200 ms typed-render debounce settles when lastTokens carries the
    # new song — the real rendezvous, never a fixed sleep.
    page.wait_for_function(
        "(sig) => window.lastTokens && "
        "window.lastTokens.map(t => t.type + '/' + "
        "(t.id || t.raw || t.dur || '-')).join(' ') === sig",
        arg=sig, timeout=10000)


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=HEADLESS,
                args=["--autoplay-policy=no-user-gesture-required"])

            # L1 — the export carries every attribute, opt-out included
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            type_song(page, SONG_ON)
            wait_sig(page, MELODY_SIG)
            page.evaluate("document.getElementById('tickMel').checked = false")
            with page.expect_download() as dl_info:
                page.click("#diskSave")
            dl = dl_info.value
            if dl.suggested_filename != "Round Trip Song.txt":
                failures.append(f"L1 filename: {dl.suggested_filename!r}")
            got = Path(dl.path()).read_text(encoding="utf-8")
            if got != SONG_OFF:
                failures.append(f"L1 export must carry the opt-out line:\n{got!r}")
            if errs:
                failures.append(f"L1 page errors: {errs}")
            page.close()

            # L2 — the default (ticking) export writes no tick line at all
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            if page.evaluate("document.getElementById('tickMel').checked") is not True:
                failures.append("L2 boot default must be ticking")
            type_song(page, SONG_ON)
            wait_sig(page, MELODY_SIG)
            with page.expect_download() as dl_info:
                page.click("#diskSave")
            got = Path(dl_info.value.path()).read_text(encoding="utf-8")
            if got != SONG_ON:
                failures.append(f"L2 export must stay tick-free:\n{got!r}")
            if "# tick" in got:
                failures.append(f"L2 must never write '# tick on': {got!r}")
            if errs:
                failures.append(f"L2 page errors: {errs}")
            page.close()

            # L3 — loading the .txt restores the whole session
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            tmp = Path(tempfile.mkdtemp(prefix="song-txt-")) / "roundtrip.txt"
            tmp.write_text(SONG_OFF, encoding="utf-8")
            page.set_input_files("#diskFile", str(tmp))
            page.wait_for_function(
                "document.getElementById('src').value === " + json.dumps(SONG_OFF),
                timeout=10000)
            state = page.evaluate("""() => ({
                title: document.getElementById('title').textContent,
                swing: document.getElementById('swing').value,
                tick: document.getElementById('tickMel').checked,
                pref: localStorage.getItem('oco-bass-c-tick'),
                tokens: JSON.stringify(parse(document.getElementById('src').value)),
                tracks: parseTracks(document.getElementById('src').value)
                    .map(t => [t.name, t.zone, t.vol,
                              t.tokens.map(x => x.type === 'bad' ? 'bad:' + x.raw
                                     : (x.type === 'note' ? x.id : x.type))
                               .join(' ')]),
            })""")
            if state["title"] != "Round Trip Song":
                failures.append(f"L3 title: {state['title']!r}")
            if state["swing"] != "25":
                failures.append(f"L3 swing dial: {state['swing']!r}")
            if state["tick"] is not False:
                failures.append(
                    "L3 '# tick off' must flip the boot-default ticking back "
                    f"off: {state['tick']!r}")
            if state["pref"] is not None:
                failures.append(
                    f"L3 the per-song override must not write the "
                    f"preference: {state['pref']!r}")
            orig = page.evaluate("(s) => JSON.stringify(parse(s))", SONG_ON)
            if state["tokens"] != orig:
                failures.append(
                    f"L3 the tick line must stay comment-only, melody tokens "
                    f"drifted: {state['tokens']!r}")
            if state["tracks"] != [["bass", "audible", 0.8, "C2 D2 bar C2"]]:
                failures.append(f"L3 #track block: {state['tracks']!r}")
            if errs:
                failures.append(f"L3 page errors: {errs}")
            page.close()
            tmp.unlink(missing_ok=True)

            # L4 — a paste into #src drives the tick line through render
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            if page.evaluate("document.getElementById('tickMel').checked") is not True:
                failures.append("L4 boot default must be ticking")
            type_song(page, "# Paste Test\nC4 D4")
            wait_sig(page, "note/C4 note/D4")
            tick = page.evaluate("document.getElementById('tickMel').checked")
            if tick is not True:
                failures.append(f"L4 no line must leave tick alone: {tick!r}")
            type_song(page, "# Paste Test\n# tick off\nC4 E4")
            wait_sig(page, "note/C4 note/E4")
            tick = page.evaluate("document.getElementById('tickMel').checked")
            if tick is not False:
                failures.append(
                    f"L4 '# tick off' in the text must switch the metronome "
                    f"off: {tick!r}")
            pref = page.evaluate(f"localStorage.getItem('{TICK_KEY}')")
            if pref is not None:
                failures.append(
                    f"L4 text-driven apply must not write the preference: "
                    f"{pref!r}")
            type_song(page, "# Paste Test\nF4 G4")
            wait_sig(page, "note/F4 note/G4")
            tick = page.evaluate("document.getElementById('tickMel').checked")
            if tick is not False:
                failures.append(
                    f"L4 dropping the line must not reset the state: "
                    f"{tick!r}")
            type_song(page, "# Paste Test\n# tick on\nA4 B4")
            wait_sig(page, "note/A4 note/B4")
            tick = page.evaluate("document.getElementById('tickMel').checked")
            if tick is not False:
                failures.append(f"L4 '# tick on' must never be enforced: {tick!r}")
            pref = page.evaluate(f"localStorage.getItem('{TICK_KEY}')")
            if pref is not None:
                failures.append(f"L4 the preference stayed unwritten: {pref!r}")
            if errs:
                failures.append(f"L4 page errors: {errs}")
            page.close()

            # L5 — the legacy JSON load path carries its tick field. (The
            # JSON swing field is legacy: the trailing render() re-drives the
            # dial from the text, which carries no swing line here, so the
            # dial ends at 0 — pre-existing behavior, not pinned.)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            tmp = Path(tempfile.mkdtemp(prefix="song-txt-")) / "legacy.json"
            tmp.write_text(json.dumps(
                {"melody": "C4 D4\n", "swing": 40, "tick": False}),
                encoding="utf-8")
            page.set_input_files("#diskFile", str(tmp))
            page.wait_for_function(
                r"document.getElementById('src').value === 'C4 D4\n'",
                timeout=10000)
            state = page.evaluate("""() => ({
                tick: document.getElementById('tickMel').checked,
                pref: localStorage.getItem('oco-bass-c-tick'),
            })""")
            if state["tick"] is not False:
                failures.append(f"L5 json tick: {state['tick']!r}")
            if state["pref"] is not None:
                failures.append(f"L5 pref: {state['pref']!r}")
            if errs:
                failures.append(f"L5 page errors: {errs}")
            page.close()
            tmp.unlink(missing_ok=True)

            browser.close()
    finally:
        httpd.shutdown()

    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: the .txt round-trip carries title/tempo/swing/tick + the "
          "#track blocks byte-for-byte; '# tick off' is the only tick "
          "declaration (exported only when off, applied on load/paste without "
          "touching the preference) and '# tick on' is never enforced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
