#!/usr/bin/env python3
# CI-side data-shape validator for the hand-tuned JSON corpus — pure stdlib,
# no browser, no runtime gate. The app deliberately boot-fails-soft on data
# oddities (loud boot gates stay behind — this corpus is hand-tuned); this
# suite is the CI twin: every structural / cross-reference defect the runtime
# merely survives is a named failure here. Checks:
#
#   JSON parses + NO duplicate object keys (a collapse the plain loader
#     silently "resolves" by keeping the last — silent data loss otherwise)
#   instruments.json: shape, unique ids, declared fingerings/svg/tone files
#     exist (tone absent = the documented deliberate-404s, allowed), tone
#     when present parses with a chambers object, svgWhen rows carry svg +
#     a song/songTitle condition, default id exists
#   fingerings.json per instrument: s-spelled note-id grammar (ids carry an
#     octave and never a display sharp — 'Fs4' not 'F#4', the gen_pages
#     live-boot lesson), unique ids, non-empty display, ascending pitch
#     order, covered arrays reference real hole names, chamber ints,
#     range{low,high} strings
#   songs.json: every entry has name + body, scalar fields typed correctly
#     (the parser owns body grammar; the slug/suffix/chain contract is not
#     duplicated here — tests/shipped_songs.py is that contract's owner)
#
#   python tests/data_validator.py         # sandbox battery + real corpus
#
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NOTE_ID = re.compile(r"^([A-G])([bs]?)(\d)$")
_N = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi_of_id(i):
    letter, acc, oct_ = NOTE_ID.match(i).groups()
    return (int(oct_) + 1) * 12 + _N[letter] + \
        (-1 if acc == "b" else 1 if acc == "s" else 0)


def _no_dup(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError("duplicate key %r" % k)
        obj[k] = v
    return obj


def load_json(path, errors, label):
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        errors.append(f"{label}: unreadable: {e}")
        return None
    try:
        return json.loads(raw, object_pairs_hook=_no_dup)
    except ValueError as e:
        errors.append(f"{label}: not-parsable-json: {e}")
        return None


class V:
    def __init__(self, root):
        self.root = root
        self.errors = []

    def err(self, file, cls, detail):
        self.errors.append(f"{file}: {cls}: {detail}")

    def needs_file(self, rel, declared_by):
        if not (self.root / rel).is_file():
            self.err("instruments.json", "missing-file",
                     f"{rel} (declared by {declared_by})")

    def _check_tone(self, rel, inst_id):
        p = self.root / rel
        if not p.is_file():
            # The documented deliberate 404s: entries may declare tone
            # ahead of the chamber measurements (instruments/README.md).
            return
        tone = load_json(p, self.errors, rel)
        if tone is None:
            return
        if not isinstance(tone, dict) or not isinstance(tone.get("chambers"), dict):
            self.err(rel, "bad-shape",
                     f"tone for {inst_id} needs a chambers object")

    def instruments(self):
        m = load_json(self.root / "instruments.json", self.errors, "instruments.json")
        if m is None:
            return
        if not isinstance(m, dict) or not isinstance(m.get("instruments"), list) \
                or not m["instruments"]:
            self.err("instruments.json", "bad-shape",
                     "needs a non-empty instruments list")
            return
        if not isinstance(m.get("default"), str):
            self.err("instruments.json", "bad-shape", "needs a default id")
        seen = set()
        for row in m["instruments"]:
            if not isinstance(row, dict):
                self.err("instruments.json", "bad-shape", "row is not an object")
                continue
            iid = row.get("id")
            if not isinstance(iid, str) or not iid:
                self.err("instruments.json", "bad-shape",
                         f"row without an id: {row!r}")
                continue
            if iid in seen:
                self.err("instruments.json", "duplicate-id", iid)
            seen.add(iid)
            fing = row.get("fingerings")
            if not isinstance(fing, str) or not fing:
                self.err("instruments.json", "bad-shape", f"{iid}: no fingerings path")
            else:
                self.needs_file(fing, iid)
                self.fingerings(self.root / fing, fing)
            svg = row.get("svg")
            if not isinstance(svg, str) or not svg:
                self.err("instruments.json", "bad-shape", f"{iid}: no svg path")
            else:
                self.needs_file(svg, iid)
            tone = row.get("tone")
            if tone is not None:
                if not isinstance(tone, str) or not tone:
                    self.err("instruments.json", "bad-shape", f"{iid}: bad tone path")
                else:
                    self._check_tone(tone, iid)
            when = row.get("svgWhen")
            if when is not None:
                if not isinstance(when, list):
                    self.err("instruments.json", "bad-shape",
                             f"{iid}: svgWhen is not a list")
                else:
                    for r in when:
                        if not isinstance(r, dict) or not isinstance(r.get("svg"), str):
                            self.err("instruments.json", "bad-shape",
                                     f"{iid}: svgWhen row without svg: {r!r}")
                            continue
                        self.needs_file(r["svg"], iid + " svgWhen")
                        if not (isinstance(r.get("song"), str)
                                or isinstance(r.get("songTitle"), str)):
                            self.err("instruments.json", "unanchored-svgWhen-row",
                                     f"{iid}: row must name song or songTitle")
                        for key in ("song", "songTitle", "theme"):
                            if key in r and not isinstance(r[key], str):
                                self.err("instruments.json", "bad-shape",
                                         f"{iid}: svgWhen {key} must be a string")
        if isinstance(m.get("default"), str) and m["default"] not in seen:
            self.err("instruments.json", "bad-default",
                     f"default {m['default']!r} is no instrument id")

    def fingerings(self, p, label):
        d = load_json(p, self.errors, label)
        if d is None or not isinstance(d, dict):
            return
        notes = d.get("notes")
        if not isinstance(notes, list) or not notes:
            self.err(label, "no-notes", "needs a non-empty notes list")
            return
        holes = d.get("holes")
        hole_names = set(holes) if isinstance(holes, dict) else None
        seen = set()
        prev_midi = None
        for n in notes:
            if not isinstance(n, dict):
                self.err(label, "bad-shape", "note row is not an object")
                continue
            nid = n.get("id")
            if not isinstance(nid, str) or not NOTE_ID.match(nid):
                self.err(label, "bad-note-id",
                         f"{nid!r} (ids are s-spelled like 'Fs4' with octave)")
                continue
            if nid in seen:
                self.err(label, "duplicate-note-id", nid)
            seen.add(nid)
            disp = n.get("display")
            if not isinstance(disp, str) or not disp:
                self.err(label, "no-display", nid)
            midi = midi_of_id(nid)
            if prev_midi is not None and midi <= prev_midi:
                self.err(label, "out-of-order", f"{nid} after {prev_midi}")
            prev_midi = midi
            chamber = n.get("chamber")
            if chamber is not None and not isinstance(chamber, int):
                self.err(label, "bad-chamber", f"{nid}: {chamber!r} is not an int")
            covered = n.get("covered")
            if covered is not None:
                if not isinstance(covered, list) \
                        or any(not isinstance(c, str) for c in covered):
                    self.err(label, "bad-covered", f"{nid}")
                elif hole_names is not None:
                    for c in covered:
                        if c not in hole_names:
                            self.err(label, "unknown-hole", f"{nid} covers {c!r}")
        rng = d.get("range")
        if rng is not None and (not isinstance(rng, dict)
                                or not isinstance(rng.get("low"), str)
                                or not isinstance(rng.get("high"), str)):
            self.err(label, "bad-range", "range needs low/high strings")

    def songs(self):
        s = load_json(self.root / "songs.json", self.errors, "songs.json")
        if s is None or not isinstance(s, dict):
            return
        for key, item in s.items():
            if not isinstance(item, dict):
                self.err("songs.json", "bad-shape", f"{key} is not an object")
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name:
                self.err("songs.json", "no-name", key)
            body = item.get("body")
            if not isinstance(body, str) or not body.strip():
                self.err("songs.json", "no-body", key)
            for field in ("hidden", "tick"):
                if field in item and not isinstance(item[field], bool):
                    self.err("songs.json", "bad-field", f"{key}: {field} must be bool")
            for field in ("tempo", "swing"):
                if field in item and (isinstance(item[field], bool)
                                      or not isinstance(item[field], (int, float))):
                    self.err("songs.json", "bad-field", f"{key}: {field} must be a number")
            if "group" in item and not isinstance(item["group"], str):
                self.err("songs.json", "bad-field", f"{key}: group must be a string")


def validate(root):
    v = V(root)
    v.instruments()
    v.songs()
    return v.errors


# --- sandbox battery: every defect class must be caught with its name ------

GOOD_MANIFEST = """{
  "default": "alpha",
  "instruments": [
    {"id": "alpha", "type": "T", "version": "V", "range": "C4?C6",
     "fingerings": "instruments/alpha/fingerings.json",
     "svg": "instruments/alpha/ocarina-template.svg",
     "svgWhen": [{"svg": "instruments/alpha/special.svg", "song": "some-song"}],
     "tone": "instruments/alpha/tone.json"}
  ]
}"""

GOOD_FINGERINGS = """{
  "instrument": "Alpha", "range": {"low": "C4", "high": "C5"},
  "holes": {"hole-a": {"hand": "left", "finger": "index", "chamber": 1}},
  "chambers": {"1": {"blow": "blow-ch1", "color": "#111111"}},
  "notes": [
    {"id": "C4", "display": "C4", "chamber": 1, "covered": ["hole-a"]},
    {"id": "Cs4", "display": "C4sharp", "chamber": 1, "covered": []},
    {"id": "D4", "display": "D4", "chamber": 1, "covered": ["hole-a"]}
  ]
}"""

GOOD_SONGS = """{
  "some-song": {"name": "Some Song", "group": "Other",
                "tempo": 120, "body": "C4 D4 E4"},
  "hidden-one": {"name": "Hidden", "group": "Other", "hidden": true,
                 "body": "C4"}
}"""

CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


def write(tmp, rel, text):
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def good_sandbox(td):
    tmp = Path(td)
    write(tmp, "instruments.json", GOOD_MANIFEST)
    write(tmp, "instruments/alpha/fingerings.json", GOOD_FINGERINGS)
    write(tmp, "instruments/alpha/ocarina-template.svg", "<svg/>")
    write(tmp, "instruments/alpha/special.svg", "<svg/>")
    write(tmp, "songs.json", GOOD_SONGS)
    return tmp


def expect_hits(errors, needle, cls, opposite=False):
    hits = [e for e in errors if cls in e and needle in e]
    if opposite:
        if hits:
            raise AssertionError(f"{cls} flagged for {needle!r} (must not): {hits}")
    elif not hits:
        raise AssertionError(f"{cls} not caught for {needle!r}: {errors}")
    return hits


@case("good sandbox corpus is clean")
def v0():
    with tempfile.TemporaryDirectory() as td:
        errs = validate(good_sandbox(td))
        if errs:
            raise AssertionError(f"good corpus flagged: {errs}")


@case("duplicate JSON keys caught on both data files")
def v1():
    with tempfile.TemporaryDirectory() as td:
        tmp = good_sandbox(td)
        write(tmp, "instruments.json",
              GOOD_MANIFEST.replace('"instruments": [',
                                    '"instruments": ["junk"], "instruments": ['))
        expect_hits(validate(tmp), "instruments", "duplicate")
        write(tmp, "instruments.json", GOOD_MANIFEST)
        write(tmp, "songs.json", GOOD_SONGS.replace(
            '"tempo": 120,', '"tempo": 120, "tempo": 121,'))
        expect_hits(validate(tmp), "songs.json", "duplicate")


@case("unique instrument ids enforced")
def v2():
    with tempfile.TemporaryDirectory() as td:
        tmp = good_sandbox(td)
        write(tmp, "instruments.json", GOOD_MANIFEST.replace(
            '"tone": "instruments/alpha/tone.json"}',
            '"tone": "instruments/alpha/tone.json"},\n'
            '    {"id": "alpha", "type": "T",'
            ' "fingerings": "instruments/alpha/fingerings.json",'
            ' "svg": "instruments/alpha/ocarina-template.svg"}'))
        expect_hits(validate(tmp), "alpha", "duplicate-id")


@case("missing declared files named with their declarer")
def v3():
    with tempfile.TemporaryDirectory() as td:
        tmp = good_sandbox(td)
        (tmp / "instruments/alpha/fingerings.json").unlink()
        errs = validate(tmp)
        fin = [e for e in errs if "missing-file" in e and "fingerings.json" in e
               and "alpha" in e]
        assert fin, errs


@case("bad note-id grammar caught (display sharp refused)")
def v4():
    with tempfile.TemporaryDirectory() as td:
        tmp = good_sandbox(td)
        write(tmp, "instruments/alpha/fingerings.json",
              GOOD_FINGERINGS.replace('"D4", "display": "D4"', '"D#4", "display": "D4"'))
        expect_hits(validate(tmp), "D#4", "bad-note-id")


@case("duplicate note id caught")
def v5():
    with tempfile.TemporaryDirectory() as td:
        tmp = good_sandbox(td)
        write(tmp, "instruments/alpha/fingerings.json",
              GOOD_FINGERINGS.replace(
                  '"D4", "display": "D4", "chamber": 1, "covered": ["hole-a"]',
                  '"Cs4", "display": "D4", "chamber": 1, "covered": ["hole-a"]'))
        expect_hits(validate(tmp), "Cs4", "duplicate-note-id")


@case("out-of-order chart pitch caught")
def v6():
    with tempfile.TemporaryDirectory() as td:
        tmp = good_sandbox(td)
        write(tmp, "instruments/alpha/fingerings.json",
              GOOD_FINGERINGS.replace(
                  '"D4", "display": "D4", "chamber": 1, "covered": ["hole-a"]',
                  '"B3", "display": "D4", "chamber": 1, "covered": ["hole-a"]'))
        expect_hits(validate(tmp), "B3", "out-of-order")


@case("covered arrays must name real holes")
def v7():
    with tempfile.TemporaryDirectory() as td:
        tmp = good_sandbox(td)
        write(tmp, "instruments/alpha/fingerings.json",
              GOOD_FINGERINGS.replace('"covered": ["hole-a"]',
                                      '"covered": ["ghost-hole"]'))
        expect_hits(validate(tmp), "ghost-hole", "unknown-hole")


@case("tone present-but-corrupt caught; deliberate-absent allowed")
def v8():
    with tempfile.TemporaryDirectory() as td:
        tmp = good_sandbox(td)
        expect_hits(validate(tmp), "tone.json", "tone", opposite=True)
        write(tmp, "instruments/alpha/tone.json", "{ not json")
        expect_hits(validate(tmp), "tone.json", "not-parsable-json")
        write(tmp, "instruments/alpha/tone.json",
              '{"instrument": "x", "chambers": [1]}')
        expect_hits(validate(tmp), "tone.json", "bad-shape")
        write(tmp, "instruments/alpha/tone.json",
              '{"instrument": "x", "chambers": {"1": [{"note": "C4", "f": 261.6}]}}')
        expect_hits(validate(tmp), "tone.json", "tone", opposite=True)


@case("svgWhen rows need svg + a song/songTitle anchor")
def v9():
    with tempfile.TemporaryDirectory() as td:
        tmp = good_sandbox(td)
        write(tmp, "instruments.json", GOOD_MANIFEST.replace(
            ', "song": "some-song"', ''))
        errs = validate(tmp)
        assert any("unanchored-svgWhen-row" in e and "alpha" in e for e in errs), errs
        (tmp / "instruments/alpha/special.svg").unlink()
        errs = validate(tmp)
        assert any("missing-file" in e and "special.svg" in e for e in errs), errs


@case("songs.json entries need name+body and typed scalars")
def v10():
    with tempfile.TemporaryDirectory() as td:
        tmp = good_sandbox(td)
        write(tmp, "songs.json",
              '{"bad": {"group": "Other"}, "empty": {"name": "E", "body": "   "}}')
        errs = validate(tmp)
        assert any("no-name" in e and "bad" in e for e in errs), errs
        assert any("no-body" in e and "empty" in e for e in errs), errs
        write(tmp, "songs.json", '{"t": {"name": "T", "body": "C4", "hidden": "yes"}}')
        expect_hits(validate(tmp), "hidden", "bad-field")


@case("bad default id caught")
def v11():
    with tempfile.TemporaryDirectory() as td:
        tmp = good_sandbox(td)
        write(tmp, "instruments.json",
              GOOD_MANIFEST.replace('"default": "alpha"', '"default": "ghost"'))
        expect_hits(validate(tmp), "ghost", "bad-default")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("== sandbox defect battery", flush=True)
    for name, fn in CASES:
        fn()
        print(f"   PASS {name}", flush=True)

    print("== real corpus", flush=True)
    errs = validate(ROOT)
    if errs:
        print("\nFAIL — the shipped corpus has defect(s):", flush=True)
        for e in errs:
            print("  - " + e, flush=True)
        return 1
    print(f"PASS: instruments.json / songs.json / every fingerings.json validated "
          f"clean ({len(CASES)} sandbox defect classes + the shipped corpus).", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
