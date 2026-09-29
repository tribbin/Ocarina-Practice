#!/usr/bin/env python3
# twin_support_level.py — the SUPPORT-LOUDNESS contract (Robin, 2026-09-28):
# "the support tracks should have the same volume" on every instrument.
# A named #track support note rendered through the Helmholtz twin on two
# instruments (12-hole and oak, both on the v45 12-hole model) must land
# within 1.5 dB of each other. Support loudness is the TWIN_SUPPORT_LEVEL
# mix, not the fitted melody row.
#
# Renders are the offline bench (skills/tone-analysis render_ours — patched
# module, dry wire, stubbed air/edge) driven in real time; ~40 s total.
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(REPO, "skills", "tone-analysis", "scripts"))
import render_ours
from tone_report import load_wav

TWIN_INST = "oot-alto-c-12"
ADD_INST = "ico-oak-leaf-bass-c-triple"
LEGS = ["E3", "G3"]  # the mid anchor + the higher support row of Epona's roots
TOL = 1.5  # dB


def plateau_db(path):
    rate, x = load_wav(path)
    x = np.asarray(x, dtype=np.float64)
    if x.ndim > 1:
        x = x[:, 0]
    rate_x = float(rate) if not hasattr(rate, "__len__") else float(rate[0])
    seg = x[int(0.70 * rate_x):int(1.20 * rate_x)]
    return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12)


def main():
    out = "/tmp/opencode" if os.path.isdir("/tmp/opencode") else os.path.join(REPO, "research", "analysis", "tmp")
    os.makedirs(out, exist_ok=True)
    twin_json = os.path.join(REPO, "instruments", TWIN_INST, "twin_model.json")
    failures = []
    plateaus = {}
    with open(twin_json, encoding="utf-8") as f:
        import json
        tw = json.load(f)
    tracks = {
        TWIN_INST: {"_fing": render_ours.fing_data(TWIN_INST), "_twin": tw,
                    "_bag": {"melodyRoute": True, "trackGain": 1.0}},
        ADD_INST: {"_fing": render_ours.fing_data(ADD_INST), "_twin": tw,
                   "_bag": {"melodyRoute": True, "trackGain": 1.0}},
    }
    for n in LEGS:
        for inst, cfg in tracks.items():
            base = dict(cfg, instId=inst, note=n, when=0.5, dur=1.2)
            wav = os.path.join(out, f"tsl_{inst}_{n}.wav")
            if not render_ours.run_page(f"tsl_{inst}_{n}.html", base, wav):
                failures.append(f"{inst} {n}: render failed")
                continue
            plateaus[(inst, n)] = plateau_db(wav)
    for n in LEGS:
        a, b = plateaus.get((TWIN_INST, n)), plateaus.get((ADD_INST, n))
        if a is None or b is None:
            continue
        delta = a - b
        if abs(delta) > TOL:
            failures.append(f"{n}: 12-hole support {a:+.2f} dBFS vs oak "
                            f"{b:+.2f} dBFS = {delta:+.2f} dB (cap ±{TOL}) — the "
                            "support loudness must not depend on the instrument")
    if failures:
        print("\nFAIL:")
        for m in failures:
            print("  - " + m)
        return 1
    print(f"\nPASS: the support/track loudness contract holds — Helmholtz "
          f"track notes land within {TOL} dB across instruments on the "
          f"anchor notes ({', '.join(LEGS)}), "
          "instrument-independent by construction (fixed TWIN_SUPPORT_LEVEL "
          "anchor × the supportLevel panel multiplier).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
