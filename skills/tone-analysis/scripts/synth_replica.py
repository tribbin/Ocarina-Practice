# synth_replica.py — numpy replica of js/audio.js's dry-path voice for fast
# local tuning iterations. Chromium offline rendering of the full voice hangs
# out; realtime headless has no audio clock; the debug panel's Export WAV
# button is the browser-side audit of the final tuned values.
#
# Same parameters as window.OCA_DEBUG.params; note articulation from repo
# fingerings.json. Mono 44.1 kHz float32. No reverb/limiter (matches the
# offline comparison harness: dry bus == getLiteBus-style outGain).
import json, math, os
import numpy as np

SR = 44100.0
APP = r"C:\Users\tribb\Documents\git\Triple-Bass-in-C-Ocarina-Tab-Maker"

_df = json.load(open(os.path.join(APP, "fingerings.json"), encoding="utf-8"))
NAMES = {"C": 0, "Cs": 1, "D": 2, "Ds": 3, "E": 4, "F": 5, "Fs": 6,
         "G": 7, "Gs": 8, "A": 9, "As": 10, "B": 11}
FREQ = {n["id"]: 440.0 * 2 ** ((NAMES[n["id"][:-1]] + (int(n["id"][-1]) + 1) * 12 - 69) / 12)
        for n in _df["notes"]}
NOTES = [n["id"] for n in _df["notes"]]
COVER = {n["id"]: len(n["covered"]) for n in _df["notes"]}
MAXCOVER = {}
for _n in _df["notes"]:
    MAXCOVER[_n["chamber"]] = max(MAXCOVER.get(_n["chamber"], 0), len(_n["covered"]))

DEFAULTS = dict(
    h2Mul=1, h3Mul=1, h4Mul=1, h5Mul=1,
    hardAmt=1, levelCurveAmt=1, wanderAmt=1, wobbleAmt=1, windAmt=1,
    lpMult=4.2, lpMax=9000, lpQ=0.70,
    hiFrom=660, hiTo=1568,
    airLevel=0.0, airFade=0.75, airRatio=2.01,
    vibRate=5.5, vibDepth=0.0035, vibHighFade=0.4, tremDepth=0.05,
    edgeBase=0.0008, edgeReg=0.0005, edgeFade=0.7,
    edgeDet=0.012, edgeDetSpread=0.008,
    wanderDepth=0.006, wanderFade=0.8,
    chiffScale=0.25, chiffBase=0.075, chiffSize=0.05,
    otBase=0.00137, otEffort=0.0011, otNoise=0.35,
    otDurMax=0.10, otDurEffort=0.05,
    masterLevel=0.40,
    reverbWet=0.20,
)

# ---- pitch-keyed voice profile (MIRROR of V_ANCHORS in js/audio.js) ----
# Keep this in sync with the JS table; the JS table is the source of truth.
V_ANCHORS = {
    "h2": [[220, 0.0095], [523.25, 0.00469], [1174, 0.0040], [1568, 0.0033]],
    "h3": [[220, 0.0140], [523.25, 0.0076], [1174, 0.0090], [1568, 0.021]],
    "h4": [[220, 0.0015], [523.25, 0.00077], [1174, 0.0008], [1568, 0.0096]],
    "h5": [[220, 0.0017], [523.25, 0.0015], [1174, 0.0006], [1568, 0.0017]],
    "levelDb": [[220, -2.5], [523.25, 0], [1174, 6.7], [1568, 4.6]],
    "wanderC": [[220, 9.0], [523.25, 6.9], [1174, 1.3], [1568, 1.05]],
    "wobPct": [[220, 7.0], [523.25, 5.5], [1568, 4.9]],
    "wobHz": [[220, 2.0], [523.25, 2.5], [1568, 4.5]],
    "noiseLoDb": [[220, -22.0], [523.25, -25.9], [1174, -28.6], [1568, -29.4]],
    # chamber-resonance bump sharpness of the breath noise: high Q on the bass
    # chamber (hiss concentrated just above the tone), broad on the top one.
    # Anchored at A3 too: below C5 the bump must NOT keep narrowing.
    "noiseBumpQ": [[220, 6.0], [523.25, 9.0], [1568, 2.5]],
    "attackF": [[220, 0.9], [523.25, 1.0], [1174, 1.25], [1568, 1.75]],
}

# Wind-noise spectral-shape constants (mirrored in js/audio.js):
# white -> chamber bump (1.26*f0, pitch-keyed Q) -> steep noise lowpass.
WIND_SHAPE = dict(bumpRatio=1.26, noiseLpRatio=2.7, noiseLpQ=1.2,
                  bumpTrim=-2.0)

def v_interp(pts, f):
    for i in range(len(pts) - 1):
        f0, v0 = pts[i][0], pts[i][1]
        f1, v1 = pts[i + 1][0], pts[i + 1][1]
        if f <= f1:
            t = max(-1.5, min(1.5, math.log2(f / f0) / math.log2(f1 / f0)))
            return v0 + (v1 - v0) * t
    f0, v0 = pts[-2][0], pts[-2][1]
    f1, v1 = pts[-1][0], pts[-1][1]
    slope = (v1 - v0) / math.log2(f1 / f0)
    return v1 + slope * max(-1.5, min(1.5, math.log2(f / f1)))

def _profile(note_id, freq, P, rng):
    sizeF, openF = _articulation(note_id)
    hh = max(0.0, min(1.0, openF * (0.25 + 0.75 * sizeF) * P["hardAmt"]))
    db2lin = lambda db: 10 ** (db / 20)
    return {
        "h": [1,
              v_interp(V_ANCHORS["h2"], freq) * P["h2Mul"],
              v_interp(V_ANCHORS["h3"], freq) * P["h3Mul"],
              v_interp(V_ANCHORS["h4"], freq) * P["h4Mul"],
              v_interp(V_ANCHORS["h5"], freq) * P["h5Mul"]],
        "levelLin": db2lin(v_interp(V_ANCHORS["levelDb"], freq) * P["levelCurveAmt"]),
        "windBump": db2lin(v_interp(V_ANCHORS["noiseLoDb"], freq) + WIND_SHAPE["bumpTrim"]) * P["windAmt"],
        "windQ": v_interp(V_ANCHORS["noiseBumpQ"], freq),
        "wanderC": (v_interp(V_ANCHORS["wanderC"], freq) + 2.0 * hh) * P["wanderAmt"],
        "wobDepth": (v_interp(V_ANCHORS["wobPct"], freq) + 2.5 * hh) / 100 * P["wobbleAmt"],
        "wobRate": (v_interp(V_ANCHORS["wobHz"], freq) + 1.2 * hh) * (0.9 + 0.2 * float(rng.random())),
        "attackF": v_interp(V_ANCHORS["attackF"], freq),
        "osDb": 0.8 + 3.2 * hh,
        "hh": hh,
    }

def _articulation(note_id):
    ch = next(n["chamber"] for n in _df["notes"] if n["id"] == note_id)
    sizeF = (3 - ch) / 2.0 if 3 > 1 else 1.0
    openF = max(0.0, min(1.0, 1.0 - COVER[note_id] / MAXCOVER[ch]))
    return sizeF, openF

def _reg(note_id, freq):
    rng = {}
    for n in _df["notes"]:
        c = n["chamber"]; f = FREQ[n["id"]]
        lo, hi = rng.get(c, (f, f))
        rng[c] = (min(lo, f), max(hi, f))
    lo, hi = rng[next(n["chamber"] for n in _df["notes"] if n["id"] == note_id)]
    if hi > lo:
        return max(0.0, min(1.0, math.log2(freq / lo) / math.log2(hi / lo)))
    return max(0.0, min(1.0, math.log2(freq / 262.0) / 2.0))

# ---- envelopes: web-audio automation semantics ----
def _segments(evlist):
    segs = []
    cur_t, cur_v = 0.0, evlist[0][2] if evlist else 0.0001
    for kind, t2, v2 in evlist:
        if kind == "set":
            if t2 > cur_t:
                segs.append((cur_t, t2, cur_v, cur_v, "hold"))
            cur_t, cur_v = t2, v2
        else:
            if t2 > cur_t:
                segs.append((cur_t, t2, cur_v, v2, kind))
            cur_t, cur_v = t2, v2
    segs.append((cur_t, 1e18, cur_v, cur_v, "hold"))
    return segs

def _seg_value(tt, t0_, t1_, v0_, v1_, kind):
    if kind == "lin":
        r = (tt - t0_) / max(t1_ - t0_, 1e-9)
        return v0_ + r * (v1_ - v0_)
    if kind == "exp":
        if v0_ <= 0 or v1_ <= 0:
            return np.full(tt.shape, v1_)
        r = (tt - t0_) / max(t1_ - t0_, 1e-9)
        return v0_ * (v1_ / v0_) ** r
    return np.full(tt.shape, v0_)

def env_(evlist, n, sr=SR):
    t = np.arange(n) / sr
    out = np.empty(n)
    for (a, b, v0, v1, kind) in _segments(evlist):
        m = (t >= a) & (t < b)
        if m.any():
            out[m] = _seg_value(t[m], a, b, v0, v1, kind)
    out[t >= _segments(evlist)[-1][0]] = _segments(evlist)[-1][2]
    return out

def rbj(kind, fc, q, sr=SR):
    w = min(max(fc, 1.0), 0.45 * sr) * 2 * np.pi / sr
    s, c = np.sin(w), np.cos(w)
    al = s / (2 * q)
    if kind == "lowpass":
        b0, b1, b2 = (1 - c) / 2, 1 - c, (1 - c) / 2
    elif kind == "highpass":
        b0, b1, b2 = (1 + c) / 2, -(1 + c), (1 + c) / 2
    else:
        b0, b1, b2 = al, 0.0, -al
    a0, a1, a2 = 1 + al, -2 * c, 1 - al
    return (b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)

def bq(x, coefs, state=None):
    y = np.empty_like(x)
    if state is None:
        x1 = x2 = y1 = y2 = 0.0
    else:
        x1, x2, y1, y2 = state
    for i in range(len(x)):
        b0, b1, b2, a1, a2 = coefs
        y[i] = b0 * x[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1 = x1, x[i]
        y2, y1 = y1, y[i]
    return y, (x1, x2, y1, y2)

def bq_sweep(x, centers, kind, q, sr=SR, chunk=256):
    y = np.empty_like(x)
    st = None
    for i in range(0, len(x), chunk):
        j = min(i + chunk, len(x))
        fc = float(np.mean(centers[i:j])) if j - i > 1 else centers[i]
        y[i:j], st = bq(x[i:j], rbj(kind, fc, q, sr), st)
    return y

def render(params, note="C5", dur=1.54, seed=12345, sr=SR, vib=False):
    P = dict(DEFAULTS); P.update(params)
    freq = FREQ[note]
    sizeF, openF = _articulation(note)
    effort = max(0.0, min(1.0, 0.6 * sizeF + 0.4 * openF))
    reg = _reg(note, freq)
    hiF = max(0.0, min(1.0, (freq - P["hiFrom"]) / max(60.0, P["hiTo"] - P["hiFrom"])))

    rng = np.random.default_rng(seed)
    vp = _profile(note, freq, P, rng)
    M = P["masterLevel"] * vp["levelLin"]
    preL = M * (0.05 / 0.26); toneL = M * (0.16 / 0.26)

    dur = max(0.12, dur)
    N = int(sr * (dur + 0.55))
    tail = 0.03
    rel = min(0.18, max(0.05, dur * 0.35))
    relStart = max(0.02, dur - rel)

    # master envelope (+ recorded-scale attack overshoot bump)
    speak = min(0.05, max(0.006, dur * 0.08)) * (0.5 + effort) * vp["attackF"]
    equilib = min(dur * 0.4, sizeF * sizeF * 0.16)
    t1, t2 = speak * 0.5, speak + 0.015
    t3 = min(relStart - 0.005, max(t2 + 0.015, t2 + equilib))
    osLin = 10 ** (vp["osDb"] / 20)
    ev = [("set", 0, 0.0001), ("lin", t1, preL), ("lin", t2, toneL)]
    if osLin > 1.02:
        osAt = min(t3 - 0.01, t2 + max(0.03, (t3 - t2) * 0.45))
        ev += [("lin", osAt, M * osLin), ("lin", t3, M)]
    else:
        ev += [("lin", t3, M)]
    ev += [("set", relStart, M), ("lin", dur, 0.0001), ("set", dur + tail, 0.0001)]
    master = env_(ev, N, sr)

    # ---- osc: peak-normalized cos wave + freq automation (+ wander FM) ----
    th = np.linspace(0, 2 * np.pi, 8192, endpoint=False)
    wave = sum(vp["h"][k - 1] * np.cos(k * th) for k in range(1, 6))
    wave = wave / (np.max(np.abs(wave)) + 1e-12)
    rise = min(0.03, max(0.01, dur * 0.12)) * (0.7 + 0.3 * effort)
    flat = 0.993 - 0.007 * effort
    over = 1.002 + 0.004 * effort
    f_inst = freq * env_([("set", 0, flat), ("lin", rise, over),
                          ("exp", rise + rise * 0.9, 1.0), ("set", relStart, 1.0),
                          ("lin", dur, 1 - (0.01 + 0.008 * effort))], N, sr)
    tt = np.arange(N) / sr

    # slow intrinsic wander: quasi-random meander from two incommensurate
    # LFOs (triangle + sine), driving pitch + loudness in phase
    wob_p = None
    if vp["wanderC"] > 0.01 or vp["wobDepth"] > 0.0005:
        r_in = env_([("set", 0, 0.0001), ("lin", 0.35, 1.0)], N, sr)
        wobA = 0.85 * r_in
        comps = [(0.85, vp["wobRate"], True),
                 (0.6, vp["wobRate"] * (0.61 + 0.08 * float(rng.random())), False)]
        wob_p = np.zeros(N)
        wob_a = np.zeros(N)
        for share, rate, tri in comps:
            ph = 2 * np.pi * rate * tt
            if tri:
                tf = (ph / (2 * np.pi) + 0.25) % 1.0
                s = 4.0 * np.abs(tf - 0.5) - 1.0
            else:
                s = np.sin(ph)
            wob_p += share * s
            wob_a += share * s
        wob_depth = freq * (2 ** (vp["wanderC"] * 1.2 / 1200) - 1)
        f_inst = f_inst + wob_depth * wob_p * r_in

    if vib and P["vibDepth"] > 0 and dur > 0.45:
        vibEnv = env_([("set", 0, 0.0), ("set", 0.35, 0.0),
                       ("lin", 0.55, freq * P["vibDepth"] * (1 - P["vibHighFade"] * hiF))], N, sr)
        f_inst = f_inst + vibEnv * np.sin(2 * np.pi * P["vibRate"] * np.arange(N) / sr)
    phase = 2 * np.pi * np.cumsum(f_inst) / sr
    pos = (phase % (2 * np.pi)) / (2 * np.pi) * 8192
    i0 = np.floor(pos).astype(np.int64) % 8192
    i1 = (i0 + 1) % 8192
    frac = pos - np.floor(pos)
    tone = wave[i0] * (1 - frac) + wave[i1] * frac

    # ---- air partial (pre-lp) ----
    pre = tone
    if P["airLevel"] > 0:
        lvl = P["airLevel"] * (1 - P["airFade"] * hiF)
        a_env = env_([("set", 0, 0.0001), ("lin", 0.03, lvl), ("set", relStart, lvl),
                      ("lin", dur, 0.0001)], N, sr)
        pre = pre + np.sin(2 * np.pi * freq * P["airRatio"] * np.arange(N) / sr) * a_env

    # ---- lp + tremolo (wob amp wobble, in phase with its FM) + master ----
    fc = min(P["lpMax"], freq * P["lpMult"])
    lped, _ = bq(pre, rbj("lowpass", fc, P["lpQ"], sr))
    if wob_p is not None:
        wob_amp = vp["wobDepth"] * 0.85 * wob_a * r_in
        lped = lped * (1 + wob_amp)
    if vib and P["tremDepth"] > 0 and dur > 0.45:
        tr = env_([("set", 0, 0.0), ("set", 0.35, 0.0), ("lin", 0.55, P["tremDepth"])], N, sr)
        lped = lped * (1 + tr * np.sin(2 * np.pi * P["vibRate"] * np.arange(N) / sr))
    core = lped * master

    # ---- edge / windway whistle (bypasses lp, into master) ----
    if P["edgeBase"] > 0:
        det = 1 + P["edgeDet"] + float(rng.random()) * P["edgeDetSpread"] * (1 - hiF)
        wrate = 7 + float(rng.random()) * 4
        wdepth = freq * P["wanderDepth"] * (1 - P["wanderFade"] * hiF)
        f_edge = freq * det + wdepth * np.sin(2 * np.pi * wrate * np.arange(N) / sr)
        phase_e = 2 * np.pi * np.cumsum(f_edge) / sr
        edge = np.sin(phase_e)
        bp_centers = np.clip(f_edge, 20, sr * 0.45)
        ebp = bq_sweep(edge, bp_centers, "bandpass", 4.0, sr)
        lvl = (P["edgeBase"] + reg * reg * P["edgeReg"]) * (1 - P["edgeFade"] * hiF)
        e_env = env_([("set", 0, 0.0001), ("lin", 0.03, lvl), ("set", relStart, lvl),
                      ("lin", dur, 0.0001)], N, sr)
        core = core + ebp * e_env

    # ---- broadband wind noise: white -> chamber bump -> steep noise LP ----
    if vp["windBump"] > 1e-5:
        nb = int(sr * 0.5)
        nbuf = rng.random(nb) * 2 - 1
        k = int(sr * 0.01)  # 10 ms seam crossfade — mirror of getWindBuffer
        w = (np.arange(k) + 1) / (k + 1)
        nbuf[-k:] = nbuf[-k:] * (1 - w) + nbuf[:k] * w
        reps = int(np.ceil(N / nb))
        nsrc = np.tile(nbuf, reps)[:N]
        wb, _ = bq(nsrc, rbj("bandpass", min(9000, freq * WIND_SHAPE["bumpRatio"]),
                             vp["windQ"], sr))
        wb, _ = bq(wb, rbj("lowpass", min(SR * 0.45, freq * WIND_SHAPE["noiseLpRatio"]),
                           WIND_SHAPE["noiseLpQ"], sr))
        wl_env = env_([("set", 0, 0.0001), ("lin", 0.06, 1.0), ("set", relStart, 1.0),
                       ("lin", dur, 0.0001)], N, sr)
        core = core + wb * (vp["windBump"] * wl_env)

    # ---- chiff ----
    if P["chiffScale"] > 0:
        chiffLen = min((P["chiffBase"] + sizeF * P["chiffSize"]) * (0.85 + 0.15 * openF),
                       relStart - 0.005)
        bright = min(9.0, 2 ** ((1 - sizeF) * 3.5 + openF * 1.2))
        startHz, endHz = min(11000, 900 * bright), min(9000, 500 * bright)
        nb = int(sr * 0.5)
        nbuf = rng.random(nb) * 2 - 1
        src_len = int((chiffLen + 0.02) * sr)
        no = np.zeros(N); no[:src_len] = nbuf[:src_len]
        hp, _ = bq(no, rbj("highpass", max(300, 300 * bright * 0.4), 0.7, sr))
        k = max(1, int(chiffLen * 0.6 * sr))
        centers = np.full(N, endHz)
        centers[:k] = startHz * (endHz / startHz) ** (np.arange(k) / k)
        lps = bq_sweep(hp[:src_len] if False else hp, centers, "lowpass", 0.4, sr)
        chAtk = max(0.012, min(0.025, chiffLen * 0.3))
        peak = (0.018 - 0.0812 * sizeF + 0.1412 * sizeF * sizeF) * P["chiffScale"]
        ch_env = env_([("set", 0, 0.0001), ("lin", chAtk, peak),
                       ("lin", chiffLen * 0.5, peak * 0.85), ("lin", chiffLen, 0.0)], N, sr)
        core = core + lps * ch_env

    # ---- onset octave overtone ----
    otF = freq * 2
    if otF < sr * 0.45 and P["otBase"] > 0:
        otRoom = relStart - 0.005
        otDur = max(0.04, min(otRoom, P["otDurMax"] + P["otDurEffort"] * effort))
        otPeak = P["otBase"] + P["otEffort"] * effort
        o_env = env_([("set", 0, 0.0001), ("lin", min(0.02, otDur * 0.25), otPeak),
                      ("exp", otDur, 0.0001)], N, sr)
        f_ot = otF * env_([("set", 0, 1.004), ("lin", otDur, 1.0)], N, sr)
        ot = np.sin(2 * np.pi * np.cumsum(f_ot) / sr)
        nb = int(sr * 0.5)
        n2 = rng.random(nb) * 2 - 1
        nsrc = np.zeros(N); nsrc[:int((otDur + 0.02) * sr)] = n2[:int((otDur + 0.02) * sr)]
        kb = max(1, int(otDur * 0.7 * sr))
        centers2 = np.full(N, otF)
        centers2[:kb] = otF * 1.02 * (1 / 1.02) ** (np.arange(kb) / kb)
        nbp = bq_sweep(nsrc, centers2, "bandpass", 18.0, sr)
        core = core + (ot + nbp * P["otNoise"]) * o_env

    return (core * 0.6).astype(np.float32)

def save_wav(path, f32, sr=SR):
    import struct
    n = len(f32)
    buf = bytearray(44 + n * 2)
    struct.pack_into("<4sI4s4sIHHIIHH4sI", buf, 0, b"RIFF", 36 + n * 2, b"WAVE",
                     b"fmt ", 16, 1, 1, int(sr), int(sr * 2), 2, 16, b"data", n * 2)
    for i, v in enumerate(f32):
        struct.pack_into("<h", buf, 44 + i * 2, int(max(-32768, min(32767, v * 0x7FFF))))
    open(path, "wb").write(bytes(buf))

if __name__ == "__main__":
    import sys, time
    args = sys.argv[1:]
    jobs = []
    for a in args or []:
        note, _, dur = a.partition(":")
        jobs.append((note, float(dur) if dur else 2.0))
    if not jobs:
        # default audit set: the three measured anchors + both unmeasured
        # extrapolation zones (bass floor + chamber-2 top)
        jobs = [("A3", 2.0), ("C5", 1.54), ("C6", 2.0), ("D6", 1.73), ("G6", 2.13)]
    for note, dur in jobs:
        t0 = time.time()
        y = render({}, note, dur)
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "replica_%s.wav" % note)
        save_wav(out, y)
        print("%s: %d samples, %.2f s render, peak %.4f -> %s"
              % (note, len(y), time.time() - t0, float(np.max(np.abs(y))), out))
