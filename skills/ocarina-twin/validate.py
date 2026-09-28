#!/usr/bin/env python3
"""Compare recorded residual air bands to the offline synth (same cutoffs)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ocarina_twin.air import HISS_TOP_HZ, hiss_hp_hz
from ocarina_twin.fit import NOM, load_mono, refine_f0, sounding_span, subtract_tracked
from ocarina_twin.model import TwinModel
from ocarina_twin.synth import render_note
from scipy.signal import butter, sosfilt


def band_rms(x, sr, lo, hi):
    ny = sr / 2
    lo = max(30.0, lo)
    hi = min(ny - 30.0, hi)
    if hi <= lo + 15:
        return 0.0
    y = sosfilt(butter(2, [lo / ny, hi / ny], btype="band", output="sos"), x)
    return float(np.sqrt(np.mean(y ** 2) + 1e-20))


def sustain(path: Path):
    x, sr = load_mono(path)
    t0, t1 = sounding_span(x, sr)
    sa, sb = t0 + 0.11, max(t0 + 0.30, t1 - 0.10)
    return x[int(sa * sr): int(sb * sr)], sr


def residual(x, sr, f0):
    _, res, _ = subtract_tracked(x, sr, f0)
    return res


def db(v, ref):
    return 20 * np.log10(v / (ref + 1e-12) + 1e-12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("wavs", nargs="+")
    args = ap.parse_args()
    model = TwinModel.from_dict(json.loads(Path(args.model).read_text()))
    print(f"{'note':5} {'f0':7} {'recHiss':8} {'synHiss':8} {'dHiss':6} "
          f"{'recNear':8} {'synNear':8} {'rec15':7} {'syn15':7}")
    for wav in args.wavs:
        p = Path(wav)
        xs, sr = sustain(p)
        name = p.stem.split("-")[0]
        guess = NOM.get(name, 500.0)
        f0 = refine_f0(xs, sr, guess)
        rec_res = residual(xs, sr, f0)
        sig = float(np.sqrt(np.mean(xs ** 2) + 1e-20))
        y = render_note(model, f0, dur_s=1.4, sr=sr, seed=1, hold_s=1.15)
        a0 = int(0.25 * sr)
        ys = y[a0:a0 + min(len(xs), len(y) - a0)]
        syn_res = residual(ys.astype(np.float64), sr, f0)
        ssig = float(np.sqrt(np.mean(ys ** 2) + 1e-20))
        hp = hiss_hp_hz(f0)
        rec_h = db(band_rms(rec_res, sr, hp, min(sr / 2 - 40, HISS_TOP_HZ)), sig)
        syn_h = db(band_rms(syn_res, sr, hp, min(sr / 2 - 40, HISS_TOP_HZ)), ssig)
        rec_n = db(band_rms(rec_res, sr, 0.65 * f0, 1.35 * f0), sig)
        syn_n = db(band_rms(syn_res, sr, 0.65 * f0, 1.35 * f0), ssig)
        rec_m = db(band_rms(rec_res, sr, 1500, 2800), sig)
        syn_m = db(band_rms(syn_res, sr, 1500, 2800), ssig)
        print(f"{name:5} {f0:7.1f} {rec_h:8.1f} {syn_h:8.1f} {syn_h-rec_h:6.1f} "
              f"{rec_n:8.1f} {syn_n:8.1f} {rec_m:7.1f} {syn_m:7.1f}")


if __name__ == "__main__":
    main()
