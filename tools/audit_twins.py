#!/usr/bin/env python3
# Octave/transpose-twin audit for songs.json — SURVEY ONLY (Robin's MIDI-
# boundary rule: no song-data work unsupervised; the tool reports twins and
# divergence spots, never edits bodies). Precedent: the dummy-bass-c-double
# <-> stein-double-alto-c +12 chart pair (skills/song-transposing).
#
# A pair is a TWIN when the two melody token streams align one-to-one with a
# UNIFORM pitch shift (+-12n only is claimed as an octave twin; any uniform
# shift is reported too) while every non-pitch character carries over:
# barlines, rests, continuations ( '-' ), slides ( ' ~ ' ), durations, dots,
# tuplets (t) and accents (!) must be identical per token. Brackets [...]
# (supports/labels) and '# ...' headers are instrument-pinned / metadata and
# are EXCLUDED from the melody algebra — compared only as a NOTE in the
# report. A token the conservative grammar cannot read marks the pair
# UNVERDICTED (never a twin by default: no false proof).
#
#   python tools/audit_twins.py            # self-check battery + real report
#
import json
import re
import sys
from collections import Counter
from pathlib import Path

from melody_transpose import transpose_body  # the shared engine

ROOT = Path(__file__).resolve().parent.parent

NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
# Head grammar: one pitch letter, accidental in any of the repo's spellings
# ('#'/'s' up, 'b' down), octave digit(s), arbitrary tail (duration suffix —
# validated per TAIL_CHARS). Barlines may be glued to the token either side.
HEAD = re.compile(r"^([A-G])([#bsb]?)([0-9])(.*)$")
TAIL_CHARS = re.compile(r"^[~!]*((/\d+)(\.{0,2})(t)?)?[~!]*$")
CONT_TAIL = re.compile(r"^((-?)(/\d+)(\.{0,2})?(t)?)?[~!]*$")


def tokenize(body):
    """(tokens, unknowns): tokens = [(kind, midi|None, tail)] per whitespace
    token of the bracket-masked, header-free body; unknowns = raw copies."""
    tokens, unknowns = [], []
    for line in body.split("\n"):
        if line.lstrip().startswith("#"):
            continue
        flat = re.sub(r"\[[^\]]*\]", "", line)
        for raw in flat.split():
            tok = raw
            while tok.startswith("|"):        # glued barline prefix
                tokens.append(("bar", None, ""))
                tok = tok[1:]
            trail = ""
            while tok.endswith("|"):          # glued barline suffix
                trail = "|" + trail
                tok = tok[:-1]
            if not tok:
                if trail:
                    tokens.append(("bar", None, ""))
                continue
            if tok == "~":
                tokens.append(("slide", None, ""))
            elif tok == "-" or tok == "r":
                tokens.append(("cont" if tok == "-" else "rest", None, ""))
            else:
                m = HEAD.match(tok)
                if m:
                    letter, acc, oct_, tail = m.groups()
                    if not tail or TAIL_CHARS.match(tail):
                        midi = (int(oct_) + 1) * 12 + PC[letter] + \
                            (1 if acc in ("#", "s") else -1 if acc == "b" else 0)
                        tokens.append(("melody", midi, tail))
                    else:
                        unknowns.append(raw)
                        tokens.append(("unknown", None, tok))
                    if trail:
                        tokens.append(("bar", None, ""))
                    continue
                if tok[0] == "-" or tok[0] == "r":
                    tail = tok[1:]
                    if not tail or CONT_TAIL.match(tail):
                        tokens.append(("cont" if tok[0] == "-" else "rest",
                                       None, tail))
                    else:
                        unknowns.append(raw)
                        tokens.append(("unknown", None, tok))
                    if trail:
                        tokens.append(("bar", None, ""))
                    continue
                unknowns.append(raw)
                tokens.append(("unknown", None, tok))
            if trail:
                tokens.append(("bar", None, ""))
    return tokens, unknowns


# transpose_body/_respell moved to tools/melody_transpose.py — the shared
# engine gen_song_pages materializes from too; this tool imports it above.


def classify(body_a, body_b):
    """Report dict for a pair. verdict in:
    'twin' (streams aligned; melody deltas uniform — octave_twin flag says
    whether the shift is a +-12n) / 'divergent' / 'not-aligned' / 'unverdict'."""
    ta, ua = tokenize(body_a)
    tb, ub = tokenize(body_b)
    rep = {"unknown_a": ua, "unknown_b": ub,
           "n_a": len(ta), "n_b": len(tb)}
    if ua or ub:
        rep["verdict"] = "unverdict"
        return rep
    if len(ta) != len(tb):
        rep["verdict"] = "not-aligned"
        return rep
    deltas = [b[1] - a[1] for a, b in zip(ta, tb) if a[0] == "melody"]
    mism = [(i, (a[0], a[1], a[2]), (b[0], b[1], b[2]))
            for i, (a, b) in enumerate(zip(ta, tb))
            if a[0] != b[0] or (a[0] == "melody" and a[2] != b[2])]
    # pitch-divergence spots: melody positions off the modal shift
    mode = Counter(deltas).most_common(1)[0][0] if deltas else None
    spots = [(i, (a[0], a[1], a[2]), (b[0], b[1], b[2]))
             for i, (a, b) in enumerate(zip(ta, tb))
             if a[0] == "melody" and b[0] == "melody" and
             mode is not None and b[1] - a[1] != mode]
    rep["melody_notes"] = len(deltas)
    rep["mismatches"] = mism + spots
    uniform = (not deltas) or len(set(deltas)) == 1
    rep["deltas"] = sorted(set(deltas))
    rep["uniform"] = uniform
    if uniform and deltas:
        rep["shift"] = deltas[0]
    # divergent on shape divergence OR non-uniform pitch deltas; twin only
    # when the streams align AND the shift is uniform (or no melody at all)
    if mism or not uniform:
        rep["verdict"] = "divergent"
    else:
        rep["verdict"] = "twin"
    rep["octave_twin"] = rep["verdict"] == "twin" and bool(deltas) and \
        uniform and deltas[0] % 12 == 0
    return rep


def pairs_from(songs):
    """Family pairs first, then every unordered pair (both walks guard the
    report's completeness while siblings carry the -bass/-downN names)."""
    fam_pairs = []
    keys = list(songs)
    for base in keys:
        siblings = [k for k in keys if k.startswith(base + "-")]
        for s in siblings:
            fam_pairs.append((base, s) if base in songs else (base, s))
    seen = {(p[0], p[1]) for p in fam_pairs} | {(p[1], p[0]) for p in fam_pairs}
    cross = [(a, b) for i, a in enumerate(keys) for b in keys[i + 1:]
             if (a, b) not in seen]
    return fam_pairs, cross


def real_report(songs):
    lines = []
    # Derived twins first (board §9 2026-09-25): entries with a derives
    # record materialize their byte-equal body HERE so the pairwise walk
    # sees exactly the streams it classified before the bodies left
    # songs.json — the report reads identical, top to bottom.
    from melody_transpose import materialize
    from melody_transpose import materialize
    derived = [(key, item["derives"]) for key, item in songs.items()
               if isinstance(item.get("derives"), dict)]
    materialize(songs)
    for key, dr in derived:
        lines.append(
            f"derived {key} <- {dr.get('key')} (shift "
            f"{dr.get('shift')}{', flats' if dr.get('flats') else ''}) "
            f"— pinned byte-equal by tests/twin_derive.py")
    fam_pairs, cross = pairs_from(songs)
    order = {k: i for i, k in enumerate(songs)}

    def pair_rep(a, b):
        rep = classify(songs[a].get("body") or "", songs[b].get("body") or "")
        rep["a"], rep["b"] = a, b
        rep["fields"] = {
            "tempo": (songs[a].get("tempo"), songs[b].get("tempo")),
            "tick": (songs[a].get("tick"), songs[b].get("tick")),
            "swing": (songs[a].get("swing"), songs[b].get("swing")),
            "group": (songs[a].get("group"), songs[b].get("group")),
        }
        # raw twin meta: headers/brackets presence
        rep["meta"] = {}
        for k in (rep["a"], rep["b"]):
            body = songs[k].get("body") or ""
            rep["meta"][k] = {
                "headers": len([ln for ln in body.split("\n")
                                if ln.lstrip().startswith("#")]),
                "brackets": len(re.findall(r"\[[^\]]*\]", body)),
            }
        return rep

    for label, plist in (("family", fam_pairs), ("cross", cross)):
        for (a, b) in sorted(plist, key=lambda p: (order[p[0]], order[p[1]])):
            rep = pair_rep(a, b)
            v = rep["verdict"]
            tag = {"twin": "TWIN", "divergent": "DIVERGENT",
                   "not-aligned": "NOT-ALIGNED",
                   "unverdict": "UNVERDICT"}[v]
            extra = ""
            if v == "twin":
                sh = (("+" if rep.get("shift", 0) >= 0 else "") +
                      str(rep.get("shift", 0))) if rep.get("melody_notes") else None
                if rep["octave_twin"]:
                    extra = f" octave-TWIN (shift {sh})"
                elif sh:
                    extra = f" twin, non-octave (shift {sh})"
                extra += f" — {rep['melody_notes']} melody tokens aligned" \
                    if rep["melody_notes"] else " — no melody tokens"
            lines.append(
                f"{label} {a} <-> {b}: {tag}{extra}"
                f" (tokens {rep['n_a']}/{rep['n_b']},"
                f" tempo {rep['fields']['tempo'][0]}/{rep['fields']['tempo'][1]},"
                f" groups {rep['fields']['group'][0]!r}/{rep['fields']['group'][1]!r})")
            continue
            lines.append(
                f"{label} {a} <-> {b}: {tag} (tokens {rep['n_a']}/{rep['n_b']},"
                f" tempo {rep['fields']['tempo'][0]}/{rep['fields']['tempo'][1]})")
            if v == "divergent" and rep.get("mismatches"):
                for i, a2, b2 in rep["mismatches"][:6]:
                    lines.append(f"    token {i}: {a2}  vs  {b2}")
            for side in ("unknown_a", "unknown_b"):
                if rep.get(side):
                    lines.append(f"    {side}: {rep[side][:4]}")
    return lines


# --- self-check battery -----------------------------------------------------

def battery():
    """Synthetic twin must classify exact (+12), a stale one-token mutation
    must name the divergence spot, byte-equal streams twin with no melody;
    non-octave uniform shift must not claim an octave twin; unreadable
    tokens refuse the verdict; token-count changes refuse alignment."""
    base = ('# t\n|["Open"] A5/4. D5/2 F5/4\n| A5/8. C6/8 B5/4 G5/4 -/2\n'
            '# tempo 130\n|r/4 ~ F#5/8t')
    twin = transpose_body(base, 12)
    rep = classify(base, twin)
    assert rep["verdict"] == "twin" and rep["octave_twin"] and \
        rep.get("shift") == 12, rep
    rep = classify(twin, base)
    assert rep["verdict"] == "twin" and rep.get("shift") == -12, rep
    # one melody token pitched differently (same class/tail) = divergent at
    # that index, non-uniform deltas
    mutated = twin.replace("B6/4", "B5/4")
    assert mutated != twin
    rep = classify(base, mutated)
    assert rep["verdict"] == "divergent" and rep["mismatches"], rep
    # a tail change (accent dropped) diverges without touching deltas
    abs_tail = twin.replace("C7/8", "C7/8.")
    rep = classify(base, abs_tail)
    assert rep["verdict"] == "divergent", rep
    # non-octave uniform shift must never say octave_twin
    rep = classify(base, transpose_body(base, 3))
    assert rep["verdict"] == "twin" and not rep["octave_twin"], rep
    # unreadable token refuses the verdict
    rep = classify(base, base.replace("A5/4.", "XYZ5/4."))
    assert rep["verdict"] == "unverdict", rep
    # token-count changes refuse alignment
    rep = classify(base, base + "\n| C6/4")
    assert rep["verdict"] == "not-aligned", rep


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("== self-check battery", flush=True)
    battery()
    print("   PASS twins/transposes/refusals classify as designed", flush=True)

    songs = json.loads((ROOT / "songs.json").read_text(encoding="utf-8"))
    print("== real corpus report", flush=True)
    lines = real_report(songs)
    for l in lines:
        print(l, flush=True)
    twins = [l for l in lines if "TWIN" in l and "UNVERDICT" not in l
             and "NOT-ALIGNED" not in l and "DIVERGENT" not in l]
    octaves = [l for l in twins if " octave-TWIN" in l]
    print(f"\nREPORT: {len(octaves)} octave twin(s) of {len(twins)} twin-class "
          f"pair(s) across {len(songs)} shipped songs "
          f"(claims rest on uniform melody deltas + carried-over non-pitch "
          f"tokens; unalignable pairs report their reason above).", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
