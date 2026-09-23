---
name: ocarina-melodies
description: >
  Transcribe playable single-line melodies into this Bass C Triple ocarina tabber
  (songs.json notation, durations, swing, loop rests, A3–G6 range). Use when adding
  or correcting a song, fixing rhythm/durations, choosing octave, or writing
  ocarina letter-note tabs. Use when the user runs /ocarina-melodies.
---

# Ocarina melodies

Add or fix tunes in `songs.json` so they play correctly in this tabber. Read `js/parse.js` and an existing song in `songs.json` before writing.

## Notation

```
C4 C#4 Db4     note + optional accidental + octave (octave sticks until changed)
|              barline (visual; does not consume time)
r / r/4 / r/1  rest
- / -/4 / -/2. continue the previous note across a bar (not a new attack)
/1 /2 /4 /8 /16   duration (default /4 = quarter)
/2. /4.        dotted (×1.5)
/8t /16t       triplet (×2/3): three /8t fill one quarter-beat
# Title
# tempo 160    starting tempo; a later "# tempo N" line changes tempo mid-song
# swing 67     omit this line when swing is 0
```

Beats of a token = `(4 / dur) * (dotted ? 1.5 : 1) * (triplet ? 2/3 : 1)`. A quarter is 1 beat.

Input spelling (`C#` vs `Db`) is what tokens and tabs show. Fingering/audio use sharp-based ids (`Cs4`). `#` at line start is a comment, not a sharp.

## Transcribe

1. Get **pitch sequence** from an ocarina/single-line source, and **durations + meter** from a source that marks them (e/q/h tabs, MIDI/IOI, user-confirmed text). Letter names alone are not enough.
2. Pick a meter and make **every bar sum to that meter** (3/4 → 3 quarter-beats). If the user pastes a finished body, use that text; do not "improve" other phrases while fixing one.
3. To hold a note across a bar, write `-` with the leftover duration (`E4/4 | -/2`). Do not repeat the note name — that is a new attack. When splitting a held note, **replace that one token**. Do not also keep the following note if that creates a third attack.
4. Endings: if Loop should hit the next downbeat cleanly, add a rest (`r/4`, `r/2`, `r/1`) so the cycle length is intentional. Loop always returns to the **start of the song**, even if playback began mid-tune.
5. Prefer the **ocarina melody**, not piano inner voices or bass.

Staccato: append `!` to a note (`C4!`, `C4/8!`) to play it short and detached with an implied pause after it. The written duration still fills the timing slot; only the sounding length is shortened. Do not put `!` on a tie/rest.

User-confirmed notation wins over all sources.

## Fit this instrument

- Range **A3–G6** (`fingerings.json` note ids). If the concert melody goes below A3, transpose up an octave.
- Prefer the octave that **minimizes chamber jumps** (chamber is on each note in `fingerings.json`). Song of Storms in D minor uses D4–F5 (D3 is below the instrument).
- Natural-minor/dorian tunes that stay on white keys fit C fingering with no accidentals.

## `songs.json`

```json
"slug": {
  "name": "Song Title",
  "group": "Songs",
  "tempo": 160,
  "swing": 67,
  "body": "D4/8 F4/8 D5/2 | ..."
}
```

- `body` is melody only (no `#` headers). The loader prepends `# name`, `# tempo`, and `# swing` only when swing > 0.
- Omit `swing` (or use 0) for straight songs. 67 ≈ triplet shuffle.
- After edit, load the song in the app: no out-of-range tokens, duration glyphs match the source, `# swing` absent when 0.

## Check before finishing

- Each `|`-delimited bar sums to the meter (except a user-specified final whole note + whole rest).
- Every note id exists in `fingerings.json`.
- No extra attacks next to a split long note.
- Loop rest exists only if needed for the groove.
