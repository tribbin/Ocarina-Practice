# hold_spectrum.py — the ground-truth maker: find the HELD tone inside a
# WAV (Robin: "finding a held tone and generating spectrum should be part of
# the skill") and emit the recorder's txt-style spectrum of the held part
# (Frequency (Hz) \t Level (dB) — one row per bin, Blackman-Harris long
# window over the best drift-free hold span) plus a small JSON summary of
# the harmonic spikes and the corrected inter-harmonic noise floors.
#
# This is what the F6 ground truth (research/analysis/12hole/F6_spectrum.txt,
# Robin's own recorder export) reproduces — use its numbers when two
# measurements disagree: the txt wins (the held-part view, not drifting).
#
# Usage:
#   python hold_spectrum.py <wav> [--nominal C5] [--label L]
#        [--outdir research/analysis/12hole]
# Writes <label>_spectrum.txt + <label>_hold.json; prints the summary.
import sys, os, json, math, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tone_report import load_wav, note_hz

SR = 44100.0

def bh(n):
    t = np.arange(n) / n
    return (0.35875 - 0.48829 * np.cos(2 * np.pi * t)
            + 0.14128 * np.cos(4 * np.pi * t) - 0.01168 * np.cos(6 * np.pi * t))

def find_hold(mono, f_guess=None, min_hold=0.30):
    """Longest stretch with stable, loud energy: envelope > peak−15 dB AND
    (if f_guess given) f0 within ±60 c of the guess; returns (t0, t1) s."""
    hop = int(0.02 * SR)
    n = len(mono) // hop
    env = np.array([20 * np.log10(np.sqrt(np.mean(mono[i * hop:(i + 1) * hop] ** 2)) + 1e-12)
                    for i in range(n)])
    pk = float(np.percentile(env, 97))
    good = env > pk - 15
    runs = []
    s = None
    for i, g in enumerate(good):
        if g and s is None:
            s = i
        elif not g and s is not None:
            runs.append((s, i)); s = None
    if s is not None:
        runs.append((s, n))
    best = None
    for a, b in runs:
        if (b - a) * 0.02 < min_hold:
            continue
        if not best or (b - a) > (best[1] - best[0]):
            best = (a, b)
    if not best:
        return None
    # trim to the stable middle (drop 40 ms at each edge for attack/reverb)
    t0 = best[0] * 0.02 + 0.04
    t1 = best[1] * 0.02 - 0.04
    return (max(0.0, t0), t1)

def main():
    argv = sys.argv[1:]
    def opt(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default
    wav = next((a for a in argv if not a.startswith("-")), "")
    nominal = opt("--nominal")
    label = opt("--label") or os.path.splitext(os.path.basename(wav))[0]
    outdir = opt("--outdir", os.path.join(os.path.abspath(os.path.join(HERE, "..", "..", "..")),
                                          "research", "analysis", "12hole"))
    rate, x = load_wav(wav)
    assert rate == 44100
    mono = (x[:, 0] + x[:, 1]) / 2 if x.shape[1] > 1 else x[:, 0]
    f_guess = note_hz(nominal) if nominal else None
    # --span ON,OFF forces the window (secs) — for cuts whose plateau tracker
    # misses (short/wobbly holds); targets.json's per-note on/off is the same
    # truth window the fit aggregates, so pass it through here.
    span = opt("--span")
    if span:
        a, _, b = span.partition(",")
        hold = (float(a), float(b))
    else:
        hold = find_hold(mono, f_guess)
    if not hold:
        print("no held tone found"); return 2
    t0, t1 = hold
    WIN = min(int((t1 - t0) * SR), 32768)
    WIN -= WIN % 32
    if WIN < 8192:  # short holds: still >=186 ms
        t1 = min(t1, t0 + 0.37)
        WIN = min(int((t1 - t0) * SR) - (int((t1 - t0) * SR) % 32), 16384)
    w = bh(WIN); wsum = float(np.sum(w)); wsq = float(np.sum(w ** 2))
    enbw = 10 * math.log10(WIN * wsq / wsum ** 2)
    seg = mono[int(t0 * SR):int(t0 * SR) + WIN]
    if len(seg) < 2048:
        print(f"window {t0:.2f}-{t1:.2f} s leaves <2048 samples in {os.path.basename(wav)} "
              f"({len(mono)/SR:.2f} s long)")
        return 2
    pad = 1 << 18
    S = np.abs(np.fft.rfft(seg * w, pad)) * 2 / wsum
    fs = np.fft.rfftfreq(pad, 1 / SR)
    # txt-format spectrum (the recorder export's own shape)
    rows = [f"Frequency (Hz)\tLevel (dB)"]
    df = fs[1] - fs[0]
    display = int(min(len(fs) - 1, 16400 / df))
    for i in range(display):
        rows.append(f"{fs[i]:.6f}\t{20 * math.log10(S[i] + 1e-15):.6f}")
    spath = os.path.join(outdir, f"{label}_spectrum.txt")
    with open(spath, "w") as f:
        f.write("\n".join(rows) + "\n")
    # f0 refine + harmonics + floors
    f0 = f_guess or 523.25
    i1 = int(np.searchsorted(fs, f0 * 0.94)); h1i = int(np.searchsorted(fs, f0 * 1.06))
    k = max(1, i1) + int(np.argmax(S[max(1, i1):h1i]))
    f0 = fs[k]
    pk = 20 * math.log10(S[k] + 1e-15)
    harm = []
    for hk in range(1, 9):
        fk = hk * f0
        if fk < 1 + 40 or fk > 17000:
            continue
        i0 = int(np.searchsorted(fs, fk)); lo, hi = max(1, i0 - 30), min(len(S) - 2, i0 + 30)
        kk = lo + int(np.argmax(S[lo:hi]))
        lev = 20 * math.log10(S[kk] + 1e-15)
        harm.append({"k": hk, "f": round(float(fs[kk]), 1), "db": round(lev, 1),
                     "relH1": round(lev - pk, 1)})
    bins = SR / pad
    bands = []
    for (r1, r2) in [(0.85, 1.95), (1.95, 3.9), (3.9, 7.0), (7.0, 12.0)]:
        i_lo, i_hi = int(r1 * f0 / bins), int(min(r2 * f0, SR / 2 - 300) / bins)
        keep = [i for i in range(max(0, i_lo), i_hi)
                if all(abs(fs[i] - hk * f0) > 80 for hk in range(1, 9))]
        med = 20 * math.log10(float(np.median(S[keep])) + 1e-15) - enbw
        bands.append({"band": f"{r1}-{r2}xf0", "floor_db": round(med, 1),
                      "rel_H1": round(med - pk, 1), "n_bins": len(keep)})
    out = {"wav": wav, "hold_s": [round(t0, 3), round(t1, 3)],
           "window_s": round(WIN / SR, 3), "f0": round(float(f0), 2),
           "peak_db": round(pk, 1),
           "harmonics": harm, "bands": bands,
           "spectrum_txt": spath, "bin_hz": round(float(df), 3)}
    jpath = os.path.join(outdir, f"{label}_hold.json")
    json.dump(out, open(jpath, "w"), indent=1)
    print(f"{label}: hold {t0:.2f}-{t1:.2f} s (win {WIN/SR:.2f}s) f0 {f0:.1f} Hz")
    print("  harmonics rel H1:", [h["relH1"] for h in harm[1:]])
    print("  band floors rel H1:", [b["rel_H1"] for b in bands])
    print("wrote", spath, "and", jpath)

if __name__ == "__main__":
    sys.exit(main())
