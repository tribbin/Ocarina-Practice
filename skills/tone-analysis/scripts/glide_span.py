# glide_span.py — measure the note-TO-note transitions inside melody takes:
# storms' glides and kokiri's tongued joints, the material Robin added the
# melodies for ("the old engine treats transitions as a glide, but on the
# real ocarina the jump is as short as tapping a finger on a hole").
# Per plateau-to-plateau transition: duration, cents path, speed profile and
# the envelope's behavior mid-jump (dip / swell / carry).
#
# Usage: python glide_span.py <wav> [--label L] [--outdir research/analysis/12hole]
import sys, os, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tone_report import load_wav, dbfs

SR = 44100.0

def f0_track(seg, hop_ms=10):
    """Per-hop f0 via autocorrelation on a 2048 frame, with the strongest
    lag peak inside 150-2200 Hz; returns (f0s, rms per hop)."""
    hop = int(hop_ms / 1000 * SR)
    n = len(seg); out_f = []; out_a = []
    w = np.hanning(2048)
    for i0 in range(0, max(0, n - 2048), hop):
        s = seg[i0:i0 + 2048].copy()
        if s.std() < 1e-5:
            out_f.append(0.0); out_a.append(-120.0)
            continue
        s -= s.mean(); s *= w
        ac = np.correlate(s, s, mode="full")[2047:]
        lo, hi = int(SR / 2200), min(int(SR / 150) + 1, len(ac) - 1)
        k = lo + int(np.argmax(ac[lo:hi]))
        if 0 < k < len(ac) - 1:
            a, b, c = ac[k - 1], ac[k], ac[k + 1]
            d = 0.5 * (a - c) / (a - 2 * b + c + 1e-30)
            f0 = SR / max(0.5, k + d)
        else:
            f0 = SR / max(0.5, k)
        out_f.append(f0)
        out_a.append(dbfs(s))
    return np.array(out_f), np.array(out_a)

def plateaus(f0s, amps, min_stable_ms=70, tol_c=35):
    """Consecutive runs where f0 stays within tol of the run's median."""
    runs = []
    start = None; ref = None; last = None
    for i, f in enumerate(f0s):
        if f <= 0:
            if start is not None and (last - start) * 10 >= min_stable_ms:
                runs.append((start, last, ref))
            start = ref = None
            continue
        if start is None:
            start = ref = i
        else:
            c = 1200 * math.log2(f / f0s[ref])
            if abs(c) > tol_c:
                if (last - start) * 10 >= min_stable_ms:
                    runs.append((start, last, ref))
                start = ref = i
        last = i
    if start is not None and (last - start) * 10 >= min_stable_ms:
        runs.append((start, last, ref))
    # merge adjacent runs whose ref-cents distance is under tol (median drift)
    merged = []
    for r in runs:
        if merged and abs(1200 * math.log2(f0s[r[2]] / f0s[merged[-1][2]])) < tol_c:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    return merged

def et_name(f):
    LET = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]
    if not f or f <= 0: return "?"
    m = 69 + 12 * math.log2(f / 440.0)
    r = int(round(m))
    return f"{LET[r % 12]}{r // 12 - 1}"

def main():
    argv = sys.argv[1:]
    def argval(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default
    wav = next((a for a in argv if not a.startswith("-")), "")
    label = argval("--label") or (os.path.splitext(os.path.basename(wav))[0].replace("example_melody_", "m"))
    outdir = argval("--outdir", os.path.join(os.path.abspath(os.path.join(HERE, "..", "..", "..")),
                                             "research", "analysis", "12hole"))
    rate, x = load_wav(wav)
    assert rate == 44100
    mono = (x[:, 0] + x[:, 1]) / 2 if x.shape[1] > 1 else x[:, 0]
    f0s, amps = f0_track(mono)
    pl = plateaus(f0s, amps)
    os.makedirs(outdir, exist_ok=True)
    print(f"{label}: {len(pl)} tone plateaus")
    trans = []
    for (a, b, ra), (c, d, rc) in zip(pl, pl[1:]):
        gap_start, gap_end = b, c
        f_start, f_end = f0s[ra], f0s[rc]
        cents = 1200 * math.log2(f_end / f_start)
        dur_ms = (c - b) * 10
        if dur_ms <= 0 or abs(cents) < 15:
            continue   # same pitch re-articulation — not a glide span
        # envelope mid-transition vs the two plateaus
        env_path = amps[b:c]
        env_dip = float(np.min(env_path) - min(amps[b - 1], amps[c + 1])) if len(env_path) else 0.0
        # where does f0 cross the halfway point (glide speed shape)
        mid_idx = None
        for t in range(gap_start, gap_end):
            cc = 1200 * math.log2(f0s[t] / f_start)
            if cc > 0.5 * cents:
                mid_idx = t - gap_start
                break
        path = [float(1200 * math.log2(f0s[t] / f_start)) for t in range(gap_start, gap_end)]
        trans.append({
            "from": et_name(f_start), "to": et_name(f_end),
            "cents": round(float(cents), 1),
            "from_t_ms": b * 10, "to_t_ms": c * 10, "dur_ms": dur_ms,
            "env_dip_db": round(env_dip, 1),
            "half_cross_frac": None if mid_idx is None else round(mid_idx / max(1, gap_end - gap_start), 2),
            "path_cents": [round(p, 1) for p in path],
        })
        print(f"  {trans[-1]['from']}-{trans[-1]['to']} {trans[-1]['cents']:+6.0f}c"
              f"  {dur_ms:4d} ms  dip {env_dip:5.1f} dB  half at {trans[-1]['half_cross_frac']}")
    out = {"wav": wav, "plateaus": [[b * 10, d * 10, et_name(f0s[rr])] for (a, b, x2), (c, d, rr) in [(None, p[1], p[2]) for p in pl]],
           "transitions": trans}
    out["plateaus"] = [{"on_ms": p[0] * 10, "off_ms": p[1] * 10,
                        "pitch": et_name(f0s[p[2]]), "f0": float(f0s[p[2]])} for p in pl]
    path = os.path.join(outdir, f"{label}_transitions.json")
    json.dump(out, open(path, "w"), indent=1)
    print("wrote", path)

if __name__ == "__main__":
    main()
