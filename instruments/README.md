Per-ocarina data, one folder per instrument
===========================================

Every ocarina lives in its own folder named exactly after the instrument's
`id` in the root `instruments.json` (the single manifest — type, version,
range and the file paths stay there). Folder contents:

    instruments/<id>/
      fingerings.json        fingering chart (notes, chambers, covered holes)
      ocarina-template.svg   the SVG body template (theme variants live here too)
      tone.json              OPTIONAL: fitted per-chamber tone anchors
      twin_model.json        OPTIONAL: fitted Helmholtz twin model

A note may list `half`: hole ids that are vented, not closed. The painter
draws a left half-disc (the songbook glyph) and does not treat them as
covered. A hole must not appear in both arrays. Older charts omit `half`.

`instruments.json` entries may carry `"tone": "instruments/<id>/tone.json"`
and `"twin": "instruments/<id>/twin_model.json"`.
A missing file is normal — that ocarina then keeps the baked-in generic model
(the alto-derived extrapolation in `js/audio.js`), and nobody notices. A
manifest entry may also declare the field ahead of its measurements (the
per-chamber tuning work is planned for every ocarina); until the file lands
the loader treats the 404 as "no data yet". If the file exists but is corrupt,
the loader also falls back — tone data must never break boot.

## Voice swap (twin vs additive)

`twin_model.json` switches the instrument's VOICE to the Helmholtz twin
(`js/helmholtz-voice.js`, rev `v4-breath`, python fitter + reference renderer
in `skills/ocarina-twin/`). The fitted tone path is unchanged: phase-locked
partials (`h`, `h_phase`) through the cavity, minute dry H2–H6 labium
partials, the slope-colored floor. The breath noise is now a layered engine,
not one static bed:

- the air band is a native band-pass on the shared slope-colored buffer
  (center `clamp(1.25·f0, air_lo_hz, air_hi_eff)`, Q 1.0);
- the band is comb-locked to f0 (delay 1/f0, feedback 0.35, wet 0.6 / dry
  0.4) and amplitude-modulated at f0 (depth ±0.5 around 1), so on-note
  breath peaks at f0, 2f0, 3f0…;
- a voicing-formant peaking filter (center/Q from the optional
  `air_formant_hz` / `air_formant_q` rows, +6 dB bump) colors the vent noise;
- open-hole venting scales the upper cutoff (`ratio^0.25`) and the air level
  (`ratio^0.5`), with a 0.15 floor so a fully closed note keeps its windway
  hiss;
- the blowing gesture rides the existing note timeline: an attack excess
  starts at `atk_noise_db` (default `air_db + 6`) and decays to the sustain
  `air_db` bed over `atk_speak_s`, the sustain gets a ±1.5 dB wander drift,
  and a +3 dB / 15 ms release puff lands just before the hold end;
- staccato (`!`) and re-attack-after-rest tokens get a scheduler-level
  ~10 ms tongued burst through the same formant filter, 15 ms before the
  body onset. There is no pre-phrase inhale. Practice's mic path never
  schedules this layer.

`?breath=0` (and the debug panel's session-only Breath switch) is the A/B:
it keeps the plain native band-pass at the same center and the legacy chiff
burst, with no comb/AM/formant/gesture/tongue layers. The additive
timbre/wind machinery in `js/audio.js` (PeriodicWave + windPark/warm/rough
shelves + edge whistle + chiff/ot bursts, `voiceProfileFor`, `V_ANCHORS`)
is the LEGACY voice: dormant while a twin model drives the instrument —
every ocarina currently declares `twin` (12-hole OoT, the ICO alto and
bass 12-holes, 6-hole, stein and the oak triple on fitted ladder models;
the dummy double rides the oak's recorded chamber 1/2 fits and the
contrabass is an octave-down extrapolation of the oak chamber 1 —
placeholders until real recordings land); removal is a later cleanup on Robin's word
(the additive path still backs the support red-green comparisons).
tone.json stays on disk only while the
additive voice still reads it: the 12-hole's was removed with its swap
(the fit history lives in git).

### Breath fields (optional, v4-breath)

Every row may carry these keys; a file from before v4 keeps working per-field
(defaults below). They live inside each chamber's `notes[]`, like every other
twin row, and interpolate in log-f only inside that chamber.

- `air_formant_hz` (Hz) — peaking-filter center for the measured vent-noise
  bump. Default `clamp(2.2·f0, air_lo_hz, air_hi_eff)`. It is the frequency
  center of the bump that tone-fit-v1's `noiseLoDb` band and `noiseBumpQ`
  describe (the fit's air/vent peak); a future re-fit maps the measured
  bump center here.
- `air_formant_q` (dimensionless) — peaking-filter Q. Default 1.0. Maps 1:1
  to tone-fit-v1 `noiseBumpQ` (the chamber bump sharpness).
- `atk_noise_db` (dB re the note's own `air_db` bed, not dBFS) — attack
  excess start level. Default `air_db + 6`. Maps to the tongued/blown onset
  excess a tone-fit-v1 `chiff` block describes (`chiff.peak` / `chiff.len`),
  while the decay length itself reuses `atk_speak_s`.

Engine constants that are not per-note schema keys (a fitter does not write
them): comb feedback 0.35, comb wet 0.6, AM depth 0.5, band Q 1.0, formant
bump +6 dB, sustain drift ±1.5 dB, release +3 dB / 15 ms, tongue burst
`air_db + 6` / 10 ms / 15 ms lead.

Vent scaling reads `instruments/<id>/fingerings.json`: a hole entry may
declare `area` (any consistent unit); absent areas fall back to counting
each hole as one unit. Half-vented holes count half. `openArea/refArea`
is clamped to a 0.15 floor (the windway's own vent), so `ratio = 1` is a
fully open chart and closed notes keep a quiet base hiss.

### The twin file shapes

Single-chamber schema ("ocarina-twin-v2" — the 12-hole):

    { "schema": "...", "notes": [...] }        // one chamber, all notes

Multi-chamber wrapper ("ocarina-twin-multi-v1" — a double/triple mid-fit;
each note's OWN chamber must carry a model — a chamber without one keeps
its notes on the additive voice, and chambers never lerp across V):

    { "schema": "ocarina-twin-multi-v1",
      "chambers": {
        "1": { "gain": 1.0,  "model": { "schema": "...", "chamber": "1", "notes": [...] } },
        "2": { "gain": 0.57, "model": { "schema": "...", "chamber": "2", "notes": [...] } }
      } }

`gain` carries the cross-chamber loudness (raw take level vs the whole
chain's loudest take): each chamber's internal `level` rows normalize to
that chamber's own peak, so the wrapper's gain is what keeps chamber 2
from sounding as loud as chamber 1 without any recording to say so.
A temp twin (3 notes measured, big gaps) interpolates across them and
CLAMPS outside — the temp whole-chamber rows hold through the unfitted
ranges until real held takes land.

Guessed twins carry `"guessed": true` (wrapper top-level, or inside
`globals` on the flat schema) and are PLACEHOLDERS scaled from another
instrument's measured model — not digital twins; the file-shape plumbing
reads them identically. Refit per chamber from real held takes when
recordings exist and discard them (the bass triple wants one short
session per chamber).

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
- levelDb rows are RELATIVE to each other (recorded absolute gain is a
  mic-chain artifact, never shipped). A fit anchors its own loudest recorded
  note at 0 dB and only the note-to-note curve ships — the app's masterLevel
  stays untouched so support tracks and reverb keep their headroom.
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
relative levels within the ocarina (levelDb rows are relative to each other,
anchored by the fit itself, never shipped against absolute mic gain) —
the melody-ladder workflow (skills/tone-analysis/SKILL.md) supersedes the
3-anchor protocol: one row per recorded note of the ladder, all of them.

The fit script itself lives with the recordings (analysis machine); the repo
receives only the finished tone.json in the ocarina's folder.
