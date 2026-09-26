#!/usr/bin/env python3
# The MIDI-track audit/rebuild for the MIDI-interpreted Outset twin.
#
# Contract (Robin's field checks caught both errors this tool guards,
# 2026-09-26): the track blocks of an interpreted-from-MIDI song must carry
# each SOURCE measure's OWN content on the melody's bar lines (measure
# k -> song bar k, bar-relative hit positions unchanged). A window-
# intersection read is wrong as soon as the melody's grid differs from the
# file's meter: the shipped melody once held a 5-beat da-dum (the reduced
# score's engraving error — its fifth beat was the arranger's own extra
# note, absent from the game's file) and every window after it rotated
# +1 beat; bar sums and the engine drift stayed green while the ear heard
# it everywhere past bar 18. The corpus now runs the game's pure 4/4
# measure-for-measure, and this tool is the source gate.
#
# The BASS map: bars 1-52 = file measure k, full hit pattern, positions
# unchanged (bin band < C#4; the register projection +24 with the sub-floor
# roots a third octave up; the finale = the game's full vamp so the loop
# seam cares for itself).
#
# The CONTRABASS map (Robin's build, derived from the file first, insight
# second): per measure the bass's root segments — octave/fifth bounces
# merge into one root-class run, a new pitch class opens a segment; the
# measure root = the longest segment's class (time-ties = the later one,
# matching the trio's hand layer); a 2+2 split only when two segments each
# span a beat or more. Register = the game's own lowest hit of the
# segment +12 (its sub-bass band lands in the deep register directly).
#
# Modes:
#   --check [songs.json path]         compare BOTH track blocks (bass +
#                                     contrabass) against their source
#                                     maps; print bar/offset/expected/
#                                     shipped mismatches; exit 1 on any.
#   --emit bass|contrabass            print the expected raw block of one
#                                     stream (register projection applied,
#                                     pre-harmonize) for splicing.
#
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "midi-to-ocarina-tab" / "scripts"))
from mid2tab import parse_midi, nm

TPQ = 192
M = 4 * TPQ                      # ticks per 4/4 measure
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

def measure_hits(notes, k):
    lo, hi = (k - 1) * M, k * M
    out = []
    for t, m in notes:
        if lo - 1 <= t < hi - 1:
            out.append(((t - lo) / TPQ, project(m)))
    return sorted(out)

def expected_bars():
    notes = file_hits()
    return [measure_hits(notes, k) for k in range(1, 53)]

def contra_bars():
    """Returns, per bar, the expected attacks as [(offset_beats, pitch)]."""
    notes = file_hits()
    bars = []
    for k in range(1, 53):
        lo, hi = (k - 1) * M, k * M
        hits = sorted((t, m) for t, m in notes if lo - 1 <= t < hi - 1)
        segs = []                       # (lo_t, hi_t, low_of_root_class)
        seg_lo, root, prev = hits[0][0], hits[0][1], hits[0][1]
        def close(end_t):
            members = [h for tt, h in hits if seg_lo <= tt < end_t]
            low = min(h for h in members if h % 12 == root % 12)
            segs.append((seg_lo, end_t, low))
        for t, m in hits[1:]:
            family = (m % 12 == root % 12 or m % 12 == prev % 12 or
                      abs(m - prev) == 12 or
                      (m - root == 7 and m > root) or
                      (m - prev == 7 and prev > root))
            if family:
                prev = m
                continue
            close(t)
            seg_lo, root, prev = t, m, m
        close(hi)
        longs = [(a, b, low) for a, b, low in segs if (b - a) >= TPQ]
        # a split only when the two leading long segments are DIFFERENT
        # root classes (a same-class pair is just the bounce continuing)
        if (len(longs) >= 2 and
                longs[0][2] % 12 != longs[1][2] % 12):
            out = [(0.0, pnm(longs[0][2] + 12)),
                   (2.0, pnm(longs[1][2] + 12))]
        else:
            pick = max(segs, key=lambda s: (s[1] - s[0], s[0]))
            out = [(0.0, pnm(pick[2] + 12))]
        bars.append(out)
    return bars

def render_bass():
    rows = []
    for hits, ln in zip(expected_bars(), LENGTHS):
        toks, pos = [], 0.0
        for rel, pid in hits:
            while pos + 1e-9 < rel - 1e-9:
                gap = round(min(0.5, rel - pos), 6)
                toks.append(("r", gap))
                pos = round(pos + gap, 6)
            toks.append((pid, 0.5))
            pos = round(pos + 0.5, 6)
        while pos + 1e-9 < ln - 1e-9:
            gap = round(min(0.5, ln - pos), 6)
            toks.append(("r", gap))
            pos = round(pos + gap, 6)
        rows.append("| " + " ".join(f"{n}/8" for n, d in toks) + "\n")
    return "".join(rows)

def render_contra():
    rows = []
    for atk in contra_bars():
        if len(atk) == 1:
            rows.append(f"| {atk[0][1]}/1\n")
        else:
            rows.append("| " + " ".join(f"{p}/2" for off, p in atk) + "\n")
    return "".join(rows)

def octave_down(pid):
    return pid[:-1] + str(int(pid[-1]) - 1)

def parse_track_blocks(songs_path):
    """{name: [(bar_index, offset, pitch)]} from a songs.json body."""
    body = json.loads(Path(songs_path).read_text())[SONG]["body"]
    i = body.find("#track")
    out = {}
    while i >= 0:
        header = body[i:body.index("\n", i)].strip()
        name = header.split()[1]
        j = body.find("#track", i + 1)
        seg = body[i:j] if j > i else body[i:]
        atk, pos, bar = [], 0.0, 0
        for line in seg.split("\n"):
            t = line.strip()
            if not t or t.startswith("#"):
                continue
            if t.startswith("|"):
                if bar > 0 or pos > 0:
                    pass
            for nm_, dur in re.findall(
                    r"([A-G][b]?\d|r|-)(/\d+\.?t?)?(?=\s|$)", t):
                if dur:
                    m = re.match(r"/(\d+)(\.?)(t?)", dur)
                    b = 4 / int(m.group(1))
                    if m.group(2): b *= 1.5
                    if m.group(3): b *= 2 / 3
                else:
                    b = 1.0
                if re.match(r"[A-G]", nm_):
                    atk.append((bar, round(pos, 3), nm_))
                pos += b
                if pos >= LENGTHS[bar] - 1e-9:
                    bar += 1; pos = 0.0
        out.setdefault(name, [])
        out[name].extend(atk)
        i = j
    return out

def check(songs_path):
    exps = {"bass": expected_bars(), "contrabass": contra_bars()}
    shipped = parse_track_blocks(songs_path)
    bad = []
    for name, exp in exps.items():
        if name not in shipped:
            bad.append(f"  {name}: no block in the shipped body")
            continue
        eoff = {}
        for k, hits in enumerate(exp):
            for rel, pid in hits:
                eoff.setdefault((k, round(rel, 3)), []).append(pid)
        soff = {}
        for bar, off, pid in shipped[name]:
            soff.setdefault((bar, off), []).append(pid)
        for key in sorted(set(eoff) | set(soff)):
            es, ss = eoff.get(key, []), soff.get(key, [])
            good = es == ss
            if not good and len(es) == len(ss):
                good = all(a == b or octave_down(a) == b for a, b in zip(es, ss))
            if not good:
                bad.append(f"  {name} bar {key[0] + 1} rel {key[1]}: "
                           f"expected {es} shipped {ss}")
    return bad

def main():
    args = sys.argv[1:]
    mode = args[0] if args else "--check"
    songs = args[2] if mode.startswith("--") and len(args) > 2 else (
        args[1] if len(args) > 1 else SONGS_PATH)
    if mode in ("--emit", "--emit-contra"):
        print(render_bass() if mode == "--emit" else render_contra())
        return 0
    bad = check(Path(songs))
    if bad:
        print(f"FAIL: {len(bad)} mismatch(es):")
        for b in bad:
            print(b)
        return 1
    print("PASS: bass and contrabass match their source maps bar-for-bar "
          "(measure-content and root-segment rules; harmonize octave moves "
          "allowed)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
