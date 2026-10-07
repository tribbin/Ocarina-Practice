#!/usr/bin/env python3
# Song data split (board §5 2026-10-07): a song's music leaves songs.json and
# lives in its own .txt file under songs/, referenced by the record's `file`
# field; the loader prefetches every unique file during boot and materializes
# the bodies (variant records share the base's file through their `derives`
# shift, the server-side twin), while name/group/intended and friends stay
# JSON metadata and the .txt headers own the music attrs (tempo/meter/swing/
# tick — text-first: the file's own declaration wins).
#
#   - a file-referenced record materializes its body byte-equal to the file
#     text; no `file`/`derives` bookkeeping leaks into the published BUILTIN
#     shape (name/group/body/...);
#   - loading the previewed song applies the FILE's own play headers: the
#     dropdown name stays JSON-authoritative (it may differ from the file's
#     title), tempo/meter/swing come off the text first, and "# tick off"
#     flips the metronome through on-load application (never the preference);
#   - a derives record derives its body from the base file's CONTENT (the
#     leading header block excluded) and inherits the base's music attrs;
#   - a .txt-only edit on disk reaches a resumed app: the resume freshness
#     check extends to the bodies even though songs.json is unchanged;
#   - the shipped inline-body corpus keeps materializing identically.
#
# Legs L1-L4 doctor their own fixture records into the served tree (pristine
# restore in finally, per-leg fresh context). L5 boots the real corpus.
#
#   python3 tests/song_files.py     # headless & silent

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv

from suite_server import start_server

# The #scale select fills only after boot's loadInstrument has fully
# resolved (the instruments_load settled rendezvous).
BOOT_WAIT = ("window.BUILTIN && document.getElementById('scale') && "
             "document.getElementById('scale').options.length > 0")

# The fixture record ids/names are deliberately outside the shipped corpus
# keys so the doctoring can never collide with real songs.
FIX_ID = "songfile-fixture-a"
FIX_DER_ID = "songfile-fixture-a-down2"
FIX_NAME = "Songfile Fixture A"
FIX_DER_NAME = "Songfile Fixture A (down 2)"
FIX_FILE = "songs/songfile-fixture.txt"

# In-range melody ids: the fixture must survive fillLibrary's hidden filter
# for the boot ocarina (an out-of-range body would vanish from the dropdown
# and the load leg would miss it).
FIX_MELODY = "A5/2 D5/4 E5/4"
FIX_RAW = ("# " + FIX_NAME + "\n"
           "# tempo 121\n"
           "# meter 3/4\n"
           "# swing 40\n"
           "# tick off\n"
           "\n"
           + FIX_MELODY + "\n")
# The loader strips the leading title line and rewrites the headers from the
# values it read off the text (JSON name stays the editor title): with the
# fixture's equal name the editor text is byte-identical to the file.
FIX_EXPECTED_SRC = FIX_RAW


def load_songs():
    return json.loads((ROOT / "songs.json").read_text(encoding="utf-8"))


def write_songs(d):
    (ROOT / "songs.json").write_text(
        json.dumps(d, separators=(",", ":")), encoding="utf-8")


def doctor_fixture(entries, txt):
    # Write the fixture .txt + extend songs.json with the file-referenced
    # records. Returns the pristine songs.json bytes for the finally restore.
    pristine = (ROOT / "songs.json").read_bytes()
    d = load_songs()
    d.update(entries)
    write_songs(d)
    f = ROOT / FIX_FILE
    f.parent.mkdir(exist_ok=True)
    f.write_text(txt, encoding="utf-8")
    return pristine


def fixture_entries():
    return {
        FIX_ID: {"name": FIX_NAME, "group": "Other", "file": FIX_FILE},
        FIX_DER_ID: {"name": FIX_DER_NAME, "group": "Other",
                     "derives": {"key": FIX_ID, "shift": -2}},
    }


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=HEADLESS,
                args=["--autoplay-policy=no-user-gesture-required"])

            # L5 first (no doctoring): the shipped corpus materializes from
            # its songs/*.txt files into BUILTIN unchanged.
            ctx = browser.new_context()
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(BOOT_WAIT, timeout=30000)
            shipped = load_songs()
            for probe in ("song-of-storms", "song-of-time"):
                f = shipped.get(probe, {}).get("file")
                if isinstance(f, str) and f:
                    want = (ROOT / f).read_text(encoding="utf-8")
                else:
                    want = shipped.get(probe, {}).get("body")
                got = page.evaluate(
                    "(k) => BUILTIN[k] ? BUILTIN[k].body : null", probe)
                if got != want:
                    failures.append(
                        f"L5 shipped corpus regression: {probe} body "
                        f"changed (want {len(want or '')} bytes, got "
                        f"{len(got or '')})")
            if errs:
                failures.append(f"L5 page errors: {errs}")
            ctx.close()

            pristine = doctor_fixture(fixture_entries(), FIX_RAW)
            try:
                # L1 — materialize: the body is byte-equal to the file text;
                # no file/derives bookkeeping leaks into BUILTIN.
                ctx = browser.new_context()
                page = ctx.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                page.goto(base)
                page.wait_for_function(BOOT_WAIT, timeout=30000)
                body = page.evaluate("(k) => BUILTIN[k] && BUILTIN[k].body",
                                     FIX_ID)
                if body != FIX_RAW:
                    failures.append(
                        f"L1 the body must be byte-equal to the file text:\n"
                        f"want {FIX_RAW!r}\ngot {body!r}")
                rec = page.evaluate(
                    "(k) => { const b = BUILTIN[k]; return b ? "
                    "{file: b.file, derives: b.derives} : null; }", FIX_ID)
                if rec is None or rec.get("file") is not None or \
                        rec.get("derives") is not None:
                    failures.append(
                        f"L1 the file/derives records must leave BUILTIN: "
                        f"{rec!r}")
                der = page.evaluate("(k) => BUILTIN[k] && BUILTIN[k].body",
                                    FIX_DER_ID)
                want_der = "G5/2 C5/4 D5/4"
                if der != want_der:
                    failures.append(
                        f"L1 the derives variant must derive from the base "
                        f"file's content (leading header block excluded):\n"
                        f"want {want_der!r}\ngot {der!r}")
                if errs:
                    failures.append(f"L1 page errors: {errs}")
                ctx.close()

                # L2 — the load drives the file's own play headers; the
                # dropdown name (JSON) stays the editor title.
                ctx = browser.new_context()
                page = ctx.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                page.goto(base)
                page.wait_for_function(BOOT_WAIT, timeout=30000)
                page.evaluate(f"BUILTIN[{FIX_ID!r}] && fillLibrary()")
                src = page.evaluate(
                    f"""() => {{
                      const sel = document.getElementById('scale');
                      sel.value = {FIX_ID!r};
                      sel.dispatchEvent(new Event('change'));
                      return document.getElementById('src').value;
                    }}""")
                if src != FIX_EXPECTED_SRC:
                    failures.append(
                        f"L2 the loaded editor text must carry the file's "
                        f"own header block under the JSON name:\nwant "
                        f"{FIX_EXPECTED_SRC!r}\ngot {src!r}")
                state = page.evaluate("""() => ({
                    tick: document.getElementById('tickMel').checked,
                    pref: localStorage.getItem('oco-bass-c-tick'),
                    swing: document.getElementById('swing').value,
                })""")
                if state["tick"] is not False:
                    failures.append(
                        f"L2 '# tick off' in the file must switch the "
                        f"metronome off: {state['tick']!r}")
                if state["pref"] is not None:
                    failures.append(
                        f"L2 the per-song override must not write the "
                        f"preference: {state['pref']!r}")
                if state["swing"] != "40":
                    failures.append(
                        f"L2 the file's '# swing 40' must drive the dial: "
                        f"{state['swing']!r}")
                if errs:
                    failures.append(f"L2 page errors: {errs}")
                ctx.close()

                # L3 — the derives variant loads with the base's music attrs
                # (its own content carries none).
                ctx = browser.new_context()
                page = ctx.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                page.goto(base)
                page.wait_for_function(BOOT_WAIT, timeout=30000)
                page.evaluate("fillLibrary()")
                src = page.evaluate(
                    f"""() => {{
                      const sel = document.getElementById('scale');
                      sel.value = {FIX_DER_ID!r};
                      sel.dispatchEvent(new Event('change'));
                      return document.getElementById('src').value;
                    }}""")
                want = ("# " + FIX_DER_NAME + "\n"
                        "# tempo 121\n"
                        "# meter 3/4\n"
                        "# swing 40\n"
                        "# tick off\n"
                        "G5/2 C5/4 D5/4")
                if src != want:
                    failures.append(
                        f"L3 the variant must load the base's attrs over its "
                        f"derived content:\nwant {want!r}\ngot {src!r}")
                if errs:
                    failures.append(f"L3 page errors: {errs}")
                ctx.close()

                # L4 — a .txt-only edit reaches a resumed app (update
                # propagation: Robin 2026-10-07): songs.json stays
                # byte-identical, the resume swaps the body.
                ctx = browser.new_context()
                page = ctx.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                page.goto(base)
                page.wait_for_function(BOOT_WAIT, timeout=30000)
                page.evaluate("fillLibrary()")
                time.sleep(1.1)  # the If-Modified-Since whole-second lesson
                # Guard the swap: if the rewrite is a no-op the leg's
                # wait would pass without any resume ever landing (the
                # boot body already equals the "new" bytes).
                new_raw = FIX_RAW.replace(
                    FIX_MELODY, FIX_MELODY + " C4/2")
                if new_raw == FIX_RAW:
                    failures.append(
                        "L4 the body rewrite must differ from the boot "
                        "bytes (leg self-check)")
                (ROOT / FIX_FILE).write_text(new_raw, encoding="utf-8")
                page.evaluate(
                    "() => document.dispatchEvent"
                    "(new Event('visibilitychange'))")
                try:
                    page.wait_for_function(
                        "(t) => BUILTIN['" + FIX_ID + "'] && "
                        "BUILTIN['" + FIX_ID + "'].body === t",
                        arg=new_raw, timeout=15000)
                except Exception:
                    failures.append(
                        "L4 an app resume must re-fetch the song .txt and "
                        "swap the body when only the file changed "
                        "(songs.json untouched)")
                boot_landed = page.evaluate(
                    "(t) => BUILTIN['" + FIX_ID + "'] && "
                    "BUILTIN['" + FIX_ID + "'].body === t", new_raw)
                if not boot_landed:
                    failures.append(
                        "L4 the resumed body must equal the fresh file bytes")
                if errs:
                    failures.append(f"L4 page errors: {errs}")
                ctx.close()
            finally:
                (ROOT / FIX_FILE).unlink(missing_ok=True)
                (ROOT / "songs.json").write_bytes(pristine)

            browser.close()
    finally:
        httpd.shutdown()

    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: file-referenced songs materialize byte-equal; the file's "
          "own play headers drive the load (name stays JSON); derives "
          "variants use the base's attrs over headerless derived content; "
          "a .txt-only edit reaches a resumed app.");
    return 0


if __name__ == "__main__":
    sys.exit(main())
