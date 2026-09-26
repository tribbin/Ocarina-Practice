---
name: song-transposing
description: Add songs to songs.json or transpose/respell tab between the repo's ocarinas (Triple Bass C, the double-C pair, alto 12-hole) with verified pitch work: feasible-transposition math, mechanical note rewriting that survives the parser (labels, octave carry, Cb/B# boundaries, s-form accents, support-bracket preservation), flat/sharp spelling conventions per sheet key signatures, and chart-range verification; use when asked to transpose a song, make an alto/bass version, correct sharps to flats, add a new song entry, or when songs.json bodies need edits that must keep notes-by-sound identical.
---

# Song transposing (songs.json ↔ ocarina charts)

## When to use
- "Transpose this song down/up", "make a double alto C version", "put in a new copy".
- Respelling sharps → flats (or the reverse) to match a sheet's key signatures.
- Adding new entries to `songs.json`; checking a body actually fits a chart.
- Any pitch-mechanical edit to a `body` where playback must stay identical.

## Where things live
- `songs.json` — library entries (2-space-indented JSON; `JSON.stringify(s, null, 2)` matches repo style). Entry anatomy:
  `{ key: { name, group, tempo, body } }` — optional `tick`, `swing`, `hidden` (all INHERITED by transposed copies: a clone of a WIP stays WIP). Transposer copies spread the source and override only name/group/body.
  Groups by instrument: "Zelda on Bass", "Zelda on Alto", "Scales", "Other".
  `body` has NO leading `# name`/`# tempo` lines (library adds headers; `tempo` property is the default). A mid-body `# tempo N` line IS kept when the song changes speed there.
- `js/parse.js` — the notation (a real ES module since the migration; the scripts load it by stripping exports and riding its windowed compat block):
  - Notes `C4 Eb4 F#4` and **s-forms `Cs4`** (≡ `C#4`, display-normalized to `#`), accidental before octave, duration `/2` half, `/4.` dotted, `/8t` triplet, `!` staccato, `r/4` rest, `-` tie/hold, `~` slide.
  - Bar `|` with hover label `|["text"]`; bar support `| [C2]` or `| ["Section", C2]`; inline support `[C2]` / `[C2/4.]` / `[-/2]` / `[~F2/4]` — all parsed as `bass`/bar tokens, played as instrument-pinned drones (Zen-only), and NOT melody.
  - Unparsable spans tokenize into visible `bad` chips (never silently vanish) — verify_song fails any body that carries one.
  - An inline `# tempo N` after music starts emits a tempo-change token (leading ones are the default, not tokenized).
- Charts (`instruments/<id>/fingerings*.json`) and the double-C pair invariant:
  - `ico-oak-leaf-bass-c-triple` `fingerings.json` — **A3–G6**, 35 notes.
  - `dummy-bass-c-double` — **A3–C6**, 28 notes; `stein-double-alto-c` `fingerings-alto.json` — **A4–C7**, 28 notes. The alto chart IS the bass-double chart shifted +12 (same width, same count): **a song that fits the bass double ALWAYS fits the alto double at +1 octave — no window math needed**, and the reverse downshift comes back clean. Pinned by tests/transpose_skill.py both directions.
  - `oot-alto-c-12` `fingerings-alto-12.json` — A4–F6 (21 notes); `ico-contrabass-11-c` — B2–F4 (19 notes).
- `js/library.js` — auto-files songs with out-of-range notes as hidden for the current ocarina (toggle "Show hidden songs"), so a wrongly transposed song vanishes from the dropdown.

## Note ids and spelling (looks like a detail, isn't)
- Chart note ids are SHARP-spelled: `Fs4`, `Gs4`, `As4`, `Cs5`; naturals plain (`F4`, `B5`). Transposer output re-spells into this system; flats and s-forms in the input come back as sharps.
- Writing flats works: parser maps `Bb4 → As4`, `Db5 → Cs5`, `Cb6 → B5` (flat letters adjust octave).
- **`E#5` is a trap**: it becomes id `Es5`, which no chart carries (F5 is spelled `Fs5`) → falsely reported out-of-range/unplayable. When a raised-6th wants `E#`, keep the enharmonic `F` instead.
- Spelling is purely cosmetic to the app; only sounding pitch matters. Match the user's convention: spell by the SHEET's key signature per section (their "sheet spelling" entries), and say so when you deviate.
- Read the BotW main theme case study in `songs.json` history: one song, four sheet key signatures (G# minor 5♯ → C major ♮ → Eb minor 6♭ → G minor 2♭) — the "same theme restated in shifting keys" structure. A tab that spells everything as sharps will LOOK like extra keys; analyze by pitch-class sets per section before claiming key changes.

## Transposition workflow
1. Find the melody's MIDI extremes (min/max over parsed notes). A transposition by S semitones is clean iff `min+S ≥ chartLow` and `max+S ≤ chartHigh` — all legal S form a contiguous window. Pick the value that best centers the register (usually shaving the painful top).
2. If the window is empty, a pure transpose is impossible: say which note breaks which end (e.g. C4→G#3 falls below A3), and offer either the max clean shift or a flagged compromise.
3. Cross-octave pairs need no window: bass double → alto double is always +12 (see charts above).
4. Case study (BotW main theme, span C4–Eb6 = 28 semitones): bass triple → **−3** (deepest clean: −4 pushes the C4 pickup to G#3 < A3), result A3–C6. Double alto C (A4–C7, exactly 28 wide) → **+9 is the only transposition that fits at all**, covering the chart's entire span with zero slack.
5. Use the scripts — they encode every trap below (repo root):
```
# preview (no write) — from repo root
node skills/song-transposing/scripts/transpose.cjs <srcKey> <shift> --dry
# create entry, verify against a chart, exit 1 on any mismatch
node skills/song-transposing/scripts/transpose.cjs <srcKey> <shift> [dstKey "Name" "Group" instruments/.../fingerings.json]
# verify any existing entry (resolvable ids + range + no bad chips)
node skills/song-transposing/scripts/verify_song.cjs <songKey> [fingerings.json]
```
On success: per-note exact-shift check (`every(src[i]+S === dst[i])` by MIDI), unknown-id check, in-chart check, printed MIDI range; on a bad-chip result the writer fails loudly (a transposed body must parse clean by construction).

## Semantics locked 2026-09-23 (Robin's calls)
- **Supports stay verbatim**: every `[...]` bracket (section labels, bar supports, inline supports, `[-/2]` extensions, `[~..]` glides) passes through a transposition untouched — supports are instrument-pinned chambers of the specific ocarina, melody only moves. The script masks bracket spans wholesale during the rewrite.
- **Track blocks transpose like the melody** (2026-09-26): `#track` header lines carry no pitches and pass verbatim; every note inside a block is unmasked plain text and moves with the shift — a bass line must stay under the melody's key. The parser oracle inside the scripts sees only the melody stream (`parse()` stops at the first valid header), so a typo'd track body is NOT caught by the transposer's bad-chip net — tests/shipped_songs owns that duty for the shipped corpus.
- **s-form notes transpose** as their sharp equivalent and re-spell into the sharp system; no manual pre-step.
- **Copies inherit everything** (tempo, tick, swing, hidden) and override name/group/body only.

## Traps (each one bit once; the scripts already avoid them)
- **Octave digit is a string**: `(o + 1)` concatenates — `"4"+1 → "41"`, giving MIDI ~500 and note names like `F40`. Always `parseInt(o, 10)` (fixed by construction).
- **Octave carry at letter boundaries**: compute MIDI as `(oct+1)*12 + PC[letter] + acc + shift` with NO chroma mod first. `Cb6` is MIDI 83 (B5) and `B#5` is MIDI 84 (C6). Re-spell from the final MIDI. (Pre-modding turned `Cb6 −3` into G#5 two octaves low.)
- **Brackets must be STASHED WHOLESALE, not sentinel-wrapped**: wrapping `\u0001` AROUND `[...]` leaves the content in-line, so the rewrite regex still reaches a pitch token inside (`C2` in `[C2/4.]` got shifted to `D2` once). Index-keyed stash + restore; dropping the closing `]` (twice, historical) made `|["Opening"]` → `|"Opening"` and label letters became phantom notes — the note-count-delta guard catches precisely this class.
- **The loader rides parse.js's own surface**, not eval internals: parse.js is an ES module (exports single- or multi-line — strip through the closing brace) that publishes its page-facing names via a windowed compat block (`window.parse = parse; ...`); the scripts shim `window` and read THROUGH the compat block (a `const parse` stays trapped in eval's lexical scope where a `function parse` leaks — the window layer catches both, and the guard fails loudly if the surface moves). The ES-modules migration (`57de8cb`) killed the old bare `eval()` loader this way; the suite caught it within one session.
- Exclude `#`-comment lines from rewriting (`/^\s*#/`), or inline `# tempo 104` lines get mangled.
- The transposer regex must NEVER see label/support text — masked first, always, even when labels look innocuous ("35th bar from midi" parses).
- Keep transposed copies' labels honest: strip stale key hints (`"(G minor)"` etc.) — keys shift under transposition. Master versions keep them.
- **PowerShell 5.1**: never pass multi-line JS to `node -e` inline (parser explodes on quotes/parentheses); write a temp `.cjs` file and run it. Server argv traps: `process.argv[1]` is the script itself.
- Verify with `songs.json` freshly re-read (users edit it between sessions — entries get renamed/removed: check keys exist before use).

## Verification checklist (run before reporting done)
1. `node skills/song-transposing/scripts/verify_song.cjs <key> <chart>` — 0 unknown ids, fits chart, sane note count, bad chips 0.
2. For transpositions: exact per-note MIDI delta (the transpose script prints it).
3. JSON.parse the final `songs.json`.
4. Sanity-read first/last body lines by eye (labels + supports intact, reasonable landing notes).
5. If respelling only (0 shift): same sounding pitches — parse both, compare id sequences.
6. Changing either side (script or parse.js surface)? `python tests/transpose_skill.py` pins the whole contract (skips cleanly where node is absent).
