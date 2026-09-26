#!/usr/bin/env python3
# The MIDI-track audit/rebuild for the MIDI-interpreted Outset twin.
#
# Contract (Robin's field check caught the rotation, 2026-09-26): the track
# block of an interpreted-from-MIDI song must carry each source measure's
# OWN content on the melody's bar lines (measure k -> song bar k, bar-
# relative hit positions unchanged). A window-intersection read is wrong as
# soon as the melody's grid differs from the file's meter by beat
# accumulations: the Outset melody held a 5-beat da-dum at bar 18 while
# the file runs straight 4/4, so every window after it rotated +1 beat and
# the bass sounded off-beat for the rest of the song even though the bar
# sums matched and the engine walk showed 0.000 drift.
#
# Correction 2026-09-26 (Robin's reads): the 5/4 itself was the reduced
# score's engraving error — its fifth beat was the arranger's own extra
# note, absent from the game's file, whose timeline is pure 4/4 (TS 4/4 at
# beat 0 with no meter changes; the tune voice is silent through
# [68, 72.5) and the groove enters exactly at 72). The melody's bar 18 is
# now 4 beats and the app grid equals the file's measure-for-measure: the
# map below carries NO drink and NO cut.
#
# Map encoded here, bar by bar, straight from the file's own evidence:
#   every bar k = file measure k, full hit pattern, positions unchanged
#   (bar 15-18's da-dum measure included; the finale bar 52 = the game's
#   full vamp, so the support continues through the loop seam).
#
# Modes:
#   --check [songs.json path]   compare a songs.json's track block against
#                               the expectation; print bar/offset/expected/
#                               shipped mismatches; exit 1 on any.
#   --emit                      print the EXPECTED raw block (register
#                               projection applied, pre-harmonize) for
#                               splicing.
#
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "midi-to-ocarina-tab" / "scripts"))
from mid2tab import parse_midi, nm

TPQ = 192
MID = ROOT / "research" / "LoZWW_Outset_Island.mid"
SONG = "outset-island-midi"
# the song's melody bar lengths (the shared-clock grid; the parser-verified
# truth lives in tests/shipped_songs's bar contract) — the game's pure 4/4
LENGTHS = [4] * 52
FLAT = {"C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb"}
BAND = 60          # the channel's harp-register doubles (>= C#4) drop
SONGS_PATH = ROOT / "songs.json"

def pnm(m):
    s = nm(m)
    return FLAT.get(s[:-1], s[:-1]) + s[-1]

def project(m):
    pic = m + 24
    if pic < 57:          # below the triple board's A3 floor
        pic = m + 36
    return pnm(pic)

def file_hits():
    notes, progs, div = parse_midi(str(MID))
    ch0 = sorted((st, m) for st, en, c, m in notes if c == 0)
    return [(t, m) for t, m in ch0 if m < BAND]

def measure_hits(notes, k, cut=None):
    lo, hi = (k - 1) * 4 * TPQ, k * 4 * TPQ
    out = []
    for t, m in notes:
        if lo - 1 <= t < hi - 1:
            rel = (t - lo) / TPQ
            if cut is not None and rel >= cut:
                continue
            out.append((rel, project(m)))
    return sorted(out)

def expected_bars():
    notes = file_hits()
    return [measure_hits(notes, k) for k in range(1, 53)]

def render_bar(hits, length):
    toks, pos = [], 0.0
    for rel, pid in hits:
        while pos + 1e-9 < rel - 1e-9:
            gap = round(min(0.5, rel - pos), 6)
            toks.append(("r", gap))
            pos = round(pos + gap, 6)
        toks.append((pid, 0.5))
        pos = round(pos + 0.5, 6)
    while pos + 1e-9 < length - 1e-9:
        gap = round(min(0.5, length - pos), 6)
        toks.append(("r", gap))
        pos = round(pos + gap, 6)
    return toks

def fmt(toks):
    return " ".join(f"{name}/8" for name, _ in toks)

def octave_down(pid):
    return pid[:-1] + str(int(pid[-1]) - 1)

def parse_shipped(songs_path):
    body = json.loads(Path(songs_path).read_text())[SONG]["body"]
    trk = body[body.find("#track"):]
    bars = []
    for line in trk.split("\n"):
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        assert t.startswith("|"), f"not a bar row: {t[:40]!r}"
        atk, pos = [], 0.0
        for name, dur in re.findall(r"([A-G][b]?\d|r|-)(/\d+\.?t?)?(?=\s|$)", t):
            if dur:
                m = re.match(r"/(\d+)(\.?)(t?)", dur)
                b = 4 / int(m.group(1))
                if m.group(2): b *= 1.5
                if m.group(3): b *= 2 / 3
            else:
                b = 1.0
            if re.match(r"[A-G]", name):
                atk.append((round(pos, 3), name))
            pos += b
        bars.append(atk)
    return bars

def check(songs_path):
    exp = expected_bars()
    sh = parse_shipped(songs_path)
    if len(sh) != len(LENGTHS):
        return [f"shipped block has {len(sh)} bars vs the melody's {len(LENGTHS)}"]
    bad = []
    for k, (e, s) in enumerate(zip(exp, sh)):
        ln = LENGTHS[k]
        eoff = {}
        for rel, pid in e:
            if rel < ln - 1e-9:
                eoff.setdefault(round(rel, 3), []).append(pid)
        soff = {}
        for off, pid in s:
            if off < ln - 1e-9:
                soff.setdefault(off, []).append(pid)
        for off in sorted(set(eoff) | set(soff)):
            es, ss = eoff.get(off, []), soff.get(off, [])
            good = es == ss
            if not good and len(es) == len(ss):
                good = all(a == b or octave_down(a) == b for a, b in zip(es, ss))
            if not good:
                bad.append(f"  bar {k + 1} rel {off}: expected {es} shipped {ss}")
        for off, pid in s:
            if off > ln - 1e-9:
                bad.append(f"  bar {k + 1} rel {off}: attack past the bar end")
    return bad

def emit():
    exp = expected_bars()
    rows = []
    for hits, ln in zip(exp, LENGTHS):
        rows.append("| " + fmt(render_bar(hits, ln)))
    return "\n".join(rows)

def main():
    args = [a for a in sys.argv[1:]]
    mode = args[0] if args else "--check"
    songs = args[1] if len(args) > 1 else SONGS_PATH
    if mode == "--emit":
        print(emit())
        return 0
    bad = check(Path(songs))
    if bad:
        print(f"FAIL: {len(bad)} mismatch(es):")
        for b in bad:
            print(b)
        return 1
    print("PASS: track matches the source measures bar-for-bar "
          "(measure-content map; harmonize octave moves allowed)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
