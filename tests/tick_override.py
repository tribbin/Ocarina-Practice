#!/usr/bin/env python3
# Tick-override semantics (Robin, IDEAS 2026-09-25): "When a song
# 'overwrites' default about tick on/off, that should not change the
# use-preference. So when switching back to a song without override,
# whatever the user had as preference is applied. However, clicking the
# click button during the override changes (or confirms) the user
# preference."
#
# The contract, pinned here:
#   - a song's own tick declaration is a PER-SONG SESSION OVERRIDE — the
#     landing/switch applies it and never writes the preference;
#   - songs without a declaration apply the stored preference (in-session
#     state carries when nothing is stored yet);
#   - BOTH user channels (the tick button, the settings carrier itself)
#     write the preference — clicking during an override confirms or
#     changes it;
#   - a programmatic song-load application (applySongTick's change
#     dispatch) must NOT write the preference — only user intent does.
#
#   python3 tests/tick_override.py        # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TICK_KEY = "oco-bass-c-tick"


from suite_server import start_server


def landed(song):
    # initBuiltin publishes BUILTIN during boot(), ahead of the await inside
    # loadInstrument. The song's tick override is applied only at the tail,
    # in loadLibraryItem, which also selects #scale. Reading #tickMel before
    # that tail sees the HTML default (checked) and reports a false miss.
    return ("() => { const s = document.getElementById('scale');"
            f" return !!(s && s.value === '{song}'); }}")


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless="--headed" not in sys.argv,
                args=["--autoplay-policy=no-user-gesture-required"])
            errs = []

            def open_page():
                # A fresh context per leg: localStorage is per context, and
                # these legs each describe a visit that has not stored a
                # preference yet. Sharing one context lets an earlier click
                # answer a later landing.
                ctx = browser.new_context()
                page = ctx.new_page()
                page.on("pageerror", lambda e: errs.append(str(e)))
                return ctx, page

            ctx, page = open_page()

            # L1 — the landing override applies and nothing is written
            page.goto(f"{base}/?song=song-of-time&inst=oot-alto-c-12")
            page.wait_for_function(landed("song-of-time"))
            checked = page.evaluate(
                "document.getElementById('tickMel').checked")
            if checked:
                failures.append("the song-of-time tick:false override must "
                                "land the metronome off")
            stored = page.evaluate(f"localStorage.getItem('{TICK_KEY}')")
            if stored is not None:
                failures.append(f"the override must not write the "
                                f"preference, got {stored!r}")
            ctx.close()

            # L2..L3 — one visit: the default, then the user's click
            ctx, page = open_page()
            page.goto(f"{base}/?song=song-of-storms&inst=oot-alto-c-12")
            page.wait_for_function(landed("song-of-storms"))
            # storms carries no tick declaration; nothing stored yet — the
            # in-session default (HTML checked) stands
            if not page.evaluate("document.getElementById('tickMel').checked"):
                failures.append("a no-override song with no stored "
                                "preference keeps the session default on")
            # L3 — the user's click writes the preference
            page.click("#tickBtn")
            # the button mirrors the carrier via the visual sync; read the state
            page.wait_for_function(
                "!document.getElementById('tickMel').checked"
                f" && localStorage.getItem('{TICK_KEY}') === '0'")
            ctx.close()

            # L4 — the override amid a set preference must not eat it
            ctx, page = open_page()
            page.goto(f"{base}/?song=song-of-storms&inst=oot-alto-c-12")
            page.wait_for_function(landed("song-of-storms"))
            page.click("#tickBtn")
            page.wait_for_function(
                f"localStorage.getItem('{TICK_KEY}') === '0'")
            # switch to the override song: session off (override), pref stays
            page.evaluate(
                "() => { const s = document.getElementById('scale');"
                " s.value = 'song-of-time';"
                " s.dispatchEvent(new Event('change',"
                " { bubbles: true })); }")
            page.wait_for_function(
                "!document.getElementById('tickMel').checked")
            stored = page.evaluate(f"localStorage.getItem('{TICK_KEY}')")
            if stored != "0":
                failures.append(f"the override must keep the stored "
                                f"preference, got {stored!r}")
            # and a no-override load applies the user preference again
            page.evaluate(
                "() => { const s = document.getElementById('scale');"
                " s.value = 'major';"
                " s.dispatchEvent(new Event('change',"
                " { bubbles: true })); }")
            page.wait_for_function(
                "!document.getElementById('tickMel').checked")
            ctx.close()

            # L5 — the click DURING the override confirms the preference
            ctx, page = open_page()
            page.goto(f"{base}/?song=song-of-time&inst=oot-alto-c-12")
            page.wait_for_function(landed("song-of-time"))
            page.wait_for_function(
                "() => !document.getElementById('tickMel').checked")
            page.click("#tickBtn")
            page.wait_for_function(
                "document.getElementById('tickMel').checked"
                f" && localStorage.getItem('{TICK_KEY}') === '1'")
            ctx.close()

            # L6 — the programmatic application never writes the pref
            ctx, page = open_page()
            page.goto(f"{base}/?song=song-of-storms&inst=oot-alto-c-12")
            page.wait_for_function(landed("song-of-storms"))
            page.click("#tickBtn")               # user intent off
            page.wait_for_function(
                f"localStorage.getItem('{TICK_KEY}') === '0'")
            page.evaluate(
                "window.applySongTick(true)")    # programmatic on
            page.wait_for_function(
                "document.getElementById('tickMel').checked")
            stored = page.evaluate(f"localStorage.getItem('{TICK_KEY}')")
            if stored != "0":
                failures.append(f"the programmatic application must not "
                                f"write the preference, got {stored!r}")
            ctx.close()

            if errs:
                failures.append(f"page errors: {errs}")
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: the tick contract holds — a song's declaration is an "
          "in-session override that never writes the preference, "
          "no-override songs boot the stored preference, both user "
          "channels write it, and programmatic applications stay silent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
