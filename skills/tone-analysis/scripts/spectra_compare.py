#!/usr/bin/env python3
# Held-note spectrum comparison: recording cuts (truth) vs our renders, in
# the corrected-floor method's own terms (harmonics rel H1 + inter-harmonic
# band floors rel H1). Thin driver over hold_spectrum.py — it subprocess-calls
# the tool per WAV (so both sides always go through the same measurement) and
# reprints the _hold.json summaries as one table with per-band deltas.
#
# Usage: spectra_compare.py WAVEPAIR...
#   WAVEPAIR = LABEL:NOTE:WAV[:SPAN_ON,OFF]   (span optional, secs)
# Pairs whose labels start with truth:/ours: get grouped; the table prints
# per NOTE the truth row followed by every ours: row with band deltas.
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def measure(wav, note, label, span=None):
    outdir = os.path.join(HERE, "..", "..", "..", "research", "analysis", "12hole")
    argv = [sys.executable, os.path.join(HERE, "hold_spectrum.py"), wav,
            "--nominal", note, "--label", label]
    if span:
        argv += ["--span", span]
    r = subprocess.run(argv, capture_output=True, text=True, cwd=outdir)
    if r.returncode:
        print("FAIL", label, (r.stderr or r.stdout).strip()[-160:])
        return None
    import json
    d = json.load(open(os.path.join(outdir, label + "_hold.json")))
    d["label"] = label
    return d


def bear(d):
    if d is None:
        return None
    h = d["harmonics"]
    b = d["bands"]
    return {
        "f0": d["f0"],
        "h2": h[1]["relH1"] if len(h) > 1 else None,
        "h3": h[2]["relH1"] if len(h) > 2 else None,
        "floors": [x["rel_H1"] for x in b],
    }


def main():
    pairs = []
    for a in sys.argv[1:]:
        parts = a.split(":")
        if len(parts) == 3:
            g, n, w = parts
            span = None
        else:
            g, n, w, span = parts[0], parts[1], parts[2], parts[3]
        pairs.append((g, n, w, span))
    sides = {g: {} for g, _, _, _ in pairs}
    for g, n, w, span in pairs:
        m = bear(measure(w, n, (g.split("/")[-1] or g) + "_" + n + "_hs", span))
        if m:
            sides[g][n] = m
    notes = []
    for g, _, _, _ in pairs:
        for n in sides.get(g, {}):
            if n not in notes:
                notes.append(n)
    fl = max(len(x["floors"]) for g in sides.values() for x in g.values()) if sides else 4
    print("note     side          f0      H2     H3   " +
          "  ".join(f"b{i+1}" for i in range(fl)))
    out = {}
    for n in notes:
        out[n] = {}
        for g in sides:
            if n not in sides[g]:
                continue
            m = sides[g][n]
            tr = sides.get("truth", {}).get(n)
            fs = "  ".join(f"{v:6.1f}" for v in m["floors"])
            print(f"{n:8} {g:12} {m['f0']:7.1f} {m['h2']:6.1f} {m['h3']:6.1f} {fs}")
            row = m
            if tr:
                d = [m["floors"][i] - tr["floors"][i]
                     for i in range(min(len(m["floors"]), len(tr["floors"])))]
                row["deltas"] = d
                if d:
                    print(f"{n:8} {g[:9]+'-delta':12} {d[0]:>28}".replace(
                        f"{d[0]:>28}", "  ".join(f"{v:+6.1f}" for v in d)))
            out[n][g] = row
    import json
    odst = os.path.join(HERE, "..", "..", "..", "research", "analysis", "12hole",
                        "spectra_compare.json")
    json.dump(out, open(odst, "w"), indent=1)
    print("wrote", odst)


if __name__ == "__main__":
    main()
