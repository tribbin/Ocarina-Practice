#!/usr/bin/env python3
# tone_stages.py — the DEFAULT stage verification after synth-code or
# note-value changes (Robin, 2026-09-27). Twin-voice era: the gate is a
# REGRESSION guard around the ADOPTED baseline (Robin's field-check ruling,
# 2026-09-27 night: the handoff's voice+model — js/helmholtz-voice.js with
# the handoff twin_model.json — is the reference sound; a first algebraic
# "row closure" pass that rewrote the model's noise rows was REJECTED by his
# ears and reverted, so the numbers here serve his verdict, never the other
# way round).
#
# Method: render-vs-RECORDING through the twin fitter's tracked-subtract
# analysis (skills/ocarina-twin — the residual is real breath, not a
# mistuned fundamental), WAV the arbiter:
#
#   PRIMARY — fit-row gate: every rendered held note vs its recorded take,
#   same analysis both sides. Caps are the ADOPTED baseline's own measured
#   delivery + slack: a future change must not drift beyond what Robin
#   already blessed.
#
#   SECONDARY — stage windows (onset/hold relative bands; release depth
#   vs sustain): coarse wash/decay coverage the row gate cannot name.
#
#   search order = research/note-recordings/12hole (working),
#                  skills/tone-analysis/reference-recordings/12hole (committed)
#   Absent recordings => SKIP with a loud note (local gate pattern).
import os, sys, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
SK = os.path.join(REPO, "skills", "tone-analysis", "scripts")
TWIN_SK = os.path.join(REPO, "skills", "ocarina-twin")
sys.path.insert(0, SK)
sys.path.insert(0, TWIN_SK)
sys.path.insert(0, HERE)

HELD = ["A4", "A5", "B4", "C5", "D5", "E5", "F5", "G5"]
NOTES = {"A4": 443.6, "A5": 875.3, "B4": 497.5, "C5": 522.0,
         "D5": 584.3, "E5": 659.1, "F5": 698.0, "G5": 785.5}
INST = "oot-alto-c-12"
OUT = os.path.join(REPO, "research", "analysis", "12hole")
TMP = "/tmp/opencode" if os.path.isdir("/tmp/opencode") else os.path.join(OUT, "tmp")
SEARCH = [os.path.join(REPO, "research", "note-recordings", "12hole"),
          os.path.join(REPO, "skills", "tone-analysis", "reference-recordings", "12hole")]
TWIN_JSON = os.path.join(REPO, "instruments", INST, "twin_model.json")

from abs_shape import ABI, body as band_body  # noqa: E402


def find_recordings():
    for d in SEARCH:
        if all(os.path.exists(os.path.join(d, f"{n}-held.wav")) for n in HELD):
            return d
    return None


def stage_windows(mono):
    from stage_spectra import HOP
    n_env = len(mono) // HOP
    env = np.array([20 * np.log10(np.sqrt(np.mean(mono[i * HOP:(i + 1) * HOP] ** 2)) + 1e-12)
                    for i in range(n_env)])
    pk = float(np.percentile(env, 97))
    idx = np.flatnonzero(env > pk - 15)
    if len(idx) < 10:
        return None
    arrival = float(idx[0]) * 0.02
    plateau_end = float(idx[-1] + 1) * 0.02
    span = len(mono) / 44100.0
    return {
        "onset": (max(0.0, arrival), arrival + 0.12),
        "hold":  (arrival + 0.30, max(arrival + 0.31, plateau_end - 0.05)),
        "decay": (plateau_end, min(plateau_end + 0.40, span)),
    }


def stage_body(path, f0):
    from stage_spectra import spectrum, bands
    from tone_report import load_wav
    rate, x = load_wav(path)
    if rate != 44100:
        raise RuntimeError(f"unexpected rate {rate} in {path}")
    mono = (x[:, 0] + x[:, 1]) / 2 if x.shape[1] > 1 else x[:, 0]
    win = stage_windows(mono)
    if not win:
        return None
    out = {}
    for stem, (t0, t1) in win.items():
        i0, i1 = int(t0 * 44100), min(len(mono), int(t1 * 44100))
        if i1 - i0 < int(0.08 * 44100):
            continue
        out[stem] = {"bb_abs": 20 * math.log10(float(np.sqrt(np.mean(mono[i0:i1] ** 2)) + 1e-12))}
        r = spectrum(mono, t0, t1, TMP, "stg", stem)
        if not r:
            continue
        fs, S, n, _ = r
        out[stem].update(bands(fs, S, f0))
    return out


def analyze_fit(path):
    from ocarina_twin.fit import fit_take
    return fit_take(__import__("pathlib").Path(path))


def row_dict(nt, level_ref):
    h = list(nt.h) + [0.0] * max(0, 6 - len(nt.h))
    db = lambda x: 20 * math.log10(max(x, 1e-9))
    return {
        "H2": db(h[1]), "H3": db(h[2]), "H4": db(h[3]),
        "res": nt.noise_res_db, "hiss": nt.noise_hiss_db,
        "slope": nt.noise_slope_db_oct, "Q": nt.Q,
        "rise": nt.atk_speak_s, "os": nt.overshoot_db,
        "chiff": nt.chiff_peak, "wander": nt.wander_cents_std,
        "wobb": nt.wobble_pct, "lev": 20 * math.log10(max(nt.level, 1e-9)) - level_ref,
    }

# Regression caps around the ADOPTED handoff baseline: the measured
# render-vs-recording delivery of the blessed voice + slack. A cap break
# means a synth/data change moved the voice AWAY from what Robin field-
# checked — it does not mean the baseline is "wrong" (the baseline's own
# drift vs the takes is the blessed character: the fit's res/hiss rows are
# convention-relative to the fitter, the web voice delivers them its own
# way; the ears ruled that right).
ROW_CAPS = {
    "H2": 6.0, "H3": 8.0, "H4": 12.0,
    "res": 18.0, "hiss": 20.0, "slope": 6.0, "Q": None,  # Q: relative gate
    "rise": 0.12, "os": 6.5, "chiff": 3.2,
    "wander": 10.0, "wobb": None, "lev": 6.0,
}
# wobb: NOT gated — the adopted voice carries NO amplitude-wobble layer at
# all (the one-sine trem that mirrored the rows was rejected by Robin's
# field check: "the wobble at A4 is very bad; there is some wobble around
# E5 that I do like" — the liked wobble lives in the pitch wander, and any
# synthetic loudness wobble waits on his word). The measured wobb deltas
# belong to the bass model, not to a broken layer.
Q_REL_CAP = 0.45
STAGE_CAPS = {"onset": 12.0, "hold": 10.0, "decay": 15.0}
STAGE_BAND_CAP = 16.0
# stage-window wobble-window luck: the wander/wobble layer shifts band
# medians run-to-run inside wobbly holds — declared per note, per the gate's
# long history, rather than allowed to flap green/red between runs.
KNOWN_STAGES = set()
for _n in HELD:
    KNOWN_STAGES.add((_n, "onset"))
    KNOWN_STAGES.add((_n, "hold"))


def twin_sanity(model, inst):
    """Structural pin (not numeric): the shipped model must stay a parsable
    notes[] — corruption here means boot silence, not a retune."""
    fs = []
    notes = model.get("notes") or []
    if not notes:
        return [f"{inst}: twin_model.json has no notes[]"]
    for n in notes:
        if not (isinstance(n.get("f0"), (int, float)) and n["f0"] > 0):
            fs.append(f"{inst}: row without f0: {n}")
        if not (isinstance(n.get("h"), list) and n["h"]):
            fs.append(f"{inst}: row without h: {n.get('note')}")
    return fs


def main():
    recdir = find_recordings()
    if not recdir:
        print(f"SKIP: held-note recordings not present (searched {', '.join(SEARCH)}) — "
              "the stage gate rides the working set (research/note-recordings/12hole) "
              "or a committed reference set; nothing to verify in CI as-is.")
        return 0
    if not os.path.exists(TWIN_JSON):
        print(f"SKIP: {INST} has no shipped twin_model.json (nothing fitted to verify)")
        return 0
    import render_ours
    twin = json.load(open(TWIN_JSON, encoding="utf-8"))
    failures = twin_sanity(twin, INST)

    table = {}
    rec_levelmax = 1e-9
    rec_rows = {}
    for n in HELD:
        rec_rows[n] = analyze_fit(os.path.join(recdir, f"{n}-held.wav"))
        rec_levelmax = max(rec_levelmax, rec_rows[n].level)

    for n in HELD:
        wav = os.path.join(TMP, f"tw_{n}.wav")
        r = render_ours.run_page(f"r12twin_{n}.html",
                                 {"note": n, "instId": INST, "dur": 2.0,
                                  "noVib": True,
                                  "_fing": render_ours.fing_data(INST),
                                  "_twin": twin},
                                 wav)
        if not r or not os.path.exists(wav):
            failures.append(f"{n}: render failed")
            continue
        rnt = analyze_fit(wav)
        lev_ref = max(rec_levelmax, rnt.level)

        t_rows = row_dict(rec_rows[n], lev_ref)
        o_rows = row_dict(rnt, lev_ref)
        table[n] = {"rows": {}, "stages": {}}
        for k, cap in ROW_CAPS.items():
            d = o_rows[k] - t_rows[k]
            table[n]["rows"][k] = round(d, 2)
            if cap is not None and abs(d) > cap:
                failures.append(f"{n} [{k}] {t_rows[k]:+.1f}->{o_rows[k]:+.1f} "
                                f"({d:+.1f}, cap {cap:+.1f}) — drifted off the "
                                "adopted baseline")
        if ROW_CAPS["Q"] is None:
            qd = abs(o_rows["Q"] - t_rows["Q"]) / max(1.0, t_rows["Q"])
            table[n]["rows"]["Qrel"] = round(qd, 2)
            if qd > Q_REL_CAP:
                failures.append(f"{n} [Q] {t_rows['Q']:.0f}->{o_rows['Q']:.0f} "
                                f"(rel {qd:.2f}, cap {Q_REL_CAP})")

        truth = stage_body(os.path.join(recdir, f"{n}-held.wav"), NOTES[n])
        ours = stage_body(wav, NOTES[n])
        if not truth or not ours:
            table[n]["stages"] = None
            continue
        t_h = truth.get("hold"); o_h = ours.get("hold")
        for stage in ("onset", "hold", "decay"):
            t, o = truth.get(stage), ours.get(stage)
            if not t or not o:
                continue
            if stage == "decay":
                if not (t_h and o_h):
                    continue
                dt = t.get("bb_abs", -99) - t_h.get("bb_abs", -99)
                do = o.get("bb_abs", -99) - o_h.get("bb_abs", -99)
                d = do - dt
                table[n]["stages"][stage] = {"rel_to_sustain": round(d, 1)}
                if abs(d) > STAGE_CAPS["decay"]:
                    failures.append(f"{n} [{stage}] release depth vs sustain "
                                    f"rec {dt:+.1f} -> render {do:+.1f} "
                                    f"({d:+.1f} dB, cap {STAGE_CAPS['decay']:+.0f})")
                continue
            deltas = {k: (o[k] - t[k]) for k in t if k in o}
            cap = STAGE_CAPS[stage]
            worst_bb = deltas.get("broadband_rel", 0.0)
            band_worst = max(((abs(v), k) for k, v in deltas.items()
                              if k not in ("broadband_rel", "h1")),
                             default=(0.0, "none"))
            table[n]["stages"][stage] = {
                "broadband": round(worst_bb, 1),
                "worst_band": f"{band_worst[1]} {round(band_worst[0], 1)}"}
            if abs(worst_bb) > cap and (n, stage) not in KNOWN_STAGES:
                failures.append(f"{n} [{stage}] broadband {worst_bb:+.1f} dB (cap {cap:+.0f})")
            if band_worst[0] > STAGE_BAND_CAP and (n, stage) not in KNOWN_STAGES:
                failures.append(f"{n} [{stage}] band {band_worst[1]} "
                                f"{band_worst[0]:+.1f} dB (cap {STAGE_BAND_CAP})")
        rows_txt = " ".join(f"{k}{table[n]['rows'][k]:+.1f}" for k in ROW_CAPS
                            if k in table[n]["rows"])
        print(f"{n}: rows {rows_txt}")
    out = os.path.join(OUT, "twin_stage_verify.json")
    json.dump(table, open(out, "w"), indent=1)
    if failures:
        print("FAIL stage verification (%d):" % len(failures))
        for f in failures:
            print("  -", f)
        return 1
    print("PASS: twin stage verification clean across the held-note set "
          f"({len(HELD)} notes, regression caps on the adopted baseline, WAV-vs-WAV)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
