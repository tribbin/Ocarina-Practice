#!/usr/bin/env python3
"""Melody-text transposer — the shared engine the derivations run on.

The byte-identity proofs shaped the rule (board §9 2026-09-25): an octave
shift (±12n) CARRIES the base letter and accidental verbatim — Bb5 -12 is
Bb4, never A#4 — which reproduces every shipped hand transcription's own
spelling (eponas' flat-side Bb and sharp-side F#/C# phrases both sit
against C naturals; only per-section intent decides, and only the hand
copy knows). Any other uniform shift respells from exact MIDI through the
sharp table (concerning-hobbits-short-c proven byte-equal under it); the
piece's accidental preferences stay hand-written-body territory. '# ...'
header lines carry music-irrelevant text and pass verbatim, [' ... ']
brackets carry the instrument-support/label spans (stashed out, restored
untouched) — label content is authored and never machine-moved.
"""
import re

NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SPELL = re.compile(r"([A-G])([#bs]?)(\d)")


TRACK_HEADER_RE = re.compile(r"^#[ \t]*track\b[ \t]*(.*?)[ \t]*$", re.I)
TRACK_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def is_track_header(line):
    """True iff the line opens a named track block — the loader's own
    boundary rule (js/parse.js isTrackHeader, board §9 2026-09-28): a valid
    '#track <name> [zone [vol]]' header opens an instrument-pinned layer
    whose stream passes through verbatim (the layer never follows the
    melody's shift); a malformed '#track …' line is comment-shaped and
    changes no boundary."""
    m = TRACK_HEADER_RE.match(line)
    if not m:
        return False
    fields = [f for f in (m.group(1) or "").split() if f]
    name = fields[0] if fields else ""
    zone, vol = "audible", None
    if len(fields) >= 2 and re.fullmatch(r"\d{1,3}", fields[1]):
        vol = fields[1]
    elif len(fields) >= 2:
        zone = fields[1]
    if len(fields) == 3:
        vol = fields[2]
    if vol is not None and (not re.fullmatch(r"\d{1,3}", vol)
                            or not 1 <= int(vol) <= 100):
        vol = None
    return bool(TRACK_NAME_RE.match(name) and zone in ("audible", "zen")
                and len(fields) <= 3
                and (len(fields) < 2 or vol is not None or fields[1] == zone)
                and (len(fields) != 3 or vol is not None))


def transpose_body(body, shift):
    """Melody-only mover; headers verbatim, bracket spans stashed verbatim.
    Octave shifts carry letters; other shifts respell via the sharp table.
    A valid '#track' header's stream stays verbatim (instrument-pinned,
    Robin 2026-09-28); a malformed one stays comment-shaped."""
    stash = []

    def _stash(m):
        stash.append(m.group(0))
        return "\x01%d\x01" % (len(stash) - 1)

    octave = shift % 12 == 0

    def _pitch(m):
        if octave:
            return m.group(1) + (m.group(2) or "") + \
                str(int(m.group(3)) + shift // 12)
        return _respell(m.group(1), m.group(2), m.group(3), shift)

    in_track = False

    def _edit(line):
        nonlocal in_track
        if in_track:
            return line
        if line.lstrip().startswith("#"):
            if is_track_header(line):
                in_track = True
            return line
        line = re.sub(r"\[[^\]]*\]", _stash, line)
        return SPELL.sub(_pitch, line)

    out = [_edit(line) for line in body.split("\n")]
    return re.sub(r"\x01(\d+)\x01", lambda m: stash[int(m.group(1))],
                  "\n".join(out))


def _respell(letter, acc, oct_, shift):
    accn = 1 if acc in ("#", "s") else -1 if acc == "b" else 0
    midi = (int(oct_) + 1) * 12 + PC[letter] + accn + shift
    return NAMES_SHARP[((midi % 12) + 12) % 12] + str(midi // 12 - 1)


def headerless_content(text):
    """The bare notation after a file's leading '# ...' header block.

    Mirrors the loader's headerlessContent (js/library.js): the file ships a
    title/meta header block, a blank separator, then the notation; the block
    and the blank separator are file decoration and leave. A base body that
    is still a hand body inline in songs.json (transition shape) starts with
    the notation itself and passes through unchanged.
    """
    lines = str(text or "").split("\n")
    h = 0
    while h < len(lines) and lines[h].strip().startswith("#"):
        h += 1
    out = "\n".join(lines[h:])
    out = re.sub(r"^[ \t]*\n", "", out)
    out = re.sub(r"\n+$", "", out)
    return out


def load_file_bodies(songs, root=None):
    """Read every record's `file` body off disk (board §5 2026-10-07).

    songs.json keeps metadata only; the song lives in songs/<id>.txt as the
    app exports it (title/tempo/meter/swing/tick header block, blank line,
    the notation verbatim). Returns the number of bodies loaded.
    """
    from pathlib import Path
    root = root or Path(__file__).resolve().parent.parent
    n = 0
    for item in songs.values():
        f = item.get("file") if isinstance(item, dict) else None
        if isinstance(f, str) and f:
            item["body"] = (root / f).read_text(encoding="utf-8")
            n += 1
    return n


def materialize(songs, root=None):
    """Fill variant bodies: file-backed bases first, then derive.

    Byte-equal to the retired hand bodies (tests/twin_derive.py freezes
    them as fixtures; a base-body edit makes those fixtures fail on
    purpose). The derive input is the base file's CONTENT — its leading
    header block excluded via the loader's own split — so a variant body
    stays notation-shaped whatever its base file's header block says.
    Idempotent: a body present alongside a derives record stays untouched
    — the data validator flags that redundancy instead. Returns the number
    of bodies generated. Passing root also loads file bodies (the gen
    stage-in loads them explicitly; direct callers of materialize may rely
    on the lazy load here).
    """
    n = 0
    if any((item.get("file") if isinstance(item, dict) else None)
           and not isinstance(item.get("body"), str)
           for item in songs.values()):
        load_file_bodies(songs, root)
    for key, item in songs.items():
        dr = item.get("derives")
        if not isinstance(dr, dict):
            continue
        body = item.get("body")
        if isinstance(body, str) and body.strip():
            continue
        base = songs.get(dr.get("key"))
        if not base or base.get("derives") or \
                not isinstance(base.get("body"), str):
            continue  # bad records are the validator's catch, not a crash
        content = base["body"] if not base.get("file") \
            else headerless_content(base["body"])
        item["body"] = transpose_body(content, int(dr.get("shift") or 0))
        n += 1
    return n
