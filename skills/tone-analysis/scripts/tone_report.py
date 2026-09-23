# tone_report.py — analyze a single-tone WAV recording and emit JSON metrics.
#
# Usage: python tone_report.py <wav> [--nominal C5] [--json out.json] [--label C5]
# Measures: envelope (attack/overshoot/plateau/release, breath wobble), pitch
# (median f0, attack drop, drift, wobble), plateau harmonic ratios re H1 with
# third-span evolution, calibrated inter-harmonic noise bands (relative to f0),
# stability-filtered inharmonic islands, onset portrait (first 250 ms).
# numpy-only (no scipy). Calibration is self-contained (sine + noise self-tests).
import struct, sys, json, math, heapq
import numpy as np

SR = 44100.0
WIN = 4096; PAD = 8192; HOP = 1024
DB_EPS = 1e-12

NOTE_HZ = {n: 440.0 * 2 ** ((midi - 69) / 12)
           for note, midi in [("C", 0), ("Cs", 1), ("D", 2), ("Ds", 3), ("E", 4), ("F", 5),
                              ("Fs", 6), ("G", 7), ("Gs", 8), ("A", 9), ("As", 10), ("B", 11)]
           for midi2, n in [(0, note)]
           for midi in [0]}  # placeholder, real map below
def note_hz(n):
    m = {"C": 0, "Cs": 1, "D": 2, "Ds": 3, "E": 4, "F": 5, "Fs": 6,
         "G": 7, "Gs": 8, "A": 9, "As": 10, "B": 11}
    p = m[n[:-1]] + (int(n[-1]) + 1) * 12
    return 440.0 * 2 ** ((p - 69) / 12)

def load_wav(path):
    raw = open(path, "rb").read()
    i = 12; fmt = None; data = None
    while i + 8 <= len(raw):
        cid = raw[i:i+4]; sz = struct.unpack("<I", raw[i+4:i+8])[0]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", raw[i+8:i+24])
        elif cid == b"data":
            data = raw[i+8:i+8+sz]; break
        i += 8 + sz + (sz & 1)
    nch, rate, bits = fmt[1], fmt[2], fmt[5]
    n = len(data) // (nch * bits // 8)
    a = np.frombuffer(data, dtype="<i2").astype(np.float64) / (32768.0 if bits == 16 else 1)
    return rate, a.reshape(n, nch)

def dbfs(v): return float(20 * np.log10(np.sqrt(np.mean(v ** 2)) + DB_EPS))

def quad_db(y, i):
    a, b, c = y[i-1], y[i], y[i+1]
    d = 0.5 * (a - c) / (a - 2*b + c + 1e-30)
    return (i + d), (b - 0.25 * (a - c) * d)

def analyze(path, nominal=None, label=None):
    rate, x = load_wav(path)
    assert rate == 44100, f"unexpected rate {rate}"
    mono = x[:, 0] if x.shape[1] == 1 else (x[:, 0] + x[:, 1]) / 2.0
    N = len(mono)
    t = np.arange(N) / SR

    # ---------- self calibration ----------
    w = np.hanning(WIN); SUMW = float(np.sum(w))
    binw = SR / PAD
    freqs = np.fft.rfftfreq(PAD, 1 / SR)
    rng = np.random.default_rng(7)
    def stft(sig):
        return np.array([np.abs(np.fft.rfft(sig[i:i+WIN] * w, PAD))
                         for i in range(0, len(sig) - WIN, HOP)])
    errs = []
    for A, f0, ph in [(0.1, 500.0, 0.0), (0.1, 512.0, 1.1), (0.05, 490.0, 2.2), (0.2, 530.0, 0.5)]:
        s = A * np.sin(2 * np.pi * f0 * t + ph)
        sp = stft(s)
        idx = int(round(f0 / binw))
        pk = idx - 2 + int(np.argmax(sp[:, idx-2:idx+3].mean(axis=0)))
        errs.append((sp[:, pk].mean() * 2 / SUMW) / A)
    CAL = float(np.mean(errs))
    nz = rng.normal(0, 0.01, N)
    spn = stft(nz)
    i900, i2200 = int(np.searchsorted(freqs, 900)), int(np.searchsorted(freqs, 2200))
    NRMS = float(np.median(np.sqrt(np.mean(spn[:, i900:i2200] ** 2, axis=1))))
    NOISE_K = NRMS / 0.01          # per-bin rms = sigma * NOISE_K
    CORR = 20 * np.log10(NOISE_K)

    # dedup gain: one STFT pass (cache hashes)
    sig_key = object()
    cache = {}

    nf = (N - WIN) // HOP
    spec = np.zeros((nf, PAD // 2 + 1))
    for j in range(nf):
        spec[j] = np.abs(np.fft.rfft(mono[j*HOP:j*HOP+WIN] * w, PAD))
    t_stft = (np.arange(nf) * HOP + WIN / 2) / SR

    # ---------- f0 window ----------
    if nominal is None:
        nominal = label or "C5"
    f_nom = note_hz(nominal)
    lo_f, hi_f = f_nom * 0.85, f_nom * 1.15
    NH = 8
    H = np.zeros((nf, NH)); f0s = np.zeros(nf)
    for j in range(nf):
        l1 = int(np.searchsorted(freqs, lo_f)); h1 = int(np.searchsorted(freqs, hi_f))
        k = l1 + int(np.argmax(spec[j][l1:h1]))
        a_, b_, c_ = (20*np.log10(spec[j][k-1] + 1e-12), 20*np.log10(spec[j][k] + 1e-12), 20*np.log10(spec[j][k+1] + 1e-12))
        f0s[j] = (k + 0.5*(a_-c_)/(a_-2*b_+c_+1e-30)) * binw
        for hi_i in range(1, NH + 1):
            fk = hi_i * f0s[j]
            if fk * 1.05 > SR / 2:
                break
            l2 = max(1, int(0.96*fk/binw) - 1); h2 = min(PAD//2 - 1, int(1.04*fk/binw) + 1)
            if h2 - l2 < 3:
                continue
            seg = 20*np.log10(spec[j][l2:h2] + DB_EPS)
            kk = int(np.argmax(seg))
            aa, bb, cc = (seg[kk-1], seg[kk], seg[kk+1]) if 0 < kk < len(seg)-1 else (seg[kk],)*3
            dd = 0.5*(aa-cc)/(aa-2*bb+cc+1e-30)
            H[j, hi_i-1] = (10 ** ((bb - 0.25*(aa-cc)*dd) / 20)) * 2 / SUMW
    H /= CAL
    h_db = 20*np.log10(H + DB_EPS)
    h_rel = h_db - h_db[:, [0]]

    active = (f0s > lo_f) & (f0s < hi_f) & (H[:, 0] > 0.25*np.max(H[:, 0]))
    act = np.where(active)[0]
    if len(act) < 4:
        raise RuntimeError("no active frames found")
    t_on, t_off = t_stft[act[0]], t_stft[act[-1]]
    pl = np.array([j for j in act if (t_stft[j] > t_on + 0.22) and (t_stft[j] < t_off - 0.12)])
    if len(pl) < 3:
        pl = act
    out = {"label": label or nominal, "file": path, "duration_s": N / SR,
           "overall_rms_dbfs": dbfs(mono), "peak_dbfs": 20*np.log10(np.max(np.abs(mono)) + DB_EPS),
           "channel_rms_dbfs": [dbfs(x[:, 0])] if x.shape[1] == 1 else [dbfs(x[:, 0]), dbfs(x[:, 1])]}

    # ---------- pitch ----------
    med_f0 = float(np.median(f0s[pl]))
    on_f0 = float(np.median(f0s[act[:max(3, len(act)//12)]]))
    drift_e = float(np.median(f0s[pl[:max(2, len(pl)//4)]]))
    drift_l = float(np.median(f0s[pl[-max(2, len(pl)//4):]]))
    fv = f0s[pl]
    ok = (fv > f0s[act].min()*0.9) & (fv < f0s[act].max()*1.1)
    if ok.sum() >= 3:
        pred = np.polyval(np.polyfit(t_stft[pl[ok]], fv[ok], 1), t_stft[pl[ok]])
        cf = 1200*np.log2(fv[ok] / pred)
    else:
        cf = np.array([0.0])
    out["pitch"] = {
        "median_hz": med_f0,
        "cents_vs_et": 1200 * np.log2(med_f0 / f_nom),
        "attack_hz": on_f0,
        "attack_to_plateau_cents": 1200*np.log2(on_f0 / med_f0),
        "plateau_drift_cents": 1200*np.log2(drift_l / drift_e),
        "wobble_std_cents": float(cf.std()),
        "wobble_pp_cents": float(cf.max() - cf.min()),
    }

    # ---------- envelope ----------
    hop5 = 220
    n5 = (N - 441)
    env_db = np.array([dbfs(mono[i:i+882]) for i in range(0, n5, hop5)])
    t_env = np.arange(len(env_db)) * hop5 / SR
    smooth = np.convolve(env_db, np.ones(9)/9, mode="same")
    on_i = int(np.argmax(env_db > -40)); off_i = int(len(env_db)-1-np.argmax(env_db[::-1] > -40))
    plateau_level = float(np.median(smooth[on_i+30:off_i-10])) if off_i - on_i > 40 else float(np.max(smooth))
    pk_i = int(np.argmax(smooth))
    over = float(smooth[pk_i] - plateau_level)
    after = smooth[pk_i:] <= plateau_level - 1.0
    settle = (t_env[pk_i] + np.argmax(after) * hop5 / SR - t_env[pk_i]) if after.any() else None
    li = on_i + int(np.argmax(smooth[on_i:] >= plateau_level - 3))
    aw = smooth[max(0, on_i):min(on_i + 40, len(smooth))]  # first 200 ms of the sound
    att_over = float(np.max(aw) - plateau_level) if len(aw) else 0.0
    lin = 10**(env_db / 20)
    kernel = np.hanning(89); kernel /= kernel.sum()
    hf = lin - np.convolve(lin, kernel, mode="same")
    lo_w = int(np.searchsorted(t_env, t_on + 0.30))
    wob = hf[lo_w:off_i]
    mean_lin = float(np.mean(lin[lo_w:off_i]))
    wob_std = float(wob.std() / mean_lin)
    sp = np.abs(np.fft.rfft(wob * np.hanning(len(wob)), 2048))
    fr = np.fft.rfftfreq(2048, hop5 / SR)
    band = (fr > 0.3) & (fr < 10)
    ib = int(np.where(band)[0][np.argmax(sp[band])])
    rel = env_db[on_i:off_i]
    out["envelope"] = {
        "sounding_s": [float(t_env[on_i]), float(t_env[off_i])],
        "attack_to_plateau_s": float(t_env[min(li, len(t_env)-1)] - t_env[on_i]),
        "attack_overshoot_db": att_over,
        "attacks_max_overshoot_db": over,
        "overshoot_peak_s": float(t_env[pk_i]),
        "overshoot_settle_s": float(settle) if settle else None,
        "plateau_dbfs": 20*np.log10(np.sqrt(np.mean(mono[int((t_on+0.25)*SR):int((t_off-0.1)*SR)]**2)) + DB_EPS),
        "plateau_spread_db": float(np.percentile(env_db[on_i+30:off_i-10], 90) - np.percentile(env_db[on_i+30:off_i-10], 10)),
        "breath_wobble_std_pct": wob_std * 100,
        "breath_wobble_pp_pct": float((wob.max() - wob.min()) / mean_lin * 100),
        "wobble_dominant_hz": float(fr[ib]),
        "wobble_dominant_depth_pct": float(2*sp[ib] / max(len(wob), 1) / mean_lin * 100),
    }

    # ---------- timbre ----------
    h_med = [float(np.median(h_rel[pl, k])) for k in range(NH)]
    L3 = max(1, (pl[-1]-pl[0])//3)
    thirds = {}
    for nm, sel in [("early", pl[:L3]), ("mid", pl[L3:-L3]), ("late", pl[-L3:])]:
        thirds[nm] = [float(10**(np.median(h_rel[sel, k])/20)) for k in range(1, NH)]
    out["timbre"] = {
        "harmonic_ratio_re_H1_median": [10**(h/20) for h in h_med[1:]],
        "harmonic_db_re_H1_median": h_med[1:],
        "harmonic_p10": [float(10**(np.percentile(h_rel[pl, k], 10)/20)) for k in range(1, NH)],
        "harmonic_p90": [float(10**(np.percentile(h_rel[pl, k], 90)/20)) for k in range(1, NH)],
        "evolution_thirds": thirds,
        "H1_plateau_rms_dbfs": float(20*np.log10(np.median(H[pl, 0])/np.sqrt(2) + DB_EPS)),
    }

    # ---------- noise ----------
    h1r = float(20*np.log10(np.median(H[pl, 0]) / np.sqrt(2) + DB_EPS))  # plateau H1 rms dBFS
    def noise_rel(j, lo, hi, notchw=8):
        f0 = f0s[j]
        s = spec[j].copy()
        for k in range(1, 10):
            c = int(round(k*f0/binw))
            l1 = max(0, c-notchw); h2 = min(PAD//2, c+notchw+1)
            s[l1:h2] = 0
        m_ = (freqs > lo) & (freqs < hi)
        r = np.sqrt(np.mean(s[m_]**2))
        return 20*np.log10(r / NOISE_K + DB_EPS) - h1r
    noise_bands = {}
    bands = [(0.85, 1.95), (1.95, 3.9), (3.9, 7.0), (7.0, 12.0)]
    f_med = med_f0
    for r1, r2 in bands:
        vals = [noise_rel(j, r1*f_med, min(r2*f_med, SR/2 - 300)) for j in pl]
        noise_bands[f"{r1:.2f}-{r2:.2f}xf0"] = {
            "db_rel_H1_median": float(np.median(vals)),
            "p10": float(np.percentile(vals, 10)),
            "p90": float(np.percentile(vals, 90)),
        }
    # evolution of the first band by thirds
    L3b = max(1, (pl[-1]-pl[0])//3)
    evo = {}
    for nm, sel in [("early", pl[:L3b]), ("mid", pl[L3b:-L3b]), ("late", pl[-L3b:])]:
        evo[nm] = float(np.median([noise_rel(j, 0.85*f_med, 1.95*f_med) for j in sel]))
    # spectral centroid of notch-residual (noise color), energy 0.9-8k
    cents = []
    for j in pl:
        f0 = f0s[j]
        s = spec[j].copy()
        for k in range(1, 10):
            c = int(round(k*f0/binw))
            s[max(0, c-8):c+9] = 0
        m_ = (freqs > 0.9*f0) & (freqs < 8000)
        e = s[m_] ** 2
        cents.append(float(np.sum(e * freqs[m_]) / (np.sum(e) + DB_EPS)))
    out["noise"] = {"bands": noise_bands, "evolution_thirds": evo,
                    "residual_centroid_hz": float(np.median(cents))}

    # ---------- inharmonic islands ----------
    targets = [(1.03, 1.09), (1.44, 1.56), (2.03, 2.08), (2.44, 2.56), (2.97, 3.09), (3.03, 3.09), (0.44, 0.56)]
    found = {}
    for r1, r2 in targets:
        hits = []
        for j in pl[::2]:
            i0 = j*HOP
            S = np.abs(np.fft.rfft(mono[i0:i0+WIN]*w, PAD3 := 32768))
            f3 = np.fft.rfftfreq(PAD3, 1/SR)
            m_ = (f3 > r1*f0s[j]) & (f3 < r2*f0s[j])
            for k in (1, 2, 3):
                m_ &= np.abs(f3 - k*f0s[j]) > 30
            if not m_.any(): continue
            kk = int(np.where(m_)[0][np.argmax(S[m_])])
            aa, bb, cc = S[kk-1], S[kk], S[kk+1]
            dd = 0.5*(aa-cc)/(aa-2*bb+cc+1e-30)
            hits.append(((f3[kk]+dd*(SR/PAD3))/f0s[j], (bb - 0.25*(aa-cc)*dd)*2/SUMW))
        if len(hits) < 4: continue
        r_ = np.array([h[0] for h in hits]); a_ = np.array([h[1] for h in hits])
        ref = float(np.median(r_))
        keep = np.abs(r_-ref) < 0.003
        if keep.mean() < 0.55: continue
        lvl = 20*np.log10(np.median(a_[keep]) * 0.9843 / np.sqrt(2) + DB_EPS) - h1r
        if lvl < -75: continue
        found[f"{ref:.3f}xf0"] = {"db_rel_H1": float(lvl), "stable_frames": float(keep.mean())}
    out["inharmonic_islands"] = found or None

    # ---------- onset portrait ----------
    W2 = 1024; P2 = 16384
    w2 = np.hanning(W2); n2 = P2//2+1
    f2 = np.fft.rfftfreq(P2, 1/SR); b2 = SR/P2
    def amp_at(S, fr_, frac=0.025):
        lo = max(1, int(np.searchsorted(f2, fr_*(1-frac))))
        hi = min(n2-1, int(np.searchsorted(f2, fr_*(1+frac)))+1)
        return float(np.max(S[lo:hi])) * 2 / np.sum(w2)
    portrait = []
    for ms in range(8, 260, 25):
        i0 = int(ms/1000*SR)
        if i0+W2 > N: break
        S = np.abs(np.fft.rfft(mono[i0:i0+W2]*w2, P2))
        l1 = int(np.searchsorted(f2, lo_f)); h1i = int(np.searchsorted(f2, hi_f))
        kd = l1 + int(np.argmax(S[l1:h1i]))
        if kd <= 0 or kd >= n2-1: continue
        d = 0.5*(S[kd-1]-S[kd+1])/(S[kd-1]-2*S[kd]+S[kd+1]+1e-30)
        f0e = (kd+d)*b2
        h1 = amp_at(S, f0e)
        if h1 < 1e-6: continue
        portrait.append({
            "t_ms": float(ms), "f0_est_hz": float(f0e),
            "H1_dbfs": float(20*np.log10(h1/np.sqrt(2)+DB_EPS)),
            "H2_ratio": float(amp_at(S, 2*f0e, 0.015)/h1),
            "H3_ratio": float(amp_at(S, 3*f0e, 0.015)/h1),
        })
    # broadband burst profile: 1f0..2.85f0 minus harmonic notches, rel plateau H1 rms
    W3 = 2048; P3b = 16384
    w3 = np.hanning(W3); f3 = np.fft.rfftfreq(P3b, 1/SR)
    notchw3 = 9
    burst = []
    for ms in range(0, 260, 20):
        i0 = int(ms/1000*SR)
        if i0+W3 > N: break
        S = np.abs(np.fft.rfft(mono[i0:i0+W3]*w3, P3b))
        m_ = (f3 > 0.95*f_med) & (f3 < 2.85*f_med)
        m_ &= np.abs(f3 - 2.01*f_med) > 0.02*f_med
        for k in (1, 2, 3, 4, 5):
            c = int(round(k*f_med/(SR/P3b)))
            m_[max(0, c-notchw3):c+notchw3+1] = False
        r = float(np.sqrt(np.mean(S[m_]**2)) / np.sqrt(0.375*W3))
        burst.append({"t_ms": float(ms + W3/2/SR*1000),
                      "db_rel_plateau_H1": float(20*np.log10(r/np.sqrt(2)+DB_EPS) - h1r)})
    out["onset"] = {"portrait": portrait, "burst_profile": burst}
    return out

if __name__ == "__main__":
    path = sys.argv[1]
    nominal = None; label = None; jout = None
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--nominal": nominal = args[i+1]
        if a == "--label": label = args[i+1]
        if a == "--json": jout = args[i+1]
    r = analyze(path, nominal, label)
    s = json.dumps(r, indent=1)
    print(s)
    if jout:
        open(jout, "w").write(s)
