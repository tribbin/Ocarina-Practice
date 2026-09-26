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

### 0. Whose MIDI is it — reduced arrangement vs full original

Wind-Waker practice (2026-09-26, Outset Island) taught a file hierarchy worth
checking first, because the two files carry different truths:

- **The full original arrangement** (third-party MIDI: no key/tempo metas,
  GM programs, 192 tpqn in that case) — the source for anything ACCOMPANIMENT:
  the bass groove lives only here (mid notes filtered to the low band catches
  the root line; watch for the FIFTH-slot of a root-octave-fifth bounce), as
  do string pads and fills.
- **The reduced/ocarina MIDI + its MuseScore score** (`<name>_ocarina.mid` +
  `...mscz`, 480 tpqn, full metas incl. key signatures and an exported
  IrregularMeasure as an explicit 5/4 for that bar) — the source for the
  MELODY carrier: the arranger already chose per section the instrument that
  owns the tune; read it section by section and splice chronologically.

If a score import exists, its written durations outrank the MIDI performance
(the MIDI releases notes early; durations in the file ≠ written values).
CAREFUL when reading the mscx: `pitch` lives on `<Note>` under `<Chord>`,
dots can live on the Note too, and grace runs print `32nd` — tally each
measure to the time signature to catch extractor dot-loss (an eighth-dotted
pair read as eighths under-fills the bar by 0.5).

### 0a. Splicing a multi-instrument carrier

Per section, keep ONE voice: the section's melodic owner only. Where two
instrument-staffs overlap in one bar (counter-melody), either pick the upper
or the tune-proper voice — a dyad bar (chord hits) keeps its LOWER voice when
the stepwise motion of the tune continues through it. Announce section for the
player with `|["Label (Key)"]` bar-heads, and carry mid-body `#` comment lines
(nothing at the very top — leading `#` lines become the title header).

### 0b. Handwritten ornaments from the MIDI

MuseScore exports performed trills/turns as real fast notes (32nd-pair +
held principal). The house convention (Outset Island, pending Robin's ears):
two 16ths + the held fundamental, e.g. `Gs5/16 ~ As5/16 ~ Gs5/4` — the `~`
slide colour reads as the turn. Bars must still sum: the turn cell must span
exactly the principal's original length.

### 0c. Pieces the chart can't reach

When the carrier dips below the ocarina chart (or attains no chart at any
octave): bars earlier/later get their own register (the Outset pizz vamp rides
+24 while the tune stays at pitch); single out-of-range notes become rests OR
the nearest octave-in neighbour, per Robin's later retune — write a `#`
comment line in the body naming exactly which notes were substituted/dropped.

### 0d. Onset-grid assembly — the technique that made the Outset run clean

This is what lifted the conversion quality (Robin: "better than any time
before") — generalize it instead of re-deriving per song:

1. **Dump ONSETS, not durations.** For each carrier channel print
   `M{bar}.{beat} pitch` from a meter map (a per-measure beat-count function:
   `4` for every bar except the score's irregular ones) — position truth
   lives in the onset grid, and the 5/4-type bars fall out of the map instead
   of breaking a global 4-beat guess.
2. **Build tokens from the gap structure.** A token OWNS the time from its
   onset to the next onset in that bar; a gap longer than the note's own
   sounding length becomes a rest. Read the WRITTEN score (mscx) where it
   disagrees with the MIDI product: the MIDI's `0.248/0.498/0.998` durations
   are early-release artifacts, not rhythm — the da-dum's real shape was
   `r/8 A/8 A/4 r/8 A/8 A/4` from the score, never from the file's durs.
3. **Snap performed ornaments to the token grid, then let the bar-sum be the
   arbiter.** Turn cells land at `.25/.625` positions in the file; a /16 pair
   rearranges them without moving the cell's span. Every bar must SUM to its
   meter's beats (the irregular bar to *its* beats) — a bar that misses by
   exactly the ornament's fuzz is a dot-loss from the extractor, not a music
   error.
4. **Two-switch acceptance loop before shipping:**
   `node skills/song-transposing/scripts/verify_song.cjs <key> <chart>` (0
   unknown ids, 0 bad chips, fits chart) + a per-bar sum check against the
   meter map (hand-counter or throwaway script — the Outset one also pinned
   the with-bass body's supports as zero-beat spans). Then the usual suites
   (shipped_songs, gen_pages) prove the data in-app.
5. **Keep every intervention visible in the body:** octave substitutions,
   dropped tails, dyad-voice choices and trill normalizations each get a `#`
   comment line naming the bar numbers — Robin retunes from those lines
   without re-deriving the source.

### 0e. Companion track from the full arrangement (Backed Melody variant, 2026-09-26)

To build a `#track <name> [audible]` block whose accompaniment is the full
arrangement's own voice (Outset Island's MIDI bass, done as `outset-island-midi`):

1. **Align to the APP's melody grid, not a meter map.** The track bar-sum
   contract (`tests/shipped_songs`) demands per-bar beat sums equal to the
   SHIPPED melody's bars — parse the melody with the real parser (a
   headless page.evaluate collecting per-bar sums) and use its cumulative
   boundaries. When the app's grid and the file's own meter disagree, stop:
   an odd measure is a suspect, not an accommodating fact — see §0f.
2. **Pick the voice by channel + band, and state the drops.** The groove
   channel (ch0) carried everything; a second low channel that chugs the
   same line in 16ths is a double, not a voice — exclude it and say so.
   Same-onset chord hits are one voice's octave register, not harmony: keep
   the LOW band (pitch < C4 for the Outset bass — the harp-register doubles
   C#4-F5 lived only in the interludes) and name the bars in a body
   comment.
3. **Project the register by rule, not hand-scan.** Whole voice +24 to the
   triple board; a projected root below the chart floor (A3 = midi 57)
   rides one octave more. Expect a below-floor root's octave PAIR
   (root + its upper octave one shimmer apart) to collapse to the same
   projected pitch — write the flattened pair down in the comment; Robin
   retunes from those lines. Flat spellings: the body speaks the melody's
   accidental language (Db/Eb/Gb/Ab/Bb), never the MIDI's sharps.
4. **Humanized 16th chugs stay out; half-beat hits stay in.** The Outset
   bass was pure eighth-hits on an exact half-beat grid — each token owns
   its onset-to-next-onset span (hit + rest fill), the tail hit past the
   melody's finale gets trimmed, and every bar sums by construction. A
   channel whose hits land off the 16th grid (humanized ornaments) would
   need the snap step instead — don't assume one pattern generalizes.
5. **Then the harmonize pass, then the suites.** Insert the block at the
   same gain as the twin it will A/B against, run
   `tools/track_harmonize.py <key>` (drops every attack the melody sounds
   the same pitch — the arrangement doubling its own tune drops down an
   octave, which is the honest sound), re-run to prove idempotence, then
   `tests/shipped_songs` re-proves the bar grid in the real app.

### 0f. Measure-content map, not window intersection (the Outset rotation, 2026-09-26)

The first MIDI-track assembly read the file by WINDOW INTERSECTION: each
melody-bar span collected whatever source hits fell inside its tick range.
Robin's ears caught the result as "out of beat past the `~` series" while
every mechanical check stayed green (bar sums matched, engine walk 0.000
drift): the shipped melody held a 5-beat da-dum bar 18 (inherited from the
reduced score's own 5/4 meta at that point), so every later bar's window
drank the NEXT measure's tail and the track content rotated one beat late —
bar 33's bass was bar 7's content displaced into its second eighth. The
file's own bars 7 and 33 were byte-identical; his thumbprint ("in the midi
they are identical") was the oracle that proved the reading, not the
engine, was faulty. Then his second read dug deeper: the 5/4 itself was
the reduced score's engraving error — its fifth beat (the ocarina.mid's
extra Eb at [72, 72.5)) was the ARRANGER's own human slip, absent from the
game's file, whose timeline is pure 4/4 (the tune voice silent through
[68, 72.5), the groove's bass entering exactly at 72). The app's melodies
now run pure 4/4 equal to the game's measure-for-measure. Rules:

0. **An odd measure is Robin's ear check, not a fact (his note,
   2026-09-26).** When any source declares an irregular meter (a 5/4 amid
   4/4, a stretched bar, a measure whose content disagrees between
   arrangements), do not swim along — surface it and ask him to verify
   against the source material by ear before the transcription ships with
   it. Two arrangements disagreeing about one bar is a meter flag, not a
   choice to make silently.
1. **Map measures to melody bars BY CONTENT, not by window.** Measure k's
   full hit pattern plays on melody bar k at unchanged bar-relative
   positions — the bar's downbeat stays the bar's downbeat. When the app's
   grid equals the file's meter, the content map is trivially exact; when
   they disagree, see rule 0 before accommodating.
2. **Parallel-bar content classes are the acceptance oracle.** The tune and
   its return are byte-parallel in the melody carrier; the bass under them
   must be the same class the file proves (7 ≡ 33, and the audit's raw
   identity graph names the shared measures). If a parallel bar's bass is
   not the file's class, the mapping is wrong even when grids align.
3. **Verify with `tools/midi_track_audit.py --check`** (the Outset
   instance: `--emit` regenerates the pre-harmonize block; `--check`
   re-derives the expectation from the file and fails naming every
   mismatched bar/offset; harmonize's single octave-down moves are
   allowed). `tests/midi_track_audit.py` runs it with a displaced-downbeat
   tripwire, CI-registered. Any future MIDI-track song adds its own
   contract line to this tool rather than re-deriving a checker.
4. **The finale feeds the loop.** A song's last bar that truncates short of
   its source measure makes the loop restart land on dead air: carry the
   source measure's full content in both streams (Outset bar 52 = the
   game's full measure-52 vamp in the track, the hold completing to 4
   beats in the melody) so the closing vamp runs straight into the opening
   one.




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
