---
name: tone-analysis
description: Analyze single-tone WAV recordings (ocarina, fipple flutes) for envelope, pitch stability, harmonic timbre, noise bands and onset behavior, cross-check recorder FFT txt snapshots, and render the repo synth offline for comparison; use when asked to analyse/compare C5.wav/D6.txt/G6.txt-style recordings, "sound characteristics", tone_report, or when re-running the alto-recordings dataset (research/analysis/alto-recordings-tone-data.json). Use ONLY for tone-recording analysis and synth-vs-recording comparison work in this project.
---

# Tone analysis (recordings vs synth)

## When to use
- The user records single notes (e.g. `research/C5.wav`, `research/D6.wav`, `research/G6.wav`, `research/C5_2nd_recording.wav`) and wants measurable characteristics or a comparison against our synth voice (`js/audio.js`).
- The implementation round needs the stored reference data (see `research/analysis/alto-recordings-tone-data.json`).
- New recordings were added: run the pipeline, update the dataset, extend trends.

## Prerequisites
- Python 3 with `numpy` (`python -m pip install numpy`). No scipy needed.
- The fit loop's render half runs the repo's venv (`.venv/bin/python3`):
  it needs numpy + playwright (`.venv/bin/pip install numpy` if a fresh venv
  lacks it — playwright already rides the suite bootstrap).

## Pipeline

### 1. Per-note WAV analysis → `scripts/tone_report.py`
```
python .opencode/skills/tone-analysis/scripts/tone_report.py <wav> --nominal C5 --label C5 --json <label>_report.json
```
Measures (all calibrated via built-in sine/white-noise self-tests):
- **pitch**: median f0, cents vs equal temperament, attack glide (sharp↔flat), plateau drift, detrended wobble (std/pp cents)
- **envelope**: sounding span, attack-to-plateau ms, attack-window overshoot, plateau level (dBFS) + spread, breath wobble (std %, dominant Hz, depth %)
- **timbre**: harmonic ratios H2..H8 re H1 (median + p10/p90), per-third evolution (early/mid/late), H1 absolute level
- **noise**: white-noise-equivalent amplitude in relative bands (0.85-1.95×f0, 1.95-3.9×f0, 3.9-7×f0, 7-12×f0) + evolution + residual spectral centroid
- **inharmonic islands**: stability-filtered side tones (e.g. D6's faint 1.032×f0 at −40 dB; C5/G6: none)
- **onset**: 23-25 ms portrait of f0/H1/H2/H3 + broadband burst profile (harmonics notched)

Key numbers are medians over plateau frames (attack first 220 ms and release tail excluded).

### 2. Static FFT snapshot cross-check → `scripts/txt_spectrum.py`
```
python .../txt_spectrum.py C5.txt --nominal C5 --json C5_txt.json
```
Reads recorder txt exports (2048-pt FFT @44.1 kHz, 21.53 Hz bins). Harmonic ratios must match the WAV-derived medians within ~5–15%; if not, the snapshot was taken during the attack or a wobble extreme (happened with C5_2nd_recording.txt) — trust the WAV time-average.

### 3. Comparison table → `scripts/summarize.py`
```
python .../summarize.py C5 C5_2nd D6 G6 --dir path/to/reports
```

### 4. Dataset consolidation → `scripts/build_dataset.py`
```
python .../build_dataset.py [--dir report_dir]
```
Writes `research/analysis/alto-recordings-tone-data.json` (measured per-note data, pitch-trend fits over the tuner trio, current-synth constants for delta bookkeeping, low-register extrapolation assumptions). New recordings: add an entry to `NOTES` in this script, rerun the pipeline, commit the dataset + reports.

### 5. Synth-side comparison (offline render) → `scripts/render_ours.py` (+ `rt_capture.html`, `handvoice.html`)
Renders `js/audio.js` voices in headless Chrome (`--headless=old --dump-dom`, `OfflineAudioContext`), emits WAV via base64 in the DOM, then runs the identical `tone_report.py` on our render. Requires two local HTTP servers: repo root on :8137 (script src) and the page dir on :8138.

## Headless-Chrome offline-audio bug log (all reproduced on this machine, Chrome stable, 2026-09)
Workarounds are ALREADY built into `scripts/render_ours.py` — keep them on any reimplementation:
1. **Convolver**: always-connected reverb convolver makes offline rendering never finish → outGain-only replacement for `getReverbBus` (default reverb is OFF in the app anyway, dry chain is identical).
2. **DynamicsCompressor + tremolo passthrough gain** hangs `startRendering()` deterministically → drop the compressor from the render bus (it rarely engages at app levels; document the deviation).
3. **air + edge + (any third layer)** (osc #2, #4, #5 of a voice) hangs → mute via stub oscillators (see `muteAirEdge` in the template; stubs kill node creation, params alone do not).
4. All three combine in one voice (playNoteAt full voice) — without the stubs even `C5` may render or hang depending on machine state; state degrades after many runs (kill stray chrome processes between batches).
5. `--mute-audio` also broke a previously-working page once — avoid the flag here.
6. Use a fresh `--user-data-dir` per page, one page per run, and a ~1.5 s gap between runs.
7. If offline keeps failing, `scripts/rt_capture.html` is the fallback: real-time AudioContext + ScriptProcessorNode capture (connect the bus out INTO the tap node), needs `--autoplay-policy=no-user-gesture-required`.
8. `scripts/handvoice.html` is the graph bisection probe (URL `#drop=air,edge,chiff,ot` toggles layers) — the tool that found 1–3.

## Measurement conventions and traps (learned the hard way)
- **The skirt trap (2026-09-26, Robin's field catch made it real): the
  notch-band noise metrics read the LOUD FUNDAMENTAL'S WINDOW SKIRT, not
  breath.** A per-frame Hann window's side lobes land right inside the
  band bounds, so "band-1 noise" measured −14..−26 dB rel H1 while the
  recording's true inter-harmonic floor is −65..−95 dB rel H1 (verified
  against the recorder's own held-part spectrum export,
  research/analysis/12hole/F6_spectrum.txt, and with a Blackman-Harris
  long window on the same cut — both agree on ~−67..−92 class floors).
  Consequences: every wind level fitted against the old band numbers is
  ~40+ dB too hot; the fit's TRUE noise targets come from the inter-
  harmonic floor method (BH window or the recorder's FFT export, wide
  harmonic exclusion, ENBW-consistent scaling), never from the notch
  bands. Harmonic RATIOS by the old per-frame pipeline remain valid
  (±few dB vs the BH read).
- **Short windows with hardly any drift** measure the instant truth
  (Robin): drifting holds smear a long FFT, diluting H1 and apparently
  shrinking the harmonic ratios — compare like windows, or better, take
  the mean-f0 grid and a short stable window. The recorder's held-part
  FFT export is the ground truth for a note's TIMBRE + noise floor.
- Noise-band scales: per-bin DFT rms = σ×√(0.375·WIN) for a Hann window; forgetting the √(WIN) factor inflates noise by ~30-68 dB. The script self-calibrates — keep it that way.
- Parabolic interpolation for frequencies/amplitudes: use dB domain for both; compare floats with tolerance (Float32Array literal amplitudes are not exact decimals).
- Notch ±5-8 bins around integer harmonics and keep ≥30 Hz clear for inharmonic islands, else you measure window skirts (they masquerade as side tones).
- Stability-filter any "inharmonic tone" claim: track per-frame and require the same frequency across ≥55% of frames.
- Attack overshoot must be measured in the first ~200 ms window (whole-note max catches slow wander).
- Mono-sum both channels; this recorder outputs identical L/R.
- Blow variance spans: H2/H3 ±3 dB take-to-take, attack overshoot 0.5→4.8 dB, onset pitch glide −20..+25 cents (direction is style-, not pitch-dependent), pitch wobble std 7-8¢ (low notes) vs 1.1-1.3¢ (high notes). Don't over-fit single takes.
- **Band-1 metric is blind to narrow side-tones**: the noise-band measurement notches ±5-8 bins around every harmonic (±43 Hz at f0), so a narrow tone at 1.01-1.02×f0 never shows in band-1. Never tune a sustained narrow tone with band metrics — check it with the island detector or analytically. (Lesson from wiring the edge whistle to band-1: the loop drove it +2 dB above the fundamental.)
- **Blow-dependent listening**: the recorded chiff is a ~60-80 ms broadband swipe, nearly inaudible (user-confirmed); our chamber-derived chiff is ~0.34 s narrowband, so at equal band-RMS it screams. Perceptual derating beat the band-metric match (chiffScale 0.4→0.25).
- **Chrome-offline omits the octave onset**: in offline renders the onset octave-overblown layer never audibly fired (setValueAtTime/linearRamp at t0=0 quirk), while the numpy replica includes it — onset-domain comparisons between replica and Chrome-offline will diverge by design; the user's runtime / debug-panel WAV export arbitrates.

## Fast tuning loop (no code changes)
`scripts/synth_replica.py` is a numpy replica of `js/audio.js`'s dry-path voice (same OCA_DEBUG parameters, articulation from fingerings.json) — ~0.3 s per render, no browser. Passes:
1. Calibrate the replica against a real Chrome-rendered WAV if one exists (steady state matched within ±1-3 dB, onset diverges per the offline-omits-octave note above).
2. `scripts/fastloop2.py` stages the tuning (pure tone → chiff → edge → octave onset → master); `scripts/fastloop3.py` applies recording-consistent overrides. Staged, decoupled corrections only — see the band-1 trap.
3. `scripts/tuned_params.json` holds the resulting OCA_DEBUG values; `research/analysis/alto-recordings-tone-data.json` records `first_pass_tweaks_C5` (achieved deltas + open gaps).
This avoids Chrome entirely; the debug panel's "⤓ Export WAV" button (js/debug.js) is the in-browser audit path: press it, play one note, the WAV downloads, then measure with `tone_report.py`.


## 12-hole melody recording → per-note fit (the loop that landed the first tone.json)
`oot-alto-c-12`'s `tone.json` was fit 2026-09-26 from Robin's MELODY recordings
(skills/tone-analysis/reference-recordings/12hole/, also the working copies under
`research/note-recordings/12hole/`):
1. `scripts/melody_cut.py <wav> [--label L]` segments a melody mid-silence to
   mid-silence (span-adaptive thresholds, stateful scan; cuts keep the full
   attack, the release and a symmetric slice of room noise) and runs each cut
   through `tone_report.analyze` with SCALABLE plateau margins (short notes
   survive). Segments land in `research/analysis/12hole/<label>_segments.json`
   + per-cut WAVs. Attribution = autocorr f0 → nearest chart note id (recorded
   cents ride along; the ladder plays ±50 cents off ET sometimes — expected).
2. Data policy (Robin): the C-major tone LADDER is the only single-note-grade
   source; kokiri/storms contain transients, glides and multi-note spans —
   they stay in the dataset as transition/glide CONTEXT (the engine's glide is
   as short as a finger-tap on the real ocarina), never as row sources.
   Notes the ladder doesn't cover stay unfitted (the loader interpolates).
3. `scripts/fit_tone.py targets` aggregates the best LADDER take per note
   (longest steady span wins); `fit` renders candidate rows through the bench
   and iterates algebraic corrections (harmonics proportional ±8 dB/round,
   level relative-to-anchor ±8, wind band-1 shift, wander/wob/attack loops);
   `publish` copies the converged draft into `instruments/<id>/tone.json`.
   Level convention (Robin): the recording gain is a mic-chain artifact —
   levelDb anchors the loudest fitted note at 0 dB and ONLY the note-to-note
   curve ships; masterLevel stays untouched (headroom for support tracks +
   reverb). Converged r3: harmonics ±2 dB, levels ±0.3 dB, band-1 ±0.7 dB;
   known residuals: deeper noise-band shape (b2/b3, the wind chain's own
   LP/bump constants) and wobble-depth delivery (rows carry the measured
   medians; the engine's slow-LFO implementation reads shallower).
4. `scripts/render_ours.py` rebuilt for the module-era audio.js: it serves a
   PATCHED copy (imports re-pointed absolute, module-local freqOf override via
   `window.__F0`, getReverbBus/getLiteBus swapped for dry outGain, air/edge/
   wander oscillators stubbed at their CALL SITES — not by osc creation order)
   and imports it through an import map (the whole library graph imports
   `./audio.js`, so the map redirects every importer to the one patched
   instance; `Object.defineProperty(window, 'audioCtx')` would throw on a
   second evaluation). Driven by Playwright in real time — `--virtual-time-
   budget` + dump-dom never resolves `startRendering()` on this chrome, even
   for a bare oscillator. One fresh context per render; ports 8137 (repo) /
   8138 (bench pages), CORS=* so cross-port module imports work.

## Transition/glide dataset (the melodies' second material)
`scripts/glide_span.py <wav> [--label L]` tracks plateaus (f0-stable runs,
tol 35 cents, ≥70 ms) and measures every plateau-to-plateau jump: duration,
cents span, the envelope dip mid-jump, where the f0 crosses halfway and the
raw cents path per 10 ms hop. First findings (both committed WAVs):
- storms (glide-joined): adjacent-step jumps 20-60 ms with NO dip (0.2-0.5 dB
  — the tone carries through the finger transfer); the chamber-switching
  F5→D6 leap 20-40 ms with a shallow dip; the octave drop 200 ms with a
  -14.5 dB dip (a real breath change).
- kokiri (tongued at tempo): joints 10-90 ms, dips −6..+7 dB (several show a
  SWELL mid-jump, the plateaus are what's quiet there).
- the ENGINE's own sequence (render_ours.py --seq "D5:0.35,F5:0.35,D6:0.35",
  measured through the same glide_span): transitions 20 ms, dips −4.2..−6.0 dB
  — the timing is already finger-tap territory, the carry is what's missing
  (each note restarts its master envelope; the real tone keeps its level).
  Held for Robin's field check; note the practice-mode dip gate EXPECTS
  tunable dips, so a carry option must live behindZen/melody semantics,
  not two note-envelopes knitting silently under practice's feet.

## Held-tone spectrum (the ground-truth maker)
`scripts/hold_spectrum.py <wav> [--nominal C5] [--span ON,OFF]` finds the longest stable
hold inside a recording, windows it with a Blackman-Harris envelope and
writes the recorder-format spectrum (`Frequency (Hz) \t Level (dB)`, the
exact shape of Robin's own F6 export) plus a `_hold.json` summary (harmonic
spikes rel H1, corrected inter-harmonic band floors). `--span` forces the
window in file-seconds — for cuts whose plateau tracker misses (B4/D6-class
wobbly holds); pass targets.json's on/off MINUS cutStart for the cut-relative
window. When two measurements disagree about a note's timbre or noise, THE
HELD-PART SPECTRUM WINS (Robin's own export is the reference; the fit's floor
method matches it within a few dB on the F6).

## Held-spectrum comparison at scale (`scripts/spectra_compare.py`)
```
python spectra_compare.py truth:B4:/abs/cut.wav:0.06,1.1 v36:B4:/abs/ours.wav ...
```
Measures every pair through hold_spectrum (one method both sides — required,
see the convention note) and prints truth-vs-ours rows + per-band deltas to
spectra_compare.json. Groups come from the label; rows without a truth
partner (extrapolation probes) print bare.
- **Tool-convention lesson (2026-09-27): the floor numbers are NOT
  comparable across methods.** hold_spectrum (long BH window, per-bin
  medians + ENBW correction), tone_report's floor_bands and the recorder's
  own FFT export disagree on ABSOLUTE band floors by 2-4 dB for the same
  WAV (bin-width/ENBW conventions). The FIT therefore converges b1 against
  tone_report's scale (targets) and stays self-consistent; acceptance vs
  the RECORDING must use one tool for both sides, and F6's export stays the
  cross-tool arbiter (delivered F6 −67.4 vs export −67, 2026-09-27).
- Per-band SHAPE deltas (band−band relations inside one tool) remain valid
  across the tool fence.

## Stage verification (the DEFAULT gate after synth or note-value changes)
`tests/tone_stages.py` (CI-registered) and `scripts/stage_spectra.py` are the
2026-09-27 doctrine: every synth-code or note-value change is verified
WAV-vs-WAV per STAGE — onset (~0.12 s), hold (plateau), decay — against the
HELD-NOTE takes (the cleanest recordings; they ride the committed reference
set skills/tone-analysis/reference-recordings/12hole, other notes
interpolate/extrapolate their classes). Plateau windows alone never caught
the white-wash-onset class (Robin: "lots of white noise, sustain but much
much more during the onset" — the bleed path was feeding RAW highpassed
white while every other noise path is chamber-shaped; the fix was a second
chamber-colored lobe, not a hidden-path hunt). Broadband + absolute-band
caps carry a declared known-open allowlist cleared wholesale as the row
family lands; wobble-window luck pairs declare per note-stage instead of
flapping green->red between runs.

## Wind-shape search through real renders
`render_ours.py ... --wind bpQ,lpRatio,lpQ` re-targets the engine's
WIND_SHAPE constants in the patched module — candidates MUST be verified by
rendering (the delivered WebAudio chain deviates from the analytic RBJ |H|
model by 3-6 dB per band at the 2-biquad level, and the deviation
magnitudes drift per candidate; the 2026-09-27 mid-wall pick
(0.6/2.6/0.8) came from a rendered candidate matrix, not the grid search).
The shipped wind buffer is 4 s (the 0.5 s loop was a 2 Hz-spaced line comb:
every "noise" line in the renders sat at k×2 Hz and the texture was
audibly wrong). Beyond the fitted anchors the fitted model HOLDS the
nearest row (`vInterpHold`) — extrapolating the clamped slope below B4's
bridge row turned A3/B3 wobble negative (−13% depth at 21 Hz, Robin's
field catch).

## Absolute noise-body layer (the 2026-09-27 rebuild unit)
The complaint spectra (Robin's IDEAS note + complaint/C5_hold_spectrum_*.txt)
proved the recorded held-noise BODY is not a broadband wash: it carries a
warm FIXED-absolute pocket bump at ~273 Hz below the tone (in every
recording), a broad warm shelf 330-650, deep holes BETWEEN the harmonics
(~700-1000 + 1500-1900 for C5 — "very big holes", not band-scale roughness)
and a rough upper bed surviving to 12 kHz (our old lp walls flattened it).
Three structural means now exist on the fitted voice (audio.js WIND_ABS +
tone.json's global gate):
- **park** (fixed-absolute peaking 273 Hz Q2.2, magnitudes in
  global.windPark) — its STRENGTH is per-note (`parkDb` rows) — measured
  span −13..+13 dB across the eight held takes (F5 nearly silent, A4 the
  loudest): the fixed-absolute bump rides per-note CAVITY COUPLING, so
  neither a chamber constant nor set gain scaling expresses it.
- **warm** (peaking 470 Q0.8) + **rough** (parallel BLEED past the per-note
  lp wall: highpass 2900 Q1.1 → shelves 6000/−10 + 9500/−7 → bleed gain;
  the series lp alone cannot carve the holes AND keep the rough tail).
Unfitted voices stay byte-identical (the layer keys gate it off).
- **abs_shape.py** measures the body: median levels per ABSOLUTE band
  (pocket 200-330, warm 330-650, hole1/H2zone/hole2, rough2/3, tail,
  airhead) rel to the hand-window's H1 envelope max, harmonics ±80 Hz
  excluded — the txt files of BOTH sides feed the same table (acceptance =
  full body agreement, not a few band medians). A 0.74 s window on wobbly
  holds carries ±3-5 dB take noise — don't chase single-band ±2 residuals
  across notes; the shape families and 8-note averages are the target.
- The layer rerenders every measurement's context: after a layer change the
  wind rows re-fit (fit_tone injects the global layer into all candidates).

## Data locations
- 12-hole fit working tree: `research/analysis/12hole/` — organized into
  per-batch subfolders (truth/, v36/, v37/, v38/, held/, shape_candidates/,
  isolation/, ladder/, early/, measures/ + fit/ with its per-round render
  tree) with the live state at top level (targets.json, segments, segments, candidate/draft tone.json,
  F6_spectrum.txt the arbiter, complaint/); targets.json paths are top-level
  in the scripts. Gitignored, the repo receives only the finished
  `instruments/<id>/tone.json`.
- Melody recordings: `research/note-recordings/12hole/` (gitignored working
  copies) and the committed set under `reference-recordings/12hole/`.
- Alto single-note pipeline (older): dataset
  `research/analysis/alto-recordings-tone-data.json` (compact trend summary in
  `trends`), raw reports + txt snapshots under `research/analysis/reports/`,
  recordings `research/` (`C5.wav`, `C5_2nd_recording.wav`, `D6.wav`,
  `G6.wav` + `.txt` snapshots) — may live only on the recording machine.
- Mic gain identical across recordings → absolute dBFS differences between
  files are real breath-pressure differences (e.g. D6 plateau ~+16 dB over C5);
  BUT the recordings' gain itself is a mic artifact — the shipped synth copies
  only the relative note curve (Robin, 2026-09-26).
- Player guidance: D6/G6/C5_2nd were recorded against a tuner (±1.5 cents); no
  intentional vibrato — model slow wobble as intrinsic.
