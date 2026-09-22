Per-ocarina data, one folder per instrument
===========================================

Every ocarina lives in its own folder named exactly after the instrument's
`id` in the root `instruments.json` (the single manifest — type, version,
range and the file paths stay there). Folder contents:

    instruments/<id>/
      fingerings.json        fingering chart (notes, chambers, covered holes)
      ocarina-template.svg   the SVG body template (theme variants live here too)
      tone.json              OPTIONAL: fitted per-chamber tone anchors

`instruments.json` entries may carry `"tone": "instruments/<id>/tone.json"`.
A missing file is normal — that ocarina then keeps the baked-in generic model
(the alto-derived extrapolation in `js/audio.js`), and nobody notices. A
manifest entry may also declare the field ahead of its measurements (the
per-chamber tuning work is planned for every ocarina); until the file lands
the loader treats the 404 as "no data yet". If the file exists but is corrupt,
the loader also falls back — tone data must never break boot.

tone.json — schema v1 ("tone-fit-v1")
-------------------------------------
One row per RECORDED ANCHOR NOTE. Each chamber gets 3 anchors: near-low,
middle, near-top. The player interpolates every field in log-f between the
anchors within the chamber (slope-clamped extrapolation to the chamber's
edge notes), so recording more anchors later only needs another row.

    {
      "instrument": "ico-stein-double-alto-c",
      "model": "tone-fit-v1",
      "recorded": {"date": "…", "mic": "…", "takes": "…"},
      "global": {                          // optional shared macros
        "lpMult": 4.2, "lpQ": 0.7          // tone lowpass (cutoff = lpMult × f0)
      },
      "chambers": {
        "1": [
          {
            "note": "A4", "f": 440.0,      // the anchor's note and frequency
            "h": [1, 0.0047, 0.0076, 0.0008, 0.0015],
              // harmonics re H1 (H2..H5) — or expand to keys "h2".."h5"
            "levelDb": 0.0,                // plateau loudness (dB re C5 reference)
            "wanderC": 6.9,                // slow pitch wander (detrended std, cents)
            "wobPct": 5.5, "wobHz": 2.5,   // breath wobble depth (%) and dominant rate
            "noiseLoDb": -25.9,            // wind/breath band re H1 (dB)
            "noiseBumpQ": 9.0,             // chamber bump sharpness of that band
            "attackF": 1.0,                // onset attack stretch (re C5)
            "osDb": 0.8,                   // attack-window overshoot (dB)
            "chiff": {                     // tongued onset burst (optional!)
              "peak": 0.018,               //   burst level (linear)
              "len": 0.09,                 //   burst length (s)
              "startHz": 900, "endHz": 500,//   sweep color (onset → settle cutoff)
              "attack": 0.02               //   burst attack (s)
            },
            "ot": {                        // onset overtone bloom (optional!)
              "peak": 0.0014,              //   level (linear)
              "dur": 0.10,                 //   bloom duration (s)
              "noise": 0.35                //   noise fraction in the bloom
            },
            "edge": {                      // edge/windway whistle (optional!)
              "level": 0.0008,             //   level — may vary per anchor row
              "detune": 0.012,             //   sharp-of-f0 comb ratio
              "spread": 0.008              //   detune instability spread
            }
          },
          …   // middle anchor — same shape
          …   // near-top anchor — same shape
        ]
      }
    }

Field notes:

- Every field stands alone. If the fit couldn't decide a value (or a whole
  sub-object), drop it — the loader keeps that one piece of the generic
  model, per field, per chamber. No all-or-nothing.
- Envelope constants that came out chamber-level (not per note) are simply
  repeated identically across the chamber's 3 rows.
- "chifff"/"ot"/"edge" replace the generic size/open-hole heuristics and the
  chamber-"registry" growth for that chamber; the fitted level already IS
  the chamber's character, no scaling is re-applied by chamber position.
- Keep numbers in the units shown; the loader does no conversions.
- Aliases: a fit script may emit `"h": [...]` (whole vector) or `"h2"..`
  keys — both accepted.

Recording protocol (per ocarina, per chamber)
---------------------------------------------
3 notes per chamber: near-lowest, middle, near-top. One steady tone each
(long enough for the fit, ideally 2+ s). Keep the mic/signal chain constant
across all notes of an ocarina, note the distance; the fit normalizes
relative levels within the ocarina (levelDb rows are relative to each other
and to the shared C5 reference).

The fit script itself lives with the recordings (analysis machine); the repo
receives only the finished tone.json in the ocarina's folder.
