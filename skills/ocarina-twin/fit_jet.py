#!/usr/bin/env python3
"""Fit the jet-drive reference model from a chamber ladder.

The model is the §5 physical basis: a 2-pole Helmholtz resonator driven by a
delayed sigmoid jet, with turbulence noise gated by the jet oscillation. The
jet's cavity-locked oscillation is the f0 sine (the lock the recording shows);
the sigmoid generates the harmonics, the delay and resonator shape the phase,
and the noise input is the chamber's fitted colored residual.

The fit is per held take. It measures the resonator linewidth (Q), the H2/H3
content (jet sigmoid steepness), the residual air level (turbulence gain) and
the H1 amplitude (output trim), then interpolates every chamber row in log-f
like the twin fit. The output is jet_model.json, a separate optional file so
the v4-breath contract stays untouched.

  python3 skills/ocarina-twin/fit_jet.py \
    --ladder path/to/chamber-ladder.wav \
    --fingerings instruments/<id>/fingerings.json \
    --chamber 1 --out instruments/<id>/jet_model.json
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

sys.path.insert(0, str(Path(__file__).parent))
import fit_ladder as fl

SCHEMA_SINGLE = "ocarina-jet-v1"
SCHEMA_MULTI = "ocarina-jet-multi-v1"
DELAY_RATIO = 0.5       # jet travel delay in periods (tau = ratio / f0)
JET_DRIVE = 0.5         # breath sine drive into the sigmoid
JET_FEEDBACK = 0.1      # resonator pressure fed back into the jet
JET_K = 1.0             # sigmoid steepness at the fitted harmonic drive
TURB_GATE = 0.5         # turbulence chopped by |jet|
TURB_BYPASS = 0.2       # direct broadband leak beside the resonator


def colored_noise(n, sr, slope, seed=7):
    rng = np.random.default_rng(seed)
    size = 1 << int(math.ceil(math.log2(max(n, 4096))))
    spec = np.fft.fft(rng.standard_normal(size) + 1j * rng.standard_normal(size))
    df = sr / size
    for k in range(size // 2):
        f = k * df
        s = (f / 700) ** (slope / 6) if f > 40 else 0.0
        spec[k] *= s
        if k > 0:
            spec[size - k] *= s
    out = np.fft.ifft(spec).real[:n]
    rms = math.sqrt(float(np.mean(out * out))) or 1.0
    return out / rms


def resonator(f0, q, sr):
    r = math.exp(-math.pi * f0 / max(q, 1) / sr)
    th = 2 * math.pi * f0 / sr
    a1 = 2 * r * math.cos(th)
    a2 = -r * r
    b0 = 1 - a1 + r * r   # unity gain at resonance
    return b0, a1, a2


def simulate(f0, q, sr, n, k, turb_gain, noise, gate=TURB_GATE,
             bypass=TURB_BYPASS, delay_ratio=DELAY_RATIO, h2=0.0, h3=0.0):
    b0, a1, a2 = resonator(f0, q, sr)
    delay = max(1, int(round(sr * delay_ratio / f0)))
    inc = 2 * math.pi * f0 / sr
    phase = 0.0
    jets = np.zeros(n)
    y = np.zeros(n)
    y1 = y2 = 0.0
    for i in range(n):
        j = math.tanh(k * (1.0 + JET_DRIVE * math.sin(phase)
                           + h2 * math.sin(2 * phase) + h3 * math.sin(3 * phase)
                           + JET_FEEDBACK * (y[i - 1] if i else 0.0)))
        jets[i] = j
        phase += inc
        if i >= delay + 1:
            edge = jets[i - delay] - jets[i - delay - 1]
        elif i >= delay:
            edge = jets[i - delay]
        else:
            edge = 0.0
        turb = turb_gain * noise[i] * (1 - gate + gate * abs(j))
        y1n = b0 * (edge + turb) + a1 * y1 + a2 * y2
        y2 = y1
        y1 = y1n
        y[i] = y1n
    out = y + bypass * turb_gain * noise
    return out


def harmonic_measure(seg, sr, f0):
    n = len(seg)
    w = np.hanning(n)
    tt = np.arange(n) / sr
    hs = []
    for h in range(1, 7):
        s = np.sin(2 * np.pi * f0 * h * tt)
        c = np.cos(2 * np.pi * f0 * h * tt)
        hs.append(2 * math.hypot(np.dot(seg * w, s), np.dot(seg * w, c)) / np.sum(w))
    h1 = hs[0] or 1e-12
    return [x / h1 for x in hs], h1


def residual_db(seg, sr, f0, h1):
    tt = np.arange(len(seg)) / sr
    res = seg.copy()
    for h in range(1, 7):
        s = np.sin(2 * np.pi * f0 * h * tt)
        c = np.cos(2 * np.pi * f0 * h * tt)
        res -= s * np.dot(res, s) * 2 / len(res) + c * np.dot(res, c) * 2 / len(res)
    amp = math.sqrt(float(np.mean(res * res))) or 1e-12
    return 20 * math.log10(amp / max(h1, 1e-12))


def linewidth_q(seg, sr, f0):
    n = 1 << int(math.log2(len(seg)))
    w = seg[:n] * np.hanning(n)
    sp = np.abs(np.fft.rfft(w))
    freqs = np.fft.rfftfreq(n, 1 / sr)
    k = int(np.argmin(np.abs(freqs - f0)))
    peak = sp[k]
    left = k
    right = k
    while left > 0 and sp[left] > peak / 2:
        left -= 1
    while right < len(sp) - 1 and sp[right] > peak / 2:
        right += 1
    width = freqs[right] - freqs[left]
    return float(np.clip(f0 / max(width, 1e-9), 10, 80))


def fit_take(seg, sr, row, noise_slope):
    f0 = row["f0"]
    target_h = row["h"]
    q = linewidth_q(seg, sr, f0)
    n = int(0.9 * sr)
    steady = int(0.45 * sr)
    quiet = colored_noise(n, sr, noise_slope, seed=3)

    def h_err(h2, h3, index):
        out = simulate(f0, q, sr, n, JET_K, 0.0, quiet, h2=h2, h3=h3)
        seg2 = out[steady:]
        hs, _ = harmonic_measure(seg2, sr, f0)
        target = target_h[index] if len(target_h) > index else 0.0
        return abs(math.log((hs[index] + 1e-9) / max(target, 1e-9)))

    h2 = float(minimize_scalar(lambda x: h_err(x, 0.0, 1),
                                bounds=(0.0, 3.0), method="bounded").x)
    h3 = float(minimize_scalar(lambda x: h_err(h2, x, 2),
                                bounds=(0.0, 3.0), method="bounded").x)

    out = simulate(f0, q, sr, n, JET_K, 0.0, quiet, h2=h2, h3=h3)
    seg2 = out[steady:]
    _, h1 = harmonic_measure(seg2, sr, f0)
    out_gain = 1.0 / max(h1, 1e-12)

    target_air = math.pow(10, (row["floor_db"] + 4) / 20)
    loud = simulate(f0, q, sr, n, JET_K, 1.0, quiet, h2=h2, h3=h3)
    seg3 = loud[steady:]
    _, h1_loud = harmonic_measure(seg3, sr, f0)
    rel = residual_db(seg3, sr, f0, h1_loud)
    turb = target_air / max(math.pow(10, rel / 20), 1e-12)
    turb = float(np.clip(turb, 0.00001, 1.0))

    return {
        "f0": row["f0"],
        "note": row["note"],
        "Q": round(q, 2),
        "delay_ratio": DELAY_RATIO,
        "jet_k": JET_K,
        "jet_h2": round(h2, 4),
        "jet_h3": round(h3, 4),
        "jet_drive": JET_DRIVE,
        "jet_feedback": JET_FEEDBACK,
        "turb_gain": round(turb, 6),
        "turb_gate": TURB_GATE,
        "turb_bypass": TURB_BYPASS,
        "out_gain": round(out_gain, 4),
        "noise_slope_db_oct": round(noise_slope, 2),
    }


def mix(a, b, t, key):
    return a[key] + (b[key] - a[key]) * t


def at(rows, f0):
    if f0 <= rows[0]["f0"]:
        return rows[0], rows[0], 0.0
    if f0 >= rows[-1]["f0"]:
        return rows[-1], rows[-1], 1.0
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        if a["f0"] <= f0 <= b["f0"]:
            t = math.log(f0 / a["f0"]) / math.log(b["f0"] / a["f0"])
            return a, b, t
    return rows[-1], rows[-1], 1.0


def fill(measured, ids):
    rows = fl.dedupe(measured)
    keys = ("Q", "delay_ratio", "jet_k", "jet_h2", "jet_h3", "jet_drive", "jet_feedback",
            "turb_gain", "turb_gate", "turb_bypass", "out_gain",
            "noise_slope_db_oct")
    notes = []
    for name in ids:
        f = fl.f0_of(name)
        a, b, t = at(rows, f)
        out = {"note": name, "f0": round(f, 2)}
        for key in keys:
            out[key] = round(mix(a, b, t, key), 6 if key == "turb_gain" else 4)
        notes.append(out)
    return notes, rows


def chamber_model(notes, instrument, chamber, anchors):
    return {
        "schema": SCHEMA_SINGLE,
        "instrument": instrument,
        "chamber": str(chamber),
        "globals": {"voice": "jet-drive-v1", "model": "2-pole+delayed-sigmoid"},
        "notes": notes,
        "recorded": {
            "fit": "per-chamber jet fit from the ladder holds, log-f inside the chamber only",
            "anchors": [r["note"] for r in anchors],
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ladder", required=True)
    ap.add_argument("--fingerings", required=True)
    ap.add_argument("--chamber", default="1")
    ap.add_argument("--instrument", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gain", type=float, default=1.0)
    args = ap.parse_args()

    finger = json.loads(Path(args.fingerings).read_text())
    ids = [n["id"] for n in finger["notes"] if str(n["chamber"]) == str(args.chamber)]
    if not ids:
        raise SystemExit(f"no notes for chamber {args.chamber}")
    segs, sr = fl.holds(args.ladder)
    if not segs:
        raise SystemExit("no holds found")
    measured = [fl.fit_hold(s, sr) for s in segs]
    lo_f = min(fl.f0_of(n) for n in ids)
    hi_f = max(fl.f0_of(n) for n in ids)
    in_chamber = [r for r in measured if lo_f * 0.97 <= r["f0"] <= hi_f * 1.03]
    if not in_chamber:
        raise SystemExit(f"no holds inside chamber {args.chamber}'s note range")
    takes = []
    for r in in_chamber:
        seg = next(s for s in segs
                   if abs(fl.fit_hold(s, sr)["f0"] - r["f0"]) < 1e-6)
        takes.append(fit_take(seg, sr, r, r["slope_db_oct"]))
    notes, anchors = fill(takes, ids)
    model = chamber_model(notes, args.instrument or finger.get("instrument", ""),
                          args.chamber, anchors)

    out = Path(args.out)
    if out.exists():
        existing = json.loads(out.read_text())
        if existing.get("schema") == SCHEMA_MULTI or "chambers" in existing:
            existing.setdefault("chambers", {})
            existing["chambers"][str(args.chamber)] = {"gain": args.gain, "model": model}
            existing["voice"] = "jet-drive-v1"
            payload = existing
        else:
            payload = model
    else:
        payload = model
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"chamber {args.chamber}: {len(takes)} jet takes -> {len(notes)} notes")
    print("anchors", [r["note"] for r in anchors])
    print("wrote", out)


if __name__ == "__main__":
    main()
