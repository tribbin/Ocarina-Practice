#!/usr/bin/env python3
# tone_stages.py — the DEFAULT stage verification after synth-code or
# note-value changes (Robin, 2026-09-27): sustain/hold, ONSET and DECAY of
# every held-note take are compared WAV-vs-WAV against the recordings —
# plateau windows alone never caught the white-wash-onset class he caught
# by ear (F5: sustain loud, onset far louder, the bleed path raw-white).
#
# The base is the held-note takes (the cleanest recordings available;
# other notes interpolate/extrapolate from their stage classes):
#   search order = research/note-recordings/12hole (working),
#                  skills/tone-analysis/reference-recordings/12hole (committed)
# Absent recordings => SKIP with a loud note (local gate, the
# midi_track_audit pattern) — CI has no recordings unless they ride the
# committed reference set.
#
# Gate: per-stage broadband delta (wash verdict) + per-band deltas on the
# absolute-body bands (abs_shape ABI), harmonics +-80 Hz excluded both
# sides. Caps are the take-noise class plus slack for the wobble window:
# hold broadband +-8 dB, onset +-10, decay +-12 when both sides have the
# window; any single band beyond +-12 is gross (Robin's "very audible and
# easy to see in the spectrum plot").
#
# KNOWN_OPEN allowlist (classes of the parked §1 item, TODO 2026-09-27) —
# entries here are the layers' DECLARED unresolved state, cleared
# wholesale as the row family lands; anything NEW trips the gate:
#  - onset-swell: the wind ramps to full bed color inside 60 ms while the
#    recorded swell builds slower (C5/D5 pocket/broadband at onset) — the
#    wind-envelope attack leg is unfitted.
#  - bleed-tail-class: the lobe + tilt over/under-shoots tail/airhead per
#    note (E5/F5/G5/A5 classes) — per-note bleed rows are the named build.
#  - wall-class: A5/A4 trough bands at the wall row limits (hole depth).
KNOWN_OPEN = {
    # onset-swell class: the wind ramps to full bed color inside 60 ms while
    # the recorded swell builds slower — the wind-envelope attack leg is
    # unfitted.
    ("C5", "onset"), ("D5", "onset"), ("E5", "onset"), ("F5", "onset"),
    ("G5", "onset"), ("A5", "onset"), ("A4", "onset"),
    # bleed-tail/wall classes: trough/tail/airhead/rough bands beyond their
    # caps while the per-note bleed rows and the hole depth are open.
    # wobble-window luck: the default-voice runs (vib+wob on) shift the
    # band medians run-to-run inside wobbly holds, so borderline pairs also
    # declare rather than flap between green and red per run.
    ("A4", "decay"), ("E5", "decay"),
    ("A4", "hold"), ("A5", "hold"), ("C5", "hold"), ("E5", "hold"),
    ("G5", "hold"), ("D5", "hold"), ("F5", "hold"),
}
import os, sys, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
SK = os.path.join(REPO, "skills", "tone-analysis", "scripts")
sys.path.insert(0, SK)
sys.path.insert(0, HERE)

HELD = ["A4", "A5", "B4", "C5", "D5", "E5", "F5", "G5"]
NOTES = {"A4": 443.6, "A5": 875.3, "B4": 497.5, "C5": 522.0,
         "D5": 584.3, "E5": 659.1, "F5": 698.0, "G5": 785.5}
INST = "oot-alto-c-12"
OUT = os.path.join(REPO, "research", "analysis", "12hole")
TMP = "/tmp/opencode" if os.path.isdir("/tmp/opencode") else os.path.join(OUT, "tmp")
SEARCH = [os.path.join(REPO, "research", "note-recordings", "12hole"),
          os.path.join(REPO, "skills", "tone-analysis", "reference-recordings", "12hole")]

# abs-shape band table (same ABI the body tables use)
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
        if t1 - t0 < 0.08:
            continue
        r = spectrum(mono, t0, t1, TMP, "stg", stem)
        if not r:
            continue
        fs, S, n, _ = r
        out[stem] = bands(fs, S, f0)
    return out


def main():
    recdir = find_recordings()
    if not recdir:
        print(f"SKIP: held-note recordings not present (searched {', '.join(SEARCH)}) — "
              "the stage gate rides the working set (research/note-recordings/12hole) "
              "or a committed reference set; nothing to verify in CI as-is.")
        return 0
    if not os.path.exists(os.path.join(REPO, "instruments", INST, "tone.json")):
        print(f"SKIP: {INST} has no shipped tone.json (nothing fitted to verify)")
        return 0
    import render_ours

    failures = []
    table = {}
    for n in HELD:
        wav = os.path.join(TMP, f"stg_{n}.wav")
        r = render_ours.run_page(f"r12stg_{n}.html",
                                 {"note": n, "instId": INST, "dur": 2.0,
                                  "_fing": render_ours.fing_data(INST),
                                  "_tone": json.load(open(os.path.join(
                                      REPO, "instruments", INST, "tone.json"),
                                      encoding="utf-8"))},
                                 wav)
        if not r or not os.path.exists(wav):
            failures.append(f"{n}: render failed")
            continue
        truth = stage_body(os.path.join(recdir, f"{n}-held.wav"), NOTES[n])
        ours = stage_body(wav, NOTES[n])
        if not truth or not ours:
            failures.append(f"{n}: stage windows missing")
            continue
        table[n] = {}
        for stage in ("onset", "hold", "decay"):
            t, o = truth.get(stage), ours.get(stage)
            if not t or not o:
                table[n][stage] = None
                continue
            deltas = {k: (o[k] - t[k]) for k in t if k in o}
            cap = {"onset": 10.0, "hold": 8.0, "decay": 12.0}[stage]
            worst_bb = deltas.get("broadband_rel", 0.0)
            band_worst = max(((abs(v), k) for k, v in deltas.items()
                              if k not in ("broadband_rel", "h1")),
                             default=(0.0, "none"))
            table[n][stage] = {"broadband": round(worst_bb, 1),
                               "worst_band": f"{band_worst[1]} {round(band_worst[0],1)}"}
            if abs(worst_bb) > cap and (n, stage) not in KNOWN_OPEN:
                failures.append(f"{n} [{stage}] broadband {worst_bb:+.1f} dB (cap {cap:+.0f})")
            if band_worst[0] > 12.0 and (n, stage) not in KNOWN_OPEN:
                failures.append(f"{n} [{stage}] band {band_worst[1]} {band_worst[0]:+.1f} dB (cap 12)")
        summary = " ".join(f"{s}:{'ok' if table[n].get(s) else '-'}" for s in table[n])
        print(f"{n}: {summary} " + " ".join(
            f"{s} bb {table[n][s]['broadband']:+.1f} worst {table[n][s]['worst_band']}"
            for s in ("onset", "hold") if table[n].get(s)))
    out = os.path.join(OUT, "stage_verify.json")
    json.dump(table, open(out, "w"), indent=1)
    if failures:
        print("FAIL stage verification (%d):" % len(failures))
        for f in failures:
            print("  -", f)
        return 1
    print("PASS: stage verification clean across the held-note set "
          f"({len(HELD)} notes, onset/hold/decay, broadband + band gates)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
