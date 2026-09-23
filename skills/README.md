# skills/

Purpose-specific capabilities that are known intent: each skill exists so a
future session (human or any AI agent) does not redo the specialized
research behind it. They are agent-neutral — nothing here is branded for a
particular tool (opencode, grok, claude...). A skill folder carries its own
SKILL.md (what it is for, how to run it, gotchas learned in real use) and
whatever scripts/data it needs.

Refine skills in place over future sessions; the file's history shows how
the understanding matured.

The skills live in Git so they follow the repo across machines (Linux
laptop, Windows partition, every clone).

## Index

- `midi-to-ocarina-tab/` — convert a `.mid` file into this tabber's
  songs.json notation (channel/instrument discovery, onset quantization
  with 16th + triplet support, meter/bar verification, A3–G6 range fitting).
  Stretches: pure-stdlib `scripts/mid2tab.py`. Feeds §9 F6 of
  `plans/TODO.md` (MIDI import baked into the app's Load-File path).
- `ocarina-melodies/` — the tab notation grammar, per-ocarina ranges and the
  songs.json entry shape; the companion context the midi skill (and any
  hand-transcription) leans on.
- `wav-sound-profile/` — (pending, hosted on the Windows partition) make a
  sound profile of a recorded WAV and iterate over synthesizer tunings very
  fast to approximate the recorded tone as closely as possible — the
  per-chamber `tone.json` fitting workflow for instruments.json. Copy it
  into this folder so it travels with the repo.
