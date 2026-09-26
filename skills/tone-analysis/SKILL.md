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

## Data locations
- 12-hole fit working tree: `research/analysis/12hole/` (segments, cuts,
  targets, candidate + draft tone.json, fit renders) — gitignored, the repo
  receives only the finished `instruments/<id>/tone.json`.
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
