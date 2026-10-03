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
(`js/helmholtz-voice.js`, python fitter + reference renderer in
`skills/ocarina-twin/`): near-sine fundamental through the cavity bandpass,
period-synchronous turbulence for the on-the-note breath, the air as a
mid pedestal bandpassed [1.25 f0, 4 kHz] with a QUIETER high hiss above
4 kHz (no highshelf, no 1.6 f0 cutoff — that path was the bug the mid-air
handoff replaced), minute dry H2–H6 labium partials. The additive
timbre/wind machinery in `js/audio.js` (PeriodicWave + windPark/warm/rough
shelves + edge whistle + chiff/ot bursts, `voiceProfileFor`, `V_ANCHORS`)
is the LEGACY voice: dormant while a twin model drives the instrument —
every ocarina currently declares `twin` (steins and 12-hole on fitted
ladder models, the three bass instruments on Grok's GUESSED ones —
`guessed: true`, scaled from the measured 12-hole, placeholders until
real held-take refits land); removal is a later cleanup on Robin's word
(the additive path still backs the support red-green comparisons).
tone.json stays on disk only while the
additive voice still reads it: the 12-hole's was removed with its swap
(the fit history lives in git).

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
