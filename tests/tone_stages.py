#!/usr/bin/env python3
"""Current-voice contract. The old render-vs-recording gate is gone.

A change may not put the band-pass fitter back, and every shipped twin
row must carry the v3k fields the voice reads.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
failures = []
voice = (REPO / "js/helmholtz-voice.js").read_text()
if 'VOICE_REV = "v3l-chamber"' not in voice:
    failures.append("helmholtz-voice.js must stamp v3l-chamber")
if "noise_mid_db" in voice or "effectiveNoiseQ" in voice:
    failures.append("the old mid-air graph is back in the voice")
if (REPO / "skills/ocarina-twin/ocarina_twin").exists():
    failures.append("the pre-v3k fitter package is back")
if (REPO / "skills/tone-analysis").exists():
    failures.append("tone-analysis would send a later session at the old synth")
for path in (REPO / "instruments").glob("*/twin_model.json"):
    data = json.loads(path.read_text())
    models = []
    if "chambers" in data:
        models = [c["model"] for c in data["chambers"].values()]
    else:
        models = [data]
    for model in models:
        row = model["notes"][0]
        for key in ("h", "h_phase", "floor_db", "slope_db_oct", "air_db", "air_lo_hz", "air_hi_hz"):
            if key not in row:
                failures.append(f"{path.parent.name} missing {key}")
if failures:
    print("FAIL:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("PASS tone_stages")
