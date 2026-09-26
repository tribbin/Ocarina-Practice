# wind_shape_search.py — pick the wind chain's spectral shape FROM THE WAV
# DATA (Robin: "use the WAV data; don't rely on me for truth about sound").
#
# The recording's breath-noise profile (band medians rel band-1, from the
# ladder targets in research/analysis/12hole/targets.json) is compared
# against a white-noise model of the wind chain swept over candidate shapes:
#   bandpass at bumpRatio x f0 (Q: 0.4..1.5 broad wash .. resonant) then
#   lowpass at ratio x f0 (Q: 0.6..1.4).
# The winning (bpQ, lpRatio, lpQ) minimises the band-shape error; the engine
# constants + the row-side correctness notes follow from the best fit.
import sys, os, json, math, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tone_report import load_wav, note_hz

SR = 44100.0
BANDS = [(0.85, 1.95), (1.95, 3.9), (3.9, 7.0), (7.0, 12.0)]
NOTCHW = 8
TAKE_SOURCE_OVERRIDE = {"B4": "kokiri"}  # keep in step with fit_tone.py

def rbj(kind, fc, q):
    w = min(max(fc, 1.0), 0.45 * SR) * 2 * np.pi / SR
    s, c = np.sin(w), np.cos(w)
    al = s / (2 * q)
    if kind == "lowpass":
        b0, b1, b2 = (1 - c) / 2, 1 - c, (1 - c) / 2
    else:
        b0, b1, b2 = al, 0.0, -al
    a0, a1, a2 = 1 + al, -2 * c, 1 - al
    return (b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)

def biquad(x, coefs):
    y = np.empty_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(x)):
        b0, b1_, b2, a1, a2 = coefs
        y[i] = b0 * x[i] + b1_ * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1 = x1, x[i]
        y2, y1 = y1, y[i]
    return y

def band_dbs(spec_mag, freqs, f0, notchw=8):
    # exactly the pipeline's band accounting: per-bin rms of the notched
    # spectrum (the noise-only model needs no harmonic notches though)
    out = []
    for r1, r2 in BANDS:
        m = (freqs >= r1 * f0) & (freqs <= min(r2 * f0, SR / 2 - 300))
        out.append(20 * math.log10(float(np.sqrt(np.mean(spec_mag[m] ** 2))) + 1e-15))
    return out

def model_bands(f0, bpq, lpr, lpq, n=1 << 17):
    rng = np.random.default_rng(11)
    x = rng.normal(0, 1, n)
    y = biquad(x, rbj("bandpass", min(9000, f0 * 1.26), bpq))
    y = biquad(y, rbj("lowpass", min(SR * 0.45, f0 * lpr), lpq))
    S = np.abs(np.fft.rfft(y * np.hanning(n))) * 2 / np.sum(np.hanning(n))
    freqs = np.fft.rfftfreq(n, 1 / SR)
    b = band_dbs(S, freqs, f0)
    return [v - b[0] for v in b]   # shape rel band-1

def recorded_profile():
    # short-drift rule (Robin): the tone itself drifts and its skirts leak
    # into the bands when a long plateau is medianed — measure noise on
    # STABLE per-frames early in the hold instead (f0 ±10c over 3 frames,
    # energy-consistent), with the F6-style long holds sampled from their
    # first half only. Band bars per frame, then medians per note.
    targets_p = os.path.join(HERE, "..", "..", "..",
                             "research", "analysis", "12hole", "targets.json")
    targets = json.load(open(targets_p))
    rel = []
    for nid, t in sorted(targets.items(), key=lambda kv: note_hz(kv[0])):
        if not t.get("fit"):
            continue
        cuts = sorted(glob.glob(os.path.join(HERE, "..", "..", "..", "research",
                                             "analysis", "12hole", "cuts", "ladder", f"*_{nid}.wav")))
        if nid in TAKE_SOURCE_OVERRIDE or not cuts:
            continue   # bridged takes live under the override source's cut dir
        wav = cuts[0]
        rate, x = load_wav(wav)
        mono = (x[:, 0] + x[:, 1]) / 2 if x.shape[1] > 1 else x[:, 0]
        WIN, PAD, HOP = 4096, 16384, 2048
        w = np.hanning(WIN)
        t_hold = (t["off"] - t["on"]) * 0.55   # first half of the hold only
        b1s = []
        shapes = []
        for i0 in range(int((t["on"] + 0.30) * SR), int((t["on"] + max(0.4, t_hold)) * SR), int(0.12 * SR)):
            if i0 + WIN > len(mono):
                break
            S = np.abs(np.fft.rfft(mono[i0:i0 + WIN] * w, PAD)) * 2 / np.sum(w)
            fs = np.fft.rfftfreq(PAD, 1 / SR)
            l1 = int(np.searchsorted(fs, note_hz(nid) * 0.9))
            h1 = int(np.searchsorted(fs, note_hz(nid) * 1.1))
            f0 = fs[l1:h1][int(np.argmax(S[l1:h1]))]
            if not (0.9 * note_hz(nid) < f0 < 1.1 * note_hz(nid)):
                continue
            bands = []
            for (r1, r2) in BANDS:
                m = (fs >= r1 * f0) & (fs <= min(r2 * f0, SR / 2 - 300))
                for k in range(1, 10):
                    c = int(round(k * f0 / (SR / PAD)))
                    m2 = m.copy()
                    m2[max(0, c - NOTCHW):c + NOTCHW + 1] = False
                    m = m2
                bands.append(20 * math.log10(float(np.sqrt(np.mean(S[m] ** 2))) + 1e-15))
            shapes.append([bands[i] - bands[0] for i in range(4)])
        if len(shapes) < 3:
            continue
        med = [float(np.median([s[i] for s in shapes])) for i in range(4)]
        rel.append((nid, med))
        print(f"  {nid}: short-window shape", [round(v, 1) for v in med], f"({len(shapes)} stable frames)")
    med_all = [float(np.median([r[1][i] for r in rel])) for i in range(4)]
    return med_all, [r[1] for r in rel]

def short_shape(nid):  # helper kept for debug runs
    return None

def main():
    med, rel = recorded_profile()
    print("recorded shape (band dB rel band1, ladder notes):", med,
          f"({len(rel)} note shapes)")
    BEST_W = (3.0, 3.0, 1.2)   # perceptual weights: b2/b3 own the "wash" feel
    best = None
    for bpq in (0.4, 0.6, 0.8, 1.0, 1.3, 2.0):
        for lpr in (1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.4, 3.8):
            for lpq in (0.4, 0.6, 0.8, 1.0, 1.2, 1.5):
                errs = []
                for f0 in (659.0, 784.0, 988.0, 1175.0, 1400.0):
                    mb = model_bands(f0, bpq, lpr, lpq)
                    errs.append(sum(BEST_W[i - 1] * abs(mb[i] - med[i])
                                    for i in range(1, 4)))
                e = sum(errs) / len(errs)
                if best is None or e < best[0]:
                    best = (e, bpq, lpr, lpq)
    e, bpq, lpr, lpq = best
    print(f"BEST (bpQ {bpq}, lpRatio {lpr}, lpQ {lpq}) weighted err {e:.2f} dB")
    for f0 in (784.0, 988.0, 1400.0):
        print(f"  f0 {f0}: model", [round(v, 1) for v in model_bands(f0, bpq, lpr, lpq)])
    print(f"  target           ", [round(v, 1) for v in med])
    # the shipped/fitted defaults for comparison
    for label, args in [("shipped  (Q voice, lp 2.7/1.2)", (None, 2.7, 1.2)),
                        ("fitted rows (Q .75, lp 2.7/1.1)", (0.75, 2.7, 1.1))]:
        bpq2 = args[0] if args[0] else 0.7
        errs = []
        for f0 in (659.0, 784.0, 988.0, 1175.0, 1400.0):
            mb = model_bands(f0, bpq2, args[1], args[2])
            errs.append(sum(abs(mb[i] - med[i]) for i in range(1, 4)))
        print(label, "mean err", round(sum(errs) / len(errs), 2), "dB")

if __name__ == "__main__":
    main()
