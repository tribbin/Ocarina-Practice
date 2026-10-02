"""Split a tone-ladder recording into one hold per note.

Usage: python cut_ladders.py ladder.wav cuts/ --min-sec 0.8
Writes <note>_<f0>.wav and a cuts.json next to them.
"""
import argparse, json
from pathlib import Path
import numpy as np
import soundfile as sf

NAMES = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]

def note_name(f):
    n = int(round(12 * np.log2(f / 261.625565)))
    return NAMES[n % 12] + str(4 + n // 12)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("ladder")
    p.add_argument("out")
    p.add_argument("--min-sec", type=float, default=0.8)
    args = p.parse_args()
    y, sr = sf.read(args.ladder, always_2d=True)
    y = y.mean(1)
    win = int(0.04 * sr)
    env = np.sqrt(np.convolve(y ** 2, np.ones(win) / win, mode="same"))
    on = env > 0.18 * np.percentile(env, 95)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cuts = []
    i = 0
    while i < len(on):
        if not on[i]:
            i += 1
            continue
        j = i
        while j < len(on) and on[j]:
            j += 1
        if j - i >= int(args.min_sec * sr):
            seg = y[i:j]
            mid = seg[len(seg) // 3: 2 * len(seg) // 3]
            spec = np.abs(np.fft.rfft(mid * np.hanning(len(mid))))
            freqs = np.fft.rfftfreq(len(mid), 1 / sr)
            lo, hi = int(70 / (sr / len(mid))), int(2500 / (sr / len(mid)))
            f0 = float(freqs[lo + int(np.argmax(spec[lo:hi]))])
            name = note_name(f0)
            path = out / f"{name}_{f0:.1f}.wav"
            sf.write(path, seg, sr)
            cuts.append({"note": name, "f0": round(f0, 2), "t": round(i / sr, 3), "dur": round((j - i) / sr, 3), "file": path.name})
        i = j
    (out / "cuts.json").write_text(json.dumps(cuts, indent=2))
    print(f"{len(cuts)} holds -> {out}")

if __name__ == "__main__":
    main()
