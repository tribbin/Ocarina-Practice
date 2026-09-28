# melody_cut.py — segment a melody WAV into per-note cuts and measure each
# with tone_report.analyze (the single-tone pipeline), so a melody recording
# (tone ladder, song take) yields per-plateau metrics exactly like held
# single notes. Silence around/between notes doubles as the measured noise
# baseline of the session.
#
# Usage: python melody_cut.py <wav> [--inst oot-alto-c-12] [--label L]
#        [--outdir research/analysis/12hole]
# Output: <outdir>/cuts/<label>/<NN>_<note>.wav + <outdir>/<label>_segments.json
# plus a printed summary table (per ET note: medians across segments).
import sys, os, json, struct, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tone_report import load_wav, dbfs, note_hz

SR = 44100.0
LET = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]

def inst_notes(inst):
    repo = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
    d = json.load(open(os.path.join(repo, "instruments", inst, "fingerings.json"), encoding="utf-8"))
    return [n["id"] for n in d["notes"]]

def write_mono(path, mono, sr=SR):
    n = len(mono)
    buf = bytearray(44 + n * 2)
    struct.pack_into("<4sI4s4sIHHIIHH4sI", buf, 0, b"RIFF", 36 + n * 2, b"WAVE",
                     b"fmt ", 16, 1, 1, int(sr), int(sr * 2), 2, 16, b"data", n * 2)
    buf[44:] = b"".join(struct.pack("<h", int(max(-32768, min(32767, v * 32767.0)))) for v in mono)
    open(path, "wb").write(bytes(buf))

def f0_by_autocorr(seg, sr=SR, fmin=150.0, fmax=2200.0):
    # coarse-to-fine AC on the segment's strongest sustained part: reduces
    # partial-dominance bias of plain argmax spectral peaks.
    n = len(seg)
    if n < 2048:
        return None
    i0 = max(0, n // 2 - 2048)
    s = seg[i0:i0 + 2048].copy()
    s -= s.mean()
    s *= np.hanning(2048)
    ac = np.correlate(s, s, mode="full")[2047:]
    lo, hi = int(sr / fmax), min(int(sr / fmin) + 1, len(ac) - 1)
    if hi - lo < 8:
        return None
    k = lo + int(np.argmax(ac[lo:hi]))
    # parabolic refine (ac[0] = lag 0)
    f = 1.0
    if 0 < k < len(ac) - 1:
        a, b, c = ac[k - 1], ac[k], ac[k + 1]
        d = 0.5 * (a - c) / (a - 2 * b + c + 1e-30)
        f = k + d
    return sr / f

def et_id(freq, notes):
    best, bc = None, 999
    for nid in notes:
        c = 1200 * math.log2(freq / note_hz(nid))
        if abs(c) < abs(bc):
            best, bc = nid, c
    return best, bc

def segment(mono, floor_db, min_on=0.09, min_off=0.09, min_gap=0.07, min_dur=0.12):
    hop = int(0.02 * SR)
    n = len(mono) // hop
    env = np.array([dbfs(mono[i * hop:(i + 1) * hop]) for i in range(n)])
    # span-adaptive thresholds: 45%/55% of the way from the measured noise
    # floor to the loudest note level — silence gaps close even when the
    # breath/reverb tail rides well above the raw floor.
    p95 = float(np.percentile(env, 95))
    on_t = floor_db + (p95 - floor_db) * 0.55
    off_t = floor_db + (p95 - floor_db) * 0.45
    above = env > on_t
    below = env < off_t
    k_on = max(1, int(min_on / 0.02))
    k_off = max(1, int(min_off / 0.02))
    # stateful scan: OFF -> ON needs k_on consecutive above frames,
    # ON -> OFF needs k_off consecutive below frames
    runs = []
    state = False
    run_on = run_off = 0
    start = 0
    for i in range(n):
        if not state:
            if above[i]:
                run_on += 1
                if run_on >= k_on:
                    state = True
                    start = i - k_on + 1
                    run_off = 0
            else:
                run_on = 0
        else:
            if below[i]:
                run_off += 1
                if run_off >= k_off:
                    runs.append((start, i - k_off + 1))
                    state = False
                    run_on = 0
            else:
                run_off = 0
    if state:
        runs.append((start, n))
    # merge runs closer than min_gap
    merged = []
    for r in runs:
        if merged and (r[0] - merged[-1][1]) * 0.02 < min_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    merged = [r for r in merged if (r[1] - r[0]) * 0.02 >= min_dur]
    # cuts span MID-SILENCE to MID-SILENCE: note k owns everything between
    # the midpoint of the gap before its onset and the midpoint of the gap
    # after its offset — full attack, full release tail, and a symmetric
    # slice of the true recording noise on both sides. First/last cut take
    # the whole leading/trailing silence the file offers.
    cuts = []
    for k, (a, b) in enumerate(merged):
        cs = 0.0 if k == 0 else 0.02 * (merged[k - 1][1] + a) / 2.0
        ce = len(mono) / SR if k == len(merged) - 1 else 0.02 * (b + merged[k + 1][0]) / 2.0
        cuts.append((cs, ce, a * 0.02, b * 0.02))
    return cuts, env, on_t, off_t, floor_db

def main():
    args = sys.argv[1:]
    wav = None
    def argval(flag, default=None, cast=str):
        return cast(args[args.index(flag) + 1]) if flag in args else default
    inst = argval("--inst", "oot-alto-c-12")
    label = argval("--label")
    outdir = argval("--outdir", os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")),
        "research", "analysis", "12hole"))
    if "--inst" in args: args[args.index("--inst") + 1] = ""
    if "--label" in args: args[args.index("--label") + 1] = ""
    if "--outdir" in args: args[args.index("--outdir") + 1] = ""
    for a in args:
        if a and not a.startswith("--") and not wav:
            wav = a
    label = label or (os.path.splitext(os.path.basename(wav))[0]
                      .replace("example_melody_", "m"))
    notes = inst_notes(inst)
    cuts_dir = os.path.join(outdir, "cuts", label)
    os.makedirs(cuts_dir, exist_ok=True)

    rate, x = load_wav(wav)
    assert rate == 44100, f"unexpected rate {rate}"
    if x.shape[1] > 1:
        d = 20 * np.log10(np.sqrt(np.mean((x[:, 0] - x[:, 1]) ** 2)) + 1e-12)
        ref = 20 * np.log10(np.sqrt(np.mean(x[:, 0] ** 2)) + 1e-12)
        if d > ref - 60:
            print(f"WARN: channels differ ({d:.1f} dBFS re {ref:.1f}) — mono-summed anyway")
    mono = (x[:, 0] + x[:, 1]) / 2.0 if x.shape[1] > 1 else x[:, 0]
    hop = int(0.02 * SR)
    env0 = np.array([dbfs(mono[i * hop:(i + 1) * hop]) for i in range(len(mono) // hop)])
    # edited recordings keep TRUE digital-silence gaps (recorder-cleared to
    # ~-240 dBFS); a raw percentile lands on the zeros and drags the adaptive
    # thresholds into the void (gaps then close only on true zeros and
    # neighbor takes merge). The floor must be the quiet NON-silent level,
    # measured over frames above the digital-zero belt; identical to the raw
    # percentile when the file has no digital silence.
    nonzero = env0[env0 > -110.0]
    floor_db = float(np.percentile(nonzero, 10)) if len(nonzero) else float(np.percentile(env0, 10))
    segs, env, on_t, off_t, floor = segment(mono, floor_db)
    print(f"{label}: floor {floor_db:.1f} dBFS, on {on_t:.1f}, off {off_t:.1f}, {len(segs)} segments")

    import tone_report
    segs_out = []
    for k, (t0, t1, on0, off0) in enumerate(segs):
        # cut = mid-silence boundary; the sounding span (on0..off0) rides along
        a = max(0, int(t0 * SR))
        b = min(len(mono), int(t1 * SR))
        cut = mono[a:b]
        f0 = f0_by_autocorr(cut)
        nid, cents = et_id(f0, notes) if f0 else (None, None)
        dur = len(cut) / SR
        cid = f"{k:02d}_{nid}"
        cut_path = os.path.join(cuts_dir, f"{cid}.wav")
        write_mono(cut_path, cut)
        rep = None
        err = None
        try:
            # short cuts lose too little plateau to the fixed 0.22/0.12
            # margins: scale them down for cuts whose sounding span is short.
            span = max(0.10, (off0 - on0))
            marg = (min(0.07, span * 0.30), min(0.06, span * 0.25))
            rep = tone_report.analyze(cut_path, nominal=nid, label=nid, margins=marg)
        except Exception as e:
            err = str(e)
        segs_out.append({
            "idx": k, "t0": float(t0), "t1": float(t1),
            "on": float(on0), "off": float(off0), "dur_cut_s": float(dur),
            "f0_hz": None if f0 is None else float(f0),
            "note": nid, "cents_vs_et": None if cents is None else float(cents),
            "cut": cut_path, "error": err,
            "report": rep,
        })
        flag = "" if rep else " [MEASURE FAIL]"
        print(f"  {k:02d} cut {t0:5.2f}-{t1:5.2f}  on {on0:5.2f}  f0 {(f0 or 0):6.1f}  ET {str(nid or '?'):4s}"
              f"  {cents if cents is not None else float('nan'):+5.0f}c  plateau {rep['envelope']['plateau_dbfs'] if rep else float('nan'):6.1f} dBFS"
              f"  wob {rep['envelope']['breath_wobble_std_pct'] if rep else float('nan'):.1f}%{flag}")

    out = {"wav": wav, "instrument": inst, "floor_dbfs": floor_db,
           "envelope_thr_db": {"on": float(on_t), "off": float(off_t)}, "segments": segs_out}
    jpath = os.path.join(outdir, f"{label}_segments.json")
    with open(jpath, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote", jpath)

if __name__ == "__main__":
    main()
