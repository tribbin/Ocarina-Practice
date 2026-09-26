#!/usr/bin/env python3
# Track harmonization (session 16, the field-check feedback pass): removes
# same-pitch doublings between a song's MELODY stream and its named tracks.
# The melody's sounding window (onset + hold, '-' ties merge) is walked per
# stream token in absolute grid beats; any track note attacking while the
# melody sounds the same canonical pitch (flat spellings canonicalized,
# Db4 == Cs4) is a collision. Drops are applied in convergence rounds:
#   round 0  the colliding token an octave down (-12) — the classic bass
#            move ("the octave below the melody's other notes"),
#   round 1  a perfect fifth below (-7) when the octave lands ON another
#            melody note (happens: the melody itself rides low octaves),
#   round 2  another octave down for anything still colliding.
# Durations/beats are untouched, so the bar-grid alignment contract
# (tests/shipped_songs) holds by construction. Section labels are preserved;
# headers (#track <name> [zen] [%]) pass through untouched — mixing levels
# are a song-data call, never this tool's.
#
#   python tools/track_harmonize.py            # every song with a bass track
#   python tools/track_harmonize.py <key>...   # specific songs.json keys
#
# Pure stdlib, LF-only, idempotent (a second run reports no collisions).

import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SONGS = ROOT / "songs.json"

SPELL = {0: ("C", 0), 1: ("Db", 0), 2: ("D", 0), 3: ("Eb", 0), 4: ("E", 0),
         5: ("F", 0), 6: ("Gb", 0), 7: ("G", 0), 8: ("Ab", 0), 9: ("A", 0),
         10: ("Bb", 0), 11: ("B", 0)}
SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

def pitch_to_pic(p):
    m = re.match(r"([A-G])([#b]?)(\d+)$", p)
    letter, acc, octv = m.group(1), m.group(2), int(m.group(3))
    return (12 * (octv + 1) + SEMI[letter] +
            (1 if acc == "#" else -1 if acc == "b" else 0))

def pic_to_pitch(pic):
    L, off = SPELL[pic % 12]
    return L + str(pic // 12 - 1 - off)

def beats(dur):
    if not dur:
        return 1.0
    m = re.match(r"/(\d+)(\.?)(t?)$", dur)
    return 4 / int(m.group(1)) * (1.5 if m.group(2) else 1) * \
        (2 / 3 if m.group(3) else 1)

TOK = re.compile(r"([A-G][#b]?\d|r|-)(\/\d+\.?t?)?(?!\d)")
LABEL = re.compile(r'^\|\s*(\[\s*"(?:[^"\\]|\\.)*"\s*(?:,[^\]]*)?\])?')

def block_lines(text):
    """bar rows as (label_or_None, [(pitch_or_rest_or_tie, dur)])"""
    rows = []
    for line in text.split("\n"):
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        if not t.startswith("|"):
            raise SystemExit(f"non-bar line in a stream: {t!r}")
        lab = LABEL.match(t)
        label = lab.group(1) if lab and lab.group(1) else None
        tail = t[lab.end():].strip() if lab else t[1:].strip()
        rows.append((label, [(m.group(1), m.group(2) or "")
                             for m in TOK.finditer(tail)]))
    return rows

def rebuild(rows):
    return ["| " + (label + " " if label else "") +
            " ".join(k + d for k, d in toks) if toks else "|"
            for label, toks in rows]

def stream_tokens(text):
    """[(abs_onset, pic_or_None, hold, row_index, tok_index)] for pitches;
    a '-' tie extends the previous pitch's sounding window (crossing
    barlines, exactly what the melody's ring bars do)."""
    rows = block_lines(text)
    out, t_abs = [], 0.0
    for bi, (_label, toks) in enumerate(rows):
        pos = 0.0
        for ti, (kind, dur) in enumerate(toks):
            b = beats(dur)
            if kind == "-":
                if out and out[-1][1] is not None:
                    on, pic, hold, rb, rt = out[-1]
                    out[-1] = (on, pic, hold + b, rb, rt)
                pos += b
            elif kind == "r":
                pos += b
            else:
                out.append((t_abs + pos, pitch_to_pic(kind), b, bi, ti))
                pos += b
        t_abs += pos
    return out

def collisions(mel, bass):
    sound = [(pic, on, on + hold) for (on, pic, hold, _b, _t) in mel]
    hits = {}
    for (on, pic, _h, b, t) in bass:
        for (mpic, s, e) in sound:
            if mpic == pic and s <= on < e:
                hits.setdefault(b, set()).add((t, pic, on))
    return hits

def split_streams(body):
    mel, streams, cur, head = [], [], None, None
    for line in body.split("\n"):
        m = re.match(r"^#[ \t]*track\b[ \t]*(.*?)[ \t]*$", line, re.I)
        if m:
            cur = []
            head = (m.group(1) or "").strip()
            streams.append((head, cur))
            continue
        (cur if cur is not None else mel).append(line)
    return "\n".join(mel), streams

def reassemble(body, streams):
    parts = body.split("#track ")[0].rstrip("\n")
    for head, txt in streams:
        parts += "\n\n#track " + head + "\n" + txt.strip("\n")
    return parts + "\n"

def harmonize(body, label):
    mel_txt, streams = split_streams(body)
    mel = stream_tokens(mel_txt)
    rebuilt = []
    changed = False
    for head, lines in streams:
        txt = "\n".join(lines)
        name = head.split()[0] if head else None
        if name != "bass" and name != "contrabass" and name:
            # melodic tracks beyond the bass family can harmonize too; only
            # support-marker-free streams are safe (the parser chips those)
            pass
        if name not in ("bass", "contrabass"):
            rebuilt.append((head, txt))
            continue
        rows = block_lines(txt)
        story = []
        for round_i, drop in enumerate((-12, -7, -12)):
            bass = stream_tokens("\n".join(rebuild(rows)))
            hits = collisions(mel, bass)
            if not hits:
                break
            for bar, toks in hits.items():
                for (ti, pic, _on) in toks:
                    kind, dur = rows[bar][1][ti]
                    if kind in ("r", "-"):
                        continue
                    rows[bar][1][ti] = (pic_to_pitch(pitch_to_pic(kind) + drop), dur)
                    story.append((bar + 1, round_i, drop))
        left = collisions(mel, stream_tokens("\n".join(rebuild(rows))))
        name_of = head or ""
        print(f"{label} [{name_of}]: {len(story)} token drop(s) "
              f"{story if story else ''}; remaining collisions: "
              f"{sorted(left) or 'clean'}", flush=True)
        if story:
            changed = True
            txt = "\n".join(rebuild(rows))
        rebuilt.append((name_of, txt))
    return reassemble(body, rebuilt) if changed else None

def main():
    keys = sys.argv[1:]
    data = json.loads(SONGS.read_text(encoding="utf-8"))
    if not keys:
        keys = [k for k, s in data.items() if "#track" in (s.get("body") or "")]
    for key in keys:
        body = data[key]["body"]
        new = harmonize(body, key)
        if new is not None:
            data[key]["body"] = new
    SONGS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                     encoding="utf-8")

if __name__ == "__main__":
    main()
