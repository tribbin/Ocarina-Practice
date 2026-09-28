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

The online voice (js/helmholtz-voice.js) mirrors synth.py graph-for-graph
(the mid-air lead, 2026-09-28): sine osc → bandpass(f0, Q) = the cavity
tone; the RMS-normalized pink noise feeds bandpass(f0, effectiveNoiseQ)
[the residual halo ON the note], a MID AIR bandpass [mid_lo = 1.25 f0
(clamp 200–3500), mid_hi = 4 kHz] — THE E6/F6 AIR, split dry/synced by
`dryMidFrac` — and a high hiss highpass at 4 kHz kept QUIETER than the
mid, each band's gain RMS-matched against its tone-RMS row via
`pinkBandComp` (the JS stand-in for synth.py's post-filter RMS match —
change filters, change THAT helper, never add an EQ stage); bandpass(f0,
2.2) envelope = chiff; H2.. tiny dry oscillators. NO highshelf, NO
1.6 f0 / 2800 Hz cutoff — that air path was the bug (starved the mid,
cooked the top with fizz). **One air definition** — canonical bands live
in `ocarina_twin/air.py` (RES_LO/HI_RATIO, MID_LO_RATIO, MID_HI_HZ,
HISS_LO/HI_HZ); the JS duplicates them in `midLoHz`, `midHiHz`,
`dryMidFrac`, `effectiveNoiseQ`, `pinkBandComp`; change one, change both.
The standing air is the Grok LEAD handoff (2026-09-28, `research/
ocarina-twin-lead.zip`, HANDOFF.md inside) — it OVERRIDES the earlier
pipeline; models fitted before it (no `noise_mid_db`) play the JS
fallback `hiss + 8` until refit (a crutch, not a home). The fitter's NOM
table carries the double-chamber upper range (Fs6..Cs7) — the lead zip
trimmed it back to F6 and it was RESTORED for the stein's chamber 2 (a
missing key rebuilt the whole subtract on a 500 Hz default once); the
12-hole's rows are all inside the base table either way. A slipped
tracked subtract (residual reads ~sin level, "res -0.0") = exclude that
take from the fit; its WAV stays committed for later re-blows (stein
ch2's E6 — re-probed under the lead fitter 2026-09-28, still slips).

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
- GUESSED twins (`guessed: true`; installed 2026-09-28 on the dummy,
  contrabass and oak triple from `research/guessed-twins.zip`): Grok
  scaled the three bass instruments from the MEASURED 12-hole mid-air
  model — hand-chosen chambers that match each chart's own chamber marks
  (dummy ch1 A3-Ds5 + ch2 E5-C6; oak triple adds ch3 Cs6-G6; contrabass
  B2-F4 flat with `guessed` inside globals and its dry-mid split
  retuned to B2-F4; lowest V = lowest Q_prior 38, most halo, least hiss;
  harmonics weaker than the alto for the bass hoot). THEY ARE
  PLACEHOLDERS, not digital twins — Grok's do-nots: the 4 kHz hiss split
  is still the ALTO split (a real bass whoosh is lower); do not treat
  F6-on-the-alto mid numbers as gospel on a contrabass; do not mix all
  triple chambers into one notes[]. Refit from real held takes per
  chamber (triple: three short sessions, one chamber each, normal blow
  only) and throw the guesses away. Support/track voices ride them
  through the anchored TWIN_SUPPORT_LEVEL path like fitted twins do.
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
   noise_res_db = residual RMS in [0.70, 1.25]×f0 re H1, noise_mid_db =
   residual RMS in [1.25×f0, 4 kHz] (THE air), noise_hiss_db = residual
   RMS in [4 kHz, 12 kHz] — the SAME three bands the voice plays
   (air.py) — residual slope (dB/octave, 250–8000 Hz), per-note noise_Q
   from the open-hole count (floor 3.8), onset chiff multiplier + 10–90 %
   rise, overshoot, wander/wobble.
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
   compares recorded vs offline-synth air bands on the shared three-band
   cutoffs (res/mid/hiss columns); the mid-air handoff's acceptance: at
   F6 the synth's 1.5–2.8 kHz sub-band lands within ~3 dB of −32 (re
   tone), 5–8 kHz stays below −45, and C5 must not grow a 2 kHz shelf
   (its 1.5–2.8 kHz floor stays quieter than the take's — never
   brighter). Top-note mid/hiss rows generally measure ~5–9 dB hotter on
   the synth side than the take (Grok's delivery convention; F6/C5 are
   the acceptance rows, his ears decide the rest).
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
  The standing air is the Grok LEAD handoff (2026-09-28, research/
  ocarina-twin-lead.zip — the mid pedestal [1.25 f0, 4 kHz] + quiet high
  hiss [4 kHz, 12 kHz]; his zip overrides both earlier ones, and the
  pipeline handoff's 1.6×f0/highshelf air path is named THE BUG inside
  it) — adopted wholesale on Robin's standing "Grok leads" order, both
  instruments refit from the committed ladder takes, stage gate
  re-anchored (H4 cap) onto the adopted delivery. Before it: the second
  handoff (research/ocarina-twin-pipeline.zip: shared air.py + 1.6×f0
  hiss HP) — superseded; the earlier session's row rewrite was REJECTED
  by his ears (the A4 one-sine wobble class) and its history stays the
  cautionary tale. Numbers steer analysis; his ears rule.
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
