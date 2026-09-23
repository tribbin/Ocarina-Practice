---
name: midi-to-ocarina-tab
description: >
  Convert a MIDI file (.mid) into this ocarina tabber's songs.json notation.
  Use when the user provides or points to a MIDI file and wants a song added,
  or asks to transcribe/extract a melody from MIDI. Handles channel/instrument
  discovery, onset quantization with 16th + triplet support, meter/bar
  verification, and A3-G6 range fitting. Trigger words: "midi", ".mid",
  "convert the midi", "from the midi", "transcribe this file".
---

# MIDI → ocarina tab

Turn a `.mid` file into a `songs.json` `body` for this Bass-C-Triple tabber.
Pairs with the **ocarina-melodies** skill (notation grammar, range, songs.json
shape). Read `js/parse.js` before finalizing.

A helper script lives beside this file: `scripts/mid2tab.py` (pure stdlib,
no deps).

## Workflow

### 1. Inspect — find the melody channel

```
python3 scripts/mid2tab.py FILE.mid --inspect
```

Lists every channel with its GM instrument, note count, the **bar it enters**,
its pitch range, and its first ~20 notes. The lead melody is often NOT the
obvious track:

- The instrument label can be misleading (e.g. Concerning Hobbits' melody was
  on a channel labelled **Cello** playing in the D5–C#6 register, not the
  Recorder).
- Match against what the user hums/expects, and against the register (melody
  usually sits highest / most stepwise, accompaniment is arpeggiated or low).
- **Confirm the channel with the user** if two candidates look plausible.

### 2. Convert one channel

```
python3 scripts/mid2tab.py FILE.mid --channel N --start-measure M \
        --beats-per-bar B [--legato] [--bars K] [--transpose S]
```

- `--start-measure M` — 1-based measure where the melody enters (its
  downbeat). The grid aligns here; earlier notes are dropped. Read it from the
  `--inspect` "enters bar" value (bar 12.0 → measure 13).
- `--beats-per-bar B` — meter numerator in quarter-beats: `4`=4/4, `3`=3/4,
  `2`=2/4. Get the real meter from the score/user, not by guessing.
- `--legato` — **prefer this first.** Each note lasts until the next onset (no
  rests). Because it is pure onset-to-onset, every bar balances exactly and it
  is robust to humanized note-off timing.
- default (articulated) — keeps real note lengths and inserts rests in the
  gaps. Captures a detached/breathy feel, but humanized MIDI note-offs usually
  leave a few bars slightly off; expect to hand-clean those bars.
- `--transpose S` — semitone shift to fit the A3–G6 range.
- `--straight-16ths` — disable triplet detection (grid = 16ths only).

Every bar is verified against the meter and printed to stderr with a
`MISMATCH` flag if it doesn't sum. **Never ship a body with a MISMATCH or an
`<UNQUANTIZED:n>` token.**

### 3. Triplets

The script auto-detects triplets: an onset closer to the 1/12-quarter grid than
the 1/16 grid becomes a triplet (`/16t`, `/8t`, `/4t`). Three `/16t` = one
eighth; three `/8t` = one quarter. This is what made bar 2 of The Shire
(`A5/16t B5/16t A5/16t`) fit — a straight-16th grid silently dropped the middle
note as a zero-length grace.

If the app lacks triplet support, add it first (parser `parseDur`: append `t`,
`beats *= 2/3`; propagate a `triplet` flag; `durLabel` shows a `³`).

### 4. Clean up and place

- Prefer `--legato` output; if the user wants the detached articulation, start
  from the articulated output and hand-fix the flagged bars (round note-off
  slivers, merge stray `-/16 r/16` tails).
- Merge zero-length grace notes into their main note (the script already drops
  them).
- Fit the range (A3–G6); transpose whole octaves if needed.
- Add a final rest so Loop returns cleanly (see ocarina-melodies).
- Paste into `songs.json` as `{ "name", "group":"Songs", "tempo", "body" }`.
  Read the tempo from the MIDI's tempo meta event (the script's parser reads it
  if you extend it, or read it from the file/DAW).

### 5. Verify

- Re-run and confirm **all bars OK: True**.
- Every note id must exist in `fingerings.json` (A3–G6).
- Load in the app: no out-of-range marks, duration glyphs match the source,
  triplets show the `³` marker.

## Notes on the MIDI format

- Handles SMF format 0 (all channels in one track) and format 1.
- `--inspect` reads GM program-change events for instrument names.
- Overlapping notes on the chosen channel are made monophonic (a note is
  truncated at the next onset).
