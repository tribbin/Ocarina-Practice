# fit_tone.py — the 12-hole per-note fit loop (melody recordings → tone.json).
#
# Stage 1 (aggregate): merge every measured melody cut into per-note records.
# The FIT VALUE rides the LADDER only (Robin: the C-major ladder is the clean
# single-note-grade material; kokiri/storms contain transients, glides and
# multi-note spans — corroboration context, never a row source). Notes the
# ladder does not cover stay unfitted; the loader interpolates between their
# neighbouring rows.
#
# Stage 2 (fit): render candidate rows through the offline bench
# (render_ours.py with --tone <candidate>), measure with the SAME pipeline,
# then solve per-field corrections in dB/algebra space and re-render until
# the residual table converges. Emits a tone.json draft (tone-fit-v1, one row
# per note — the loader interpolates nothing between them inside the range).
#
# Usage:
#   python fit_tone.py targets          # stage 1
#   python fit_tone.py fit [--rounds 3] # stage 2
#   python fit_tone.py render           # render BASELINE (generic model) set
import json, os, subprocess, sys, statistics, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tone_report import load_wav as _load_wav

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
AN = os.path.join(REPO, "research", "analysis", "12hole")
INST = "oot-alto-c-12"
RENDERS = os.path.join(AN, "renders")
CAND = os.path.join(AN, "candidate_tone.json")
DRAFT_TONE = os.path.join(AN, "oot-alto-c-12.tone.draft.json")
OUT_TONE = os.path.join(REPO, "instruments", INST, "tone.json")

# Robin's hard rule (2026-09-27): kokiri and storms are NEVER held-tone
# references — they stay transition/glide CONTEXT only, for every tool and
# every fitting (the old B4 kokiri bridge is retired with the rule). Notes
# the ladder can't support value the ladder's own held part, and any field
# a short/blipped ladder take can't carry (onset domains) holds the nearest
# clean ladder neighbor:
#   B4: the ladder's only take opens with the re-blow blip — held-part
#       fields (harmonics/level/wobble/wind) come from its plateau frames;
#       the onset fields (atk/chiff) hold Cs5's (the pivot whose take has
#       the earliest clean ladder onset), so the blip's own burst never
#       becomes B4's row.
# (The B4 onset hold retired 2026-09-27: Robin's held-note recording
# (research/note-recordings/12hole/B4-held.wav) gives B4 a real take with
# its own clean onset — no neighbor fields needed.)
NEIGHBOR_ONSET_HOLD = {}

# The global noise-wall constants the shipped engine carries (WIND_SHAPE in
# js/audio.js, mirrored here and in synth_replica/wind_shape_search); the
# per-note rows noiseLpRatio/noiseLpQ grow from these in the fit loop.
NOISE_WALL = {"ratio": 2.6, "q": 0.8}


def wobble_measurable(t):
    """Robin, 2026-09-27: a short held span cannot imply a wobble (the B4
    bridge's 9.4 Hz/10.7% reading was onset-driven; his recording carries none
    worth louder). A plateau statistic needs real cycles after the 220 ms
    attack margin — takes under 0.40 s span skip the wobble/wander fields and
    the load-time fallback keeps the generic anchored doctrine (interpolate
    from the ladder, exactly as the loader's missing-field fallback does)."""
    return (t.get("span") or 0.0) >= 0.40

# Single-take smoothing of the wind rows (noiseLoDb): the take-to-take blow
# variance is ±3 dB but single 12-hole takes sat 7-9 dB above their neighbors
# (Robin's raspiness catch on B5/C6) — the row takes the median of the note
# and its pitch neighbours, never the raw outlier alone.

FREQ = {}
def note_hz(n):
    NAMES = {"C": 0, "Cs": 1, "D": 2, "Ds": 3, "E": 4, "F": 5, "Fs": 6,
             "G": 7, "Gs": 8, "A": 9, "As": 10, "B": 11}
    objects = NAMES[n[:-1]] + (int(n[-1]) + 1) * 12
    return 440.0 * 2 ** ((objects - 69) / 12)

def load_sources(sources=("ladder", "held", "kokiri", "storms"), primary="ladder"):
    out = {}  # note -> [take dicts, best first]
    def push(nid, take):
        if nid is None:
            return
        out.setdefault(nid, {}).setdefault("takes", []).append(take)
    for name in sources:
        path = os.path.join(AN, f"{name}_segments.json")
        if not os.path.exists(path):
            print(f"skip {name}: no segments json")
            continue
        data = json.load(open(path))
        for s in data["segments"]:
            r = s.get("report")
            if not r:
                continue
            nid = s["note"]
            t = r["timbre"]
            h = t["harmonic_ratio_re_H1_median"]
            bands = r["noise"]["bands"]
            env = r["envelope"]
            p = r["pitch"]
            take = {
                "source": name, "on": s["on"], "off": s["off"],
                "cutStart": s["t0"], "cut": s.get("cut"),
                "cents": p["cents_vs_et"],
                "h2": h[0], "h3": h[1], "h4": h[2], "h5": h[3],
                "h1db": t["H1_plateau_rms_dbfs"],
                "plateau": env["plateau_dbfs"],
                "band1": bands["0.85-1.95xf0"]["db_rel_H1_median"],
                "band2": bands["1.95-3.90xf0"]["db_rel_H1_median"],
                "band3": bands["3.90-7.00xf0"]["db_rel_H1_median"],
                "band4": bands["7.00-12.00xf0"]["db_rel_H1_median"],
                "wobPct": env["breath_wobble_std_pct"],
                "wobHz": env["wobble_dominant_hz"],
                "attack": env["attack_to_plateau_s"],
                "osDb": env["attack_overshoot_db"],
                "wanderC": p["wobble_std_cents"],
                "islands": r.get("inharmonic_islands") or {},
            }
            take["span"] = max(0.01, s["off"] - s["on"])
            # attack stages: the time to full level is the mask-free plateau
            # metric already measured; the pre-breath fraction rides the
            # onset portrait's own H1 level at ~10 ms vs the plateau H1.
            prof = ((r.get("onset") or {}).get("portrait") or [])
            early_h1 = [p["H1_dbfs"] for p in prof if p["t_ms"] <= 14]
            if early_h1:
                take["atkPre"] = round(min(0.999, 2 ** ((early_h1[0] - t["H1_plateau_rms_dbfs"]) / 6.02)), 4)
            # onset-derived chiff (the recorded tongue transient IS the aim —
            # Robin: "use my recordings of transients for the tap"; the bursts
            # run -40..-55 dB rel plateau H1 while the shipped generic chiff
            # sits ~12 dB hotter, the sand-paper texture on the keyboard's
            # B5/C6 hovers). peak = the burst's own dB rel plateau H1; len =
            # where it first falls 6 dB under the peak (else 0.08 s).
            burst = ((r.get("onset") or {}).get("burst_profile") or [])
            # The burst window must end BEFORE the tone arrives: the notched
            # profile reads the tone's own establishment swell otherwise (the
            # A4 held take measured a "-0.045 dB burst" = its rising tone —
            # which the fit turned into a 200%-gain chiff: Robin's "tongue
            # puff I don't hear in my recording", 2026-09-27).
            prof = ((r.get("onset") or {}).get("portrait") or [])
            arrive_ms = 90.0
            for p in prof:
                if p["H1_dbfs"] >= t["H1_plateau_rms_dbfs"] - 14.0:
                    arrive_ms = p["t_ms"]
                    break
            early = [p for p in burst if p["t_ms"] < arrive_ms - 8.0]
            if early:
                pk = max(p["db_rel_plateau_H1"] for p in early)
                take["arrivalMs"] = arrive_ms
                take["burstPre"] = [{"t_ms": p["t_ms"],
                                     "db_rel_plateau_H1": p["db_rel_plateau_H1"]}
                                    for p in early]
                take["chiffDb"] = pk
                after = [p for p in early if p["t_ms"] > 20]
                ln = None
                for p in after:
                    if p["db_rel_plateau_H1"] < pk - 6.0:
                        ln = p["t_ms"] / 1000.0
                        break
                take["chiffLen"] = round(min(ln or 0.08, 0.12), 3)
                # the burst's own band edges (Robin's puff catch on
                # E5/F5/G5: the shipped sweeps read broad/bright; the row's
                # startHz/endHz carry the sweep the take actually made —
                # the engine's eChiff sub already reads both fields)
                try:
                    edges = onset_band_edges(s, note_hz(nid))
                    if edges:
                        take["chiffStartHz"], take["chiffEndHz"] = edges
                except Exception as e:
                    print(f"  onset spectrum {nid}: {e}")
            push(nid, take)
    # best take per note = the LONGEST steady sounding span (a melody's
    # fragment blips and tongued trios do not own the row; the ladder's
    # steady notes do); corroboration rides as the rest of the takes.
    for nid in out:
        out[nid]["takes"].sort(key=lambda t: -t["span"])
    return out

def median(v):
    return statistics.median(v) if v else None

def stage_targets():
    src = load_sources()
    all_h1 = [t["h1db"] for d in src.values() for t in d["takes"]]
    lvl_ref = statistics.median(all_h1)
    targets = {}
    for nid, d in sorted(src.items()):
        takes = d["takes"]
        # single-note-grade sources: the ladder's melody cuts AND Robin's
        # dedicated held-note recordings (2026-09-27 — the cleanest take wins
        # by span, which the held set usually is). kokiri/storms stay context.
        fit_pool = [t for t in takes if t["source"] in ("ladder", "held")]
        if fit_pool:
            fit = dict(max(fit_pool, key=lambda t: t["span"]))  # best ladder take
            fit["fit"] = True
            fit["took_source"] = fit["source"]
        else:
            # no ladder coverage: the note's values arrive by the post-pass
            # interpolation from the fitted ladder rows — kokiri/storms takes
            # stay context-only (Robin's rule), never note values at any tier
            fit = {"fit": False, "took_source": "interp", "source": "interp",
                   "takes": d["takes"]}
        # Onset-domain fields a blipped/short ladder take can't carry ride
        # the nearest clean ladder neighbor's own take (the B4 re-blow blip:
        # its burst is a real attack of THAT take, not B4's serial character).
        if fit.get("fit") and nid in NEIGHBOR_ONSET_HOLD:
            nb = NEIGHBOR_ONSET_HOLD[nid]
            nt = [p for p in (src.get(nb) or {}).get("takes", [])
                  if p["source"] == "ladder"]
            if nt:
                npick = max(nt, key=lambda t: t["span"])
                for f in ("atkPre", "chiffDb", "chiffLen", "attack",
                          "chiffStartHz", "chiffEndHz"):
                    if npick.get(f) is not None:
                        fit[f] = npick[f]
                fit["onset_from"] = nb
        # corrected noise floors for the fit take (the inter-harmonic floor
        # method — the old notch-band numbers measure the fundamental's skirt)
        if fit.get("fit") and fit.get("cut"):
            try:
                rate, xw = _load_wav(fit["cut"])
                mw = (xw[:, 0] + xw[:, 1]) / 2 if xw.shape[1] > 1 else xw[:, 0]
                import tone_report as _tr
                f0m = note_hz(nid) * (2 ** (fit.get("cents", 0) / 1200))
                on_rel = fit["on"] - fit.get("cutStart", 0.0)
                hold = max(0.30, min(0.8, fit["span"] * 0.75))
                t0 = on_rel + 0.10
                n = min(int(hold * 44100.0), len(mw) - int(t0 * 44100.0))
                if n >= 8192:
                    fb = floor_bands(mw[int(t0 * 44100.0):int(t0 * 44100.0) + n], f0m)
                    if fb:
                        fit.update(fb)
            except Exception as e:
                print(f"  floor re-cache {nid}: {e}")
        fit["n_takes"] = len(takes)
        fit["level_ref_db"] = lvl_ref
        fit["sources"] = sorted(set(t["source"] for t in takes))
        fit["takes"] = takes
        targets[nid] = fit

    # The notes the ladder never carries get their values INTERPOLATED (or
    # slope-extrapolated, clamped) from the nearest fitted ladder rows —
    # Robin's rule: kokiri/storms never supply note values at any tier; they
    # stay in takes[] as context only.
    fitted = {n: t for n, t in targets.items() if t.get("fit")}
    RATIO_KEYS = ("h2", "h3", "h4", "h5")
    LINEAR_KEYS = ("h1db", "plateau", "band1", "band2", "band3", "band4",
                   "fb1", "fb2", "fb3", "fb4", "osDb", "attack", "atkPre",
                   "chiffDb", "chiffLen", "chiffStartHz", "chiffEndHz",
                   "wobPct", "wobHz", "wanderC")

    def _lerp_notes(k0, k1, tfrac):
        a, b = targets[k0], targets[k1]
        vals = {}
        for k in RATIO_KEYS:
            va, vb = a.get(k), b.get(k)
            if va and vb:
                da, dbe = 20 * math.log10(va), 20 * math.log10(vb)
                vals[k] = 10 ** ((da + (dbe - da) * tfrac) / 20)
        for k in LINEAR_KEYS:
            va, vb = a.get(k), b.get(k)
            if va is not None and vb is not None:
                vals[k] = va + (vb - va) * tfrac
        return vals

    def _fill_interp(nid):
        f = note_hz(nid)
        anchor = sorted((note_hz(k), k) for k in fitted)
        below = [x for x in anchor if x[0] <= f]
        above = [x for x in anchor if x[0] > f]
        import math as _m
        if not above:
            (mf0, k0), (mf1, k1) = anchor[-2], anchor[-1]
        elif not below:
            (mf0, k0), (mf1, k1) = anchor[0], anchor[1]
        else:
            (mf0, k0), (mf1, k1) = below[-1], above[0]
        tf = _m.log2(f / mf0) / _m.log2(mf1 / mf0)
        tf = max(-0.75, min(1.75, tf))
        targets[nid].update(_lerp_notes(k0, k1, tf))

    for nid in targets:
        if targets[nid].get("took_source") == "interp":
            _fill_interp(nid)

    # Onset resolution from OTHER takes of the same note (a continuation
    # fragment after the segmenter's breath split starts inside the first
    # portrait frame — no pre-state for the fit to read; the engine would
    # then fall back to its loud generic chiff: Robin's puff catches).
    ONSET_FIELDS = ("atkPre", "chiffDb", "chiffLen", "attack",
                    "chiffStartHz", "chiffEndHz")
    for nid, t in targets.items():
        if not t.get("fit") or 0 < (t.get("atkPre") or 0) <= 0.4:
            continue
        got = False
        for cand in [x for x in (src.get(nid) or {}).get("takes", [])
                     if x["source"] in ("ladder", "held")
                     and x.get("atkPre") is not None and x["atkPre"] <= 0.4]:
            for f in ONSET_FIELDS:
                if cand.get(f) is not None:
                    t[f] = cand[f]
            t["onset_from"] = f"{cand['source']} entry take"
            got = True
            break
        if got:
            continue
        # no resolvable take: the nearest fitted pitch neighbor that CAN
        # speak its own onset (Robin's rule: interpolate from the ladder)
        pool = sorted((abs(note_hz(n2) - note_hz(nid)), n2)
                      for n2, t2n in targets.items()
                      if t2n.get("fit") and 0 < (t2n.get("atkPre") or 0) <= 0.4
                      and t2n.get("chiffDb") is not None)
        if pool and (t.get("atkPre") is None or t["atkPre"] > 0.4):
            nb = pool[0][1]
            for f in ONSET_FIELDS:
                if targets[nb].get(f) is not None:
                    t[f] = targets[nb][f]
            t["onset_from"] = f"{nb} (no resolvable onset)"

    os.makedirs(AN, exist_ok=True)
    path = os.path.join(AN, "targets.json")
    json.dump(targets, open(path, "w"), indent=1)
    # readable table (fit take = the best take per note)
    notes = sorted(targets, key=note_hz)
    print(f"{'note':5}{'s':>1} {'h2 dB':>7}{'h3':>7}{'h4':>7}{'h5':>7} {'H1':>7}"
          f"{'b1':>7}{'b2':>7}{'b3':>7} {'wob%':>6}{'hz':>6} {'att':>6} {'os':>6} {'sc':>5} {'cents':>6} src(span)")
    for nid in notes:
        t = targets[nid]
        def dd(key):
            v = t.get(key)
            return "" if v is None else ("" if v == 0 else f"{20*math.log10(v):6.1f}")
        fmt = lambda v, f: "" if v is None else f.format(v)
        print(f"{nid:5}{'*' if t['fit'] else '-'}"
              f" {dd('h2'):>7}{dd('h3'):>7}{dd('h4'):>7}{dd('h5'):>7}"
              f" {fmt(t.get('h1db'), '{:6.1f}')}"
              f" {fmt(t.get('band1'), '{:6.1f}')}{fmt(t.get('band2'), '{:6.1f}')}{fmt(t.get('band3'), '{:6.1f}')}"
              f" {fmt(t.get('wobPct'), '{:5.1f}')}{fmt(t.get('wobHz'), '{:.1f}')}"
              f" {fmt(t.get('attack'), '{:.3f}')} {fmt(t.get('osDb'), '{:5.1f}')}"
              f" {fmt(t.get('wanderC'), '{:.1f}')} {fmt(t.get('cents'), '{:+.0f}')}"
              f" {'/'.join(t.get('sources') or []) or 'interp(ladder rows)'}({(t.get('span') or 0):.2f}s) took {t['source']}")
    print("wrote", path)

def per_note_targets():
    path = os.path.join(AN, "targets.json")
    return json.load(open(path))

# mirror of the JS V_ANCHORS interpolation (log2-f, slope-clamped ±1.5 oct)
VA = {
    "noiseBumpQ": [[220, 6.0], [523.25, 9.0], [1568, 2.5]],
    "attackF": [[220, 0.9], [523.25, 1.0], [1174, 1.25], [1568, 1.75]],
}
def v_interp(pts, f):
    import math
    for i in range(len(pts) - 1):
        f0, v0 = pts[i]; f1, v1 = pts[i + 1]
        if f <= f1:
            t = max(-1.5, min(1.5, math.log2(f / f0) / math.log2(f1 / f0)))
            return v0 + (v1 - v0) * t
    f0, v0 = pts[-2]; f1, v1 = pts[-1]
    slope = (v1 - v0) / math.log2(f1 / f0)
    return v1 + slope * max(-1.5, min(1.5, math.log2(f / f1)))

def analyze_render(wav, note, margins=(0.07, 0.06)):
    import tone_report
    return tone_report.analyze(wav, nominal=note, margins=margins)

def render_note(note, cand_path, tag):
    import render_ours
    out = os.path.join(AN, "fit", tag, f"render_{note}.wav")
    render_ours.run_page(
        f"r12fit_{tag}_{note}.html",
        {"note": note, "instId": INST, "dur": 2.0,
         "_tone": json.load(open(cand_path, encoding="utf-8")) if cand_path else None,
         "_fing": render_ours.fing_data(INST)},
        out)
    return out

def measure_note(wav, note):
    r = analyze_render(wav, note)
    h = r["timbre"]["harmonic_ratio_re_H1_median"]
    bands = r["noise"]["bands"]
    env = r["envelope"]
    out = {
        "h2": h[0], "h3": h[1], "h4": h[2], "h5": h[3],
        "h1db": r["timbre"]["H1_plateau_rms_dbfs"],
        "band1": bands["0.85-1.95xf0"]["db_rel_H1_median"],
        "band2": bands["1.95-3.90xf0"]["db_rel_H1_median"],
        "band3": bands["3.90-7.00xf0"]["db_rel_H1_median"],
        "wobPct": env["breath_wobble_std_pct"],
        "wobHz": env["wobble_dominant_hz"],
        "attack": env["attack_to_plateau_s"],
        "osDb": env["attack_overshoot_db"],
        "wanderC": r["pitch"]["wobble_std_cents"],
    }
    burst = ((r.get("onset") or {}).get("burst_profile") or [])
    early = [p for p in burst if p["t_ms"] <= 90]
    if early:
        out["chiffDb"] = max(p["db_rel_plateau_H1"] for p in early)
    try:
        rate, xr = _load_wav(wav)
        mr = (xr[:, 0] + xr[:, 1]) / 2 if xr.shape[1] > 1 else xr[:, 0]
        f0 = note_hz(note)
        n = int(min(1.4, max(0.5, 2.0 - r["envelope"]["attack_to_plateau_s"])) * 44100.0)
        n = min(n, len(mr) - int(0.35 * 44100.0))
        if n >= 8192:
            fb = floor_bands(mr[int(0.35 * 44100.0):int(0.35 * 44100.0) + n], f0)
            if fb:
                out.update(fb)
    except Exception as e:
        print(f"  render floor {note}: {e}")
    return out

def db(x):
    import math
    return 20 * math.log10(x) if x and x > 0 else -120.0

def lin(dbv):
    return 10 ** (dbv / 20) if dbv > -119.5 else 0.000011

# ---------------------------------------------------------------------------
# floor_bands — the corrected noise measurement (the skirt-trap fix): a
# Blackman-Harris window over the held part, inter-harmonic floor medians
# per band with ±80 Hz harmonic exclusion, scaled consistently on both the
# recording and the render side. The old notch-band numbers were the loud
# fundamental's window skirt (~45-70 dB hotter than the real breath).
# ---------------------------------------------------------------------------
import numpy as _np

def floor_bands(seg, f0, sr=44100.0, pad=1 << 17, excl=80.0):
    n = len(seg)
    if n < 4096:
        return None
    t = _np.arange(n) / n
    w = (0.35875 - 0.48829 * _np.cos(2 * _np.pi * t)
         + 0.14128 * _np.cos(4 * _np.pi * t) - 0.01168 * _np.cos(6 * _np.pi * t))
    wsum = float(_np.sum(w))
    enbw_db = 10 * _np.log10(n * float(_np.sum(w ** 2)) / wsum ** 2)
    S = _np.abs(_np.fft.rfft(seg * w, pad)) * 2 / wsum
    fs = _np.fft.rfftfreq(pad, 1 / sr)
    bin_hz = sr / pad
    i1 = int(_np.searchsorted(fs, f0 * 0.94)); l1 = max(1, i1 - 1)
    h1i = int(_np.searchsorted(fs, f0 * 1.06))
    k = l1 + int(_np.argmax(S[l1:h1i]))
    pk = db(float(S[k]))
    out = {}
    for bi, (r1, r2) in enumerate([(0.85, 1.95), (1.95, 3.9), (3.9, 7.0), (7.0, 12.0)]):
        i_lo, i_hi = int(r1 * f0 / bin_hz), int(min(r2 * f0, sr / 2 - 300) / bin_hz)
        keep = [i for i in range(max(0, i_lo), max(0, i_hi))
                if all(abs(fs[i] - hk * f0) > excl for hk in range(1, 9))]
        if len(keep) < 40:
            out[f"fb{bi+1}"] = None
            continue
        med = db(float(_np.median(S[keep]))) - enbw_db
        out[f"fb{bi+1}"] = med - pk
    return out

def onset_band_edges(s, f0, sr=44100.0, burst_s=0.055, ref_at=0.10, excl=80.0):
    """The recorded tongue burst's own band edges: BH window over the burst
    (spanning its own ~60 ms before and past the plateau start) vs a quiet
    window early in the plateau; log-spaced 1/3-oct medians with harmonic
    exclusion; the burst's span is where the excess stays > 4 dB (the burst
    dilutes ~1-2 dB inside the window — the threshold stays conservative).
    Returns (startHz, endHz) — the sweep bounds the shipped chiff should use —
    or None when fewer than two bands qualify."""
    cut = s.get("cut")
    if not cut:
        return None
    rate, x = _load_wav(cut)
    mono = (x[:, 0] + x[:, 1]) / 2 if x.shape[1] > 1 else x[:, 0]
    n = int(burst_s * sr)
    if n < 4096:
        return None
    t = _np.arange(n) / n
    w = (0.35875 - 0.48829 * _np.cos(2 * _np.pi * t)
         + 0.14128 * _np.cos(4 * _np.pi * t) - 0.01168 * _np.cos(6 * _np.pi * t))
    wsum = float(_np.sum(w))
    wsq = float(_np.sum(w ** 2))
    enbw_db = 10 * _np.log10(n * wsq / wsum ** 2)
    on_rel = s["on"] - s.get("t0", 0.0)
    b0 = int(max(0.0, on_rel - 0.05) * sr)   # the burst rides the attack
    r0 = int((on_rel + ref_at) * sr)         # ref: early plateau, cut time
    if b0 + n > len(mono) or r0 + n > len(mono):
        return None
    B = _np.abs(_np.fft.rfft(mono[b0:b0 + n] * w, 1 << 16)) * 2 / wsum
    Q = _np.abs(_np.fft.rfft(mono[r0:r0 + n] * w, 1 << 16)) * 2 / wsum
    fs = _np.fft.rfftfreq(1 << 16, 1 / sr)
    bins = fs[1] - fs[0]
    edges_loud = []
    lvl = [250.0, 353.0, 500.0, 707.0, 1000.0, 1414.0, 2000.0,
           2828.0, 4000.0, 5657.0, 8000.0]  # log 1/3-oct grid
    fm = f0 * (2 ** (s.get("cents", 0.0) / 1200.0))
    excess = []
    for hi_b in lvl:
        a = hi_b / (2 ** (1.0 / 6.0))
        bl = hi_b * (2 ** (1.0 / 6.0))
        keep = [i for i in range(max(1, int(a / bins)), int(bl / bins))
                if all(abs(fs[i] - hk * fm) > excl for hk in range(1, 12))]
        if len(keep) < 20:
            excess.append(None)
            continue
        eb = 20 * _np.log10(float(_np.median(B[keep])) + 1e-15) - enbw_db
        er = 20 * _np.log10(float(_np.median(Q[keep])) + 1e-15) - enbw_db
        excess.append((eb, er, hi_b))
    # contiguous span of >6 dB excess from the first qualifying band outward
    bands = [e for e in excess if e]
    loud = [e for e in bands if e[0] - e[1] > 4.0]
    if len(loud) < 2:
        return None
    top = max(e[2] for e in loud)
    bot = min(e[2] for e in loud)
    if top <= bot:
        return None
    return (round(min(11000, top), 1), round(max(200, bot), 1))


def naive_candidate():
    targets = per_note_targets()
    rows = []
    # level anchor: the LOUDEST fitted note rows at 0 dB — the recorded
    # absolute gain is a mic-chain artifact (Robin), so only the note-to-note
    # curve ships, all rows <= 0 keeps the app's master/headroom untouched.
    max_h1 = max(t.get("h1db") or 0.0 for t in targets.values())
    for nid, t in sorted((kv for kv in targets.items() if kv[1].get("fit")),
                         key=lambda kv: note_hz(kv[0])):
        f = note_hz(nid)
        h = [1.0] + [min(max(t.get(k) or 0.0, 0.0), 0.5) for k in ("h2", "h3", "h4", "h5")]
        h1db = t.get("h1db") or 0.0
        levelDb = round(h1db - max_h1, 2)
        noiseLoDb = round((t.get("fb1") or t.get("band1") or -26.0), 2) + 2.0
        rows.append({
            "note": nid, "f": round(f, 2), "h": [round(v, 6) for v in h],
            "levelDb": levelDb,
            "noiseLoDb": round(noiseLoDb, 2),
            "noiseBumpQ": 0.4,    # the wash profile: broad, non-resonant (search winner)
            "attackF": None,   # filled from the baseline render ratio
            "osDb": round(t.get("osDb") or 1.0, 2),
        })
        # wobble/wander fields only when the take's plateau supports the
        # statistic — missing fields are the loader's job (generic doctrine).
        if wobble_measurable(t):
            rows[-1]["wanderC"] = round(t.get("wanderC") or 0, 2)
            rows[-1]["wobPct"] = round(t.get("wobPct") or 0, 2)
            rows[-1]["wobHz"] = round(t.get("wobHz") or 2.5, 2)
        # the recorded tongue transient IS the aim (Robin): the burst runs
        # -40..-55 dB rel plateau H1 while the shipped generic chiff sits
        # ~25 dB hotter (the sand-paper onsets). A linear peak + the measured
        # length; startHz/endHz/attack stay generic per-field fallbacks.
        if t.get("chiffDb") is not None:
                ch = {"peak": round(2 * lin(t["chiffDb"]), 6),
                      "len": round(t.get("chiffLen") or 0.08, 3)}
                # the take's own swell start: the first pre-tone frame within
                # 12 dB of the burst peak (0 keeps the legacy t0 start)
                bmp = None
                if t.get("arrivalMs") is not None:
                    cand = [p for p in (t.get("burstPre") or [])
                            if p["db_rel_plateau_H1"] >= t["chiffDb"] - 12.0]
                    if cand:
                        bmp = cand[0]["t_ms"] / 1000.0
                if bmp is not None:
                    ch["delay"] = round(max(0.0, bmp - 0.01), 3)
                if t.get("chiffStartHz") is not None:
                    ch["startHz"] = round(max(400, min(11000, t["chiffStartHz"])), 1)
                    ch["endHz"] = round(max(200, min(9000, t["chiffEndHz"])), 1)
                rows[-1]["chiff"] = ch
        # the row-expressible attack stages (the engine reads eAtk.speak/pre)
        rows[-1]["atk"] = {"speak": round(min(0.12, max(0.004, t.get("attack") or 0.02)), 3)}
        if t.get("atkPre") is not None:
            rows[-1]["atk"]["pre"] = round(max(0.01, min(0.6, t["atkPre"])), 3)
    return {"instrument": INST, "model": "tone-fit-v1",
            "recorded": {"date": "2026-09-26",
                         "takes": "12-hole melodies (ladder primary, kokiri/storms corroboration)",
                         "anchor": "levelDb re the take median (self-consistent within the ocarina)"},
            "chambers": {"1": rows}}

def kv(nid):
    return note_hz(nid)

def write_candidate(data, path=CAND):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(data, open(path, "w"), indent=1)

def render_compare(cand_data, tag, notes):
    cand_path = os.path.join(AN, f"fit_{tag}.json")
    write_candidate(cand_data, cand_path)
    results = {}
    for nid in notes:
        wav = render_note(nid, cand_path, tag)
        if not wav or not os.path.exists(wav):
            results[nid] = None
            continue
        try:
            results[nid] = measure_note(wav, nid)
        except Exception as e:
            print(f"measure fail {nid}: {e}")
            results[nid] = None
    return results, cand_path

def fit_rounds(rounds=3):
    targets = per_note_targets()
    all_notes = sorted(targets, key=kv)
    notes = [n for n in all_notes if targets[n].get("fit")]
    skipped = [n for n in all_notes if not targets[n].get("fit")]
    print("fitting:", " ".join(notes))
    print("unfitted (no ladder take, loader interpolates):", " ".join(skipped))
    rows = naive_candidate()["chambers"]["1"]
    for r in rows:
        for k, v in zip(("h2", "h3", "h4", "h5"), r["h"][1:]):
            r[k] = v
    rowmap = {r["note"]: r for r in rows}

    # round 0: baseline render at the NAIVE candidate (rows carry measured
    # values; attackF unset -> generic), to seed attackF ratios + noise shifts.
    base, _ = render_compare(naive_candidate(), "r0", notes)
    for nid in notes:
        t, r = targets[nid], base.get(nid)
        if not r: continue
        t_att = t.get("attack")
        if r["attack"] > 0.02 and t_att and t_att > 0.01:
            rowmap[nid]["attackF"] = round(max(0.5, min(2.5, t_att / r["attack"]) * 1.0), 3)
        else:
            rowmap[nid]["attackF"] = 1.0

    for R in range(1, rounds + 1):
        tag = f"r{R}"
        res, cand_path = render_compare(
            {"instrument": INST, "model": "tone-fit-v1",
             "recorded": naive_candidate()["recorded"],
             "chambers": {"1": rows}}, tag, notes)
        deltas = []
        # anchor: the fitted note with the highest recorded H1 — its render is
        # the level reference; a global (mic-gain) offset cancels out.
        anchor = None
        if res.get("F6"):
            anchor = "F6"
        else:
            for nid in notes:
                if res.get(nid):
                    if anchor is None or targets[nid]["h1db"] > targets[anchor]["h1db"]:
                        anchor = nid
        # solve corrections
        for nid in notes:
            t, r = targets[nid], res.get(nid)
            if not r: continue
            row = rowmap[nid]
            # harmonics: proportional in amplitude, capped at ±8 dB/round
            for k in ("h2", "h3", "h4", "h5"):
                tv, rv = t.get(k), r[k]
                if tv is None or rv <= 0:
                    continue
                ddb = max(-8.0, min(8.0, db(tv) - db(rv)))
                row[k] = round(max(row[k] * lin(ddb), 1e-5), 6)
                # a dead harmonic cannot recover by multiplication alone —
                # restart it from the measured target directly
                if row[k] < 0.00005 and tv > 0:
                    row[k] = round(tv, 6)
            # level: relative-to-anchor on BOTH sides (mic-gain-free); the
            # absolute master level stays where the app parked it (headroom
            # for support tracks / reverb — never rises to the recording).
            target_rel = t["h1db"] - targets[anchor]["h1db"] if anchor else 0.0
            render_rel = r["h1db"] - res[anchor]["h1db"] if anchor else 0.0
            shift = target_rel - render_rel
            deltas.append(("level", shift))
            row["levelDb"] = round(row["levelDb"] + min(8.0, max(-8.0, shift)), 2)
            # wind: corrected inter-harmonic floor band-1 level shift
            shift1 = t.get("fb1") or t.get("band1") or -26.0
            sh = shift1 - (r.get("fb1") or r["band1"])
            deltas.append(("band1", sh))
            row["noiseLoDb"] = round(row["noiseLoDb"] + min(45.0, max(-45.0, sh)), 2)
            # per-note noise-wall: the LP position/Q rows move toward the
            # take's own b2/b3 wall (rendered family: Δb2 ≈ 6.5 dB per Δratio,
            # ≈ 6.7 dB per Δratio at b3; Q fine-trims b3 at ~2.5 dB per 0.1
            # in this engine — measured on the rendered candidate matrix).
            t2, t3 = t.get("fb2"), t.get("fb3")
            if t2 is not None and r.get("fb2") is not None:
                # Δlpr raises the rendered b2 by ~6.5 dB per unit (measured on
                # the rendered matrix) — move by target−render, clamped.
                base = row.get("noiseLpRatio") or NOISE_WALL["ratio"]
                dl = max(-1.2, min(1.2, (t2 - r["fb2"]) / 6.5))
                row["noiseLpRatio"] = round(max(1.4, min(4.6, base + dl)), 2)
            # wander/wobble direct (skipped when the take can't support it —
            # a short span implies nothing; the fallback keeps generic)
            if wobble_measurable(t):
                row["wanderC"] = round(t.get("wanderC") or 0, 2)
                row["wobPct"] = round(t.get("wobPct") or 0, 2)
                row["wobHz"] = round(t.get("wobHz") or 2.5, 2)
            else:
                row.pop("wanderC", None)
                row.pop("wobPct", None)
                row.pop("wobHz", None)
            # attack stage loop (candidate-feedback on the expressible rows)
            t_att = t.get("attack")
            if t_att and t_att >= 0.006 and r["attack"] >= 0.004 and "atk" in row:
                sp = row["atk"]["speak"] * max(0.6, min(1.6, t_att / r["attack"]))
                row["atk"]["speak"] = round(min(0.12, max(0.004, sp)), 3)
            # overshoot gain (only when the take showed a real spike)
            t_os = t.get("osDb")
            if t_os is not None and t_att and t_att > 0.08:
                row["osDb"] = round(row["osDb"] + max(-4, min(4, t_os - r["osDb"])), 2)
            # onset burst (the transient target): the render's own burst
            # peak vs the recording's, one shift per round
            if "chiff" in row and t.get("chiffDb") is not None and r.get("chiffDb") is not None:
                dsh = max(-12, min(12, t["chiffDb"] - r["chiffDb"]))
                row["chiff"]["peak"] = round(max(row["chiff"]["peak"] * lin(dsh), 1e-6), 6)
        json.dump({"instrument": INST, "model": "tone-fit-v1",
                   "recorded": naive_candidate()["recorded"],
                   "chambers": {"1": rows}},
                  open(cand_path, "w"), indent=1)
        # residual table
        print(f"== round {R} residuals (target − render; level relative to the anchor note)")
        print(f"{'note':5}{'h2':>7}{'h3':>7}{'h4':>7}{'h5':>7}{'H1rel':>7}{'b1':>7}{'b2':>7}{'b3':>7}{'wob%':>7}{'att':>8}{'os':>6}")
        import math as _m
        worst = 0.0
        for nid in notes:
            t, r = targets[nid], res.get(nid)
            if not r: continue
            dh = []
            for k in ("h2", "h3", "h4", "h5"):
                tv, rv = t.get(k), r[k]
                dh.append("" if tv is None else f"{db(tv) - db(rv):6.1f}")
            lh = ((t["h1db"] - targets[anchor]["h1db"]) -
                  (r["h1db"] - res[anchor]["h1db"])) if anchor else 0.0
            worst = max(worst, max(abs(float(x)) for x in dh if x) if any(dh) else 0.0,
                        abs(lh))
            b1 = t.get("fb1") or t.get("band1")
            b2 = t.get("fb2") or t.get("band2")
            b3 = t.get("fb3") or t.get("band3")
            if r.get("fb2"): r2_, r3_ = r["fb2"], r["fb3"]
            else: r2_, r3_ = r["band2"], r["band3"]
            r1_ = r.get("fb1") or r["band1"]
            wp = t.get("wobPct"); at = t.get("attack"); osv = t.get("osDb")
            tail = ""
            tail += "" if b1 is None else f"{b1 - r1_:7.1f}"
            tail += "" if b2 is None else f"{b2 - r2_:7.1f}"
            tail += "" if b3 is None else f"{b3 - r3_:7.1f}"
            tail += "" if wp is None else f"{wp - r['wobPct']:7.1f}"
            tail += "" if at is None else f"{at - r['attack']:8.3f}"
            tail += "" if osv is None else f"{osv - r['osDb']:6.1f}"
            print(f"{nid:5}{dh[0]:>7}{dh[1]:>7}{dh[2]:>7}{dh[3]:>7}{lh:7.1f}{tail}")
        print(f"worst |delta| {worst:.2f} dB")
    # final: write the shipped tone.json draft
    for r in rows:
        r["h"] = [round(1.0, 6), r["h2"], r["h3"], r["h4"], r["h5"]]
    final = {"instrument": INST, "model": "tone-fit-v1",
             "recorded": {
                 "date": "2026-09-27",
                 "takes": "12-hole tone ladder melody cuts + Robin's dedicated "
                          "held-note recordings (research/note-recordings/12hole/*-held.wav, "
                          "2026-09-27: the cleanest single-note-grade sources), "
                          "kokiri + storms kept as transition/glide context, NEVER note "
                          "values (Robin 2026-09-27); notes without takes are interpolated "
                          "or extrapolated from the fitted ladder rows; "
                          "recording gain is a mic-chain artifact — levelDb anchors the "
                          "loudest fitted note at 0 dB, only the note-to-note curve ships",
                 "anchor": "loudest fitted note (levelDb 0); masterLevel untouched — "
                           "headroom for support tracks and reverb preserved",
             },
             "chambers": {"1": rows}}
    write_candidate(final, CAND)
    json.dump(final, open(DRAFT_TONE, "w"), indent=1)
    print("wrote", CAND, "and", DRAFT_TONE)

RECORDED_META = {
    "date": "2026-09-27",
    "takes": "12-hole tone ladder melody cuts + Robin's held-note recordings "
             "(research/note-recordings/12hole/*-held.wav); kokiri + storms stay "
             "transition/glide context, NEVER note values; notes without takes "
             "ride the fitted ladder rows interpolated; "
             "recording gain is a mic-chain artifact — levelDb anchors the "
             "loudest fitted note at 0 dB, only the note-to-note curve ships",
    "anchor": "loudest fitted note (levelDb 0); masterLevel untouched — "
              "headroom for support tracks and reverb preserved",
}

def publish():
    """Copy the converged draft into the shipped instrument path."""
    d = json.load(open(DRAFT_TONE, encoding="utf-8"))
    d["recorded"] = dict(RECORDED_META)
    json.dump(d, open(OUT_TONE, "w", encoding="utf-8"), indent=1)
    print("published", OUT_TONE)

if __name__ == "__main__":
    if not sys.argv[1:]:
        print(__doc__)
    elif sys.argv[1] == "targets":
        stage_targets()
    elif sys.argv[1] == "fit":
        rounds = int(sys.argv[sys.argv.index("--rounds") + 1]) if "--rounds" in sys.argv else 3
        fit_rounds(rounds)
    elif sys.argv[1] == "publish":
        publish()
    else:
        print(__doc__)
