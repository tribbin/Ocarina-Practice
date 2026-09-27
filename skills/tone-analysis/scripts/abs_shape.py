#!/usr/bin/env python3
# Absolute-band noise-BODY shape from a hold_spectrum *_spectrum.txt:
# median level per absolute Hz window (harmonics +-80 Hz excluded, k=1..8 —
# the tone's own harmonics never belong to the body), both sides the same
# method (acceptance = full-body agreement, rel-H1 columns, txt scale).
# The band list (pocket/warm/holes/rough/tail/airhead) is in ABI; NOTES has
# the held-take f0s. Usage: abs_shape.py <folder-with-spectrum-txts>
# [<out.json>] — reads any *<NOTE>*_spectrum.txt per note.
import sys, json, math
import numpy as np

ABI = [
    ("pocket", 200, 330),
    ("warm",   330, 650),
    ("hole1",  650, 1000),
    ("H2zone", 1000, 1500),
    ("hole2",  1500, 1900),
    ("rough1", 1900, 2400),
    ("trough", 2400, 2900),
    ("rough2", 2900, 4000),
    ("rough3", 4000, 5600),
    ("tail",   5600, 8000),
    ("airhead", 8000, 12000),
]

def rows_of(path):
    f, l = [], []
    with open(path) as fh:
        next(fh)
        for line in fh:
            a, _, b = line.partition("\t")
            f.append(float(a)); l.append(float(b))
    return np.array(f), np.array(l)

def body(path, f0, win_s=0.74):
    # The txt rows are masked to per-bin magnitude (~2/winSum, exact power-vs
    # energy conventions differ across tools) — the MEDIAN COLUMN reads
    # txt-scale noise and, subtracted same-tool on both sides, compares as
    # rel-H1 shape data (the cross-tool floor-scale convention lesson holds
    # here too: absolute floors from this table do NOT compare to
    # hold_spectrum's json floors — same-side txt only).
    fs, lv = rows_of(path)
    f0 = float(f0)
    ex = np.array([abs(fs - k * f0) <= 80 for k in range(1, 9)]).any(axis=0)
    # rel-H1 column: H1 peak from the txt rows' own max within f0 +-6%.
    i1 = np.searchsorted(fs, f0 * 0.94); i2 = np.searchsorted(fs, f0 * 1.06)
    h1_pk = float(lv[i1:i2].max())
    out = {"h1": round(h1_pk, 1)}
    L = 10 ** (lv / 20)
    for name, a, b in ABI:
        keep = (fs >= a) & (fs < b) & ~ex
        if not keep.any():
            out[name] = None; continue
        med = 20 * np.log10(np.median(L[keep]) + 1e-15)
        out[name] = round(float(med - h1_pk), 1)  # rel H1, txt-scale
    return out

NOTES = {"A4": 443.6, "A5": 875.3, "B4": 497.5, "C5": 522.0,
         "D5": 584.3, "E5": 659.1, "F5": 698.0, "G5": 785.5}

if __name__ == "__main__":
    import glob, os
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    base = sys.argv[1] if len(sys.argv) > 1 else "held"
    folder = base if os.path.isabs(base) or os.path.sep in base else os.path.join(
        root, "research", "analysis", "12hole", base)
    res = {}
    hdr = ["note"] + [n for n, _, _ in ABI]
    print(("%-5s" % "note") + "".join("%10s" % n for n in hdr[1:]))
    for n, f0 in NOTES.items():
        p = sorted(glob.glob(os.path.join(folder, f"*{n}*_spectrum.txt")))
        if not p:
            print(n, "MISSING"); continue
        d = body(p[0], f0)
        res[n] = d
        print(("%-5s" % n) + "".join("%10s" % (d[c] if d.get(c) is not None else "-") for c in hdr[1:]))
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    if dst:
        json.dump(res, open(dst, "w"), indent=1)
        print("wrote", dst)
