#!/usr/bin/env python3
"""Support loudness is one mix, not a per-instrument row.

The old offline render bench is gone. The contract that remains: every
support note goes through TWIN_SUPPORT_LEVEL, independent of the fitted
melody level.
"""
import sys
from pathlib import Path

text = (Path(__file__).resolve().parents[1] / "js/audio.js").read_text()
failures = []
if "const TWIN_SUPPORT_LEVEL = 0.75;" not in text:
    failures.append("TWIN_SUPPORT_LEVEL anchor missing")
if "TWIN_SUPPORT_LEVEL * (AUDIO_DEBUG.supportLevel || 1) / nf.level" not in text:
    failures.append("support notes must cancel the fitted level and use the anchor")
if failures:
    print("FAIL:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("PASS twin_support_level")
