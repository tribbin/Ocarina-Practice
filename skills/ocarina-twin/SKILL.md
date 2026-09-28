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
                         offline reference renderer, model.py dataclasses,
                         air.py THE SHARED AIR DEFINITION)
  run_fit.py             CLI: refit a chamber from held-note WAVs
  validate.py            rec-vs-offline-synth air-band check (same cutoffs)
instruments/<id>/twin_model.json   the fitted chamber (shipped data)
js/helmholtz-voice.js    the Web Audio voice audio.js drives with it
```

The online voice (js/helmholtz-voice.js) mirrors synth.py graph-for-graph:
sine osc → bandpass(f0, Q) = the cavity tone; the same noise, period-synced
by a gain driven through a waveshaper, feeds bandpass(f0, effectiveNoiseQ)
[the residual bump ON the note] → highpass **1.6×f0 clipped 700–3500 Hz**
[hole-rush, bypasses the cavity, split dry/synced by dry_hiss_frac and
shelved by the fitted slope] → bandpass(f0, 2.2) envelope = chiff; H2..
tiny dry oscillators. **One air definition** — canonical numbers live in
`ocarina_twin/air.py`; the JS duplicates them in `hissHpHz`, `dryHissFrac`,
`effectiveNoiseQ`, `slopeShelfDb`; change one, change both. The adopted
pipeline (2026-09-28) is the Grok handoff's (`research/
ocarina-twin-pipeline.zip`, HANDOFF.md inside); `fitted_noise_q` writes
already-open-hole-scaled rows and BOTH engines re-apply the open-hole
derate onto the row the same way — internally consistent, do not
"correct" one side alone. The fitter's NOM table carries the double-
chamber upper range (Fs6..Cs7) — a missing key rebuilt the whole subtract
on a 500 Hz default once; do not trim the table back. A slipped tracked
subtract (residual reads ~sin level, "res -0.0") = exclude that take from
the fit; its WAV stays committed for later re-blows (stein ch2's E6).

- multi-chamber wrapper ("ocarina-twin-multi-v1"): `chambers: {ch: {model,
  gain}}` — the web voice routes each NOTE by its chart chamber and a chamber
  without a model keeps that note on the additive voice (a temp twin can
  cover as much as the takes do). `gain` = the chamber's raw take level vs
  the chain's loudest take (each chamber's internal levels normalize to
  their own peak; the gain carries cross-chamber loudness). Chambers never
  lerp across V — the fitter is run once per chamber, never with mixed
  chambers.
- temp twins: too few rows mean whole-range clamps (the first stein twin:
  chamber 1 = C5+D6 rows, chamber 2 = G6's single row — retired 2026-09-28
  for its full ladder fit). Expected artifacts:
  interpolated rows drift across the wide gaps and every unfitted section
  rides its chamber's edge row. Field check steers; more takes fix it.
- cross-instrument relative volume: within an instrument, each chamber's
  `gain` carries its raw peak vs the instrument's loudest raw take; an
  instrument-level scale folds into every chamber gain so the instrument's
  max-volume sits against its anchor instrument (the 12-hole's ladder
  session anchored the stein, both recorded "similarly" so the land sits
  close — Robin records a dedicated one-take calibration for the true
  cross-instrument relative volume; never assume separate sessions are
  calibrated without that word).

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
   residual RMS above hiss_hp_ratio×f0 (clip 700–3500) — the SAME band the
   voice plays — residual slope (dB/octave, 250–8000 Hz), per-note
   noise_Q from the open-hole count (floor 4.5), onset chiff multiplier +
   10–90 % rise, overshoot, wander/wobble.
   Levels normalize to the loudest take of the chamber (mic gain is a mic-
   chain artifact, never an instrument parameter).
3. Sanity peeks (fit_take exposes everything; the JSON is the contract):
   residual should sound like breath through the clay with NO singing
   sine left — a sine remaining means the tracker slipped (the numeric
   tell: res_hiss_db ≈ 0 or res ≈ 0 re tone — exclude the take).
4. ```
   python skills/ocarina-twin/validate.py --model <model.json> \
     <C5-held.wav> <F6-held.wav>
   ```
   compares recorded vs offline-synth air bands on the shared cutoffs;
   dHiss within ~4 dB is the handoff's acceptance at the top, and C5 must
   stay QUIETER than the take in 1.5–2.8 kHz (never brighter).
5. `python -c "from ocarina_twin ..."` renders the reference WAVs:
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

## Known-open items (logged 2026-09-27; air pipeline adopted 2026-09-28)

- THE FIELD RULING (the skill's first law): Robin's ears decide the sound.
  The adopted AIR pipeline is the second Grok handoff (2026-09-28,
  research/ocarina-twin-pipeline.zip: shared air.py definition, per-note
  hiss HP at 1.6×f0, open-hole noise_Q, offline validate.py) — Robin's
  order was wholesale adoption ("Don't keep both — only keep the
  chorus/reverb and the rest use Grok's stuff"); the earlier session's row
  rewrite was REJECTED by his ears (the A4 one-sine wobble class) and its
  history stays the cautionary tale. Numbers steer analysis; his ears rule.
- The SPAN rule is Grok's (2026-09-28): thr = max(peak·0.08, median·4).
  The med·4 leg can collapse a span onto the 0.15/0.85 fallback when the
  take is sustain-heavy (release + silence fitted as sustain) AND a
  fallback slice that swallows the attack can slide the tracker into a
  wrong well on a wobbly take (stein ch2's E6: res −0.0, excluded — the
  tell is scipy-level: ftrack glued inside the refine band). Watched, not
  re-engineered — Robin's "don't keep both" order owns it; a take that
  fails this way is input curation, not a code fix.
- No amplitude-wobble layer in the web voice (the module interpolates
  wobble_pct and leaves it unused — the handoff's choice, field-blessed:
  synthetic loudness wobble read as bad pumping at A4; the liked wobble
  around E5 is the pitch wander). Do not "complete" it without Robin's ask.
- The shipped 12-hole model spans C5-F6 (2026-09-28 ladder retune; the
  placeholder 8-take fit A4-A5 it replaced was only installed to proof the
  synth). Notes below the fit's bottom end ride the edge row the same way a
  top-end note would (the 12-hole's A4/As4/B4 ride C5's row). Refit when
  recordings cover a wider span; end-clamped notes are the tell to listen
  for after a refit.
- The ring-up: the render's attack rise measures ~0.08 s where the
  envelope rows say 8-26 ms (the cavity Q rings up from silence; the
  takes' rises are player breath + the same ring). A Q-ramp "assist" is a
  held idea — audible behavior, his ears first.
