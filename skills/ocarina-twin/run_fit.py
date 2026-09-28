#!/usr/bin/env python3
"""WAV held-notes → twin_model.json (one chamber)."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ocarina_twin.fit import fit_chamber, load_fingerings


def main():
    ap = argparse.ArgumentParser(description="Fit one Helmholtz chamber from held WAVs")
    ap.add_argument("wavs", nargs="+", help="held-note WAV paths, one chamber only")
    ap.add_argument("--instrument", default="ocarina")
    ap.add_argument("--chamber", default="1")
    ap.add_argument("--fingerings", default="", help="fingerings.json for open-hole counts")
    ap.add_argument("-o", "--out", default="twin_model.json")
    args = ap.parse_args()
    fingerings = load_fingerings(Path(args.fingerings)) if args.fingerings else None
    model = fit_chamber(
        [Path(p) for p in args.wavs],
        instrument=args.instrument,
        chamber=args.chamber,
        fingerings=fingerings,
    )
    Path(args.out).write_text(json.dumps(model.to_dict(), indent=2))
    print("wrote", args.out)
    for n in model.notes:
        h2 = 20 * math.log10((n.h[1] if len(n.h) > 1 else 1e-12) + 1e-12)
        print(f"{n.note or '?':5} f0={n.f0:7.1f} holes={n.open_holes} "
              f"Q={n.Q:5.1f} nQ={n.noise_Q:4.1f} H2={h2:6.1f}dB "
              f"res={n.noise_res_db:6.1f} hiss={n.noise_hiss_db:6.1f} "
              f"slope={n.noise_slope_db_oct:5.1f} lvl={n.level:.2f}")


if __name__ == "__main__":
    main()
