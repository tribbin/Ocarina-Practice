# Unit tests for the song-transposing skill scripts (transpose.cjs /
# verify_song.cjs). The scripts are node tools that eval the app's real
# js/parse.js as the syntax oracle, so the suite drives them over a
# synthetic songs.json in a temp sandbox and asserts on plain output â€”
# no browser, no playwright. Skips (exit 0, named) when node or the
# skill scripts are absent, so machine-less environments stay green.
#
# Pins the semantics agreed 2026-09-23:
#   - every [...]-bracket (section labels, bar supports, inline supports,
#     [-/2] extensions, [~..] glides) passes VERBATIM: supports are
#     instrument-pinned chambers, never melody
#   - s-form tokens (Cs4) transpose as their sharp equivalent, output
#     re-spelled into the sharp system
#   - note-shift exactness stays the internal guard (src+shift == dst)
#   - written entries inherit ALL source fields (tick, swing, hidden, ...)
#     and override name/group/body only
#   - comments and inline # tempo lines are untouched
#   - verify_song reports out-of-chart bodies with exit 1

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "song-transposing" / "scripts"
PARSE = REPO / "js" / "parse.js"
CHART = REPO / "instruments" / "ico-oak-leaf-bass-c-triple" / "fingerings.json"
CHART_BASS_DOUBLE = REPO / "instruments" / "dummy-bass-c-double" / "fingerings.json"
CHART_ALTO_DOUBLE = REPO / "instruments" / "stein-double-alto-c" / "fingerings.json"

# melody inside A3-G6; +2 lands D#4/F#4/G4/A4/A#4; +31 overflows the top
BODY = ('# heading comment\n'
        'Cs4 E4 F4 | ["Section", C2/2] G4 [C2/4.] r/4 [-/2] [~F2/4] Gs4\n'
        '# tempo 104\n'
        'Cs4 E4 | ["plain desc"]')
SRC = {"name": "Probe One", "group": "Other", "tempo": 96,
       "tick": True, "swing": 33, "hidden": True, "body": BODY}


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True,
                          encoding="utf-8", errors="replace", timeout=120)


def main():
    if shutil.which("node") is None:
        print("SKIP transpose_skill (node absent â€” nothing to test)")
        return 0
    if not (SCRIPTS / "transpose.cjs").exists() or not PARSE.exists():
        print("SKIP transpose_skill (skill scripts or parse.js absent)")
        return 0

    sandbox = Path(tempfile.mkdtemp(prefix="transpose-probe-"))
    failures = []
    try:
        (sandbox / "js").mkdir()
        shutil.copy(PARSE, sandbox / "js" / "parse.js")
        shutil.copy(CHART, sandbox / "fingerings.json")
        shutil.copy(CHART_BASS_DOUBLE, sandbox / "bass-double.json")
        shutil.copy(CHART_ALTO_DOUBLE, sandbox / "alto-double.json")
        (sandbox / "songs.json").write_text(
            json.dumps({"probe1": SRC}, indent=2), encoding="utf-8")

        args = [str(SCRIPTS / "transpose.cjs"), "probe1", "+2", "--dry"]
        r = run(["node", *args], sandbox)
        if r.returncode != 0:
            failures.append(f"dry run exit {r.returncode}: {r.stderr.strip()}")
        else:
            out = r.stdout
            for phrase in ('["Section", C2/2]', '[C2/4.]', '[-/2]',
                           '[~F2/4]', '["plain desc"]',
                           "# heading comment\n", "# tempo 104\n"):
                if phrase not in out:
                    failures.append(f"dry lost verbatim: {phrase!r}")
            if "Cs4" in out:
                failures.append("dry kept an s-form token unnormalized")
            for want in ("D#4", "F#4", "A#4"):
                if want not in out:
                    failures.append(f"dry missing normalized {want}")
            if "exact +2 per note: true" not in out:
                failures.append("dry: per-note exactness not true")

        r = run(["node", str(SCRIPTS / "transpose.cjs"),
                 "probe1", "+2", "probe2", "Probe Two", "Other"], sandbox)
        if r.returncode != 0:
            failures.append(f"write run exit {r.returncode}: {r.stderr.strip()}")
        else:
            songs = json.loads((sandbox / "songs.json").read_text(encoding="utf-8"))
            dst = songs.get("probe2")
            if not dst:
                failures.append("probe2 entry not written")
            else:
                for k, want in (("tick", True), ("swing", 33), ("hidden", True),
                                ("name", "Probe Two"), ("tempo", 96)):
                    if dst.get(k) != want:
                        failures.append(f"inherited field {k}: {dst.get(k)!r} != {want!r}")
                for phrase in ('["Section", C2/2]', '[C2/4.]', '[~F2/4]'):
                    if phrase not in dst["body"]:
                        failures.append(f"written body lost verbatim: {phrase!r}")

        r = run(["node", str(SCRIPTS / "verify_song.cjs"),
                 "probe2", "fingerings.json"], sandbox)
        if r.returncode != 0:
            failures.append(f"verify in-range exit {r.returncode}: {r.stdout.strip()}")
        elif "unknown ids: none" not in r.stdout or "fits chart: true" not in r.stdout:
            failures.append(f"verify verdict wrong: {r.stdout.strip()}")

        r = run(["node", str(SCRIPTS / "transpose.cjs"),
                 "probe1", "+31", "probe3", "Out Of Chart", "Other"], sandbox)
        if r.returncode != 0:
            failures.append(f"overflow transposition itself failed: {r.stderr.strip()}")
        r = run(["node", str(SCRIPTS / "verify_song.cjs"),
                 "probe3", "fingerings.json"], sandbox)
        if r.returncode != 1:
            failures.append(f"out-of-chart verify exit {r.returncode} (want 1)")
        elif "fits chart: false" not in r.stdout:
            failures.append(f"out-of-chart verdict wrong: {r.stdout.strip()}")

        # chart-pair invariant (Robin, 2026-09-23): a song fitting the bass
        # double (A3-C6) always fits the alto double (A4-C7) at +1 octave â€”
        # the alto chart IS the bass-double chart shifted 12 (28 notes both).
        r = run(["node", str(SCRIPTS / "transpose.cjs"),
                 "probe1", "+12", "probe4", "Alto Double", "Other"], sandbox)
        if r.returncode != 0:
            failures.append(f"+12 transposition failed: {r.stderr.strip()}")
        else:
            r = run(["node", str(SCRIPTS / "verify_song.cjs"),
                     "probe4", "alto-double.json"], sandbox)
            if r.returncode != 0 or "fits chart: true" not in r.stdout:
                failures.append(f"+12 double-pair misfit: {r.stdout.strip()}")
            r = run(["node", str(SCRIPTS / "transpose.cjs"),
                     "probe4", "-12", "probe5", "Back To Bass", "Other"], sandbox)
            if r.returncode != 0:
                failures.append(f"-12 back-shift failed: {r.stderr.strip()}")
            else:
                r = run(["node", str(SCRIPTS / "verify_song.cjs"),
                         "probe5", "bass-double.json"], sandbox)
                if r.returncode != 0 or "fits chart: true" not in r.stdout:
                    failures.append(f"-12 return misfit: {r.stdout.strip()}")
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    if failures:
        print("FAIL transpose_skill:", len(failures))
        for f in failures:
            print("  -", f)
        return 1
    print("PASS transpose_skill: brackets verbatim, s-form normalized, "
          "fields inherited, verify gates in/out of chart")
    return 0


if __name__ == "__main__":
    sys.exit(main())
