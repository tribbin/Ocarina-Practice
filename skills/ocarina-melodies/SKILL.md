---
name: ocarina-melodies
description: The up-to-date truth for writing and editing music in this tabber's songs.json — the full notation grammar (notes/s-forms, durations, dots, triplets, ties, slides, staccato), the bar/section/support feature family and its Zen-only playback, per-chart fitting across all five ocarinas, player-facing formatting conventions, and the transcription craft rules (bar balancing, tie-split token rule, loop rests). Use when adding or correcting a song, when asked what the tabber supports, when writing support drones or section labels, or when standardizing existing song bodies. Not music theory — tool application.
---

# Ocarina melodies

The single source of truth for what this tabber's notation and features can
express, and how to apply them correctly when adding or fixing a tune in
`songs.json`. Read `js/parse.js` and an existing song before writing; the
transposer skill (`song-transposing/SKILL.md`) owns pitch rewrites and chart
pair math — this file owns general notation and conventions.

## `songs.json` entries

```json
"slug": {
  "name": "Song Title",
  "group": "Songs",
  "tempo": 160,
  "body": "D4/8 F4/8 D5/2 | ..."
}
```

- Optional fields: `swing` (0–100-ish; omit or 0 = straight; 67 ≈ triplet
  shuffle), `hidden: true` (WIP carrier — stays in Git but hidden from the
  dropdown until "Show hidden songs"; songs with out-of-range notes for the
  current ocarina are auto-hidden the same way), `tick` (stores the
  metronome switch with the entry; `"tick": false` makes the song load with
  the metronome off).
- `body` carries melody only, no leading `#` headers — the loader prepends
  `# name`, `# tempo`, and `# swing` (only when swing > 0) into the editor.
- Load the song in the app after every edit: no out-of-range marks,
  duration glyphs match the source, `# swing` absent when 0.

## Notation (tokenizer truth — `js/parse.js`)

| | |
|---|---|
| `C4 C#4 Db4 Cs4` | note + accidental + octave; s-forms (`Cs4`) are melody grammar and display-normalize to `#`. Octave sticks until changed |
| `r`, `r/4`, `r/1` | rest |
| `-`, `-/4`, `-/2.` | continue the PREVIOUS note across bar(s) — a tie, never a new attack |
| `~`, e.g. `F4 ~ A4` | slide into the note (practice treats a slide as a chain to travel) |
| `/1 /2 /4 /8 /16` | duration, default `/4`; `/2. /4.` dotted (×1.5); `/8t /16t` triplet (×2/3) |
| `!`, `C4!` `C4/8!` | staccato: sounding length shortens, the written duration still fills the slot; never on a tie/rest |
| `\|` | barline (visual; consumes no time — an empty bar adds zero time) |
| `\| [Section]` | names a bar: shown on hover and as a header row in section-aware views |
| `# anything` | comment line. A leading `# title` is the default; `# tempo N` mid-body changes tempo mid-song |
| `bad` chips | anything unparsable shows as a visible tan chip — a body must produce ZERO bad chips |

Beats of a token: `(4/dur) × (dotted ? 1.5 : 1) × (triplet ? 2/3 : 1)`. A
quarter is 1 beat.

## Support voices (bracket family — Zen playback only)

Instrument-pinned drones, heard as a chamber-voice under the melody in Zen
playback practice only. Supports are never transposed: the pitch names are
chambers of the specific ocarina, not melody notes.

- `| [C2]` — bar support: rings for that whole bar.
- `| ["Section name", C2]` — named section bar that ALSO carries a support.
- `[C2]` — inline support, rings to the next bar/rest. `[C2/4.]` — its own
  length.
- `[-/2]` — extends the running support's ring (`[C2/2] [-/2]` = one
  4-beat voice, tie-chain-like).
- `[~F2/4]` — glide that slides in from the running chain's pitch.

Support pitches live BELOW the melody chart (C2/C3 territory); every note id
inside an inline/bar support must resolve for the ocarina's support voice.
Support starts AFTER the previous chain ends: the engine starts a support
with the next rest/note following the previous note chain.

First real ships 2026-09-26 (the Outset Island trio — read them as worked
examples): `outset-island-with-bass` was BORN with per-bar root drones
(`| [Cs2]`, section-head brackets `|["Opening (Db major)",Cs2]`); the same
day it moved ON to a real groove track (below) and no longer carries
brackets — the drones survive only as the Zen-only layer's mechanism.

Engine-side craft rules (from `audio.js` `buildSupportPlan`):

- Support pitch spellings accept **sharp, s-form AND flat** (`Gs2`, `G#2`,
  `Ab2`) — everything canonicalizes to the s-spelled chart id through the
  parser's shared flat table (`Ab2`→`Gs2`, `Db2/4.`→`Cs2/4.`, `Cb3`→`B2`),
  so all three spellings reach the same drone (parse.js `coreIdOf`, pinned by
  tests/parse_edges). What still vanishes silently: anything that is NOT a
  fully-shaped pitch with an octave digit — junk tails and label prose stay
  desc-only, never bad chips.
- A bracket PARKS and fires on the next melody note OR REST: to start a
  support mid-bar you need the melody to attack there; the Outset bottom-half
  splits (`| [F2/2] … [As2/2]`) lean on a beat-2 melody note. A rest also
  pivots, so a support can sit alone over a rest bar.
- Durationless ring = to the next BARLINE (or, past the last note, to the last
  token); explicit length `[Cs2/2]` sounds that many beats; `[-/2]` extends the
  running chain; `[~F2/4]` glides in from the running chain's pitch.
- Supports never count against the melody's range check (melody notes only) —
  but the drone does ring through the melody voice's model at that frequency,
  so unreachable-looking ids still sound (tuned by ear; the model extrapolates).
- Sub-register + stepper: keep the drone's pitch BELOW the melody's own
  octave; the melody voice already implies its own octave — drones belong in
  the lower-chamber world.

## Multi-track (named `#track` blocks — real second melodies)

Parallel-line serialization (Robin's election 2026-09-26): a `#track <name>
[zen|audible]` header line opens a REAL second token stream in the body
text. Everything before the first valid header stays the melody; the melody
stream never consumes a block.

- Grammar: `#track bass` (audible by default = plays wherever the melody
  plays, NORMAL practice included) / `#track bass zen` (the support-layer's
  Zen gating); a trailing percent sets the track's MIX level —
  `#track bass audible 50` (a numeric second field also works with the zone
  at its default: `#track bass 50`). The percent becomes the voice's master
  gain directly (audio.js `voiceGain`, one point in `playNoteAt`), so every
  layer of the voice scales with it; the note sink reports it as its sixth
  arg for tests. Header is line-anchored + case-insensitive; the same name
  appearing twice APPENDS into one stream (a bass written in two halves is
  one line); the newest zone word and volume win on the merged stream.
  Malformed headers (bad zone, non-numeric percent, 0 or >100) chip and
  change NO stream boundary.
- **The bar-alignment contract**: one melody bar = one track bar (bar count
  AND per-bar beat sums equal, mixed meters included). Every consumer stands
  on it: the two streams start together, pause/resume/loop/stop together,
  and a melody `# tempo` inside a stream moves the shared quarter from that
  point. tests/shipped_songs pins the contract for the whole shipped corpus.
- Track tokens use the FULL melody grammar (accidental spellings, ties via
  `~` slides and `-`, staccato…); track voices are the melody voice's own
  `playNoteAt` with NO chart range check — a groove may sit below the melody
  ocarina's carve, exactly like a support drone.
- Melody-stream syntax is out of place inside a block: support brackets
  (`[C2]`, `|[Ab2]`, `[-/2]`) CHIP there, never silently carry. Malformed
  headers chip and change NO stream boundary (their lines stay with
  whatever stream was open — no silent loss). Track junk chips in the token
  strips after a `#track <name>` pill (clean bodies render none).
- **Harmonizing over doubling** (field-check lesson, 2026-09-26): a support
  voice must never attack WHILE the melody sounds the same pitch — the
  doubled attack is what makes the two voices hard to tell apart. The repair
  pass is mechanical and repeatable: `python tools/track_harmonize.py`
  (stdlib, idempotent) walks absolute onsets (melody holds extend over `-`
  ties, cross-barline) and drops colliding tokens in convergence rounds —
  an octave down first ("the octave below the melody's other notes"), then
  a perfect FIFTH below when the octave would land on another melody note
  (the melody itself rides low octaves), then another octave. Durations are
  untouched, so the bar-grid contract holds by construction. Percentages are
  a mixing call (field values 2026-09-26: pizz 50 %, contrabass 75 %).
- Worked example: `outset-island-with-bass` — melody on top, then
  `#track bass audible 50` carrying the entire `outset-island-bassline`
  groove (its own triple-fitting register; colliding tokens harmonized by
  the pass above), the finale truncated to the melody's half-bar; and
  `#track contrabass audible 75` holding grounded per-bar roots. The
  `-up12` twin carries the same pair with the contrabass raised onto the
  real `ico-contrabass-11-c` chart (B2-F4) — the A/B pair Robin field-
  checks register by register.

## Player-facing formatting conventions (house target)

These are cosmetic today (the parser reads `|` wherever it stands; a body
with barlines at line end parses identically) — they exist so players read
sheets at a glance:

- **Barline starts the line.** When a body is wrapped across lines, the
  house target is `| A4/4 B4/4 C5/4 r/4` — the bar token OPENS the line,
  announcing the downbeat — not `... |\nA4/4` as most current bodies do.
  Standardization of shipped songs may happen in a later pass (see TODO).
- **Name long-form sections** with `| [Verse]` where players would want a
  header; keep labels short, singular and stable across a song.
- Keep bodies wrapped at musically sensible sentences: phrase-per-line
  beats machine-free column counting.

## Fit this instrument

| Chart | Instrument | Range |
|---|---|---|
| `fingerings.json` | ico-oak-leaf-bass-c-triple | A3–G6 (35 notes) |
| `fingerings.json` | dummy-bass-c-double | A3–C6 (28 notes) |
| `fingerings-alto.json` | stein-double-alto-c | A4–C7 (28 notes) |
| `fingerings-alto-12.json` | oot-alto-c-12 | A4–F6 (21 notes) |
| `fingerings.json` | ico-contrabass-11-c | B2–F4 (19 notes) |

- The double-C pair is exact: a song fitting the bass double (A3–C6) always
  fits the alto double at **+1 octave**, and −12 returns it — no window math
  for that pair.
- Choose the OCTAVE placement that **minimizes chamber jumps** (chamber data
  sits on each note in `fingerings.json`): Song of Storms in D minor plays
  D4–F5 rather than reaching D3. Natural-minor/dorian tunes that stay on
  white keys fit the C fingering with no accidentals.
- Songs with out-of-range notes for the current ocarina vanish from the
  dropdown (auto-hidden); the "Show hidden songs" toggle reveals them.
- **C major and chromatic are generated tools, not shipped entries**: the
  library synthesizes them for the LOADED chart on every instrument install
  (chromatic = the chart's ids in order, major = minus black keys) — they
  are never in songs.json and get no public landing pages.

## Song slugs — the frozen link contract (locked 2026-09-24)

Public URLs address a SONG: `/song/<category>/<base-slug>`. The base slug is
the song's permanent identity; arrangement copies live as suffixed sibling
keys and are never their own indexed pages.

- **URL default player: the 12-hole C alto** when a link gives only a song.
  Future ocarina families (single/double/triple/quadruple chamber counts,
  soprano, ...) extend the marker list — they never rename bases.
- **Category token** normalizes from the songs.json group family (today:
  zelda, scales, other — "Zelda on Bass"/"Zelda on Alto" both collapse to
  zelda). The category also keys per-category theming: zelda → the Hyrule
  look; other categories default to Plain or acquire their own in the future.
- Grammar: base slugs are lowercase-hyphen ASCII. Variant keys end in a
  REGISTERED suffix from the closed list — ocarina markers (`alto`, `12`,
  `contrabass`, future names) and interval markers (`c`, `upN`, `downN`).
  Every suffixed key must chain to an existing key once the suffix is
  stripped (variants hang off real bases; bases are forever). Content-shaping
  words (`short`, …) belong to the BASE slug, not the suffix list.
- Grace-period markers (Robin, 2026-09-24): bodies that fall below the
  12-hole floor take a **`-bass`** suffix and, when even the triple bass is
  too high, **`-contrabass`** — the suffix list gains them at the
  standardization pass (adding them now would orphan existing families
  mid-rename). First application: the leaf bass songs
  (`zelda-lullaby-bass`); family heads that already
  carry upper arrangements keep their names until the naming wave.
- **Landing pages boot the ladder across the FAMILY** (gen_song_pages):
  first fit through 12-hole > double alto C > triple bass C > contrabass;
  the member booted is the base slug when it fits, else the first variant
  that does — `/song/zelda/song-of-time/` boots `song-of-time-alto` on the
  12-hole, never the bass body with range marks.
- Enforced by `tests/shipped_songs.py` (fails CI on any violating key). The
  `-alt`/`-alto` spell split was fixed before first indexing (`major-alto`,
  `chromatic-alto`); nothing is indexed yet, so no alias table was needed.

## Transcription craft (the rules that survive edits)

1. Get **pitch sequence** from an ocarina/single-line source, and
   **durations + meter** from a source that marks them (e/q/h tabs, MIDI,
   user-confirmed text). Letter names alone are not enough.
2. Pick a meter and make **every bar sum to that meter** (3/4 → 3
   quarter-beats). Mixed meters ride per bar: a bar sums to ITS OWN length.
   **Odd meters are suspects first (Robin, 2026-09-26):** Outset Island's
   shipped 5/4 da-dum bar came from the reduced score's engraving of the
   full arrangement — its fifth beat was the arranger's own extra note,
   absent from the game's file, which ran pure 4/4; the transcription
   faithfully inherited a wrong meter and the whole mid-song alignment
   shifted one beat. When a source (score or MIDI) declares an irregular
   measure, cross-check it against the other arrangement's and Robin's,
   before shipping it. If the user pastes a finished body, use that text;
   do not "improve" other phrases while fixing one.
3. To hold a note across a bar, write `-` with the leftover duration
   (`E4/4 | -/2`). Do not repeat the note name — that is a new attack. When
   splitting a held note, **replace that one token**. Do not also keep the
   following note if that creates a third attack.
4. Endings: if Loop should hit the next downbeat cleanly, add a rest
   (`r/4`, `r/2`, `r/1`) so the cycle length is intentional. Loop always
   returns to the START of the song, even if playback began mid-tune.
5. Prefer the **ocarina melody**, not piano inner voices or bass.
6. User-confirmed notation wins over all sources.

## Check before finishing

- Every `|`-delimited bar sums to the meter (except a deliberate whole-note
  + whole-rest ending).
- Every note id exists in the target chart (out-of-range = quietly hidden
  entry — that is a trap, verify the dropdown actually lists it).
- No extra attacks beside a split long note; no bars lost their rests.
- Load in the app: triplets show the `³` glyph, duration glyphs match the
  source, section labels hover, support drones sound only in Zen.
- For scripts: `node skills/song-transposing/scripts/verify_song.cjs <key>
  <chart>` (0 unknown ids, fits chart, bad chips 0). Changing the notation
  grammar? Keep `tests/parse_edges.py` and `tests/shipped_songs.py` green.
