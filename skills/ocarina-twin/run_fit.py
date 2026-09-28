#!/usr/bin/env python3
"""Fit a chamber from held-note WAVs. Intended to be edited only for paths."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ocarina_twin.fit import fit_chamber, load_fingerings
from ocarina_twin.synth import render_note
from ocarina_twin.model import TwinModel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wavs", nargs="+", help="held-note WAV paths (one chamber)")
    ap.add_argument("--instrument", default="ocarina")
    ap.add_argument("--chamber", default="1")
    ap.add_argument("--fingerings", default="")
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
        h2 = 20 * __import__("math").log10((n.h[1] if len(n.h) > 1 else 1e-12) + 1e-12)
        print(f"{n.note or '?':5} f0={n.f0:7.1f} Q={n.Q:5.1f} H2={h2:6.1f}dB "
              f"res={n.noise_res_db:6.1f} hiss={n.noise_hiss_db:6.1f} lvl={n.level:.2f}")


if __name__ == "__main__":
    main()
