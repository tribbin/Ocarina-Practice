#!/usr/bin/env python3
# stage_spectra.py — per-STAGE verification of a held-note WAV vs its render
# (Robin, 2026-09-27: sustain/hold, ONSET and DECAY are part of the default
# verification, not only the plateau windows). The hold takes
# (research/note-recordings/12hole/*-held.wav) are the cleanest recordings;
# they are the base and other notes interpolate/extrapolate from their
# stage classes.
#
# Windows found from the WAV itself (envelope, 20 ms hops):
#   arrival = first hop above peak-15 dB; plateau end = last such hop.
#   ONSET = arrival .. arrival+0.12 s        (the swell/burst stage)
#   HOLD  = arrival+0.30 .. plateau_end-0.05
#   DECAY = plateau_end .. +0.40 s or last point
# Per stage: Blackman-Harris spectrum in the recorder txt format + the
# abs_shape absolute band medians rel that stage's own H1 peak + top band.
# Usage: stage_spectra.py <wav> [--nominal F5] [--label L]
import sys, os, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tone_report import load_wav, note_hz
from abs_shape import ABI

SR = 44100.0
HOP = int(0.02 * SR)


def bh(n):
    t = np.arange(n) / n
    return (0.35875 - 0.48829 * np.cos(2 * np.pi * t)
            + 0.14128 * np.cos(4 * np.pi * t) - 0.01168 * np.cos(6 * np.pi * t))


def spectrum(mono, t0, t1, outdir, label, stem):
    a, b = int(t0 * SR), int(t1 * SR)
    seg = mono[a:b]
    n = min(len(seg), 32768); n -= n % 32
    if n < 2048:
        return None
    w = bh(n); wsum = float(np.sum(w))
    S = np.abs(np.fft.rfft(seg[:n] * w, 1 << 18)) * 2 / wsum
    fs = np.fft.rfftfreq(1 << 18, 1 / SR)
    rows = ["Frequency (Hz)\tLevel (dB)"]
    for i in range(min(len(fs) - 1, int(16400 / (fs[1] - fs[0])))):
        rows.append(f"{fs[i]:.6f}\t{20 * math.log10(S[i] + 1e-15):.6f}")
    path = os.path.join(outdir, f"{label}_{stem}_spectrum.txt")
    with open(path, "w") as fh:
        fh.write("\n".join(rows) + "\n")
    return fs, S, n, path


def bands(fs, S, f0):
    lv = 20 * np.log10(S + 1e-15)
    ex = np.array([abs(fs - k * f0) <= 80 for k in range(1, 9)]).any(axis=0)
    i1 = int(np.searchsorted(fs, f0 * 0.94)); i2 = int(np.searchsorted(fs, f0 * 1.06))
    h1 = float(lv[i1:i2].max()) if i2 > i1 else float(lv.max())
    out = {"h1": round(h1, 1)}
    L = 10 ** (lv / 20)
    for name, a, b in ABI:
        keep = (fs >= a) & (fs < b) & ~ex
        out[name] = None if not keep.any() else round(
            float(20 * np.log10(np.median(L[keep]) + 1e-15) - h1), 1)
    # broadband stage level vs its own H1 (the "wash" verdict indicator)
    out["broadband_rel"] = round(float(20 * np.log10(
        np.sqrt(float(np.mean((S ** 2)[~ex])) ) + 1e-15) - h1), 1)
    return out


def stage_spectra(wav, nominal, label):
    rate, x = load_wav(wav)
    assert rate == 44100
    mono = (x[:, 0] + x[:, 1]) / 2 if x.shape[1] > 1 else x[:, 0]
    n_env = len(mono) // HOP
    env = np.array([20 * np.log10(np.sqrt(np.mean(mono[i * HOP:(i + 1) * HOP] ** 2)) + 1e-12)
                    for i in range(n_env)])
    pk = float(np.percentile(env, 97))
    good = env > pk - 15
    idx = np.flatnonzero(good)
    if len(idx) < 10:
        print("no held stage found"); return 2
    arrival = float(idx[0]) * 0.02
    plateau_end = float(idx[-1] + 1) * 0.02
    f0 = note_hz(nominal)
    outdir = os.path.join(HERE, "..", "..", "..", "research", "analysis", "12hole")
    out = {"wav": os.path.abspath(wav), "f0": round(float(f0), 2),
           "arrival": round(arrival, 3), "plateau_end": round(plateau_end, 3),
           "stages": {}}
    span = min(plateau_end + 0.40, len(mono) / SR)
    windows = {
        "onset": (max(0.0, arrival), arrival + 0.12),
        "hold":  (arrival + 0.30, max(arrival + 0.31, span) - 0.05),
        "decay": (plateau_end, span),
    }
    for stem, (t0, t1) in windows.items():
        if t1 - t0 < 0.05:
            continue
        r = spectrum(mono, t0, t1, outdir, label, stem)
        if not r:
            continue
        fs, S, n, txt = r
        st = bands(fs, S, f0)
        st["window"] = [round(t0, 3), round(t1, 3)]
        st["txt"] = os.path.basename(txt)
        out["stages"][stem] = st
        keys = ("pocket", "warm", "hole1", "H2zone", "hole2", "rough1",
                "trough", "rough2", "rough3", "tail", "airhead")
        print(f"{label} [{stem}] {t0:.2f}-{t1:.2f}s H1 {st['h1']:.1f} broadband {st['broadband_rel']}")
        print("   " + " ".join(f"{c}={st[c]}" for c in keys if st.get(c) is not None))
    jpath = os.path.join(outdir, f"{label}_stages.json")
    json.dump(out, open(jpath, "w"), indent=1)
    print("wrote", jpath)
    return 0


def main():
    argv = sys.argv[1:]
    def opt(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default
    wav = next((a for a in argv if not a.startswith("-")), "")
    nominal = opt("--nominal", "C5")
    label = opt("--label") or os.path.splitext(os.path.basename(wav))[0]
    sys.exit(stage_spectra(wav, nominal, label))


if __name__ == "__main__":
    main()
