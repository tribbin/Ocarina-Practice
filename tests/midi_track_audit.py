#!/usr/bin/env python3
# The MIDI-track audit as a suite: the tool (tools/midi_track_audit.py) is
# the sole verifier that the MIDI-interpreted twin's '#track' block carries
# each SOURCE measure's own content on the melody's bar lines. The rotation
# Robin caught by ear (bar 33 reading one beat late after the da-dum) is the
# class this pins against — a window-intersection read whose bar sums were
# all correct and whose engine walk showed 0.000 drift, yet sounded
# off-beat everywhere past bar 18.
#
#   python3 tests/midi_track_audit.py    # headless & silent

import json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "midi_track_audit.py"

# The melody grid (parser-truth lives in tests/shipped_songs): pure 4/4,
# 52 bars of 4 = 208 beats, equal to the game file's measure-for-measure
# timeline (the old 5-beat da-dum engraving was retired; see the tool).
LENGTHS = [4] * 52


def run(args):
    return subprocess.run(
        [sys.executable, str(TOOL)] + args,
        capture_output=True, text=True, cwd=str(ROOT))


def main():
    failures = []

    # Leg 1 — the shipped state passes the source audit (harmonize moves
    # allowed as recorded single octave-downs). Any edit that drifts the
    # interpreted block from the file's own measures fails here, bar named.
    r = run(["--check"])
    if r.returncode != 0:
        failures.append("shipped block fails the source audit:\n"
                        + (r.stdout or r.stderr)[-2000:])

    # Leg 2 — the raw regeneration is deterministic and fits the melody
    # grid: 52 bar rows, every row's /8 tokens sum to its melody bar length
    # (the da-dum row to 5, the finale row to 2).
    r = run(["--emit"])
    if r.returncode != 0:
        failures.append(f"--emit exited {r.returncode}: {r.stderr[-500:]}")
    else:
        rows = [l for l in r.stdout.split("\n") if l.startswith("| ")]
        if len(rows) != 52:
            failures.append(f"--emit produced {len(rows)} bar rows, want 52")
        for i, row in enumerate(rows):
            beats = 0.5 * row.count("/8")
            want = LENGTHS[i]
            if abs(beats - want) > 1e-6:
                failures.append(f"raw bar {i + 1} sums {beats} vs melody's "
                                f"{want}")
    raw_rows = rows if failures == [] else None

    # Leg 3 — the tripwire: a mutated bar 19 must fail the audit AND be
    # named. The mutation lengthens the swap: bar 19's first two tokens
    # trade places (its downbeat hit is displaced), exactly the shape of an
    # out-of-beat edit.
    if raw_rows:
        doctored = json.loads((ROOT / "songs.json").read_text())
        body = doctored[SONG := "outset-island-midi"]["body"]
        split = body.find("#track")
        head = body[:split]
        trk_lines = body[split:].split("\n")
        rows_in_body = [i for i, l in enumerate(trk_lines)
                        if l.lstrip().startswith("|")]
        toks = raw_rows[18].split(" ")  # "| Db4/8 Db5/8 r/8 ..." (bar 19)
        toks[1], toks[2] = toks[2], toks[1]  # displace the downbeat
        trk_lines[rows_in_body[18]] = " ".join(toks)
        cracked = dict(doctored)
        cracked[SONG] = dict(doctored[SONG],
                             body=head + "\n".join(trk_lines) + "\n")
        with tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False) as tf:
            json.dump(cracked, tf, indent=2, ensure_ascii=False)
            tf.write("\n")
            tmp = tf.name
        r = run(["--check", tmp])
        Path(tmp).unlink()
        if r.returncode == 0:
            failures.append("audit blind: a displaced bar-19 downbeat passed")
        elif "bar 19" not in r.stdout:
            failures.append(f"audit caught the edit but did not name bar 19:"
                            f"\n{r.stdout[-600:]}")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: the MIDI-interpreted twin's track matches its source "
          "measures bar-for-bar (displaced-downbeat tripwire caught).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
