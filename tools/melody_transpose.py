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


def transpose_body(body, shift):
    """Melody-only mover; headers verbatim, bracket spans stashed verbatim.
    Octave shifts carry letters; other shifts respell via the sharp table."""
    if shift % 12 == 0:
        return SPELL.sub(
            lambda m: m.group(1) + (m.group(2) or "") +
            str(int(m.group(3)) + shift // 12), body)
    stash = []

    def _stash(m):
        stash.append(m.group(0))
        return "\x01%d\x01" % (len(stash) - 1)

    def _edit(line):
        if line.lstrip().startswith("#"):
            return line
        line = re.sub(r"\[[^\]]*\]", _stash, line)
        return SPELL.sub(
            lambda m: _respell(m.group(1), m.group(2), m.group(3), shift),
            line)

    out = [_edit(line) for line in body.split("\n")]
    return re.sub(r"\x01(\d+)\x01", lambda m: stash[int(m.group(1))],
                  "\n".join(out))


def _respell(letter, acc, oct_, shift):
    accn = 1 if acc in ("#", "s") else -1 if acc == "b" else 0
    midi = (int(oct_) + 1) * 12 + PC[letter] + accn + shift
    return NAMES_SHARP[((midi % 12) + 12) % 12] + str(midi // 12 - 1)


def materialize(songs):
    """Fill bodies for entries declaring a derives record and lacking one.

    Byte-equal to the retired hand bodies (tests/twin_derive.py freezes
    them as fixtures; a base-body edit makes those fixtures fail on
    purpose). Idempotent: a body present alongside a derives record stays
    untouched — the data validator flags that redundancy instead.
    Returns the number of bodies generated.
    """
    n = 0
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
        item["body"] = transpose_body(base["body"], int(dr.get("shift") or 0))
        n += 1
    return n
