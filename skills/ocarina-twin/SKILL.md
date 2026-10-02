---
name: ocarina-twin
description: "Fit a chamber from a tone-ladder recording and its fingerings, write twin_model.json, and leave the v3k voice alone. Use when a new ladder arrives, a chamber needs refitting, or an instrument without a recording must be copied or extrapolated."
---

# Ocarina twin pipeline

One chamber, one ladder, one fit. The voice in `js/helmholtz-voice.js` reads the rows. Do not retune attack, release, chorus, or reverb while fitting.

## What the voice plays

Phase-locked partials (`h`, `h_phase`), a slope-colored floor (`floor_db`, `slope_db_oct`), and an air band levelled after the filter (`air_db`, `air_lo_hz`, `air_hi_hz`). No cavity band-pass and no halo. The old `noise_mid_db` / `noise_hiss_db` graph in `ocarina_twin/` is the pre-v3k fitter. Do not use it for a new ladder.

## Inputs

- A tone-ladder WAV for one chamber. Held notes, silence between them. Not a melody.
- `instruments/<id>/fingerings.json`. The `chamber` field on each note is the boundary. Never interpolate across it.

## Fit one chamber

```
python3 skills/ocarina-twin/fit_ladder.py \
  --ladder path/to/chamber-ladder.wav \
  --fingerings instruments/<id>/fingerings.json \
  --chamber 1 \
  --instrument "Name" \
  --out instruments/<id>/twin_model.json
```

Run it once per chamber. An existing multi-chamber file is updated in place; other chambers stay. The script cuts holds, measures each hold, and log-f interpolates onto that chamber's fingering notes only. Missing notes at either end clamp to the edge hold.

Measured per hold:

- H2/H3/H4 level and phase against the fundamental
- floor from the residual spectrum, shifted +28 dB into the voice's RMS range, clamped −62..−46
- slope of the residual from 900 Hz to 5 kHz, clamped −12..−4
- air center at the loudest residual peak, band from center−600 to center+900, and never below 1.4×f0

Honk rule: if H3 is louder than half of H2, pull H3 down to that and H4 to a quarter of H2. A locked H3 as loud as H2 is the clean pipe (oak E5/F5).

Envelope rows are the standing values (`atk_pre_s` 0.008, `atk_speak_s` 0.028, `rel_s` 0.08). Do not fit them from the ladder.

## After the write

- Twin JSON is fetched fresh. A voice change still needs a `sw.js` cache bump and the `helmholtz-voice.js?v=` query in `js/audio.js`.
- Listen to the chamber's ends and to any note where H3 was pulled. Anchors are listed in `recorded.anchors`.
- Do not render a comparison through the page reverb. The model is the dry voice.

## No recording

- Same range as a fitted chamber: copy that chamber's model and retitle it. The double bass chambers 1 and 2 are the oak triple chambers 1 and 2.
- Larger instrument, no take: extrapolate from the largest fitted chamber an octave down, weaken partials, drop the air band, add a little body. The contrabass is that, with floor and air lowered another 10–12 dB because it is a support track.

## Do not

- Fit from a melody clip.
- Mix chambers into one `notes[]`.
- Fill spectral gaps with a white-noise shelf.
- Phase-lock odd partials up to the fundamental to replace missing air.
- Change `playNoteAt` attack, the `~` hold (`dur + rel`), chorus, or reverb as part of a fit.
