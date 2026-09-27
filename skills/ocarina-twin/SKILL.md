---
name: ocarina-twin
description: Fit and use the ocarina digital-twin voice (Helmholtz- cavity
  model, ocarina-twin-v2 schema) from held-note recordings; refit a chamber
  from new takes, render the offline reference synth for comparison, and
  understand the web voice this model drives. Use when re/fitting
  twin_model.json from held takes, when a chamber's voice needs replacing,
  or when analyzing the twin voice's deviations from recordings. Tone-
  spectrum plumbing (hold_spectrum, stage_spectra, the tone.json harmonic
  model) stays in the tone-analysis skill; this skill owns the subtractive
  twin path.
---

# Ocarina digital twins (Helmholtz cavity model)

## Physical picture (why this replaces the harmonic+noise model)

An ocarina is a fipple-driven Helmholtz resonator, not a pipe:
`f0 ≈ (c / 2π) · sqrt(A_eff / (V · L_eff))`. The body does NOT make
a harmonic series: after a *tracked* H1–H8 subtract (fit.py's
`subtract_tracked` — the tracker follows f0 through breath wander, so
the "residual" is real noise, not a mistuned fundamental), leftover
energy sits ON f0 at −26..−35 dB, plus a weaker hiss above ~2.8 kHz.
H2/H3 live at −25..−50 dB and must be mixed DRY — sending them
through the cavity bandpass deletes them. The faint partials come
from the jet, not from the body.

One chamber = one model. Interpolation is log-f INSIDE the chamber,
never across a chamber boundary (a second chamber is a different V).

## Files

```
skills/ocarina-twin/
  ocarina_twin/          the python package (fit.py fitter, synth.py
                         offline reference renderer, model.py dataclasses)
  run_fit.py             CLI: refit a chamber from held-note WAVs
instruments/<id>/twin_model.json   the fitted chamber (shipped data)
js/helmholtz-voice.js    the Web Audio voice audio.js drives with it
```

The online voice (js/helmholtz-voice.js) mirrors synth.py graph-for-graph:
sine osc → bandpass(f0, Q) = the cavity tone; the same noise, period-synced
by a gain driven through a waveshaper, feeds bandpass(f0, noise_Q) [the
residual bump ON the note] → highpass 2.8 kHz [hiss, bypasses the cavity]
→ bandpass(f0, 2.2) envelope = chiff; H2.. tiny dry oscillators.

## Refit a chamber (the whole loop)

1. One held take per fingering, silence at both ends is fine. Sustain
   window lands automatically (~110 ms after onset to ~100 ms before
   release). Do NOT fit note values from melody clips — held takes only.
2. ```
   .venv/bin/python3 skills/ocarina-twin/run_fit.py \
     research/note-recordings/<inst>/A4-held.wav ... \
     --instrument "..." --chamber 1 \
     --fingerings instruments/<id>/fingerings.json \
     -o instruments/<id>/twin_model.json
   ```
   The fitter measures per take: tracked-subtract harmonic ratios (h[0..5]
   linear re H1), Q from the tone's 3 dB width (clamped 18..80),
   noise_res_db = residual RMS in [0.65, 1.35]×f0 re H1, noise_hiss_db =
   residual RMS above 2.8 kHz, residual slope (dB/octave, 250–8000 Hz),
   onset chiff multiplier + 10–90 % rise, overshoot, wander/wobble.
   Levels normalize to the loudest take of the chamber (mic gain is a mic-
   chain artifact, never an instrument parameter).
3. Sanity peeks (fit_take exposes everything; the JSON is the contract):
   residual should sound like breath through the clay with NO singing
   sine left — a sine remaining means the tracker slipped.
4. `python -c "from ocarina_twin ..."` renders the reference WAVs:
   `render_note(model, f0, dur_s, hold_s=...)` — buffer length includes
   release (`hold_s` = musical length, `dur_s = hold_s + rel_s`).
   `render_model_scale` renders the whole ladder.

## The web voice plumbing (what audio.js does)

- The instrument manifest declares `"twin": "instruments/<id>/twin_model.json"`;
  app.js fetches it like tone.json (404 = no data yet) and calls
  `installTwinModel(obj, instId)` (in js/audio.js, exported on window).
- The installed model becomes the voice for EVERY note of that instrument
  (the additive voice in playNoteAt is bypassed for fitted instruments):
  `interpNote(model, f0)` log-f interpolates inside the chamber, clamped
  at the fitted range ends (unfitted top/bottom notes ride the edge rows —
  refit when recordings cover them).
- Envelope is absolute-time: atk_pre silence → atk_speak rise → sustain
  → rel_s after hold. Duration changes sustain length only. The note
  slot (durSec) CONTAINS the release: audio.js passes
  `hold = dur − rel_s`; a note flowing into a `~` slide passes
  `hold = dur + 0.04` so its 40 ms crossfade lands past the junction.
- Glide (`~`): the cavity osc's `frequency` ramps from slideFromHz over
  AUDIO_DEBUG.slideTapMs (the finger-tap). Zen vibrato/stereo chorus:
  the chorus is TWO scheduled voices — clean core panned −zenPan, the
  vibrato twin panned +zenPan (one vibrato LFO on the twin's f0).
- AUDIO_DEBUG knobs that still apply: masterLevel (scalar on the model's
  own relative levels), slideTapMs, vibRate/vibDepth/vibHighFade/vibDelay,
  wanderAmt/wobbleAmt (scale the model's wander/wobble rows at interp
  time), reverb/cut buses unchanged. The additive voice's knobs
  (h2Mul..windAmt, lp*, edge*, chiff*, ot*, air*, windPark/Warm/Rough)
  belong to the legacy voice only — inert where a twin model is installed.

## Known-open items (logged 2026-09-27)

- THE FIELD RULING (the skill's first law): the handoff's voice + model
  (js/helmholtz-voice.js with the handoff twin_model.json) is the ADOPTED
  baseline — Robin field-checked it and it stands. A follow-up pass
  algebraically rewrote the model's noise rows (a span fix for synthetic
  renders + a render-closing calibration) to make the rows numerically
  self-consistent with the renderers; his ears rejected it ("the wobble at
  A4 is very bad... some onset noise and shit back"), it was reverted, the
  model file and the module are the handoff state again (only the 4 s
  crossfaded noise buffer stayed — the line-comb lesson). Numbers steer
  analysis; HIS EARS decide the sound. Any future row rewrite waits on his
  field check wording, never closes numerically alone.
- The span fix itself STAYS in fit.py (peak·0.08: the old median*4 guard
  collapsed every span onto the 0.15/0.85 fallback — releases and silence
  fitted as sustain — for flat synthetic sustains AND for these quiet
  takes; a future refit measures honest spans). It re-fits differently
  than the shipped model does; that is fine — the shipped file is the
  adopted reference, not "the fit", and refits go through the field check.
- No amplitude-wobble layer in the web voice (the module interpolates
  wobble_pct and leaves it unused — the handoff's choice, field-blessed:
  synthetic loudness wobble read as bad pumping at A4; the liked wobble
  around E5 is the pitch wander). Do not "complete" it without Robin's ask.
- The shipped model clamps at A5: notes above ride A5's row — record the
  top register and refit.
- The ring-up: the render's attack rise measures ~0.08 s where the
  envelope rows say 8-26 ms (the cavity Q rings up from silence; the
  takes' rises are player breath + the same ring). A Q-ramp "assist" is a
  held idea — audible behavior, his ears first.
