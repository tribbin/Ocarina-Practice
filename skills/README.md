# skills/

Purpose-specific capabilities that are known intent: each skill exists so a
future session (human or any AI agent) does not redo the specialized
research behind it. They are agent-neutral — nothing here is branded for a
particular tool (opencode, grok, claude...). A skill folder carries its own
SKILL.md (what it is for, how to run it, gotchas learned in real use) and
whatever scripts/data it needs.

Refine skills in place over future sessions; the file's history shows how
the understanding matured.

The skills live in Git so they follow the repo across every machine,
partition and clone.

## Index

- `midi-to-ocarina-tab/` — convert a `.mid` file into this tabber's
  songs.json notation (channel/instrument discovery, onset quantization
  with 16th + triplet support, meter/bar verification, A3–G6 range fitting).
  Stretches: pure-stdlib `scripts/mid2tab.py`. Feeds §9 F6 of
  `plans/TODO.md` (MIDI import baked into the app's Load-File path).
- `ocarina-melodies/` — the up-to-date truth for writing music in this
  tabber: the notation grammar and feature family (supports, sections,
  swing/tick/hidden, slide chains), per-chart fitting across all five
  ocarinas, the player-facing formatting conventions (barline-open-lines
  house target), and the transcription craft rules (bar balancing, the
  replace-that-one-token tie rule, loop rests). Companion to the midi skill.
- `tone-analysis/` — single-tone WAV measurement and synth-approximation
  workflow: envelope/pitch-stability/harmonic-timbre/noise/onset reports
  (self-calibrating scripts), recorder FFT-snapshot cross-checks, offline
  Chrome renders of the repo synth for comparison (with a reproduced-bug
  log in the SKILL.md), and the staged fastloop tuning loop against
  recorded reference takes — drives the per-chamber `tone.json` fitting
  for instruments.json. Feeds §1 B5 of `plans/TODO.md` (chamber tuning
  for every ocarina); the tone.json schema and recording protocol live in
  `instruments/README.md`.
- `song-transposing/` — verified pitch work on `songs.json` bodies:
  transpose/respell between the ocarina charts (incl. the bass-double →
  alto-double +12 pair invariant and the s-form/sharp respelling rules),
  with the double-C chart pair, support-bracket verbatim semantics and
  every learned rewriting trap encoded in `transpose.cjs`/`verify_song.cjs`
  and pinned by `tests/transpose_skill.py`.

`skills/` is the canonical committed home. `.opencode/skills/` holds
opencode's runtime-registered copies (gitignored) — when a skill changes
here, refresh its `.opencode/skills/` mirror so both stay word-identical.
