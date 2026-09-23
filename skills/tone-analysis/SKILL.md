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


## Data locations
- Dataset: `research/analysis/alto-recordings-tone-data.json` (compact trend summary lives in `trends`).
- Raw reports + txt snapshots: `research/analysis/reports/<label>_report.json` / `<label>_txt.json`.
- Recordings: `research/` (`C5.wav`, `C5_2nd_recording.wav`, `D6.wav`, `G6.wav` + `.txt` snapshots).
- Mic gain identical across recordings → absolute dBFS differences between files are real breath-pressure differences (e.g. D6 plateau is ~+16 dB louder than C5).
- Player guidance: D6/G6/C5_2nd were recorded against a tuner (in tune ±1.5 cents); no intentional vibrato — model slow wobble as intrinsic.
