#!/usr/bin/env python3
"""Fit one chamber from a tone-ladder recording onto its fingering notes.

The output is the twin_model.json the v3l voice reads: phase-locked
partials, a slope-colored floor, and three noise pieces (halo on f0,
whoosh, hiss) plus an air band that starts above f0. Interpolation
stays inside the chamber. Only atk_speak_s is fitted; rel_s stays.

  python3 skills/ocarina-twin/fit_ladder.py \
    --ladder path/to/chamber-ladder.wav \
    --fingerings instruments/<id>/fingerings.json \
    --chamber 1 \
    --instrument "Name" \
    --out instruments/<id>/twin_model.json
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf

NAMES = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]
ENVELOPE = {
    "level": 0.8,
    "atk_pre_s": 0.008,
    "atk_speak_s": 0.028,
    "overshoot_db": 0.4,
    "chiff_peak": 1.4,
    "chiff_len_s": 0.04,
    "chiff_db": -50,
    "rel_s": 0.08,
    "wander_cents_std": 2.5,
    "wobble_hz": 0.45,
}


def note_name(f):
    n = int(round(12 * math.log2(max(f, 1) / 261.625565)))
    return NAMES[n % 12] + str(4 + n // 12)


def f0_of(name):
    pc = NAMES.index(name[:2] if len(name) > 2 and name[1] == "s" else name[0])
    octv = int(name[-1])
    midi = (octv + 1) * 12 + pc
    return 440 * 2 ** ((midi - 69) / 12)


def holds(path, min_sec=0.55):
    y, sr = sf.read(path, always_2d=True)
    y = y.mean(1)
    win = int(0.04 * sr)
    env = np.sqrt(np.convolve(y ** 2, np.ones(win) / win, mode="same"))
    on = env > 0.12 * np.percentile(env, 95)
    out = []
    i = 0
    while i < len(on):
        if not on[i]:
            i += 1
            continue
        j = i
        while j < len(on) and on[j]:
            j += 1
        if j - i >= int(min_sec * sr):
            a, b = i + int(0.2 * sr), j - int(0.12 * sr)
            if b - a > int(0.25 * sr):
                out.append((y[a:b], y[i:j], sr))
        i = j
    return out, sr


def rise_10_90(seg, sr):
    win = max(1, int(0.01 * sr))
    env = np.sqrt(np.convolve(seg ** 2, np.ones(win) / win, mode="same"))
    peak = float(np.percentile(env, 95)) or 1e-9
    above = np.where(env > 0.1 * peak)[0]
    if len(above) < 2:
        return 0.028
    span = env[above[0]:above[-1]]
    lo = 0.1 * peak
    hi = 0.9 * peak
    a = np.where(span >= lo)[0]
    b = np.where(span >= hi)[0]
    if len(a) == 0 or len(b) == 0:
        return 0.028
    return max(0.008, min(0.12, (b[0] - a[0]) / sr))


def fit_hold(seg, sr, onset=None):
    n = 1 << int(math.log2(len(seg)))
    w = seg[:n] * np.hanning(n)
    spec = np.fft.rfft(w)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    mag = np.abs(spec)
    lo, hi = int(60 / (sr / n)), int(2300 / (sr / n))
    k = lo + int(np.argmax(mag[lo:hi]))
    f0 = float(freqs[k])
    sl = seg[: int(0.45 * sr)]
    t = np.arange(len(sl)) / sr
    rows = {}
    for harm in (1, 2, 3, 4):
        ww = 2 * np.pi * f0 * harm
        s = np.sin(ww * t)
        c = np.cos(ww * t)
        a = np.dot(sl, s)
        b = np.dot(sl, c)
        rows[harm] = (2 * math.hypot(a, b) / len(sl), math.atan2(b, a))
    h1 = rows[1][0] or 1e-9
    res = seg.copy()
    tt = np.arange(len(res)) / sr
    for harm in range(1, 7):
        ww = 2 * np.pi * f0 * harm
        s = np.sin(ww * tt)
        c = np.cos(ww * tt)
        res -= s * np.dot(res, s) * 2 / len(res) + c * np.dot(res, c) * 2 / len(res)
    rspec = np.abs(np.fft.rfft(res[:n] * np.hanning(n)))
    rdb = 20 * np.log10(rspec / (np.max(mag) + 1e-12) + 1e-12)
    band = (freqs > 900) & (freqs < 5000)
    slope = float(np.polyfit(np.log2(freqs[band]), rdb[band], 1)[0])
    mask = band.copy()
    for harm in range(1, 8):
        mask &= np.abs(freqs - f0 * harm) > 0.06 * f0
    floor_bins = mask & (freqs > 400) & (freqs < 2500)
    floor_db = float(np.median(rdb[floor_bins])) + 28 if floor_bins.any() else -54
    # Air peak above the note. A peak under f0 is the skirt, and opening a band there is the shell.
    above = np.where(mask & (freqs > f0 * 1.05) & (freqs < 6000))[0]
    air_f = float(freqs[above[int(np.argmax(rspec[above]))]]) if len(above) else f0 * 1.8
    def band_db(lo, hi):
        sel = (freqs >= lo) & (freqs < hi) & mask
        if not sel.any():
            return -100.0
        return float(np.max(rdb[sel]))
    whoosh = band_db(180, min(2000, max(800, f0 * 0.95)))
    mid = band_db(max(f0 * 1.05, air_f - 350), air_f + 350)
    hiss = band_db(5000, 11000)
    h = [1.0] + [rows[k][0] / h1 for k in (2, 3, 4)]
    # A locked H3 as loud as H2 is the clean honk. Keep the measured H2.
    if h[2] > h[1] * 0.5:
        h[2] = h[1] * 0.5
    if h[3] > h[1] * 0.25:
        h[3] = h[1] * 0.25
    phase = [0.0] + [
        (rows[k][1] - k * rows[1][1] + math.pi) % (2 * math.pi) - math.pi for k in (2, 3, 4)
    ]
    return {
        "f0": f0,
        "note": note_name(f0),
        "h": h,
        "h_phase": phase,
        "floor_db": float(floor_db if f0 >= 1100 else np.clip(floor_db, -80, -46)),
        "slope_db_oct": float(np.clip(slope, -12, -4)),
        "air_f": air_f,
        "whoosh_db": whoosh,
        "mid_db": mid,
        "hiss_db": hiss,
        "rise_s": rise_10_90(onset if onset is not None else seg, sr),
    }


def dedupe(rows):
    rows = sorted(rows, key=lambda r: r["f0"])
    out = []
    for r in rows:
        if out and abs(r["f0"] - out[-1]["f0"]) < 8:
            out[-1] = r
        else:
            out.append(r)
    return out


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


def mix(a, b, t, key):
    return a[key] + (b[key] - a[key]) * t


def fill(measured, ids):
    rows = dedupe(measured)
    notes = []
    for i, name in enumerate(ids):
        f = f0_of(name)
        a, b, t = at(rows, f)
        air_f = mix(a, b, t, "air_f")
        floor = mix(a, b, t, "floor_db")
        whoosh = mix(a, b, t, "whoosh_db")
        mid = mix(a, b, t, "mid_db")
        hiss = mix(a, b, t, "hiss_db")
        rise = mix(a, b, t, "rise_s")
        lo = max(f * 1.02, air_f - 350)
        hi = max(lo + 220, min(air_f + 350, lo + 900))
        bass = f < 520
        row = {
            "open_holes": i,
            "note": name,
            "f0": round(f, 2),
            "h": [round(a["h"][k] + (b["h"][k] - a["h"][k]) * t, 6) for k in range(4)],
            "h_phase": [round(a["h_phase"][k] + (b["h_phase"][k] - a["h_phase"][k]) * t, 3) for k in range(4)],
            "floor_db": round(floor, 2),
            "slope_db_oct": round(mix(a, b, t, "slope_db_oct"), 2),
            "air_db": round(mid, 2),
            "air_lo_hz": round(lo, 1),
            "air_hi_hz": round(hi, 1),
            "whoosh_db": round(whoosh, 2),
            "whoosh_lo_hz": 180.0,
            "whoosh_hi_hz": round(min(2000.0, max(700.0, f * 0.92)) if bass else 2000.0, 1),
            "hiss_db": round(hiss, 2),
            "hiss_lo_hz": 5000.0,
            "hiss_hi_hz": 11000.0,
            "halo_db": -62.0,
            "halo_lo_hz": round(f - max(28, 0.06 * f), 1),
            "halo_hi_hz": round(f + max(28, 0.06 * f), 1),
            "chiff_db": round((whoosh - 8) if bass else (mid + 4), 2),
            **ENVELOPE,
        }
        row["atk_speak_s"] = round(rise, 4)
        row["chiff_len_s"] = 0.09 if bass else 0.04
        notes.append(row)
    return notes, rows


def chamber_model(notes, instrument, chamber, anchors):
    return {
        "schema": "ocarina-twin-v2",
        "instrument": instrument,
        "chamber": str(chamber),
        "globals": {"voice": "v3l-chamber", "chiff_q": 2.2},
        "notes": notes,
        "recorded": {
            "fit": "per-chamber ladder fit, log-f inside the chamber only",
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
    segs, sr = holds(args.ladder)
    if not segs:
        raise SystemExit("no holds found")
    measured = [fit_hold(s, sr, onset) for (s, onset, sr) in segs]
    notes, anchors = fill(measured, ids)
    model = chamber_model(notes, args.instrument or finger.get("instrument", ""), args.chamber, anchors)
    out = Path(args.out)
    if out.exists():
        existing = json.loads(out.read_text())
        if existing.get("schema") == "ocarina-twin-multi-v1" or "chambers" in existing:
            existing.setdefault("chambers", {})
            existing["chambers"][str(args.chamber)] = {"gain": args.gain, "model": model}
            existing["voice"] = "v3l-chamber"
            payload = existing
        else:
            payload = model
    else:
        payload = model
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"chamber {args.chamber}: {len(anchors)} holds -> {len(notes)} notes")
    print("anchors", [r["note"] for r in anchors])
    print("wrote", out)


if __name__ == "__main__":
    main()
