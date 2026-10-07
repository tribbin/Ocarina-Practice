#!/usr/bin/env python3
# Twin derivations (Robin, board §9 2026-09-25): the proven twins derive
# AT LOAD — their hand-written bodies left songs.json and the loader
# materializes each from its base body + declared uniform shift,
# byte-equal. The byte-identity proofs shaped the engine: OCTAVE shifts
# carry the base letter + accidental verbatim (Bb5 -12 is Bb4 — the flat
# orthography of eponas' hand copy cannot come from a midi respell until
# per-section intent is machine-readable), other shifts respell through
# the sharp table (proven on concerning-hobbits-short-c). This suite IS
# the guard: the fixtures are the retired hand bodies, frozen at the
# derivation commit — a future edit to any BASE body changes what the
# loader generates for its variants, so the fixtures fail on purpose and
# force a manual revisit of the derivation.
#
# Derived census (byte-identical proofed before the bodies left):
#   song-of-time-bass          = song-of-time             -12
#   sarias-song-bass           = sarias-song             -12
#   botw-theme-down3           = botw-theme              -12
#   concerning-hobbits-short-c = concerning-hobbits-short  -2 (sharp table)
#
# HELD hand-written (authored content a shift cannot know, Robin 2026-09-25):
#   botw-theme-bass — key-name bracket labels ("Opening (F minor)"...), the
#     split "Ramping up opening (C major)" label line, flat orthography;
#   eponas-song-bass — one bracket label ("A2" vs the base's "A1") plus the
#     same hand-spelling story: flat-side Bb beside sharp-side F#/C#,
#     both against C naturals.
#   song-of-storms-bass — its own arrangement (Robin, 2026-10-02): the lead
#     sits an octave down only for the first half, and its bass track
#     rests where the held B4 beat against the low A4/D5.
# kokiri-forest is no twin (audit refusal-free, NOT-ALIGNED).
#
#   python3 tests/twin_derive.py        # headless & silent

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent

# Robin 2026-09-28: "Don't drop the contrabass down an octave" — a track
# block is an instrument-pinned layer (the 11-hole contrabass window), so
# the derive hands it through VERBATIM and shifts only the melody stream.
# The frozen tail below is the block byte-equal as shipped in sarias-song's
# base body.
SARIAS_CONTRABASS = (
'| F3/8 A3/4.',
'| F3/8 A3/4.',
'| F3/8 A3/4.',
'| F3/8 A3/4.',
'| E3/8 G3/4.',
'| E3/8 G3/4 C3/8',
'| C3/8 G3/4.',
'| E3/8 G3/4 C3/8',
'| C3/8 A3/4.',
'| F3/8 A3/4.',
'| F3/8 A3/4.',
'| F3/8 A3/4.',
'| E3/8 G3/4.',
'| E3/8 G3/4 C3/8',
'| E3/8 G3/4.',
'| E3/8 G3/4 E3/8',
'| D3/8 F3/8 D3/8 F3/8',
'| G3/8 D3/8 G3/8 D3/8',
'| C3/8 E3/8 C3/8 E3/8',
'| A3/8 E3/8 A3/8 E3/8',
'| D3/8 F3/8 D3/8 F3/8',
'| G3/8 D3/8 G3/8 D3/8',
'| C3/8 E3/8 C3/8 E3/8',
'| A3/8 E3/8 A3/8 E3/8',
'| D3/8 F3/8 D3/8 F3/8',
'| G3/8 D3/8 G3/8 D3/8',
'| C3/8 E3/8 C3/8 E3/8',
'| A3/8 E3/8 A3/8 E3/8',
'| D3/8 F3/4 r/8',
'| D3/8 F3/4 r/8',
'| C3/8 G3/4 r/8',
'| C3/8 G3/4 r/8',
'| E3/8 A3/8 r/8 A3/8',
'| E3/8 A3/8 r/8 A3/8',
'| E3/8 G#3/4 E3/8',
'| E3/8 r/8 E3/8 r/8',
)

DERIVES = [
    {
        "key": 'song-of-time-bass',
        "base": 'song-of-time',
        "shift": -12,
        "fixture": '|["Opening"] A4/4. D4/2. F4/4.\n| A4/4. D4/2. F4/4.\n| A4/8. C5/8. B4/4. G4/4. F4/8. G4/8.\n| A4/4. D4/4. C4/8. E4/8. D4/4.\n| -/1\n\n|["Middle repeat 1"] D4/8. C4/8. E4/4. C4/4. E4/8. F4/8.\n| D4/1\n| D4/8. C4/8. E4/4. C4/4. F4/8. G4/8.\n| D4/1\n| A4/8. C5/8. B4/4. C5/4. A4/4.\n| C5/4. G4/4. A4/4. D4/8. C4/8.\n| E4/4. D4/1 -/8\n| F4/8. G4/8. F4/4. G4/4. E4/8. C4/8.\n| F4/8. E4/8. D4/1 -/8\n\n|["Middle repeat 2"] D4/8. C4/8. E4/4. C4/4. E4/8. F4/8.\n| D4/1\n| D4/8. C4/8. E4/4. C4/4. F4/8. G4/8.\n| D4/1\n| A4/8. C5/8. B4/4. C5/4. A4/4.\n| C5/4. G4/4. A4/4. D4/8. C4/8.\n| E4/4. D4/1 -/8\n| F4/8. G4/8. F4/4. G4/4. E4/8. C4/8.\n| F4/8. E4/8. D4/1 -/8\n\n|["End"] A4/4. D4/2. F4/4.\n| A4/4. D4/2. F4/4.\n| A4/8. C5/8. B4/4. G4/4. F4/8. G4/8.\n| A4/4. D4/4. C4/8. E4/8. D4/4.\n| -/1.',
    },
    {
        "key": 'sarias-song-bass',
        "base": 'sarias-song',
        "shift": -12,
        "fixture": 'F4/8! A4/8! B4/4 | F4/8! A4/8! B4/4 |\nF4/8! A4/8! B4/8 E5/8 | D5/4 B4/8 C5/8 |\nB4/8 G4/8 E4/4 | -/4. D4/8 |\nE4/8 G4/8 E4/4 | -/2 |\nF4/8! A4/8! B4/4 | F4/8! A4/8! B4/4 |\nF4/8! A4/8! B4/8 E5/8 | D5/4 B4/8 C5/8 |\nE5/8 B4/8 G4/4 | -/4. B4/8 |\nG4/8 D4/8 E4/4 | -/2 |\nD4/8 E4/8 F4/4 | G4/8 A4/8 B4/4 |\nC5/8 B4/8 E4/4 | -/2 |\nD4/8 E4/8 F4/4 | G4/8 A4/8 B4/4 |\nC5/8 D5/8 E5/4 | -/2 |\nD4/8 E4/8 F4/4 | G4/8 A4/8 B4/4 |\nC5/8 B4/8 E4/4 | -/2 |\nD4/8 C4/8 F4/8 E4/8 | G4/8 F4/8 A4/8 G4/8 |\nB4/8 A4/8 C5/8 B4/8 | D5/8 C5/8 E5/16 ~ F5/8 D5/16 |\nE5/2 | -/2 | r/2 | r/2'
                   + "\n\n#track contrabass audible 70\n"
                   + "\n".join(SARIAS_CONTRABASS),
    },
    {
        "key": 'botw-theme-down3',
        "base": 'botw-theme',
        "shift": -12,
        "fixture": '|["Opening"] A5/4. B5/8 C6/4\n| A5 G5 F5\n| -/2 E5\n| D5/2. -/4 r/4\n| A5/4. B5/8 C6/4\n| A5 G5 F5\n| G5/2 A5\n| -/2.\n\n|["Slow opening"] r/2 F4/8 C5/8\n| C5/8 D#4/8 F4/2\n| C5/8 G4/8 G#4 A#4\n| C5/8 F4/8 F5/4. D#5/8\n| C5/2 F4/8 D5/8\n| C5/2.\n| -/2 F4/8 D5/8\n| -/8 C5/8 -/2\n| -/2.\n\n# tempo 104\n|["Ramping up opening"] C#5/4. D5/8 E5/4\n| C#5/4 B4/4 A4/4\n|  -/2 G#4\n| F#4/2.\n| C#5/4. D5/8 E5/4\n| C#5/4 B4/4 A4/4\n| B4/2 C#5/4\n| -/2 A3/8 E4/8\n| D#4/4. A#3/8 D4/8 D#4/8\n| F4/4. D#4/8 F4/8 A#4/8\n| C5/8t F4/8t G4/8t A#4 D5\n| D#5/2.\n| D5/8 D#5/8 F5/2\n| -/2 D#5/8t F5/8t G#5/8t\n| G5/2. | -/2.\n\n|["Main theme body"] E5/8 A4/8 A5/4. G5/8\n| E5/2.\n| E5/8 G4/8 A4/2\n| E5/8 A#4/8 C5 D5\n| E5/8 A4/8 C6/4. B5/8\n| E5/2.\n| -/2 G5/8 F#5/8\n| -/8 E5/2 -/8\n\n|["Main theme body repeat"] E5/8 A4/8 A5/4. G5/8\n| E5/2.\n| E5/8 G4/8 A4/2\n| E5/8 A#4/8 C5 D5\n| E5/8 A4/8 C6/4. B5/8\n| E5/2.\n| E5/4. F#5/8 G5\n| -/8 A5/2 -/8\n\n|["End"] B4/8 G4/8 A4 A4/8 G4/8\n| B4/8 F#4/8 A4 D5/8 B4/8\n| A4/8 E5/8 E5/8 E5 C5/8\n| D5/8 A5/8 -/4 A4/8 B4/8\n| C5/4. D5/8 E5\n| D5 B5/2 r/1. A4/1. r/1.',
    },
    {
        "key": 'concerning-hobbits-short-c',
        "base": 'concerning-hobbits-short',
        "shift": -2,
        "fixture": 'C5/16 D5/16 E5/8 r/4. E5/8 r/8 E5/8 |\nG5/16t A5/16t G5/16t D5/8 C5/8 D5/8 r/2 |\nG4/16 A4/16 B4/8 r/8 B4/4 C5/8 r/8 A4/8 |\nE4/4 -/16 r/16 G4/8 D4/8. r/4 r/16 |\nr/4 G4/8 B4/8 C5/16 D5/16 E5/8 r/8 E5/8 |\nr/4. G5/8 E5/16t F5/16t E5/16t D5/8 r/8 C5/8 |\nD5/8 B4/8 r/8 B4/16t C5/16t B4/16t A4/4. -/16 r/16 |\nr/4 r/16 E5/16 A5/16 B5/16 C6/4. B5/8 |\n-/4. G5/8 E5/4. F5/16 E5/16 |\nD5/4. C5/16 D5/16 E5/2 |\n-/4. E5/16 F5/16 G5/2 |\nD5/2 C5/16 D5/16 E5/8 r/4 |\nr/8 E5/8 r/8 E5/8 D5/16 E5/16 F#5/8 r/8 F#5/8 |\nr/8 F#5/8 r/8 F#5/8 E5/16 F#5/16 G#5/4 -/16 r/16 |\nG#5/16 r/16 G#5/4 G#5/16 G#5/16 G#5/4. -/16 r/16 | r/2',
    },
]

# The exact open-entry census: these keys derive, nobody else does, the
# held keys keep their hand bodies, and bases never derive themselves.
WANT_DERIVE_KEYS = {d["key"] for d in DERIVES}
HELD_HAND_WRITTEN = ("botw-theme-bass", "eponas-song-bass")


from suite_server import start_server


def main():
    failures = []
    songs = json.loads((ROOT / "songs.json").read_text(encoding="utf-8"))

    # --- data shape (pure python, no browser) ------------------------------
    # The song data split (board §5 2026-10-07): the notation left songs.json
    # into songs/<id>.txt; base records carry the `file` pointer, variant
    # records the derives declaration.
    for d in DERIVES:
        rec = songs.get(d["key"])
        if rec is None:
            failures.append(f"{d['key']}: missing from songs.json")
            continue
        if "body" in rec or "file" in rec:
            failures.append(f"{d['key']}: a derives record is a pointer — "
                            "no hand body, no own file "
                            "(it lives frozen in this suite now)")
        dr = rec.get("derives")
        if not isinstance(dr, dict):
            failures.append(f"{d['key']}: must declare a derives record, "
                            f"got {dr!r}")
            continue
        if dr.get("key") != d["base"]:
            failures.append(f"{d['key']}: derives.key {dr.get('key')!r} "
                            f"!= base {d['base']!r}")
        if dr.get("shift") != d["shift"]:
            failures.append(f"{d['key']}: derives.shift {dr.get('shift')!r} "
                            f"!= the proven {d['shift']}")
        base = songs.get(dr.get("key") or "")
        base_file = (base or {}).get("file")
        if not (isinstance(base_file, str) and base_file and
                (ROOT / base_file).is_file()):
            failures.append(f"{d['key']}: base {dr.get('key')!r} must point "
                            "at its own song .txt file (bases never derive)")
    for held in HELD_HAND_WRITTEN:
        hf = (songs.get(held, {}) or {}).get("file")
        if not (isinstance(hf, str) and hf and (ROOT / hf).is_file()):
            failures.append(f"{held}: the held key keeps its hand body "
                            "under its own song .txt (it is authored "
                            "content, not derivable)")
        if "derives" in songs.get(held, {}):
            failures.append(f"{held}: the held key must not carry a "
                            "derives record")
    for key, item in songs.items():
        if key in WANT_DERIVE_KEYS:
            continue
        if "derives" in item:
            failures.append(f"{key}: carries a derives record outside the "
                            "proven census — the audit must see it first")

    # --- the loader materializes byte-equal bodies --------------------------
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless="--headed" not in sys.argv)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            # The derive finishes inside boot's async tail (materialize runs
            # beside the first instrument install) — wait for the BODIES,
            # not the paper-thin entry publication.
            page.wait_for_function(
                'window.BUILTIN && window.BUILTIN["song-of-time-bass"] && '
                'window.BUILTIN["song-of-time-bass"].body')
            got = page.evaluate(
                "() => Object.fromEntries(Object.entries(window.BUILTIN)"
                ".map(([k, v]) => [k, v.body == null ? null : String(v.body)]))")
            # The strip: no derives record may leak into BUILTIN (the
            # published shape stays name/group/tempo/body/...).
            leaked = page.evaluate(
                "() => Object.entries(window.BUILTIN)"
                ".map(([k, v]) => [k, v.derives]).filter(([, v]) => v)")
            if leaked:
                failures.append(f"BUILTIN leaked derives records: {leaked}")
            for d in DERIVES:
                body = got.get(d["key"])
                if body is None:
                    failures.append(f"{d['key']}: BUILTIN entry missing at "
                                    "boot (initBuiltin materialization?)")
                elif body != d["fixture"]:
                    fail = []
                    gl, wl = body.splitlines(), d["fixture"].splitlines()
                    for i in range(max(len(gl), len(wl))):
                        a = gl[i] if i < len(gl) else "<absent>"
                        b = wl[i] if i < len(wl) else "<absent>"
                        if a != b:
                            fail.append(f"line {i + 1}: got {a!r} want {b!r}")
                    failures.append(
                        f"{d['key']}: generated body diverges from the "
                        f"frozen hand transcription ({len(fail)} lines)\n    "
                        + "\n    ".join(fail[:6]))
            if errs:
                failures.append(f"loader: page errors {errs}")
            browser.close()
    finally:
        httpd.shutdown()

    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: the derive census matches the board's proven classes, the "
          "loader materializes every derived body byte-equal to its frozen "
          "hand transcription, no derives record leaks into BUILTIN, and the "
          f"held keys ({', '.join(HELD_HAND_WRITTEN)}) keep their hand "
          "bodies.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
