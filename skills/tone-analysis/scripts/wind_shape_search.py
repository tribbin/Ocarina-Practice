# wind_shape_search.py — pick the wind chain's spectral shape FROM THE WAV
# DATA (Robin: "use the WAV data; don't rely on me for truth about sound").
#
# Ground truth: the recording's inter-harmonic noise floor per band
# (Blackman-Harris long window over the held part, ±80 Hz harmonic
# exclusion — the notch-band pipeline reads the fundamental's window skirt,
# not breath; see the skirt-trap note in SKILL.md). The model side is the
# ANALYTIC |H(f)| of the white-noise chain (bandpass at 1.26 f0 Q, lowpass
# at ratio f0 Q) evaluated on the same band grid — no time-domain rendering
# needed; band levels derive from mean |H|² over each band (input = flat
# PSD white noise). The winner minimises the weighted band-shape error.
import sys, os, json, math, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tone_report import load_wav, note_hz

SR = 44100.0
BANDS = [(0.85, 1.95), (1.95, 3.9), (3.9, 7.0), (7.0, 12.0)]
NOTCH_EXCL = 80.0     # Hz excluded around every harmonic for the floor
# Robin's hard rule: ladder cuts only for held-tone reference — kokiri/storms
# never feed any fitting anywhere (2026-09-27).

def rbj_coefs(kind, fc, q):
    w = min(max(fc, 1.0), 0.45 * SR) * 2 * np.pi / SR
    s, c = np.sin(w), np.cos(w)
    al = s / (2 * q)
    if kind == "lowpass":
        b0, b1, b2 = (1 - c) / 2, 1 - c, (1 - c) / 2
    else:
        b0, b1, b2 = al, 0.0, -al
    a0, a1, a2 = 1 + al, -2 * c, 1 - al
    return (b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)

def h_mag(coefs, freqs):
    b0, b1, b2, a1, a2 = coefs
    wf = 2 * np.pi * freqs / SR
    e = np.exp(-1j * wf)
    H = (b0 + b1 * e + b2 * e ** 2) / (1 + a1 * e + a2 * e ** 2)
    return np.abs(H)

def model_band_shape(f0, bpq, lpr, lpq):
    # mean |H|^2 per band of white noise through the two biquads
    hi = min(SR / 2 - 300, 12 * f0)
    f = np.linspace(20.0, hi, 24000)
    H = h_mag(rbj_coefs("bandpass", min(9000, f0 * 1.26), bpq), f)
    H = H * h_mag(rbj_coefs("lowpass", min(SR * 0.45, f0 * lpr), lpq), f)
    P = H ** 2
    out = []
    for (r1, r2) in BANDS:
        m = (f >= r1 * f0) & (f <= min(r2 * f0, hi))
        out.append(10 * math.log10(float(np.mean(P[m])) + 1e-30))
    return [v - out[0] for v in out]

def recorded_floor_profile():
    """Per-note inter-harmonic floors from the ladder cuts (short drift-free
    windows, BH long window), medianed; returns the shape rel band-1."""
    targets_p = os.path.join(HERE, "..", "..", "..",
                             "research", "analysis", "12hole", "targets.json")
    targets = json.load(open(targets_p))
    rel = []
    WIN = 4096
    w = bh(WIN)
    wsum = float(np.sum(w))
    wsq = float(np.sum(w ** 2))
    enbw_db = 10 * math.log10(WIN * wsq / wsum ** 2)   # BH bin-noise gain vs peak norm
    for nid in sorted(targets, key=note_hz):
        t = targets[nid]
        if not t.get("fit"):
            continue
        # prefer the target's own cut path (held_* sources live in per-note
        # dirs the old glob pattern never matched)
        cuts = []
        if t.get("cut") and os.path.exists(t["cut"]):
            cuts = [t["cut"]]
        else:
            cuts = sorted(glob.glob(os.path.join(HERE, "..", "..", "..", "research",
                                                 "analysis", "12hole", "cuts",
                                                 t["source"], f"*_{nid}.wav")))
        if not cuts:
            continue
        rate, x = load_wav(cuts[-1])
        mono = (x[:, 0] + x[:, 1]) / 2 if x.shape[1] > 1 else x[:, 0]
        f0m = note_hz(nid) * (2 ** (t.get("cents", 0) / 1200))
        on_rel = t["on"] - t.get("cutStart", 0.0)
        shapes = []
        hold = max(0.30, min(0.8, t["span"] * 0.75))  # first, drift-free part
        for t0 in np.arange(on_rel + 0.08, on_rel + hold - WIN / SR, 0.08):
            seg = mono[int(t0 * SR):int((t0 + WIN / SR) * SR)]
            if len(seg) < WIN:
                break
            S = np.abs(np.fft.rfft(seg * w, 1 << 18))
            fs = np.fft.rfftfreq(1 << 18, 1 / SR)
            lev = S * 2 / wsum
            i1 = int(np.searchsorted(fs, f0m * 0.95)); l1 = i1 - 1
            h1i = int(np.searchsorted(fs, f0m * 1.05))
            k = l1 + int(np.argmax(lev[l1:h1i]))
            pk = 20 * math.log10(lev[k] + 1e-15)
            bands = []
            for (r1, r2) in BANDS:
                i_lo = int(r1 * f0m / (SR / (1 << 18)))
                i_hi = int(min(r2 * f0m, SR / 2 - 300) / (SR / (1 << 18)))
                keep = [i for i in range(max(0, i_lo), i_hi)
                        if all(abs(fs[i] - hk * f0m) > NOTCH_EXCL for hk in range(1, 9))]
                # noise: BH bins carry the ENBW factor vs the peak-normalized scale
                med = 20 * math.log10(float(np.median(lev[keep])) + 1e-15) - enbw_db
                bands.append(med - pk)
            shapes.append(bands)
        if len(shapes) < 2:
            continue
        med = [float(np.median([s[i] for s in shapes])) for i in range(4)]
        rel.append(med)
        print(f"  {nid} ({t['source']}):", [round(v, 1) for v in med], f"({len(shapes)} windows)")
    return ([float(np.median([r[i] for r in rel])) for i in range(4)], rel)

def bh(n):
    t = np.arange(n) / n
    return (0.35875 - 0.48829 * np.cos(2 * np.pi * t)
            + 0.14128 * np.cos(4 * np.pi * t) - 0.01168 * np.cos(6 * np.pi * t))

def main():
    med, rel = recorded_floor_profile()
    med = [v - med[0] for v in med]  # shape rel band-1 (the model's own space)
    print("recorded floor SHAPE (band dB rel band1):", [round(v, 1) for v in med],
          f"({len(rel)} notes)")
    W = (3.0, 3.0, 1.2)
    best = None
    for bpq in (0.4, 0.6, 0.8, 1.0, 1.3, 2.0, 3.0):
        for lpr in (1.6, 1.9, 2.2, 2.5, 2.8, 3.1, 3.4):
            for lpq in (0.4, 0.6, 0.8, 1.0, 1.2, 1.5):
                errs = []
                for f0 in (659.0, 784.0, 988.0, 1175.0, 1400.0):
                    mb = model_band_shape(f0, bpq, lpr, lpq)
                    errs.append(sum(W[i - 1] * abs(mb[i] - med[i]) for i in range(1, 4)))
                e = sum(errs) / len(errs)
                if best is None or e < best[0]:
                    best = (e, bpq, lpr, lpq)
    e, bpq, lpr, lpq = best
    print(f"BEST (bpQ {bpq}, lpRatio {lpr}, lpQ {lpq}) weighted err {e:.2f} dB")
    for f0 in (784.0, 988.0, 1400.0):
        print(f"  f0 {f0}: model", [round(v, 1) for v in model_band_shape(f0, bpq, lpr, lpq)])
    print(f"  target      ", [round(v, 1) for v in med])

if __name__ == "__main__":
    main()
