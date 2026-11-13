#!/usr/bin/env python3
"""ICO 12-hole alto and bass, each fitted from a diatonic C-to-F ladder.

Sharps between recorded notes are log-f blends. The three notes below C
were not in the take, so they wear the C hold at their own pitch. A later
take that includes those notes changes the anchors, and this pin changes
with it.

  python3 tests/ico_12hole_twins.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECTRAL = ("h", "h_phase", "floor_db", "slope_db_oct", "air_db", "air_hi_hz")
# (id, diatonic anchors, clamped note ids, chart C, manifest fields)
INSTRUMENTS = (
    {
        "id": "ico-alto-c-12",
        "type": "Alto C 12-hole",
        "version": "Imperial City",
        "range": "A4\u2013F6",
        "title": "Alto C 12-hole (Imperial City)",
        "chart_range": {"low": "A4", "high": "F6"},
        "anchors": ["C5", "D5", "E5", "F5", "G5", "A5", "B5", "C6", "D6", "E6", "F6"],
        "clamped": ["A4", "As4", "B4"],
        "chart_c": "C5",
        "same_holes_as": "oot-alto-c-12",
        "octave_shift": 0,
    },
    {
        "id": "ico-bass-c-12",
        "type": "Bass C 12-hole",
        "version": "Imperial City",
        "range": "A3\u2013F5",
        "title": "Bass C 12-hole (Imperial City)",
        "chart_range": {"low": "A3", "high": "F5"},
        "anchors": ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "E5", "F5"],
        "clamped": ["A3", "As3", "B3"],
        "chart_c": "C4",
        "same_holes_as": "oot-alto-c-12",
        "octave_shift": -1,
    },
)

failures = []


def fail(msg):
    failures.append(msg)


def load(rel):
    path = ROOT / rel
    if not path.is_file():
        fail(f"missing {rel}")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def shift_id(nid, semitone_octaves):
    return nid[:-1] + str(int(nid[-1]) + semitone_octaves)


def main():
    manifest = load("instruments.json")
    oot = load("instruments/oot-alto-c-12/fingerings.json")
    if manifest is None or oot is None:
        return finish()
    if manifest.get("default") != "oot-alto-c-12":
        fail(f"default instrument moved: {manifest.get('default')!r}")

    for spec in INSTRUMENTS:
        iid = spec["id"]
        row = next((i for i in manifest["instruments"] if i["id"] == iid), None)
        finger = load(f"instruments/{iid}/fingerings.json")
        twin = load(f"instruments/{iid}/twin_model.json")
        if row is None:
            fail(f"instruments.json has no {iid}")
        else:
            expect = {
                "id": iid,
                "type": spec["type"],
                "version": spec["version"],
                "range": spec["range"],
                "fingerings": f"instruments/{iid}/fingerings.json",
                "svg": f"instruments/{iid}/ocarina-template.svg",
                "twin": f"instruments/{iid}/twin_model.json",
            }
            for key, want in expect.items():
                if row.get(key) != want:
                    fail(f"{iid} manifest {key}: {row.get(key)!r} != {want!r}")
            if "svgWhen" in row:
                fail(f"{iid} does not wear the OoT Saria drawing")
        if finger is None or twin is None:
            continue

        if finger.get("instrument") != spec["title"]:
            fail(f"{iid} chart title: {finger.get('instrument')!r}")
        if finger.get("range") != spec["chart_range"]:
            fail(f"{iid} chart range: {finger.get('range')!r}")
        if finger.get("system") != "Asian linear":
            fail(f"{iid} chart system: {finger.get('system')!r}")
        if finger.get("holes") != oot.get("holes") or finger.get("chambers") != oot.get("chambers"):
            fail(f"{iid} hole map differs from the 12-hole chart")
        shifted = []
        for note in oot["notes"]:
            expect_note = dict(note)
            if spec["octave_shift"]:
                expect_note["id"] = shift_id(note["id"], spec["octave_shift"])
                expect_note["display"] = "".join(
                    "₀₁₂₃₄₅₆₇₈₉"["₀₁₂₃₄₅₆₇₈₉".index(ch) + spec["octave_shift"]]
                    if ch in "₀₁₂₃₄₅₆₇₈₉" else ch
                    for ch in note["display"])
            shifted.append(expect_note)
        if finger.get("notes") != shifted:
            fail(f"{iid} fingerings are not the 12-hole chart"
                 + (" shifted one octave" if spec["octave_shift"] else ""))

        svg_path = ROOT / "instruments" / iid / "ocarina-template.svg"
        svg = svg_path.read_text(encoding="utf-8") if svg_path.is_file() else ""
        if not svg:
            fail(f"{iid} missing ocarina-template.svg")
        else:
            holes = set()
            for note in finger["notes"]:
                holes.update(note.get("covered") or [])
                holes.update(note.get("half") or [])
            for hole in sorted(holes):
                if f'data-hole="{hole}"' not in svg:
                    fail(f"{iid} svg has no data-hole {hole}")
            if 'data-blow="blow-ch1"' not in svg:
                fail(f"{iid} svg has no chamber-1 blow hole")

        notes = twin.get("notes") if isinstance(twin.get("notes"), list) else []
        ids = [n.get("note") for n in notes]
        chart_ids = [n["id"] for n in finger["notes"]]
        if twin.get("schema") != "ocarina-twin-v2":
            fail(f"{iid} schema: {twin.get('schema')!r}")
        if twin.get("chamber") != "1":
            fail(f"{iid} chamber: {twin.get('chamber')!r}")
        if (twin.get("globals") or {}).get("voice") != "v3k-chamber":
            fail(f"{iid} voice: {(twin.get('globals') or {}).get('voice')!r}")
        if ids != chart_ids:
            fail(f"{iid} twin notes {ids} != chart {chart_ids}")
        anchors = (twin.get("recorded") or {}).get("anchors")
        if anchors != spec["anchors"]:
            fail(f"{iid} anchors {anchors} != {spec['anchors']}")

        by_note = {n.get("note"): n for n in notes}
        missing = [n for n in spec["clamped"] + spec["anchors"] if n not in by_note]
        if missing:
            fail(f"{iid} missing rows {missing}")
            continue
        shared = {key: by_note[spec["clamped"][0]][key] for key in SPECTRAL}
        for name in spec["clamped"][1:]:
            for key in SPECTRAL:
                if by_note[name][key] != shared[key]:
                    fail(f"{iid} {name}.{key} is not the low-end clamp")
        chart_c = by_note[spec["chart_c"]]
        if chart_c["h"] == shared["h"] and chart_c["floor_db"] == shared["floor_db"]:
            fail(f"{iid} {spec['chart_c']} collapsed onto the low-end clamp")

    return finish()


def finish():
    if failures:
        print("FAIL ico_12hole_twins:")
        for msg in failures:
            print(" -", msg)
        return 1
    print("PASS ico_12hole_twins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
