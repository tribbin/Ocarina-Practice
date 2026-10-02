---
name: ocarina-twin
description: "Fit a chamber from a tone-ladder recording and its fingerings, write twin_model.json, and leave the partial body alone. Use when a new ladder arrives, a chamber needs refitting, or an instrument without a recording must be copied or extrapolated."
---

# Ocarina twin pipeline

One chamber, one ladder, one fit. The voice in `js/helmholtz-voice.js` reads the rows. Do not retune attack, release, chorus, or reverb while fitting.

## What the voice plays

Phase-locked partials (`h`, `h_phase`), a slope-colored floor (`floor_db`, `slope_db_oct`), a narrow halo on f0, a whoosh under 2 kHz, a 5–11 kHz hiss, and an air band above f0 (`air_db`, `air_lo_hz`, `air_hi_hz`). No cavity band-pass. Do not bring back the pre-v3k `ocarina_twin/` fitter.

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
- floor from the residual spectrum, shifted +28 dB. The −46 dB clamp is dropped on high 12-hole notes so a quiet residual is not lifted
- slope of the residual from 900 Hz to 5 kHz, clamped −12..−4
- air center at the loudest residual peak above f0, band about 700 Hz wide, always starting above f0
- whoosh under 2 kHz and hiss at 5–11 kHz from the residual, not one band under the note
- `atk_speak_s` from the 10–90% onset rise, log-f interpolated inside the chamber

Honk rule: if H3 is louder than half of H2, pull H3 down to that and H4 to a quarter of H2. A locked H3 as loud as H2 is the clean pipe (oak E5/F5).

Leave `rel_s` (0.08) and the `~` hold alone. Fit `atk_speak_s` from the rise. A bass blow gets a longer, quieter chiff; an alto blow does not get a louder one. Chiff stays off notes shorter than a blow.

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
