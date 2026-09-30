# Ocarina Practice — DONE (completed-work archive)

Built 2026-09-24 by renaming the old TODO.md here at the moment of the split
(Robin: keep TODO.md fresh "as it says on the tin") — the only bytes changed
were this heading and this preamble. What the file holds: every completed item
with its strike-through and ✅ date + SHA markers, the whole session log
through session 9, and the working conventions as they stood. plans/IDEAS.txt
stays Robin's untouched scratchpad.

From here on:
- A completed item MOVES into this file at the same bookkeeping moment it
  completes (strike-in-place in TODO.md is retired). TODO.md carries no struck
  corpses; open work lives only there.
- The `- [ ]` entries below that were still open at snapshot time are FROZEN
  copies kept for context — TODO.md remains the authoritative board for
  anything not struck here.
- Session-log entries below run through session 9. New sessions append to
  TODO.md's own log; entries retire here once the next session has opened
  from them.
- Struck hot-list rows were navigational echoes of the items here; they are
  preserved below exactly as they stood. Declined items (e.g. §9 F2 section
  looping) are archived WITH their revival notes.

Working doc for tracking improvements between AI sessions, committed under
`plans/` so it follows the repo across every machine, partition and clone. It carries
working notes, not shipped documentation. The idle
idea pool lives beside it in `plans/IDEAS.txt` — see the note in §9.

## How to use this file (conventions)

- Every item is a `- [ ]` checkbox line.
- **When done:** mark `- [x]`, strike the title through and add completion date:
  `- [x] ~~Title~~ ✅ 2026-09-22`. Keep the line (archive value for future sessions).
- **New findings** go into the matching type section, sorted by importance
  (risk first, then urgency, then effort).
- **Session log:** append a dated entry at the bottom describing what was done to
  app code and to this file.
- Re-check stale items every few sessions: delete anything obsolete.

### Test/fix ordering (agreed 2026-09-22)

No blanket upfront test push — the existing Playwright suites already cover the
dangerous flows. Instead: **write tests for exactly what you change, ideally
before it** (red → green proves the fix). Concretely:
- library.js storage/slug work (B1–B3): test-first → done via
  `tests/library_hardening.py`.
- Before §4 P1 (render refactor): ~~pin token/sheet rendering behaviour~~ ✅
  `d812a96` → `tests/render_pin.py` (in CI): strip chip sequence/classes/
  texts (subscript spellings, duration glyphs), grid composition (sec-head/
  tab-bar/tab-tempo, junk excluded, tie/rest card shapes), scroll-band
  difference (named bar keeps its tagged line), `highlightToken` .now
  propagation across both strips + sheet card, focus-restore across rebuild.
  ~~§4 P1 may now start.~~ **Done 2026-09-23:** the pin grew the debounce
  contract (red pre-fix) and `tests/svg_cache.py` froze clone coordinates
  before `842d004` landed debounce + svg reuse.
- Before §5 ES-modules migration: parse.js + transport-level tests first.
- §6 T1 parse.js unit suite stays cheap and worth doing whenever its
  neighbours (math dedup, modules) get scheduled.

### Color legend

Each item carries 3 tags in a trailing code span: `🟥 🔴 ⚙S` = first square → risk,
first circle → urgency, last letter → effort.

| Risk (■) | Meaning |
|---|---|
| 🟥 | Severe — loses user data or breaks core flows |
| 🟧 | Moderate — degrades correctness/UX on common paths |
| 🟨 | Minor — edge cases, polish, noise |
| 🟢 | Cosmetic / negligible |

| Urgency (●) | Meaning |
|---|---|
| 🔴 | Do at the very next session |
| 🟠 | Soon — next few sessions |
| 🟡 | Later / backlog |
| ⚪ | Idle idea — do if touched anyway |

| Effort | Meaning |
|---|---|
| ⚙S | ~30 min or less |
| ⚙M | A few hours |
| ⚙L | Multi-session refactor |

---

## Hot list (importance across all types)

Picks for the next session(s), roughly damage × imminence ÷ effort:

| # | Item | Section |
|---|---|---|
| 1 | ~~Slug collisions silently overwrite saved library songs~~ ✅ 43147f5 | §1 B1 |
| 2 | ~~Guard localStorage writes + protect against corrupt library JSON~~ ✅ 43147f5 | §1 B2/B3 |
| 3 | ~~Replace silent empty `catch` blocks (synth failures invisible)~~ ✅ 4480fab | §2 R1 |
| 4 | ~~Instrument-switch race: old fetch can clobber new install~~ ✅ c23f3d8 | §1 B4 |
| 5 | ~~Audio unlock happens on `pointerover` (breaks on Firefox)~~ ✅ 97e86f0 | §2 R2 |
| 6 | ~~Keyboard/touch access for piano keys and token chips~~ ✅ 3094ad7 (keyboard; long-press-on-touch still open) | §7 A1/A2 |
| 7 | ~~Debounce/diff the per-keystroke full re-render~~ ✅ 842d004 | §4 P1 |
| 8 | parse.js edge-case tests + eslint in CI — ~~parse tests~~ ✅ 9cdab5d; ~~eslint~~ ✅ 62d056d (warn-level; tighten after first CI counts) | §6 T1/T5 |
| 9 | ~~Clean up tone.json manifest entries (3 × guaranteed 404)~~ — **reframed, not a fix**: entries are intentional, per-chamber measurements planned; README reworded ✅ 9cfccfb | §1 B5 |
| 10 | ~~Favicon/meta + shrink `hyrule.jpg`~~ — favicon ✅ 9cfccfb; hyrule ✅ 09efb80 | §8 H1/H2 |

All ten originals are closed. Fresh picks for the next session(s), same
formula (damage × imminence ÷ effort):

| # | Item | Section |
|---|---|---|
| 1 | ~~Support voices bypass the cut-bus (audible legacy-fade clicks on the support path)~~ — **held for ears** (changes audible support-voice behavior; Robin must audition) | §5 M3 |
| 2 | ~~PWA/offline mode (also owns cache-busting — deferred there by Robin's call)~~ ✅ 54d1832 | §9 F1 |
| 3 | ~~Section looping~~ ❌ DECLINED 2026-09-24 (Robin doesn't want loops now; entry kept for revival) | §9 F2 |
| 4 | ~~Schema validation of instruments/songs/fingerings on boot~~ — **superseded by §9 F1**: the prism of the SW-derived precache means a bad manifest entry breaks CI's offline suite, and Robin may not want a loud-boot gate for his hand-tuned data — reconfirm intent before building | §2 R4 |
| 5 | ~~Practice autocorrelation off the main thread (Worker)~~ ✅ 08f40e6 | §4 P2 |
| 6 | ~~Small autonomous batch: additive drift guard, title-only tooltips, instrument-id validation~~ ✅ 3bb5bfa (+#err append-survives fix) | §5 M4, §7 A7, §5 M8 |
| 7 | ~~Cache-busting~~ resolved by the PWA SWR (delivered with §9 F1) | §5 |
| 8 | Robin-field feedback stack: ~~M3 support cut-bus audition~~ ✅ done, PWA install + airplane-mode practice (§9 F1), theme/help/title-bar eyeball, history line, new highlight-plan playback eyeball, dip dipMs/dipFrac by ear (§4 P2's retuned gate) | feel checks |
| 9 | Open work: ~~ES-modules~~ ✅ closed 22/22 (`28eadd8`), ~~§5 M3 cut-bus~~ ✅ closed (routed `9f91eab`, ear-checked), section looping ❌ declined 2026-09-24, then §9 features (transpose, MIDI import, recording) | §5/§9 |
| 10 | **Search-engine perma-links BEFORE the November Switch-2 OoT launch** — the one deadline-bound item in the pool (slug freeze → per-song static stubs → og/meta → robots on verification; ~5 weeks) | §9 |

---

## 1. Bugs (correctness / data loss)

- [x] ~~**Slug collisions overwrite saved library songs** — `slugName` fallback is dead code (`"u-" + … || fallback`, `+` binds tighter than `||`) so it never fires; junk names collapse to id `u-` and names differing only in punctuation collide and silently overwrite each other in the saved library. Fix precedence + add uniqueness suffix. (library.js:22, library.js:433)~~ ✅ 2026-09-22 `43147f5` — `slugName` fixed; new `uniqueUserId(lib, name)`: same-name re-save keeps overwrite semantics, other collisions get `-2, -3…`. Covered by tests/library_hardening.py.
- [x] ~~**localStorage writes unguarded** — `setUserLib` and `setShowHidden` call `setItem` without try/catch: QuotaExceeded or Safari private mode throws inside async click handlers → save silently fails with no feedback; contrast guarded read at library.js:13-15. Wrap + surface a toast/error. (library.js:18, library.js:48)~~ ✅ 2026-09-22 `43147f5` — `setUserLib` returns true/false, fail-soft; `setShowHidden` swallows; libSave/libRemove toast on refusal.
- [x] ~~**Corrupt library JSON → silent data loss** — `userLib()` turns unparseable JSON into `{}` and the next save overwrites it. Detect corruption, back up the raw string (e.g. `oco-bass-c-library.corrupt-<ts>`) before recovering. (library.js:13-15)~~ ✅ 2026-09-22 `43147f5` — backup-max-once then reset; parsed non-objects (e.g. `[1,2]`) count as corrupt too. Tested.
- [x] ~~**Instrument-switch race** — `loadInstrument` awaits fingerings+SVG then unconditionally installs; a slow older fetch can clobber a newer instrument's install. Only the tone model has a `CURRENT_INSTRUMENT` guard. Add a generation/sequence counter around the whole load. (app.js:87-111)~~ ✅ 2026-09-22 `c23f3d8` — `instLoadGen` generation guard in `loadInstrument` (superseded loads bail before installing); `switchInstrument` skips follow-up UI work for superseded loads. `tests/instrument_switch_race.py` (in CI): throttled dummy-bass switch loses to fast stein switch (red pre-fix: A4 clobbered back to A3).
- [x] ~~**Hard-coded Saria special case in generic matcher** — `songMatchesStem` regexes `"sarias-song"` by title in app code; fold into the manifest's `svgWhen` rule instead. (app.js)~~ ✅ 2026-09-22 `c985bd9` — manifest rules may carry their own `songTitle` regex (`^saria'?s song$` now lives in instruments.json); matcher takes the rule's regex. 3-case pin added to `tests/instruments_load.py`: by stem-ahead id (`?song=sarias-song-alto&oot`), by hand-typed `# Saria's Song` body, unrelated title stays generic. **Finding while pinning:** on the Alto C the plain `sarias-song` body is out of range so the dropdown stays empty — the stem-prefix branch of the id path is what makes `sarias-song-alto` fire; the Saria svg ALSO can't fire from links to the plain body there (out of range hides it) unless the toggle reveals it.
- [x] ~~**aria-expanded mismatch on load** — collapse-btn elements say `aria-expanded="true"` in markup but JS collapses both input/playback blocks on init. Sync at init. (index.html:28,57; ui.js:1567)~~ ✅ 2026-09-22 `c69448f` — blocks start `.collapsed` + `aria-expanded="false"` + `title="Expand"` in the markup; no flash of expanded content before scripts run either.
- [x] ~~**Two inconsistent fill metrics exposed** — `OCA_PRACTICE.fillPct` divides by `targetSec*1000` while `barFrac` divides by sum of `segTargets`; pick one definition. (practice.js:1209 vs practice.js:213-216)~~ ✅ 2026-09-22 `567ec29` — Robin decided: engine stays untouched (75%-credit bars pass, play-tested and liked). The debug surface now carries BOTH meanings with distinct names: `fillPct` = note-time fraction (1.0 at full notated length), new `creditPct` = credit progress (1.0 exactly at the pass point).
- [x] ~~**render() calls fitInput() twice** — (ui.js:360, ui.js:362)~~ ✅ 2026-09-22 `c69448f` — second call sat after a title-only change that can't affect textarea height.
- [x] ~~**Same-line function definitions** — `function isMelodyPlaying() {…}function isMelodyPaused() {…}` formatting smell. (audio.js:1685)~~ ✅ 2026-09-22 `c69448f`
- [x] ~~**Normal-mode transport lacks a Stop** — zen's focus bar has a Stop button; the regular playback bar only cycles Play/Pause (and Space now pauses too since `1d6e03e`).~~ ✅ 2026-09-22 `017284e` + `1f904b6` + `0c58a50` — final shape per Robin: the four round controls (Loop, Play, Practice, Stop — same order, same ACTIVE colors) are TRULY CENTERED over the playback box-head (absolute, static-wrap fallback ≤760px); Loop/Tick lead the left cluster; the text Play/Practice buttons and hear-hint span retired; **Lite's header checkbox removed** (hidden `#liteMel` carrier keeps the one shared state the perf switch/glitch toast/audio read and persist). **Resting rounds wear the inactive ghost look** (Robin: black is the "activated" vocabulary; active colors untouched, glyphs go paper-colored when a state is on). **Tempo & Swing: each row is its own `title|slider|value` grid with FIXED column tracks** (`48px | 90px | value`) so the two sliders sit directly over each other (the earlier `display:contents` share-4-items version broke into a mess). Stop semantics shared via `transportStopAll`. Probe in `tests/keyboard_widgets.py` (incl. squares-gone). Needs only Robin's final eyeball.

- [x] ~~**Deep-link instrument change does not redirect to root+vars (field-observed)** — Robin IDEAS 2026-09-25: "If I use a song deep link and change instrument, I'm not redirected to root+vars." The shipped landed-crawler contract wanted every LATER content change off a /song/ path to resolve to the site root with ?song=&inst= (an instrument change alone rides the switchInstrument same-song rewrite path in js/library.js), and gen_pages pins that switch leg in its test boots — so either the live root-served stubs behave differently from the staged legs or the instrument-only path misses the rewrite in the wild; reproduce on a live /song/ stub first (field check, his device), then red-first the fix. Hot: the domain is Search-Console-verified and the sitemap URLs are now permanent, so the intent contract (a /song/ path never plays different content) must hold before the crawler's first real sweep. `🟧 🟠 ⚙S`~~ ✅ 2026-09-25 `ff53abb` — Field answer 2026-09-25 closes the observation: instrument switching on a
live /song/ stub DOES resolve to root+vars on the deployed site (Robin
field-checked; headless probe agrees — /song/zelda/botw-theme/ →
/?song=botw-theme&inst=stein-double-alto-c). But the contract had two
latent holes left to red-first: (1) the rewrite dropped the MOUNT prefix —
STUB_PATH had no capture group, so m[1]||"/" always resolved to the domain
root, masked only because the pinned domain serves at /; (2) once off the
deep path, ?song= stopped tracking the playing song — a later library load
found the stub matcher already empty and returned early, leaving the
previous song's var in place. Fixed in js/library.js rewriteLanderUrl
(mount-anchored regex + in-place var refresh, extras like theme params
survive) and pinned by the new MOUNTED boot leg in tests/gen_pages.py
(instrument switch, library switch, typed replacement all resolve to the
mount root).

- [x] ~~**tone.json declared but absent — INTENTIONAL, not a bug** — instruments.json lists `tone` paths for stein-double-alto-c, oot-alto-c-12, ico-contrabass-11-c: Robin is going to measure/tune every ocarina chamber; until each tone.json is recorded the loader treats the 404 as "no data yet" (correct behaviour). REWORDED instruments/README.md to say entries may declare the field ahead of measurements ✅ 2026-09-22 `9cfccfb`. **Opens instead: the actual measurement/fitting work per chamber.** `🟩 ⚪ ⚙L`~~ ✅ 2026-09-26 — TRIAGED 2026-09-26 (Robin: "TODO carries what we need TODO"): the loader side is complete — the manifest may declare tone paths ahead of measurements and the 404 reads as "no data yet" (README rewording shipped 2026-09-22 `9cfccfb`). The remainder is the measurement/fitting work itself; it continues as the compact §1 item.

- [x] ~~**Twin voice for the 12-hole: the adopted baseline and its open classes** — the Helmholtz twin (`js/helmholtz-voice.js` + `instruments/oot-alto-c-12/twin_model.json`, handoff from Grok via Robin) REPLACES the additive voice outright — Robin field-checked the handoff VOICE and ruled it the baseline ("it was perfect before" as handed over; the pass that rewrote the model's noise rows algebraically was REVERTED by his ears — A4's metronomic one-sine wobble "very bad", the liked E5 wobble is the pitch wander's). Standing state 2026-09-28 (evening): the voice module is the THIRD Grok handoff VERBATIM — the mid-air LEAD (`research/ocarina-twin-lead.zip`; his HANDOFF says it OVERRIDES the earlier zips and names the 1.6×f0-highshelf air path THE BUG): the air is a MID PEDESTAL [1.25 f0, 4 kHz] (`noise_mid_db` — "this is E6/F6 air"), RMS-matched per band against the tone (`pinkBandComp` on an RMS-normalized noise buffer), plus a QUIETER true hiss [4 kHz, 12 kHz] — NO highshelf, NO 2800/1.6f0 cutoff, NO airFade (AUDIO_DEBUG.airLevel stays 0, untouched). The MODEL is the ladder fit REFIT under the lead fitter: 11 rows C5-F6, mid rows −31..−39, hiss rows −43.6..−59.5 (the pipeline-era "hiss rows −33..−41" measured mid+hiss TOGETHER on one wide band — Grok: extra fizz is not hole-rush, that is why E6/F6 "still not airy enough"); git keeps the retune history (`9c04a7a` → `6ce668f` → this adoption); the manifest declares `twin`, tone.json stays retired (the additive voice still serves stein double + contrabass). A4/As4/B4 ride the C5 row end-clamped (symmetric with the old top-clamp) — part of his field check. Acceptance numbers on the lead's own spec (`skills/ocarina-twin/validate.py` translated to his three bands): F6 synth 1.5–2.8 kHz −31.4 vs target −32 ±3 ✅; C5 clean (syn15 4 dB under the take — never brighter, no 2 kHz shelf; mid d −0.2); F6 syn 5–8 kHz −42.2 (13 dB under the mid band per his structural clause, but 2.8 dB above his strict −45 line — MARGINAL, left untouched, his ears rule); D6/E6 read ~6-14 dB hotter than their takes measure (dHiss +11..+14 at D6 — Grok's delivery convention class, named not fixed). OPEN classes, ears-first per the skill's first law: (a) ATTACK ring-up — the gate's render-vs-take rise deltas read 0.0 across the ladder on this baseline — the cavity-Q ring-up assist stays the held idea, his word first; (c) NO amplitude-wobble layer persists (the module interpolates wobble_pct unused — do not "complete" it without his ask); (d) release taper: rel_s still the fitter's flat 0.07 — the decay leg re-passed inside its 15 dB cap on the lead baseline; (e) future refits may NOT reproduce the shipped file (the span rule is Grok's and the lead zip keeps it: thr = max(peak*0.08, med*4); the shipped model is the adopted reference, not "the fit"). Regression gate: tests/tone_stages green across the 11-note held set with the H4 cap re-anchored to 18 on the lead delivery (the mid pedestal now plays INTO the 4f0 window the starved path didn't reach: C5/D5 measured +14.3..+14.5 while the delivered band still sits ~1 dB off the take's own 1.5-2.8 kHz floor; H2/H3 stay row-tracked ±4; the suite comment carries the reasoning). `🟧 🔴 ⚙M`~~ ✅ 2026-09-28 `8c4f435` — Robin field-checked the mid-air voice the same evening (after 8c4f435):

12-hole: "it is VERY good. Sounds like real recordings of my ocarina, but
played by a pro instead of me."
Stein double: "sounds good."

That blesses the adopted baseline (voice module + both fitted models at
8c4f435) end to end — the ranking the item tracked stands complete: the
mid-air lead is the field-checked baseline of the twin voice. The
previously-open marginal numerics (F6 5-8 kHz 2.8 dB over the strict -45
line, top-note delivery +6..+14 hotter than the takes measure) ride the
blessed voice as delivered, not as defects. Remaining in this area: the
guessed bass voices (separate item), the one-take calibration recording
for the true cross-instrument scale, and per-chamber refits when real
recordings land.

- [x] ~~**Grok's low-note presence fix lands (Robin deployed the two files; no refit, JSON rows stay)** — playbackQ caps the tone ring (30 + f0*0.035, ~48 at C5) and the mid path lifts lowNotePresence(f0) x2.4 -> x1 by A5, mirrored identically in synth.py's offline reference; F6's mid/hiss untouched, the validate acceptance holds, C5's 1.5-2.8 kHz floor back to -49.5 vs the take's -51.2, the stage gate re-anchored red-first on the hotter-by-design C5/D5 classes (H4 21, hiss 24, H2 8); full sweep 47/47, sw oco-pwa-v49 (commit `ecc5413`). Robin's field check: "Sounds perfect." `🟨 ⚪ ⚙S`~~ ✅ 2026-09-28 `ecc5413`

- [x] ~~**Fit the twin model per chamber (Robin records held takes; the tone-analysis era closed for the 12-hole)** — skills/ocarina-twin/run_fit.py refits a chamber from held takes (one per fingering; the subtract analysis tracks f0 so the residual is real breath); the handoff model reproduced bit-for-bit from research/note-recordings/12hole's 8 held takes (A4-A5). LANDED chambers, BOTH now on the mid-air lead (2026-09-28 evening adoption, three-band rows): stein-double-alto-c carries its full two-chamber LADDER fit, re-refit under the lead fitter (chamber 1: 11 takes As4-Ds6, anchor Ds6; chamber 2: 5 takes F6-C7, anchor A6 — the second chamber fitted where the temp rode one clamped row; E6's take RE-PROBED under the lead fitter and excluded AGAIN: its tracked subtract still slips, res read −0.0 re tone, so E6 end-clamps onto F6's row until a cleaner take; reference-recordings/double-alto-c/E6-held.wav stays committed), and the cross-chamber loudness rides the wrapper gains carried VERBATIM into this refit (the raw takes are unchanged between fits, so the measured chain stands rather than a re-derivation with a new ad-hoc method: ch1 0.9783, ch2 0.7277 = ch2 under ch1 by 2.57 dB, both gains folding the cross-instrument scale that normalizes the stein's max-volume with the 12-hole's ladder session — Ds6 raw peak −0.19 dB over the 12-hole's E6, s = 0.9783 — the sessions were recorded similarly so the land sits close); chamber validates on the lead's three bands: ch1 C5 mid d 0.0 / no-shelf, Ds6 +6.6; ch2 G6 +7.1, C7 +9.0 — the same synth-hotter-than-take class the 12-hole's top showed, named not fixed. THE 12-HOLE refits under the same lead fitter (11 rows C5-F6; mid −31..−39, hiss −43.6..−59.5; F6 mid-acceptance ✅, see the §1 12-hole item). THE CROSS-INSTRUMENT TRUTH waits on Robin's dedicated one-take calibration recording (his word: "In the future I will give a one-take recording to specifically match both (or more) instruments to their true relative volume") — never treat separate sessions as calibrated without it. STILL REMAINING AS REAL FITS (the gaps carry GUESSED twins meanwhile, 2026-09-28 late, `research/guessed-twins.zip` installed): dummy-bass-c-double (ch1 A3-Ds5 gain 1.0 + ch2 E5-C6 gain 0.92 — its chart carries chambers 1|2), ico-contrabass-11-c (single chamber B2-F4, flat schema, `guessed` inside globals, Q_prior 38, dry-mid split retuned to its own f0 range 123-349 Hz), ico-oak-leaf-bass-c-triple (ch1 A3-Ds5 + ch2 E5-C6 gain 0.92 + ch3 Cs6-G6 gain 0.85 — the chart carries 1|2|3). Grok scaled these from the measured 12-hole mid-air model ("no WAV from these instruments was used", `guessed: true` on the wrappers/contrabass globals; his do-nots in the zip's HANDOFF: the 4 kHz hiss split is STILL THE ALTO SPLIT — a real bass whoosh is lower; do not treat F6-alto mid numbers as gospel on a contrabass; do not call them digital twins; the triple's refit wants three short sessions, one chamber each, then throw the guesses away). ALL FIVE instruments now declare `twin` — melody AND support/track voices play the twin engine on every instrument (TWIN_SUPPORT_LEVEL's anchored support path); the additive voice is dormant legacy kept for the red-green support comparisons and the future cleanup wait; the manifests ride DATA_NETWORK_FIRST so no sw VERSION bump (data-only precedent `9c04a7a`). The fitter's span rule is now peak*0.08 (the old median*4 guard collapsed EVERY span onto the 0.15/0.85 fallback — release+silence fitted as sustain — so historical fitted levels/wobble read through that window; the lead zip trimmed the fitter's nominal table back to F6 and the Fs6..Cs7 rows were RESTORED in place for the stein's chamber 2 — a missing key had read G6 at a 500 Hz default and the whole subtract built on a wrong octave; the 12-hole's rows are inside the base table either way). Cross-twin A/B of 2026-09-28 (the TEMP stein vs the then-12-hole) is SUPERSEDED by the ladder fits: the old stein numbers (2-3 dB quieter + an E5-class 8.2 dB hole from ch1's two-anchor lerp C5 0.176 → D6 1.0) described the temp rows, not the instrument — the ladder fit re-levels per-take and the chain-level normalization sits in the wrapper gains above. THE STANDING TRUTH survives it: the two models' absolute anchors come from separate mic sessions (the engine's masterLevel is shared so the takes' own levels are the whole story), now anchored to each other only by the similar-sessions word + the −0.39 dB raw-peak scale; Robin's one-take calibration remains the arbiter. Support-layer parity probe (Robin's ask, 2026-09-28): the support-class track notes are ALREADY instrument-independent — C3/E3/G3 within ±0.1 dB across the two (both clamp below-chart track notes to their chamber-1 anchor row) — but the melody:track ratio at E5 flips 12-hole +15.8 dB vs stein +7.7 dB, so the fixed-volume support reads ~2× too loud under the stein's E5 hole; a ch1 wrapper lift would raise voice AND tracks together (shared path) and preserve the flip, so the balance restore needs the melody anchors, not the wrapper. THEN THE REAL FORK (Robin's URLs, 2026-09-28): the 12-hole support measured 12.7-13.1 dB QUIETER than the OAK-LEAF-TRIPLE's support — the support on non-twin instruments rides the additive-GENERIC voice (a much hotter scale) while twin-instrument support rides the fitted clamped level rows; eponas support D3/E3/G3 twin ≈ −29.5 dBFS vs additive ≈ −16.6 dBFS through the identical bench. BUILT (held for Robin's field check): js/audio.js TWIN_SUPPORT_LEVEL 0.75 — every support voice (track walker both zones + the legacy support forwarder; NOT the melody bag, NOT the flag-less preview voices — `bag.melodyRoute && bag !== melodyBag`) divides the interpolated level back out and plays at the anchored constant × the new `supportLevel` panel multiplier (debug Output row, default 1); timbre keeps the fit. Red→green tests/twin_support_level.py (CI-registered): E3/G3 twin-support vs additive-support plateaus within 1.5 dB — red carried the defect verbatim (−12.82/−13.14), green after; eslint clean; sw oco-pwa-v45. The stein's support lifts the same +13 dB (its ladder-era chamber gains — ch1 −0.39 dB, ch2 −3.24 dB — ride the support path equally). His hands-on time as he gets it. `🟩 ⚪ ⚙L`~~ ✅ 2026-09-28 `8c4f435` — THE LANDED ERA (struck): every chamber that CAN be fitted from recordings
IS fitted and field-blessed - the 12-hole's full-range ladder fit (11 rows
C5-F6, one session; three refits: the pipeline, the mid-air lead, the
low-note-presence delivery; Robin's "Sounds perfect" on the last; his
"VERY good ... played by a pro" on the mid-air voice) and the stein
double's full two-chamber ladder fit (ch1 As4-Ds6 anchor Ds6, ch2 F6-C7
anchor A6, E6's take excluded twice under the tracker slip - res -0.0 -
so E6 rides F6's row end-clamped; his "Stein sounds good / sounds
perfect"). The placeholder era behind them: the 8-take A4-A5 12-hole fit
and the stein's sep-17 3-note temp twin were PROOFS, replaced wholesale
by Robin's word ("a placeholder to proof the new synth"). The
cross-chamber loudness (ch2/ch1 -2.57 dB, ch1 0.9783, ch2 0.7277) and
the cross-instrument scale (s = 0.9783, Ds6 -0.19 dB over the 12-hole's
E6) are measured from the RAW take peaks and folded into the wrapper
gains - standing through every refit because the raw takes did not
change; the true arbiter remains Robin's dedicated one-take calibration
recording. The remaining instruments ride Grok's GUESSED twins
(research/guessed-twins.zip, no WAV from them; his do-nots recorded;
refit per chamber when real recordings land - the slim item carries the
plan). Support/track voices ride the twin engine everywhere (the
anchored TWIN_SUPPORT_LEVEL 0.75 path, red-greens in
tests/twin_support_level). The support-E5-flip finding (12-hole +15.8
vs stein +7.7) and the TWIN_SUPPORT_LEVEL build story live here as
history; the balance restore still waits on the melody anchors, not the
wrapper. The fitter's span rule is Grok's (thr = max(peak*0.08, med*4));
the NOM table carries Fs6..Cs7 (trimmed by the lead zip, restored for
the stein's chamber 2).

- [x] ~~**Record real held takes -> refit per chamber (the only remaining twin-fitting work; the guessed twins carry every instrument until then)** — dummy-bass-c-double ch1 A3-Ds5 + ch2 E5-C6; ico-oak-leaf-bass-c-triple ch1+ch2+ch3 (Grok: THREE short sessions, one chamber per session, normal blow only); ico-contrabass-11-c one session B2-F4 (its guessed model even retunes the dry-mid split to the instrument's own f0 range — the refit replaces that guess with a measured split). PLUS the stein ch2's E6 re-blow for a fittable take (two fails: res -0.0 both times — tracker slips on that wobble's attack slice); then the wrapper gains re-derive from the raw peaks. The cross-chamber/cross-instrument gain doctrine + refit loop live in skills/ocarina-twin/SKILL.md; refits go through Grok's lead fitter unchanged. Superseded 2026-09-29 (dfc7199): the guessed per-chamber twins DO ship on the v45 engine — oak/dummy/contrabass keep their own scaled rows, 12-hole + stein keep the v45 fitted models; the mid-air JSON stays parked in git history. `🟨 🟡 ⚙M`~~ ✅ 2026-09-30 — Robin 2026-09-30: the guessed per-chamber twins stand (field-checked fine) — held takes, the stein E6 re-blow and the one-take calibration re-derivation all wait until he owns the instruments; the refit loop + gain doctrine stay in skills/ocarina-twin

- [x] ~~**Transport sync: tracks desync across pause/unpause + tempo change; first note sometimes "hurries"** — Robin's planted bugs (IDEAS BUGS): the #track streams (walkTrackStreams, js/audio.js:1432) drift from the melody clock through pauseMelody/resumeMelody (audio.js:1181/1196) and mid-play tempo changes; the first note can also start early when playing from the start; pin red-first in tests/transport_schedule.py; engine change ⇒ full sweep + his field check. `🟧 🔴 ⚙M`~~ ✅ 2026-09-30 `3eb740d` — pause/resume + tempo drift fixed and pinned (two new phase-lock legs); the first-note "hurries" symptom stayed unreproducible in the harness — first-onset equality is pinned, held for Robin's field check (re-open if it persists after oco-pwa-v60)

- [x] ~~**Zen chorus audit: did the twin engine drop the zen chorus? (IDEAS question)** — report-first: the twin path still carries the zen stereo chorus (audio.js twChorus: gated on vibOn && dur > vibDelay+0.1, depth faded by vibHighFade 0.4, zenPan 0.9) — check the zen defaults + the lite-voice path and report; fix only if truly lost (field-check class). `🟨 🟡 ⚙S`~~ ✅ 2026-09-30 — Report-first audit, closed with no code change: the zen stereo chorus was NOT dropped by the twin engine. Full twin voice keeps the legacy gating verbatim — twChorus = vibratoEnabled && dur > vibDelay + 0.1 (js/audio.js:1033) with the clean core hard LEFT and the vibrato twin hard RIGHT at ±zenPan (audio.js:1050–1073), identical to the additive chorus gating stripped at 8a7d68d. Zen defaults intact (vibDepth 0.0035, vibHighFade 0.4, zenPan 0.9, vibDelay 0.35 — AUDIO_DEFAULTS js/audio.js:46–66; dev-panel sliders js/debug.js:38–48); vibratoEnabled is owned by the zen transitions (exitZen → false, toggleZen/sync → isFocusMode(), js/ui.js:1776/1980). The LITE twin voice (audio.js:979–1021) has no chorus/panner, but the legacy additive lite branch skipped the vibrato layers too — a consistent reduction, not a loss; zen+lite stays chorus-free by design (Robin may revisit that combination on his field check). The "fix only if truly lost" clause does not trigger.

## 2. Robustness / error handling

- [x] ~~**Silent empty catches swallow synth failures** — `playNoteAt` wraps the entire voice builder in `try { … } catch (e) {}` (zero feedback), same in `playTickAt` and `simulateLag`, plus ~a dozen bare try/catch through audio/hover/position code. Log at least once per session into `#err` or a debug counter. (audio.js:975→1633, audio.js:1683, audio.js:131)~~ ✅ 2026-09-22 `4480fab` — `recordVoiceError(site, e)` records count+site+cause with a 1 s throttled console warn; exposed as `OCA_DEBUG.voiceErrors()/clearVoiceErrors()` (the debug panel can read it); wired into both playNoteAt and playTickAt. The small teardown/hover try/catches stay by design (they guard benign node-stop races); `simulateLag` already lives behind the debug panel. Verified by `tests/voice_error_visibility.py` (in CI).
- [x] ~~**AudioContext unlock on pointerover fails cross-browser** — context created/resumed on mere hover; Firefox requires a real gesture for `resume()` → rejected promise, never handled. Move the unlock to `pointerdown`/`keydown` and handle the rejection. (audio.js:540-542)~~ ✅ 2026-09-22 `97e86f0` — unlocked on `pointerdown`/`keydown`/`touchstart` only; resume rejection caught explicitly.
- [x] ~~**Weak global error reporting** — `window.onerror` prints `message @line` only (no stack), clobbers `#err` content, and unhandled promise rejections are uncaptured. Add `unhandledrejection` listener; append rather than overwrite. (app.js:1-4)~~ ✅ 2026-09-22 `812b25f` — `reportGlobalError` appends lines to `#err` (never clobbers render/boot's two writers); onerror now carries the stack's throw-site frame; `unhandledrejection` listener added. Test-first in `voice_error_visibility.py` (red: 'precious' clobbered + rejection invisible → green).
- [x] ~~**AudioContext lifecycle** — never `close()`d, no
`statechange` handling for autoplay-policy suspensions mid-session
(playback halts silently after tab-background policies kick in).~~
✅ 2026-09-24 `8c3c89b` — Robin picked the design himself ("lifecycle...
you may do", pause-clean over stop): a statechange watch attached at all
six context-creation sites (assign-then-attach: the first draft dropped
the `audioCtx ||` short-circuit, recreated fresh (autoplay-blocked,
suspended) contexts at every note and paused every melody — the
transport sweep red caught it before any commit) pauses the transport
cleanly when a RUNNING context is suspended mid-playback (the UI stops
claiming playback over a frozen clock; grid position preserved, so Play
resumes from the frozen beat), while a return to running NEVER silently
restarts — the user resumes. `tests/audio_state.py` (in CI, red first).
`🟨 🟡 ⚙M`
- [x] ~~**Error text injected into markup** — `ocarinaSVG` catch returns `"<div>" + String(e) + "</div>"`; escape or use textContent. (ocarina.js:62)~~ ✅ 2026-09-22 `f21284f` — catch builds a div via textContent and returns its innerHTML (escaped).
- [x] ~~**URL.revokeObjectURL in same tick as click** — historically aborts downloads in some engines; defer the revoke. (library.js:503, ui.js:1083)~~ ✅ 2026-09-22 `8c6b85a` — both download spots now drain via `setTimeout(…, 5000)` (the pattern debug.js export already used); blob lives ≤5 s, download binds in ms. No behavioral test (network-layer engine quirk); suites green. **Robin convention: shipped code comments carry NO references to the local TODO doc** (code-to-code file refs are fine; commit titles informative, §-refs only inside TODO.md itself).
- [x] ~~**Decorated `round()` CSS only on modern engines** — `width: max(round(down,100%,35mm), …)` silently dropped on older browsers. Add a plain fallback declaration above. (app.css:451)~~ ✅ 2026-09-22 `f21284f` — explicit `width: 100%` fallback before the round() line at all three sites (print, base, fullscreen); degradation stays the documented old full-width block, now by declaration instead of drop-accident.
- [x] ~~**Page-lifetime costs accepted but unbounded** — watchdog `setInterval` never torn down (audio.js:292-311), anchor oscillator runs forever in reverb bus (audio.js:398-405), waveform cache grows unbounded on debug tweaks (audio.js:907-923). Document as intentional or add teardown hooks.~~ ✅ 2026-09-22 `96d5f85` — Option A: README "Accepted by design" paragraph (Robin: all three don't-care; watchdog/reverb negligible, waveform cache "I have 128GB of RAM").

- [x] ~~**No schema validation of data files** — REFRAMED 2026-09-24 with Robin: the shape is a CI-side pure-stdlib validator suite — no loud runtime boot gate for hand-tuned data (a malformed manifest already breaks CI's offline suite, but only accidentally). The suite validates instruments.json / songs.json / fingerings.json structure AND cross-references (declared files exist, tone paths either exist or are the deliberate 404s, unique ids, chart-range sanity) and fails CI naming the offending path/class. The original loud-boot-gate idea stays archived in DONE §2 — revive only if data ever becomes user-supplied. `🟧 🟡 ⚙M`~~ ✅ 2026-09-25 `f62ede5`

- [x] ~~**Sporadic single-frame audio "ticks" — one waveform jump per tick, and the CURRENT note goes silent after it** — Robin field notes 2026-09-24: ticks on Windows AND on his phone, on the phone even with the Lite voice (rules OUT node-count/CPU pressure), the perf screen's glitch counter never fires for them (it counts audio-clock-vs-wall lag at a 0.3 s criterion, audio.js:352 — a sample-plane discontinuity never gets near it), "after such a tick, the current note seems silenced", sporadic with no identified trigger yet. Class read: this is a RENDERED-SIGNAL discontinuity, not starvation — prime suspects: (1) AudioParam event-timeline re-anchoring of a LIVE envelope: a later linearRamp's implicit anchor or a `cancelScheduledValues` path restamp the running gain to a stale event value → one step (the tick) plus a dead envelope remainder (the silenced note) — the neighborhoods audio.js:1131-1133 (non-melody bag fade) and 1671-1673 (live/hover rampFades) plus the documented implicit-event hazard (~audio.js:1363); this exact neighborhood has real-device history — cancelAndHoldAtTime "popped on real hardware" and was engineered out; (2) the DynamicsCompressor limiter pumping at multi-voice seams; (3) zen mono↔stereo anchor/pan events; (4) device-level (Windows shared-mode WASAPI) — least likely given lite-invariance. Detection plan: a debug-only spike detector on the perfAnalyser time-domain tap (single-frame |Δx| > K·system-RMS, with the markSystemSound onset/stop windows subtracted) logging timestamp + a state card (in-flight onsets, retire window, tempo move, zen in/out, lite flag) to the perf panel + OCA_DEBUG; the next field tick then names its own automation seam. **Field answers 2026-09-24:** playback CONTINUES at the next note after the silenced one → voice-seam class confirmed, context/device death ruled out; the same song does NOT reproduce consistently across replays → a timing race at event collation, not a per-note mapping error; observed on MAIN (pre-existing shipped behavior, independent of the refactor4 chain); repro rate ~every 2 playbacks of Concerning Hobbits short in Google Chrome, NOT reproducible in VS Code's embedded browser (engine-timing sensitive — different Chromium build, different event-alignment odds). (✅ 2026-09-24 `17fae24`) **the spike watch detector landed** (test-first, `tests/spike_watch.py` in CI): a pure two-shape classifier (ONE delta to a new sustained level — the jump-to-silence that kills the note — or a mirrored up-then-down pair for the single-sample excursion; N-adjacent above-threshold deltas = ramp class, rejected) reads the post-limiter analyser every 20 ms (overlapping 23 ms windows, full coverage), the markSystemSound onset/stop windows subtracted, each hit logged as a state card (audio-clock t, jump size, 96th-grid melody position, lite flag, recent playNoteAt onsets from a new ring) on the perf panel's new 'Signal spikes (ticks)' row plus a throttled console warn; `spikeFake()` lets suites probe the row; sw VERSION → v4. **Next field catch now names its own seam** — Robin reproduces in Chrome, the row/card + console line identifies the automation neighborhood; the fix itself stays held for the evidence. **Field evidence lifted from IDEAS 2026-09-24:** on the phone the three perf counters stay at 0 while ticks happen — now described as MULTIPLE consecutive ticks, not yet a buzz — and a screen-orientation flip ALWAYS triggers them ("seems related to the visual processing"); not reproducible on the Windows desktop as of now (earlier Windows reports stand, so repro availability drifts by device/build). Robin's open questions: can background visuals freeze in Zen (and Zen visuals in normal)? Can audio be prioritized over visuals? Would pre-calculating waveforms on song selection even help (this ties the IDEAS PERF waveform idea to the hunt)? The shipped spike watch ("Signal spikes (ticks)" perf row) has NOT yet met the phone — after his next orientation-flip session, whether THAT detector fires while the counters stay silent will itself name the plane the discontinuity lives on. 2026-09-25 56c4ae0: spike cards gain an ambient context ring beside the onsets — orientationchange (legacy + screen.orientation) and a throttled resize burst record kind+agoMs (4 s age-out), riding the state cards, the spikeFake probe and the throttled console warn; the newest field evidence (flip ALWAYS triggers, counters stay 0, ticks run) now pairs itself — a card near a flip names the seam plane, continued silence while the phone still hops proves the device level; detector-side done, the FIX stays held for the evidence. `🟧 🟠 ⚙M`~~ ✅ 2026-09-26 — Robin 2026-09-26 (interactive panel): "Move to done and I will re-introduce it when necessary." — the hunt machinery ships (spike cards + ambient ring from session 14, detect macro); the field catches stay Robins; the item reopens on his word whenever the ticks matter again.

- [x] ~~**Resume invalidation for instrument data (Robin's answered batch 2026-09-29, DEFERRED at his word — "let's do that some other time"; all four forks took the recommended picks: 1 a manifest+loaded-model-only via a 30s-gapped visibility resume slot that TEXT-compares instruments.json and the loaded twin_model.json and reinstalls TWIN_MODEL audio-only, 2 a fingerings.json + ocarina-template*.svg join network-first in the SW closing the last one-visit-late class with the install-derived precache as the offline fallback and a VERSION bump riding along, 3 a silent swaps exactly the songs precedent, 4 a skip while melody/practice active silent retry later; fingerings/svg changes surface a quiet reload nudge instead of a mid-session chart redraw, failures stay silent offline)** — CI: offline_pwa red-first supervisor leg (resume with changed twin_model.json on disk under a pristine try/finally must fire a fresh model fetch + zero page errors; the svg/fingerings serving rides the same pattern), verified red-first then green before commit; the phone case it closes is the noise-hunt's known remainder (a resumed app keeps the manifest and the loaded twin model from its last boot indefinitely). `🟧 🟡 ⚙M`~~ ✅ 2026-09-29 `91983dc` — Landed on the session branch as 91983dc (sw oco-pwa-v55): resume slot re-checks instruments.json + the loaded twin model under the songs gates, model reinstalls audio-only, fingerings/template/svgWhen drift defers with a console.info flag, and the SW data branch widens to every per-instrument file. The one held piece: the reload nudge's VISUAL surface is console.info-only for now — the on-page slot choice is Robin's design call, flagged before any UI passes his eyes.

## 3. Security (low today — matters if data files become user-supplied)

- [x] ~~**innerHTML surface audit (~35 uses)** — flag risky-but-reachable spots: `${name}` from instruments.json interpolated into innerHTML in range warning (ui.js:344-346); instrument template SVG claimed as trusted because it's fetched and used via `clone.outerHTML`/`tpl.innerHTML = svgText` — if a template SVG ever carried `on*` attributes they activate in HTML context (ocarina.js:60, ocarina.js:8). Sanitize SVG (strip `script`/`on*`) before install.~~ ✅ 2026-09-23 `0d4be18` — **template safety:** `sanitizeSvgTemplate` at the single install choke point (DOMParser svg root; script/foreignObject dropped; on* handlers stripped; javascript:/data: hrefs dropped; unparsable text installs NOTHING — and `ensureOcarinaTemplate` marks the path consumed on failure so a bad template cannot live-lock the render loop, a regression the fail branch nearly introduced). **innerHTML audit result:** the remaining ~35 uses interpolate parser-constrained chirps (note ids/durations — char-limited by the parser) or the user's own typed text (self-xss only, by Robin's threat model), both title-assignments are engine-escaped; the one data-file→innerHTML path (range warning: manifest type/version + fingerings DISPLAY range) now goes through the new `escHtml`. `tests/svg_sanitized.py` (in CI): hostile template payload driven through a real boot, unparsable-template fallback, poisoned manifest name rendered as text. `🟨 🟡 ⚙M`

- [x] ~~**Print popup `document.write(html)`** — title already HTML-escaped; keep consistent when touching. (ui.js:827-845) `🟢 ⚪ ⚙S`~~ ✅ 2026-09-25 `94f6ddc`

## 4. Performance

- [x] ~~**Per-keystroke full re-render** — `#src` input → `render()` → full parse + `drawTokens` (builds *both* token strips) + `sheet.innerHTML=""` rebuild where every note card clones the whole SVG and loops all holes; fresh mouse listeners per token per keystroke. O(tokens × holes) per character. Debounce input, and/or diff-token rendering, cache cloned SVGs per note. (ui.js:917-922, ui.js:370-716; ocarina.js:11-64)~~ ✅ 2026-09-23 `18e1ef3`+`842d004` — Robin chose "debounce + SVG cache". Typed input now coalesces one render per 200 ms settle (Robin: 60 was machine-short; 200 is the human hush between typed units, so half-parsed bursts never flash; practice-session invalidation still fires immediately; programmatic loads render directly) and ocarinaSVG memoizes its clone output keyed by template-generation · chamber · covered set · big-holes view, invalidated wholesale on every template/fingering install (512-entry cap). Guardrails: `tests/render_pin.py` gained a freshness wait + the debounce contract (red pre-fix), NEW `tests/svg_cache.py` freezes clone coordinates (same-input ⇒ same svg; big-holes view; instrument swap and back; green pre-fix pin). Deeper diff-token rendering remains an idle idea if typing ever feels heavy again. `🟧 🟠 ⚙L`
- [x] ~~**Practice autocorrelation on main thread** — `autoCorrelate` ≈ up to 2M multiply-adds per 66 ms tick plus 9 `fine()` passes → jitter on slow devices during practice. Move to a Worker (buffer transfer) or AudioWorklet. (practice.js:615-709)~~ ✅ 2026-09-23 `08f40e6` — **one detector, one truth**: DSP moved to `js/pitch-dsp.js` (also loaded as a classic script before practice.js); `js/pitch-ac-worker.js` imports it and owns the compute — frames transferred (2048-float copy per tick), results return in a few ms; the practice state machine advances once per consumed frame (spacing stretches only if the worker genuinely falls behind; dt keeps crediting the dispatched cadence). Silent/TEST-provider/below-gate frames complete synchronously exactly as before; pause/stop drop in-flight frames (`acJobs` seq-tagged, never reused); worker failure → bit-identical main-thread fallback forever. Suite hooks: `testAC` stays sync, NEW `testACAsync` (worker path) + `usingWorker()`; NEW `tests/ac_worker.py` (in CI) — worker ≡ sync bit-identical on a 13-tone battery, concurrent pairing, no-worker fallback honest. practice acceptance broke transiently during the split (finishFrame never called its continuation) — restored green (16/5/20 s, same as historical). **Real-DSP validation (§6 T6) still open.** `🟧 🟡 ⚙M`
- [x] ~~**Hundreds of pre-scheduled highlight `setTimeout`s** — one timer per scheduled token, alive up to song length; replace with a shared lookahead list + rAF. (audio.js:2039)~~ ✅ 2026-09-23 `4d9dd9b` — `highlightPlan`: one shared timer/rAF pair fires the whole song's highlight schedule (rAF for batches due inside the frame window; the timer wakes 16 ms ahead of the next item so near-term batches land in-frame). Dropped on stop and pause. `🟨 🟡 ⚙M`
- [x] ~~**Per-note DOM writes during playback** — `highlightToken` runs 2–3 `querySelectorAll` sweeps per token plus `getBoundingClientRect` math; zen glow forces reflow per note (`void panel.offsetWidth`). Cache selectors/positions per render. (ui.js:416-463, ui.js:522)~~ ✅ 2026-09-23 `4d9dd9b` — `tokByI` (both strips) + `cardByI`, string-keyed on data-i, filled at the rebuild seams (drawTokens/fillFullSheet/fillLiveSheet); the two per-note [data-i] sweeps became Map lookups (a string-vs-number key bug on token 0 was caught by the keyboard suite's focus-preview pin — exactly why the pin exists). The scroll-band math keeps its rects (velocity depends on live layout, not cacheable). zen glow reflow stays: it restarts a CSS transition by design. `🟨 🟡 ⚙M`
- [x] ~~**Reverb impulse generated with Math.random on main thread at first bus** — first-load only; fine, just a note. (audio.js:219-230, audio.js:367)~~ ✅ 2026-09-23 — already covered by the README "Accepted by design" paragraph (§2 R9); nothing further to do. `🟢 ⚪ ⚙S`

- [x] ~~**enlargeSmallHoles is O(holes²) per card render** — (ocarina.js:92-110) `🟢 ⚪ ⚙S`~~ ✅ 2026-09-25 `7a580ee`

## 5. Architecture / maintenance

- [x] ~~**Migrate to ES modules**~~ ✅ 2026-09-23 `57de8cb` landed the migration (index.html = one `<script type=module src="js/app.js">`; the import matrix is the real cross-file surface (only 3 cross-module let writes existed — now explicit seams: `setAppCss`/`sharedAudioCtx`/`bumpHoverQuiet`); module-internal names are no longer monkeypatchable, so the suites moved onto intentional seams (`setNoteSink` = full playNoteAt args, `setAuditionSink` = playNote auditions, `setHoverProbe` = dwell-path observer) plus a windowed compat block for page-facing tests; pitch-dsp is shared ESM (page + module-type pitch worker); eslint = sourceType module; html-validate guards index.html structure. **Fully closed 2026-09-23 `28eadd8`:** the 20th suite's stall was the module compat surface, NOT teardown — a classic-script top-level `let` stayed visible to `page.evaluate` via the shared global lexical scope, a module `let` does not; transport leg 4 used bare `audioCtx` → inner promise rejected silently (executor throw → rejected promise, outer never settled) → evaluate waited forever, which read as a `browser.close()` hang. Compat block now mirrors `audioCtx` through a live getter (plain assignment would freeze the lazy `undefined`) + `sharedAudioCtx`; leg reads `audioCtx || sharedAudioCtx()`. Same splice-class casualty restored: `OCA_PRACTICE.usingWorker()` (lost in the practice-history commit) — ac_worker green again. Sweep now 22/22 local. `🟧 🟡 ⚙L`
- [x] ~~**Support voices bypass the cut-bus** — melody docs say every melody-bag voice feeds the cut layer, but `playSupportAt` pushes through a pseudo-bag that fails `isMelodyBag()`, so support/contrabass voices connect straight to the reverb bus and take the legacy click-prone `.value` fade path. Align doc or route support through the cut path. (audio.js:1883-1889, audio.js:453, audio.js:434-441)~~ ✅ 2026-09-23 `9f91eab` — routed: the forwarder bag declares `melodyRoute`, so `isMelodyBag()` sends support voices through the same cut-bus generation + melody stop horizon (collection into melody bag + bass bag untouched). Support suite + transport cut-bus leg green. **Robin's ear-check DONE 2026-09-23: bracket drone auditioned in Zen — "no problems with the support"; clean cuts confirmed by ear. CLOSED.** `🟧 🟡 ⚙M`
- [x] ~~**Additive float-position drift before swing parity test** — `melodyPos += tokenGridBeats(tok)` accumulates; swing parity via `Math.round(pos*2)%2` drifts on long songs. Compare via beat integer instead. (audio.js:2010, audio.js:204)~~ ✅ 2026-09-23 `3bb5bfa` — Robin's "beat integer" instinct: the scheduler now keeps `melodyPos96` — an EXACT integer grid of 96ths of a beat (96 divides every duration parse.js emits: dyadic values, dots, triplets; `Math.round(tokenGridBeats*96)` per token, exact at every step). `swungBeats` reads the integer (`Math.round(pos96/48)%2` = today's half-up rounding semantics, no tolerance). Loop-restart re-grids `gridBeatsBefore` through the same round. Diagnostics: `OCA_DEBUG.melodyPos96()`; NEW `tests/swing_grid.py` (in CI) — live playback of a triplet+half-beat looping melody with swing 33 samples the getter and asserts pure integer grid. Note: the pre-fix drift was ~1e-13/note — the pin is a standing rail (red on the getter's absence, not on astronomical drift), not a behavior flip. `🟨 🟡 ⚙S`
- [x] ~~**Duplicate prompts near-identical markup** — `libPrompt`/`libConfirm` share ~90% structure. (library.js:359-413)~~ ✅ 2026-09-23 `1c82c80` — one `libModal` core builds the card, wires Enter/Escape/buttons and closes exactly once; `libPrompt` keeps its prompt()-shaped semantics (input, empty submit = cancel), `libConfirm` stays a bare true/false ask. Library suite (save/remove dialogs) green. `🟢 ⚪ ⚙S`
- [x] ~~**Dead CSS** — `.melody-field`, `footer.hint`, `.voicing`/`.bodyfill`, `.tab-heading` unreferenced. (app.css:436-484, app.css:591, app.css:929)~~ ✅ 2026-09-22 `57fcf70`
- [x] ~~**Unused `hidden` song flag** — supported by library code but no shipped song uses it; document in README or drop. (library.js:62)~~ ✅ 2026-09-23 `4da683d` — documented per Robin: `"hidden": true` is the WIP carrier — a song stays in the repo (rides every commit) but stays out of the dropdown until "Show hidden songs" is ticked. README paragraph next to the Extending-it note. `🟢 ⚪ ⚙S`
- [x] ~~**No cache-busting on js/css** — script tags without `?v=`; a GH Pages update can serve stale assets. A service worker (see §9 F1) or query-string versions solve it.~~ ✅ 2026-09-23 — Robin's call: leave it for the PWA service worker (§9 F1), which handles caching properly and keeps `?v=` bookkeeping out of the markup. Hot-list note records the deferral. `🟨 🟡 ⚙S`
- [x] ~~**Instrument ids referenced from URL params with no uniqueness check** — `svgWhen.song` matches by id or stem prefix; no id/file-existence validation upstream of use. (app.js:44-49)~~ ✅ 2026-09-23 `3bb5bfa` — boot now reports into `#err` (append-div, fail-soft): a duplicated manifest id ("instruments.json repeats ocarina id(s): …") and an unknown `?inst` id ("Unknown ocarina id 'x' — using the default instrument instead.") both surface naming the offending value while the boot still lands. Test legs appended to `tests/instruments_load.py` (bogus param; duplicated id via routed doctored instruments.json). **Bigger find landed with this:** render() had been textContent-wiping every appended `#err` line each render — the append-vs-overwrite tension between the error net and the true render writer, exposed by the boot diagnostics; render now owns ONE persistent child line (`.err-render`, hidden when empty) and leaves appended divs standing. `🟨 🟡 ⚙S`

- [x] ~~**Deduplicate pitch/maths (4 copies each)** — CLUSTERS 1-3 ✅ 2026-09-24 (`a6b15c0` + `938bc6f`): (1) midi/frequency → `js/music-math.js` single source (audio re-exports the binding so ESM + windowed surfaces stay bound for tests/debug; ui's zen-glow noteMidi wraps it with the 69 fallback; practice's defensive freqOfId duplicate deleted; **parse.js keeps its own midiOf DELIBERATELY** — the transposer skill loads parse.js raw through a window-shim eval that strips exports but cannot carry imports); (2) grid-beats → shared tokenGridBeats, where the two copies had already DIVERGED (audio's fallback lost the 2/3 triplet factor; the parser pre-computes beats so it only bit synthetic durationless tokens — now impossible), practice's gridBeats dies with its three call sites; (3) quarter-seconds → shared quarterSecFor, ui's quarterSec keeps only its editor-reading wrapper. Remaining: PLAY/PAUSE DOM WRITES (audio.js vs ui.js) — last cluster of the item. `🟨 🟠 ⚙M`~~ ✅ 2026-09-25 `504b42d` — the closing cluster turned out to be a deletion, not a move: the four #playMel label writes
  (audio.js, "Play"/"Pause" textContent) aimed at an element that does not exist
  anywhere — the header's text Play square was replaced by the round mirror glyphs
  ages ago, absence pinned by tests/keyboard_widgets.py's squaresGone leg — so all
  four vestigial writes left audio.js, whose transport DOM write goes through
  syncTransport → updateTransportUI alone. Targeted suites green
  (transport_schedule, keyboard_widgets, audio_state, spike_watch) + eslint;
  engine-unobservable (null-guarded) so no red phase existed. M1 fully closed.

- [x] ~~**The twin-era dead tone.json declarations leave the manifest (Robin's file:// preview caught the console noise; his ruling: "I don't want tone.json back - we're gonna dismantle that code path soon")** — the stein + contrabass declared paths whose files never shipped: the two dead lines go, the dynamic allowlists in the boot suites absorb the zero-declared state with no edits (5 instruments, 0 declare tone.json, allowed misses 0); the additive-CODE teardown boards as a §5 item behind the guessed-voices field check (commit `b7ac225`). `🟨 ⚪ ⚙S`~~ ✅ 2026-09-28 `b7ac225`

- [x] ~~**Dismantle the additive/tone.json voice path (Robin's call 2026-09-28: "I don't want tone.json back. We're gonna dismantle that code path soon")** — the additive machinery is dormant since all five instruments declare `twin` (fitted or guessed). The teardown: installToneModel/TONE_MODEL + the tone.json fetch in loadInstrument (app.js) + voiceProfileFor + the V_ANCHORS/wind chain (windPark/warm/rough, air*, edge*, chiff*, ot* — the additive-only debug rows in js/debug.js retire too) + the additive lite voice (the twin has its own lite branch). Known entanglements: tests/twin_support_level uses the additive engine as its red-green comparison leg (rework to a twin-only anchored contract); instruments_load's "tone model install / interpolate / fallback" legs retire with the path; instruments/README.md's voice-swap + tone file-shapes sections rewrite. Order of play: after the guessed voices' field check + any last additive-backed comparisons — the tone.json DECLARATIONS are already gone (2026-09-28, the file:// console-noise unit), only the code remains. Additive is live again on oak, dummy and contrabass (site-matching). Teardown waits until a twin that beats the v45 pair exists for those instruments. `🟨 🟡 ⚙M`~~ ✅ 2026-09-29 `8a7d68d` — Helmholtz-only. Oak/dummy/contrabass share the v45 12-hole twin; missing chamber keys fall back to chamber 1. Additive graph, tone.json load, and additive debug groups are gone.

- [x] ~~**Engine upgrade drawing board (last good = live v45 pair)** — ocarina-practice.com still serves oco-pwa-v45 original Helmholtz + A4–A5 12-hole model (Pages deploy of PR #29 failed). The mid-air voice (4 kHz split, noise_mid_db, RMS-normalized noise) is noisier than that pair; it is parked (git history + ignored research/mid-air-upgrade/). Next attempt: A/B against the live site, ship engine JS and twin JSON as one deploy, bump the helmholtz `?v=` token with the module bytes. `🟧 🔴 ⚙L`~~ ✅ 2026-09-30 `3b6e0e5` — Robin 2026-09-30 closed the drawing board: the v45 pair is the shipping engine and the mid-air upgrade stays parked in git history + research/mid-air-upgrade, re-openable only as one A/B deploy (engine JS + twin JSON together, ?v= bump with the module bytes)

## 6. Tests & CI

- [x] ~~**parse.js edge-case unit tests (pure JS, cheap)** — accidentals/octave shift (Db→Cs logic parse.js:103-107), octave inheritance, `/0`, 10th octave (`C10` silently drops the `0`), `!` normalization (parse.js:8), `withPlayHeaders`/`withTempoLine`/`withTitleAndTempo`, `titleFromText`/`swingFromText`, inline `# tempo` mid-song, triplet/dotted beat math tolerances.~~ ✅ 2026-09-22 `9cdab5d` — `tests/parse_edges.py` (in CI, ~40 assertions). Found + fixed two silent data-loss bugs: multi-digit octave (`C10` became C1 — now no token, digit-boundary `(?!\d)`) and inline `# tempo N` swallowing the rest of its line (scanner rewinds; other comments keep whole-line swallow). Locked gotcha → new TODO item below.
- [x] ~~**Grammar decision: canonical 's' ids as melody text**~~ ✅ 2026-09-22 Robin chose a+b, implemented in `81a906d`:
  - **a** — `s`-form IS melody grammar now (`Cs4` ≡ `C#4`, display normalized to `#`); README row updated.
  - **b** — every unparsable span tokenizes into a visible `bad` chip (typos, `C10`/`C44`, trailing junk, words) instead of silently vanishing. Stray letters stay legal octaveless notes by design (`foo` → `F4` + bad `oo` chip — locked in tests).
  - **bonus (Robin: "only keep r for rest")** — an orphan `-` (no note before it; text start or after a rest) is now its own bad chip, never a silent rest. Bar-crossing ties (`A4/2. | -/2.`) unaffected — verified against ALL shipped song bodies before the change (none use dash-after-rest).
- [x] ~~**Add lint step to CI** — eslint (no unused vars, formatting split-brain like audio.js:1685); optionally `tsc --allowJs --checkJs` with JSDoc types.~~ ✅ 2026-09-23 `62d056d` — flat `eslint.config.js` eslint 9 runs in CI before the suites (setup-node 22, `npx eslint@9 js/`; no node locally, verified only in CI). Rule set: hard-error on unambiguous defect classes, **deliberately no `no-undef`** (classic-script globals ARE the module system), `no-unused-vars` at **warn** with args/caught-errors off — tighten to error after the first run's counts. `🟧 🟠 ⚙S`
- [x] ~~**library.js tests** — save/remove/file load/save, slug collisions (after §1 B1), quota/corruption paths.~~ ✅ 2026-09-22 `43147f5` — `tests/library_hardening.py` (Playwright, in-CI): slug/junk-name ids, uniqueUserId collision + re-save semantics, real save-button flow with two colliding spellings, storage-refusal fail-soft for setUserLib/setShowHidden, corrupt-JSON backup-once-then-reset, non-object-is-corrupt.
- [x] ~~**Instrument-switch regression test** — rapid dropdown swaps ends on installed instrument; plus `?song`/`?zen` boot flows.~~ ✅ 2026-09-24 `75c5f0a` — rapid swaps: `tests/instrument_switch_race.py` since 2026-09-22 `c23f3d8` (the §1 B4 guard suite); boot flows: two new legs in `tests/instruments_load.py` — bare `?song=eponas-song` boots the arrangement on the manifest default and must stay GRID, quiet of zen; `?song=eponas-song&zen&nofs=1` must land in the pinned CSS-fallback zen with the single view armed — both asserting the loaded title, the `#src` body head, zero `.card.oor` on the 12-hole and exactly one checked mode radio (the paths the landing stubs and shared zen links ride). `🟨 🟡 ⚙M`
- [x] ~~**Audio scheduler/cut-bus tests** — scheduleMelody timing, cut-bus behavior parity melody-vs-support, Lite voice.~~ ✅ 2026-09-23 `2326c5b` — `tests/transport_schedule.py` (in CI): onset gaps == the swung 96th-grid arithmetic recomputed OUTSIDE the scheduler from lastTokens (inline `# tempo` switches included), staccato/tie durations exact, end-of-song auto-stop, loop wraps replay identical pitch/duration classes, cut-bus lifecycle (bus generation during play → retire-on-stop within the decay horizon → fresh generation on instant replay → no zombies for support brackets), Lite voice builds strictly fewer oscillators (createOscillator counting around playNote). Diagnostics: `OCA_DEBUG.melodyAlive()/busAudit()`. Unblocked M3 (same code) and the ES-modules migration. This suite also caught a real boot-tail race early (home song re-render clobbering typed src) — probes wait for their own title now. `🟨 🟡 ⚙L`

Currently covered (don't lose this): practice acceptance (4 cases strict+closed-loop), practice dip gate (hold-through blocked, silence/50%-notch dips pass, 75% duck shut, legato free), practice seat across view rebuilds + zen-entry stopMelody + overlay zen-only seats, console-hygiene boot scan (4 boots; allowlist = manifest-declared tone misses), support-bracket battery incl. bit-identical melody-vs-support equivalence + Zen timing/gating, instrument load/tone-model install per manifest (incl. svgWhen id/title paths + boot diagnostics in per-leg fresh contexts), render pin (chips/grid/scroll-band/highlight/focus-restore + typed-render debounce contract), svg clone coordinates, debug panel build-on-open contract, transport scheduler arithmetic/cut-bus/lite, practice history, template safety, theme toggle, offline SW boot+swap, ac worker parity, swing grid, sr hints, spike watch (the tick hunt). CI = push/PR/manual, explicitly not a deploy gate. (.github/workflows/practice-tests.yml — console-hygiene + 24 suite steps + eslint + html-validate; local run-all counted 25 green on 2026-09-23 on the Linux partition and again on the Windows partition — partition sweep red 24/25 until the runner's UTF-8 child-env fix, see session log ~2026-09-23) NOTE: practice_accepts flaked ONE strict case under full-sweep load 2026-09-23, green twice standalone afterward and in the diag run — watch it, the arbiter hardening already took one such race; support_accepts flaked the same class 2026-09-24 (fixed wall-clock read window vs audio-clock lag under sweep CPU contention) and got the class cure: the read is now a real rendezvous with wall-fire stamps + ctx snapshots `335c4b4`)

- [x] ~~**CI job title "practice accepts the play output" is a fossil** — the workflow's job name predates the 30-suite reality (the job runs the whole battery now); Robin calls it clearly outdated (2026-09-25). Rename to something honest for the modern shape in practice-tests.yml (no UI/Behavior impact; run-record cosmetics only). `🟢 ⚪ ⚙S`~~ ✅ 2026-09-25 `ee4e2ec` — Renamed in practice-tests.yml to "the practice battery (suites + lint)"; the header comment above the trigger describes the modern shape (hygiene scan + full suite set + lint pair) instead of the play-output suite.

- [x] ~~**General readability (contrast) sweep — "a general test of readability of every component"** — Robin, 2026-09-25, prompted by a visible HiFi problem; wanted a general non-roster detector. `🟨 🟡 ⚙M`~~ ✅ 2026-09-25 `a529fd0` — tests/readability.py (in CI): a full-DOM scanner, not a roster — per look (plain/hyrule/hifi) and per state (base with collapsed blocks opened, floating tuner, zen, zen+tuner in-card, theme menu, help overlay, library dropdown, save dialog, audio performance pop, ?debug=1 panel) it walks every visible element that paints its own text or a button glyph, composites the real background chain (rgba stops blended), and holds WCAG 4.5/3.0 by size. Every state must MEASURE something (pass-by-nothing fails loudly — the class Robin caught with the song-library miss). The scanner found and the same commit fixed: the HiFi light-sheet internals, a HYRULE theme-menu class, the piano now-key label, --token-pause, and the Hyrule dbg heading. Note field for the next session: state minimums are distinct-path caps (35 base / 12 zen / small popups) — re-tune if a state's content changes.

- [x] ~~**Suite servers print BrokenPipeError tracebacks into CI logs (the IDEAS CI paste, pruned; run `36187303217` job `108243773139`, pr 15 — passed anyway)** — browser teardown mid-GET races `copyfileobj` inside the suite-facing ThreadingHTTPServer (e.g. tests/instruments_load.py:30); the suites themselves pass, so the console noise is the defect: quiet the expected-teardown class in the suite-server pattern without hiding real failures. `🟨 🟠 ⚙S`~~ ✅ 2026-09-26 `c40991e` — landed 2026-09-25 (session 15 `c40991e`): the byte-identical server block in 34 suites became one hardened place (tests/suite_server.py — handle_error swallows only the ConnectionError family, real handler failures stay loud), every suite imports start_server, gen_pages borrows the hardened server for its staged mounts; tests/suite_hardened.py pins both directions red-first; 42/42 sweep green after the migration.

- [x] ~~**Real-DSP validation for autoCorrelate** — CI uses synthetic frames only; record WAV fixtures and run the classifier offline against known pitches (`OCA_PRACTICE.testAC` already hooks it, practice.js:1218-1232). `🟨 ⚪ ⚙M`~~ ✅ 2026-09-26 — Robin 2026-09-26: "So remove DSP from TODO" — the tone synthesis work is bespoke and will keep moving as his measurement data grows (he may even drop very-low-dB-contribution harmonics); test-validating a moving hand-tuned engine contradicts its point. Re-opens only on his word.

- [x] ~~**debug.js coverage** — nothing tested; low value. `🟢 ⚪`~~ ✅ 2026-09-26 — Robin 2026-09-26 (leaning "as-is?"): debug.js stays untested by election — a debug-only tool whose coverage never was worth a suite; the console-hygiene boot scan already covers its assembly contract on the shipped surface.

## 7. Accessibility & UX

- [x] ~~**Piano keys are click-only `<div>`s** — no button semantics, no keyboard, no aria-label (title attr only). Make them buttons with aria-labels + keyboard. (ui.js:770-799)~~ ✅ 2026-09-22 `3094ad7` — role=button + aria-labels + roving tabindex (one tab stop), arrows (L/R chromatic, U/D octave, Home/End), Enter/Space audition; clicks move the anchor. Kept as styled `div`s with role=button (zero CSS/theme risk vs real `<button>`s). `tests/keyboard_widgets.py` in CI.
- [x] ~~**Token chips are mouse-only spans** — `mouseenter`+`click` but no tabindex/role/keyboard path; hovering to hear a note is inaccessible to keyboard and touch users. Long-press listen for touch. (ui.js:623-690)~~ ✅ 2026-09-22 `3094ad7` — role=button + aria-labels, roving tabindex per strip + focus restore on rebuild, arrows/Home/End, Enter/Space = play-from-here, silent highlight-preview on keyboard focus; touch long-see split out as its own item above. `tests/keyboard_widgets.py` in CI.
- [x] ~~**Mode segment needs roving tabindex** — all `role="radio"` buttons tabbable instead of one. (index.html:98-102)~~ ✅ 2026-09-22 `6cc812c` — one tab stop follows the checked mode (markup seeds it), arrows move focus AND selection with wrap, Home/End supported, tab stop follows clicks; probe in `tests/keyboard_widgets.py` (test part landed with the `812b25f` amend).
- [x] ~~**prefers-reduced-motion only covers zen halo** — gate token pulse, zen wave, toasts too. (app.css:906-915)~~ ✅ 2026-09-22 `a130f88` — gate block moved to file end (later-position tie would have lost otherwise); range-warn + perf-alert pulses die, zen wave keeps opacity-only fade (new reduce keyframes), focus-token swell/transition freeze. Toasts诊 have no motion (nothing to gate). NEW `tests/reduced_motion.py` (in CI): probes identical class-chain stand-ins in BOTH emulated modes so selector rot can't pass silently.
- [x] ~~**title-only tooltips** — several affordances exist only as `title` (e.g. "click = play from here"); invisible to touch/AT. Add visible hints or aria-describedby. (ui.js:626)~~ ✅ 2026-09-23 `3bb5bfa` — one shared `#sr-gesture-hints` block (index.html, `.sr-only` style in app.css) named by `aria-describedby` from every activatable token chip (roles + junk pills) and every playable piano key (white + black); text covers tap-vs-hold on touch, right-click add, and the fix-or-remove instruction. Bonus AT fix in the same pass: out-of-range chips wear a real label now — "Play from B3 — below this ocarina's range (…), the note itself can't be played" — instead of the RANGE being title-only. Titles stay for desktop hover. NEW `tests/sr_hints.py` (in CI). `🟨 🟡 ⚙S`

- [x] ~~**Info screen links the GitHub issues page** — Robin, IDEAS 2026-09-25: add a link to https://github.com/tribbin/Ocarina-Practice/issues on the info/help screen so users can report problems. Static link, no behavior; render/sr pins updated where they enumerate that screen. `🟢 🟡 ⚙S`~~ ✅ 2026-09-25 `720373e` — shipped with the landed-crawler lifts in the same `720373e` (session6, PR #12): the help dialog's .help-meta colophon carries the GitHub issues link (target=_blank rel=noopener); no render/sr pin enumerates the help screen, so none needed the update the item anticipated

- [x] ~~**The playback swing dial lives under practice's silent-dials contract (`.dial-off`) like the tempo dial** — Robin, live 2026-09-25: on the main site the swing slider was 'not disabled like tempo' during practice; the cause is that the idea never became code (commit `1766fad` was Robin planting the IDEAS line, not an implementation — the IDEAS-cleanup record had wrongly counted it shipped). Fix: the swing row joins the playback-only dim family (opacity .18 + pointer-events none via ui.js updateTransportUI, beside tempo/focus-tempo), red→green `b86ddf3` with tests/practice_dials.py pinning engage-inert/disengage-restore/re-engage; sw VERSION → oco-pwa-v14. `🟨 🟠 ⚙S`~~ ✅ 2026-09-25 `b86ddf3` — red first, landed with the dim-family toggle; his phone eyeball after merge+deploy is the deciding pass per the field-check class — the wake-lock play+practice hold was separately CONFIRMED live the same day

- [x] ~~**Collapse buttons + misc** — §1 B7 was completed long ago; see `plans/DONE.md` §1 for what it covered and pick the misc remainder on touch. `🟢 🟡 ⚙S`~~ ✅ 2026-09-26 — Robin 2026-09-26: "I do not understand the item." — it traced to the long-shipped B7 collapse work plus a vague touch remainder; dropped as incomprehensible. If the concern resurfaces Robin re-plants it. (The item was: whether the collapsing section buttons needed a touch pass.)

- [x] ~~**Token chips: long-press-to-listen on touch** ✅ 2026-09-22 `ab4ce0c` — hold rides the SAME 260 ms dwell as mouse/keyboard (`hoverPreview`): touch-down highlights, planted dwell auditions (once), completed hold swallows the follow-up tap (no transport start), quick taps keep native play-from-here, drift/pinch cancels silently. Pressing keeps `-webkit-touch-callout`/selection off. Pinned in `tests/keyboard_widgets.py` (touch section, playNote-call oracle — voice counts inflate from lingering nodes). Robin's feel-check on a real device still open. `🟨 🟠 ⚙S`~~ ✅ 2026-09-26 — Robin 2026-09-26 (panel): "All good" over the standing feel stack (chips, tuner close glyph, history line; HiFi knobs covered by the new retune list) — the hold clears.

- [x] ~~**Zen note bar lags on small vertical screens (field-planted in IDEAS, now pruned)** — the note bar moves too slowly toward center as a note highlights and even leaves the screen partially (phone, vertical screen, session night: Robin planted 2026-09-25 `985942e`). Session-15 unit: INVESTIGATED + BUILT 2026-09-25 `b15d2ce` — the seat was the browser-native smooth scroll (UA animation ~200 ms/step, ~500 ms/jump, restarted mid-flight per note → the bar trails; throttled headless measured it and reproduced the 655 px trail); scrollFocusStripTo now glides with the sheet's bounded rAF contract (≤160 ms eased, far jumps snap, wheel grab cancels), pinned by tests/zen_notebar.py (CI-registered, five legs), app-path after-measure 67 ms / ~0 px trail; sw v21. **HELD for Robin's phone field check** — the deciding pass; he retunes the glide feel if the 160 ms bound reads too quick/markety on the OLED. `🟧 🟠 ⚙M`~~ ✅ 2026-09-26 — Robin 2026-09-26 (panel): KEEP the 160 ms bound as built — his pre-call on the glide feel; the phone still decodes, and the seat is measured. Done.

- [x] ~~**HiFi/theme retune batch (Robin 2026-09-26)** — dark-amber ghost buttons: `#160a04` off / `#56300d` on, plus always a thin white outline around them when off (his values, "apply using own insight"); the Grid|Scroll|Single segment and the instrument dropdown must NOT have white backgrounds; zen red darker with white text; the tuner's separated LEDs must keep their discrete illusion — the fill stops gliding between steps. Shipped themes carry the LED/zen/segment parts; HiFi carries the amber buttons. `🟨 🟠 ⚙S`~~ ✅ 2026-09-26 `33fc135` — SHIPPED 2026-09-26 (session 15 `33fc135`): the amber chrome family (#160a04/#56300d + white resting line), the segment row + instrument select de-whitened, the zen CTA reads #b32317 with white text, and the LED rows quantize fills to the 10px grid through one fill-width seam (transition killed under hifi only). tests/hifi_retune.py pins both sides of the theme flip; the .1s glide stays on the plain. css-v2, sw v22.

- [x] ~~**Field-check the game arrangement (Audible-behavior hold — Robin's ears decide)** — the Outset corpus is now ONE version: `outset-island-midi` = "Outset Island (arrangement)" (melody + `#track bass audible 50` + the derived `#track contrabass audible 75`; the with-bass trio, its up12 twin and the bassline solo retired before deploy); his pass names: the plain-view balance (bass/contra levels vs the melody at 50/75), the contra register choice (the game sub-bass +12 reading), the ♭ chord labels in the sheet's caps styling, the loop seam (the closing vamp into the opening one), and whether the layers stay audible INSIDE an active practice session (today they play; the tuner-deafening worry stands). `🟧 🔴 ⚙S`~~ ✅ 2026-09-30 `2dbab7a` — Robin field-checked 2026-09-30 and cleared the trio: bass/contrabass balance, the contrabass register, the flat chord labels, the loop seam and in-practice audibility all accepted

- [x] ~~**Theme no-flash: apply the saved theme pre-paint (IDEAS: skip default CSS)** — the index.html head script only honors ?oot; the saved oco-theme (localStorage) applies late in js/app.js so the default theme flashes on every load; resolve param > localStorage > default in the pre-paint head script and pin the early data-theme. `🟨 🟠 ⚙S`~~ ✅ 2026-09-30 `f84b564`

## 8. Housekeeping

- [x] ~~**Favicon + meta description + theme-color missing** in index.html.~~ ✅ 2026-09-22 `9cfccfb` — favicon.svg (ocarina glyph, app palette) + link + meta description + theme-color.
- [x] ~~**hyrule.jpg is 609 KB** for one theme — serve WebP/AVIF or lazy-load. (css/app.css:98)~~ ✅ 2026-09-22 `09efb80` — 1280w WebP q80 = 90 KB (–85%); the theme's `blur(2px)` hides the upscale on big viewports; jpg deleted (single CSS reference).
- [x] ~~**Debug panel DOM created on every page load** even when never shown — lazy-create on `?debug=1`/first open. (debug.js:118-140)~~ ✅ 2026-09-23 `1058657` — whole panel build (skeleton, drag wiring, buttons, slider groups, footer) moved into `buildPanel()`, called on first open only; module-level listeners (resize, zen relocation) guard a null panel. Red→green via NEW `tests/debug_panel.py` (plain visit has no `#dbgPanel`; DEBUG=1/?debug=1 build+open; DEBUG=0 hides). `🟢 ⚪ ⚙S`
- [x] ~~**Debug naming inconsistency** — `OCA_DEBUG` / `OCO_DEBUG` / `DEBUG` setters coexist. (debug.js:481-500)~~ ✅ 2026-09-23 `1058657` — **OCA_DEBUG is the one public handle** (Robin's pick); the `window.OCO_DEBUG = api` alias and its header mention are retired; the `DEBUG=1/0` console knob stays (that's the documented UX). Pinned in `tests/debug_panel.py`. `🟢 ⚪ ⚙S`
- [x] ~~**tests/\_\_pycache\_\_ on disk** — gitignored; rm locally.~~ ✅ 2026-09-23 — removed (and re-removed after the suite run). `🟢 ⚪ ⚙S`
- [x] ~~**window.onerror pre-dates render()/boot() use of `#err`** — conceptual conflict; resolve when touching §2 R3. (app.js:1-4)~~ ✅ 2026-09-22 `4f065b3` — resolved together with §2 R3 (append-not-overwrite).

- [x] ~~**Board tool allegedly accumulates empty lines in TODO/DONE (the IDEAS report, now pruned)** — verify first (full file scans + verify's lint), fix red-first in tools/board.py + tests/board_tool.py if real, otherwise record "not real" with the evidence in a completion note. `🟨 🟠 ⚙S`~~ ✅ 2026-09-25 `a566a0e` — verified REAL 2026-09-25 (session 15 `a566a0e`): _insert_line stacked one blank per move beside an item trailing blank — 11-blank runs stood in the live TODO; the sandbox leg showed a 4-blank run after three adds. Fixed: writes collapse runs (self-healing), verify lint names any run on both files, the live board normalized once (whitespace-only), board_tool 12/12.

## 9. Functional ideas (features)

- [x] ~~**Offline/PWA** — service worker + manifest so the practice tool works with no connection (matches offline nature of sheet usage); also fixes cache-busting (§5).~~ ✅ 2026-09-23 `54d1832` — Robin picked this off the refreshed hot list. `sw.js` (root, classic): CORE shell hand-listed + per-instrument files DERIVED from instruments.json at install (fingerings/svg/all svgWhen svgs; tone best-effort, 404 = "no recordings yet"); only res.ok responses ever enter the cache. Nav = network-first (cached-shell fallback offline); rest = stale-while-revalidate with background refresh (deployed updates live on the 2nd visit); skipWaiting+claim; VERSION bump is the manual old-cache flush. Manifest (`start_url./`, standalone) + generated 192/512 icons from favicon.svg (playwright raster) + apple-touch-icon; registration best-effort from app.js on load. Cache-busting (§5) IS this now — the deferral resolved. `tests/offline_pwa.py` (in CI): offline reload boot + offline instrument swap. Bonus: instruments_load svgWhen leg was racing the boot tail (probe hit between fingerings install and library fill) — suite-side wait added. **Robin's eyeball pass still open: install prompt + airplane-mode run on a real device.** `🟢 🟠 ⚙M`
- [x] ~~**Section looping** — loop bars N–M instead of whole song only; drill a tricky phrase.~~ ❌ **DECLINED 2026-09-24** (Robin: "I don't think I want loops, but keep them in if I change my mind later" — kept so a future revival starts from this note instead of a redesign; the pipe-through-the-scheduler sketch above survives with it). `🟢 ⚪ ⚙M`
- [x] ~~**Practice history / progress tracking** — persist per-song accuracy & cent-deviation history in localStorage; small progress view.~~ ✅ 2026-09-23 `177e9ff` — completed-run records {ts, wipes, mean-cents, sec} per song key, guarded localStorage (library id, else body hash; last 24), tuner panel one-line summary refreshed at engage/completion, `OCA_PRACTICE.history()`. `tests/practice_history.py` (in CI) drives two full synthetic runs. 🟢 🟠 ⚙M
- [x] ~~**Theme toggle** — dark/light/OoT switch instead of only `?oot` URL param.~~ ✅ 2026-09-23 `077a432` — Hyrule/classic-light flip beside Clear, persisted under `oco-theme`, chrome-color hint repainted from live body background, re-render so svgWhen rules re-resolve; `?plain`/`?oot` keep outranking the saved choice (a detour never rewrites saved state). `tests/theme_toggle.py` (in CI). `🟢 🟠 ⚙S`
- [x] ~~**Generated scales Dropdown: location and order** — lifted from IDEAS 2026-09-24 (BUG: "Scales should be on top of list; first C-major and then chromatic").~~ ✅ 2026-09-24 `bee525c` — the whole Scales group opens the dropdown (above every song group and My songs), C major pinned before Chromatic inside it regardless of synthesis key order; red→green leg in `tests/library_hardening.py`; the custom libDd menu inherits the order (it mirrors the select's children). `🟨 🟠 ⚙S`
- [x] ~~**Keyboard-shortcut help overlay** — Space is global but undocumented; list shortcuts.~~ ✅ 2026-09-23 `f2ba16e` — `?` ghost button + `?` key (never while typing) open a paper-card dialog of every gesture/key (Space pause/continue, Enter, arrows, Home/End, right-click add, tap-vs-hold), aria-modal frame, focus to close and back to opener on ✕/backdrop/Escape. `tests/sr_hints.py` pins all four paths. `🟢 🟠 ⚙S`

- [x] ~~**Instrument switch auto-selects the same song in range** — when switching ocarinas manually, look up the current song's family variants and jump to the one that fits the new chart — the same ladder walk the landing stubs use (best-fit 12-hole > double alto > triple bass > contrabass); if nothing fits, keep the current song and stay quiet; no transport start from a wet switch. Lifted from IDEAS (OTHERS) 2026-09-24, Robin approves the build. Pin in `tests/instruments_load.py` or the library suite: switch with a song loaded, land on the fitting family member, dropdown reflects it. `🟨 🟠 ⚙S`~~ ✅ 2026-09-25 `4ddeb1f`

- [x] ~~**Phone wake-lock during play/practice** — Robin, IDEAS bugs line: telephones go to sleep mode during play; keep the screen active the way a video player does — practicing is the case that hurts. `🟨 🟠 ⚙S`~~ ✅ 2026-09-25 `e375203` — js/wakelock.js (one screen sentinel behind a Set of reasons "melody"/"practice", re-acquire on return to visibility, silent on unsupported) + audio.js seams (play/stop/pause/resume) + practice.js seams (engage, pauseToggle, re-anchor, standby, un-press). tests/wake_lock.py drives the REAL module through the setWakeLockSource seam (setNoteSink pattern — navigator.wakeLock is a readonly WebIDL getter no script can shadow; proven three probes deep) and pins: engage/play hold, disengage/pause drop, swap play releases practice then holds melody, hidden+system-release keeps wanting and re-request on visible, bare boot with the real API (headless denies with NotAllowedError) stays console-clean. sw VERSION → oco-pwa-v8. FIELD CHECK FOR ROBIN: his phone must stay awake through play and practice; emulated-leg reds only.

- [x] ~~**Practice layout pair: tuner close button + mic-icon practice button** — Robin, IDEAS LAYOUT: "Add close-button top-right of the (non-Zen mode) practice/tuner to un-press the practice" + "inform the user through a microphone icon in the blue button, instead of the note". `🟢 🟡 ⚙S`~~ ✅ 2026-09-25 `b106cba` — .prac-close on the floating tuner (stopPractice full un-press; hidden on zen's in-card strip), row1 reserves the corner under the ✕ for the status prose/engine glyph (Robin live-tested the overlap mid-session — fixed at 30px reservation); ♪ retired on BOTH transports (#mirrorPractice, #practiceFocusBtn) for the g-mic svg, titles/aria kept. tests/practice_close.py (red→green, CI-registered): one ✕ per floating tuner, close un-presses + hides + un-presses aria, re-engage carries one ✕ again, both buttons mic-glyph/no-text/title kept. sw VERSION → oco-pwa-v9. FIELD CHECK: Robin confirmed close works; the glyph look (and the ✕ placement after the fix) awaits his next eyeball.

- [x] ~~**HiFi theme (the 80s black audio-stack) + theme switcher menu** — Robin, IDEAS THEMES 2026-09-25: "Additional 80s black audio-stack with square-row LED displays. The red understripe for headers can remain the same as other." + "Switching between themes in a way that signifies the color theme without showing it in the current theme during normal usage." Named "HiFi" (code hifi) by Robin at the batch. `🟨 🟡 ⚙M`~~ ✅ 2026-09-25 `bccb4f8` — FIRST PASS LANDED, retunable by design: theme combo now a menu (button opens a neutral popover listing Plain/Hyrule/HiFi in one uniform ink — Escape/outside/pick close; picks apply+persist "oco-theme"+re-render); themeBtn reads the ACTIVE look still. HiFi = data-theme="hifi": black chassis tokens, LED-amber mono dial numerals, square-segment LED rows on the tuner scale/track/fill, red header understripe untouched, chamber/token symbology untouched, ?hifi param outranks saved. theme_toggle.py rewritten for the menu contract (red→green, CI step exists). sw VERSION → oco-pwa-v10. FIELD CHECK FOR ROBIN: the whole look is his to retune — LED colors, chassis shades, row geometry are first-pass guesses; the "square-row" idiom currently shows on the practice tuner's meters only (perf-pop meters and the stats line stay token-styled for now). **FOLLOWUP same day `a529fd0`:** Robin live-verified the chassis-paint shape, then the general readability scan (§6, the song-library and "there's more" pushes) found the light-sheet internals the first pass inverted — the shape that stayed: paper/ink plain, chassis painted per-surface (the OoT pattern); menu ink per face (light on the dark menu, dark on the selected paper strip), light card face + dur, dark kbd ink, zen button dark on the LED red, --key-now-label token, --token-pause one step darker (4.5 bar), Hyrule dbg heading green; sw VERSION → oco-pwa-v12. **STEERED HIDDEN same day (`4c4456c`, sw v13):** Robin: branch close but not merge-ready yet ("minor issues and subjective problems we'll correct later") — the HiFi theme goes hidden until finished: the menu lists only Plain/Hyrule, and ?hifi explores it exactly like the old ?oot hidden era; saved hifi choices still rule; theme_toggle rewritten for the hidden contract.

- [x] ~~**Landed-crawler URL semantics: leaving a stub path never plays different content under it** — Robin, IDEAS 2026-09-25 (verbatim intent): when a user lands on a `/song/…` page via search and then switches song or instrument (or otherwise loads different content), the URL must "refer to the root of the domain with the ? GET vars" — `/?song=<key>&inst=<id>` (or bare `/?` when nothing library-identifiable is loaded) — "as you don't want someone to play a different song under a specific path". The landing page's OWN seed keeps its clean path (that is the canonical for that song); only SUBSEQUENT switches move to the root. Also: "make clicking the site title direct to the entry-point of the domain" — the header title becomes a plain link to `/` (its href must carry the serving prefix / stay relative so the artifact stays mount-agnostic). Touches only history.replaceState + header markup; no audio, no editor semantics; gen_pages boot legs gain the switch-assert (switch → URL becomes root+query, and the SW-era deep-link tests already cover the ?var side). `🟨 🟠 ⚙S`~~ ✅ 2026-09-25 `720373e` — shipped in `720373e` on session6 (merged via PR #12): later warm switches resolve to the site root with ?song=&inst= (root read off the pathname, mount-agnostic), typed/cleared/file loads go to bare root after the dropdown drops, boot deep-links stay gated behind markUrlLanded forever, the site title is `header h1 > a[href='./']` under the <base>; gen_pages pins seed-path/title-anchor/switch-root+vars/typed-bare-root on all 8 stub boots; sw VERSION → oco-pwa-v7, superseded by the session12 v13 chain

- [x] ~~**Deduplicate octave/transpose-twinned song bodies (survey first)** — Robin: "Deduplicating songs (that only differ in octave/transpose) would be a nice touch." FIRST step is tooling only (his MIDI-boundary rule: no song-data work unsupervised): a `tools/` audit that proves which songs.json variants are exact octave shifts of one another (the dummy↔stein +12 pair is the precedent — see skills/song-transposing). Report the twin classes + per-class divergence spots; then decide WITH Robin whether variants keep hand-written bodies or derive from a base body at load (keys/URLs MUST stay frozen either way — the permalink contract). ﻿Night survey 2026-09-25 (tools/audit_twins.py `33bd3fa`, report-only, no bodies touched): **5 octave twins** â€” song-of-time/-bass, song-of-storms/-bass, sarias-song/-bass, eponas-song/-bass (every -bass arrangement is its alto base's melody one octave DOWN, modulo nothing: barlines, rests, continuations, slides, durations and accents all carried over) and botw-theme/-down3 (also -12). **3 uniform non-octave twins** â€” concerning-hobbits-short/-c (shift -2), botw-theme/-bass (shift -9), botw-theme-bass/-down3 (shift -3; the two bass arrangements are a uniform -3 apart). **No other twins**: all cross pairs are NOT-ALIGNED (different token counts), and kokiri-forest-bass refuses every verdict until its stray lowercase `g4/4` token is resolved (tool refuses on unreadable shapes by construction). So: the four -bass bodies and botw's -down3 are PROVEN derivable-at-load candidates (keys/URLs stay frozen either way per the permalink contract); the three non-octave twins are shift-derivable too; kokiri is a potential fifth body once its stray token is explained â€” that one needs Robin's eyes before any claim. Kokiri held verdict resolved 2026-09-25 at 098115d: the stray lowercase g4/4 was a typo (parse.js uppercases note letters — it played identically all along); the audit now runs refusal-free across all 15 shipped songs and kokiri-forest is NOT-ALIGNED against everything (the renamed leaf is no twin), so the census stands at 8 proven twins. Robin calls 2026-09-25: DERIVE ALL 8 at load (five octave twins + three uniform non-octave shifts), keys/URLs frozen; transpose fork resolves TOKEN-LEVEL (editor text untouched, display/playback shifted). Remaining: the at-load derivation build. `🟨 🟡 ⚙M`~~ ✅ 2026-09-25 `eee3bbe` — Dedup SHIPPED 2026-09-25 eee3bbe — Robin's batch answers became the final census: 5 derives records ship (song-of-time-bass, song-of-storms-bass, sarias-song-bass all -12; botw-theme-down3 -12; concerning-hobbits-short-c -2), folded at load byte-equal by tests/twin_derive.py fixtures; the byte-identity test drove the theory discovery — octave shifts CARRY the base letter (Bb5→Bb4) because eponas mixes flat- and sharp-side spellings per section — so the flats flag died; HELD hand-written: botw-theme-bass (key-name labels + line split) and eponas-song-bass (A2 label), both Robin's calls; kokiri is no twin. The audit now prints provenance lines and keeps the 5+3 census refusal-free. 

- [x] ~~**Intended-instrument per-song landing default** — Robin, IDEAS 2026-09-25: "Some songs are really not made for the alto, but were added because not many people have a bass ocarina." — `songs.json` may declare `"intended": "<instrument-id>"` on a base song; the landing seed then prefers that instrument over Robin's ladder WHEN any family member fits its chart, falling back to the ladder otherwise (a member of the family must fit: the seed never boots a dead display). SHIPPED exemplar 2026-09-25: botw-theme → ico-oak-leaf-bass-c-triple (members -bass/-down3 fit the triple; the alto base won the ladder order today; the live /song/zelda/botw-theme/ stub now seeds the bass body on the triple after merge+deploy). The data_validator owns the field (optional, string, manifest-known — sandbox v12); the gen_pages botw pin freezes the outcome (want (botw-theme-bass, triple)). REMAINING: per-song values are Robin's musical calls to plant over time — nothing else declared yet; the field changes nothing in-app (the picker stays free, the wet-switch auto-select ignores it). Robin settles the model (2026-09-25, live): BOTH instrument-tagged versions keep existing as entries (the alto-named base is the alto version; -bass named "(bass)" stays — the deletion proposal is declined), and the user lands on the intended instrument — WHEN the base declares it — via the NON-SPECIFIC (clean) URL: the base's own body needs no fit; the first family member (base first, then variants alphabetically) that fits the intended chart is the seed. No field → the ladder rules. The clean page's og/title reads the LANDED version's name (what actually plays). Do not rekey entries for this; do not strip the parenthetical tags; the field's semantics is the family walk, never a body rewrite. Second exemplar per Robin's live call (2026-09-25): the corpus had NO kokiri-forest base — the bass-c transcription sat on the leaf key kokiri-forest-bass with its own stub URL. Robin wants the non-specific URL to exist and land the bass version: the key was re-titled kokiri-forest-bass → kokiri-forest (byte-identical body; name "Kokiri Forest (bass)" — Robin explicitly kept the committed tag naming for the entry; group/tempo untouched; introduced "intended": ico-oak-leaf-bass-c-triple) so /song/zelda/kokiri-forest/ is the canonical landing — the old kokiri-forest-bass URL retires in the trial period (nothing indexed; the sitemap/stub set stays 8, the kokiri path becomes the clean one). The only kokiri reference outside data was the SKILL.md leaf example, updated in place. BotW semantics ruling stands (versions keep their keys; only the non-specific URL moves). `🟢 ⚪ ⚙S`~~ ✅ 2026-09-26 — Robin 2026-09-26: "Per song when I feel like it. Move to done." — semantics shipped (family walk + fallback + validator) and botw-theme exemplar live; new declarations ride his per-song calls, no session blocks on it.

- [x] ~~**SEO guides application pass** — Robin IDEAS 2026-09-25: "Read this and apply where appropriate" — https://support.google.com/webmasters/answer/9128669 and https://developers.google.com/search/docs/fundamentals/seo-starter-guide. Opener = read-then-audit against the artifact (robots.txt/sitemap.xml/song stubs/og tabs already serving; the sitemap set is now frozen-permanent, the domain Search-Console-verified), reporting what applies (title/meta/OG policy, structured data, internal linking, crawl directives) — DONE 2026-09-25 session 14 as a report (the artifact already meets most of the guides; candidates: shell rel=canonical, JSON-LD variants, stub cross-links). Robin's picks LANDED 2026-09-25 `8370dd7` (session 15 unit 1): shell rel=canonical `/` + one WebApplication JSON-LD (EducationalApplication / OS "Any" / browserRequirements / free Offer, description verbatim from the meta); build_stub strips both from stubs (one canonical per page, zero per-stub JSON-LD), pinned by tests/seo_shell.py (CI-registered); sw v20. Not elected today: per-stub JSON-LD, cross-links, Breadcrumb/MusicComposition variants. `🟨 🟠 ⚙M`~~ ✅ 2026-09-26 — Robin 2026-09-26: "Keep song data for crawlers per-song." — already the case (every stub serves its own title/description/OG set + canonical, session 15 pinned one-canonical-zero-JSON-LD); Breadcrumb/MusicComposition stay unelected. Done.

- [x] ~~**URL always reflects selection — discussion (the IDEAS discussion line, now pruned)** — the shipped rewriter (`ff53abb`) already moves every later content change to root+vars; the discussion residuals: typed text (bare root), user-saved songs, whether ANY non-library state belongs in the URL; REPORT-ONLY audit, Robin picks any extension. Handed for a hands-on session. Reported 2026-09-25 (session 15, report-only): the rewriter covers the library truth completely now — boot keeps its landing path; builtin AND user-saved picks land on root+?song=&inst= (a user id degrades to the fallback load cross-device, faithful in-session); instrument switches refresh the vars in place; typed/Clear/file-load leave bare root and typed text autosaves NOWHERE (session-only — bare root says so honestly). Non-library state (display mode, zen, tempo/swing/tick, practice, perf) stays OUT of the URL by design: identity + theme extras ride along, shareability is the contract. Extensions (a typed-text seed param, content-hash song URLs) are picks for Robin if ever wanted — the full audit table is in the session-15 log. `🟢 ⚪ ⚙S`~~ ✅ 2026-09-26 — Robin 2026-09-26: "Decline (Recommended)" — the URL keeps its identity+theme contract (root+?song=&inst= on library loads, bare root on typed text, theme extras ride); no seed param, no content-hash URLs.

- [x] ~~**Waveform pre-cache for songs + deploy minify/SVG-generation (the IDEAS perf block, now pruned)** — pre-calculate note waveforms per song with a progress bar and stop-on-playback (the pre-cache exists to prevent playback-time strain); GitHub-actions minify of JS/CSS on deploy; GitHub-actions generation of the large hole SVGs. Robin picks which become units (the pre-cache is the one with real device value). Reported 2026-09-25 (session 15, report-only) — none of the three warrants a build today: (1) waveform pre-cache: the strain it targeted is already healed by the shipped caches (ocWaveCache keys PeriodicWaves by harmonic set, chiffBuf/windBuf cache the noise buffers, the Lite voice covers CPU-strained devices); what remains per note is osc + envelope automation (sub-ms) — a per-song pre-warm UI (progress bar + stop-on-playback) buys nothing measurable; if Robins phone shows a FIRST-note hiccup in the perf panel, the cheap half-measure is a versioned-wave warm at song load, not a pre-cache feature. (2) deploy minify: js/ is 387 KB raw but already 124 KB gzipped in transfer (Pages gzips automatically); minify would claw back maybe 25-30 KB gzip-total while destroying production stacks and console diagnostics (OCA_DEBUG readability, landing pages debug). Lighthouse mobile perf sits 95-96 — no parse-time pain on the evidence; revisit only if a throttling run shows otherwise. (3) hole-SVG generation in CI: the templates are ~10 KB each (92 KB across instruments, gzip-cheap) and the app NEEDS the client-side assembly for live hole state — static generation would add dead files, no transfer win. Full numbers table in the session-15 log. `🟨 ⚪ ⚙M`~~ ✅ 2026-09-26 — Robin 2026-09-26: minify + waveform pre-cache/warm DECLINED (no warrant per the report); the SVG idea re-elected in the enlarged-small-holes form (gen the enlarged variant so hole sizes are not scaled on the fly) — carried as its own item for the investigate-then-build.

- [x] ~~**Transpose** — shift melody ±semitones in parse/eval to fit other-key ocarinas. ﻿Stretch pick F6 transpose HELD for Robin 2026-09-25 (night): the placement was the granted call, but building touched a mid-flight fork the night cannot decide â€” text-level shift (the transposer skill's proven semantics reused on the editor text) vs a token-level shift inside parse/eval (original text untouched, displayed/rendered tokens moved): the second changes what the user SEES vs what the editor HOLDS while saved bodies keep original pitches â€” a surface/feel decision with audible consequences, exactly Robin's field-check class. Budget ruled too: one more unit + full sweep would have hit the watch line with the closing bookkeeping unlanded (rule 18). Worked around: nothing blocks on it; the twin-survey report (Dedup item, same night) plus the transposer skill already carry the shift semantics for any future build. 2026-09-25 eee3bbe: fork resolved TOKEN-LEVEL per Robin (editor text untouched, display/playback shifted, saved bodies stay original) — the derivation engine built for the twin dedup (tools/melody_transpose.py + js/library.js deriveBody) carries the proven shift semantics the future build reuses: octave shifts carry letters, other shifts respell via the sharp table; still HELD as a build until Robin wants it. `🟢 🟡 ⚙M`~~ ✅ 2026-09-26 — Robin 2026-09-26: declined — "focus on C (octave) and what we have; new ocarina players at Zelda release are the audience, not transposers to weird keys." The token-level + octave engines stay available through the twin derivation; the UI build does not happen.

- [x] ~~**MIDI import to tabs in-app** — `.grok/midi-to-ocarina-tab/scripts/mid2tab.py` already converts MIDI→tab notation; bake into "Load file" as JS. `🟢 🟡 ⚙M`~~ ✅ 2026-09-26 — Robin 2026-09-26: "Drop idea entirely. Is not gonna work automated." — the transcription stays a local tooling skill (skills/midi-to-ocarina-tab), no in-app import path.

- [x] ~~**Recording & A/B compare** — record mic during practice, replay against synth reference, pitch-curve overlay (WAV tap already exists in debug export). `🟢 🟡 ⚙L`~~ ✅ 2026-09-26 — Robin 2026-09-26: "Remove idea." — vanishes from the board by election, not by claim.

- [x] ~~**Enlarge-small-holes SVG pre-generation (Robin elects 2026-09-26, conditional)** — "Gen the enlarged small holes SVGs so hole-sizes do not have to be scaled on the fly. Only do this if you think it will help phones handle the processing." Investigate what an enlarged render pays on the fly today, then build the pre-generation ONLY if the measurement answers yes. `🟨 ⚪ ⚙S`~~ ✅ 2026-09-26 — INVESTIGATED 2026-09-26 (session 15, condition answered): pre-generation would not help phones. The on-the-fly pass is already memoized per epoch (ocarina.js enlargePlan — the O(holes²) neighborhood solve runs once per template/fingering install; later renders replay a handful of recorded setAttribute writes, and the output HTML itself is cached per state). Headless measurement (single view, 30 renders): enlarged 1.53 ms/render vs flat 1.77 ms — the enlarge work is inside measurement noise. A pre-generated enlarged template adds ~10 KB per instrument folder and a two-file switch to save nothing measurable. Not built, by the measurement Robin asked for.

- [x] ~~**Library favorites pinning (Robin elects 2026-09-26)** — the small first step ahead of any search work: pin favorite songs to the top of the library menu, persisted with the user library; the picker stays free. `🟨 🟠 ⚙S`~~ ✅ 2026-09-26 `390c431` — SHIPPED 2026-09-26 (session 15 `390c431`): the star affordance per row, a FIRST persisted Favorites group in pin order across both corpora, exactly-once rendering, reload-stable, free picker. tests/library_favorites.py red-first. sw v23.

- [x] ~~**Search-engine perma-links BEFORE the Switch-2 OoT launch (November)** — lifted from IDEAS 2026-09-24 and refined with Robin's rules: per-song landing URLs where "content may change, but the link must serve what the crawl expected". URL shape locked 2026-09-24: **`/song/<category>/<base-slug>`**, default player **12-hole C alto**, category (zelda/scales/other, normalized from group; "on Bass"/"on Alto" collapse) keys per-category theming (zelda → Hyrule, else Plain/new). Progress: (✅ 2026-09-24) **slug freeze enforced** — closed suffix list + chain rule + grammar in `tests/shipped_songs.py` (CI fails on violating keys), the `-alt`/`-alto` split fixed pre-index (`major-alto`, `chromatic-alto`), the contract documented in `skills/ocarina-melodies/SKILL.md`; (✅ 2026-09-24) **serving layer built + live-boot corrected** — `tools/gen_song_pages.py` emits shell-only landing stubs per base slug: canonical + og:url on the site-prefix path, single song-specific description, `?song=<key>&inst=<chosen>` pre-boot seed, hidden/variants excluded, byte-deterministic, staging git-ignored; the LIVE URL check on the first deployed stub caught the generator-class defect string tests missed — the app's runtime fetches (`songs.json`/`instruments.json`/css text/manifest-driven instrument files; even the SW registration) resolve relative to the PAGE and 404'd two directories deep, killing boot — fixed with a `<base href="{site-prefix}/">` injection (root-absolute `/…` rejected in review: bakes the prefix everywhere, breaks relocatability, and cannot reach runtime fetches without app changes); the landing default became Robin's corrected LADDER — best-fit by 12-hole > double alto C > triple bass C > contrabass (Song of Time's bass body lands on the triple; every stub boots playable, no range marks) — and `tests/gen_pages.py` upgraded to a real-boot leg: the staging tree assembled exactly like the deploy workflow's allowlist, served under the /Ocarina-Practice mount, boot asserted for right song/right ocarina/zero out-of-range chips/rendered sheet/one description/clean console (allowlist semantics: every 404 must BE a tone.json; a healthy boot can legitimately have NO 404s — the triple's tone.json exists); `.github/workflows/deploy-site.yml` publishes on served-content path pushes + manual dispatch; (✅ 2026-09-24 `89a39f0`) **og/meta card stage complete** — og:type/og:site_name/og:description (same wording as the meta description, one description per page holds) + og:image riding the already-generated 512 icon (width/height/alt) + summary twitter:card, injected at the END of head so the shell's charset keeps its first-KB seat; URLs stay site-prefix path form (canonical/og:url/og:image consistent; fully-absolute held until a domain is pinned); gen_pages pins every tag per stub over the still-green real-boot matrix. (✅ 2026-09-24 `e7718bc`) **domain landed + serving layer switched to it** — `ocarina-practice.com` is now the site's pinned origin (registered along the forever-perma rule; registrar and registration details stay out of this public repo on Robin's call): the deploy artifact carries a CNAME file, gen_pages gained `--site-origin` (default the domain) and now emits ABSOLUTE canonical/og:url/og:image with `<base href="/">`, the gen_pages suite re-pins every contract against a ROOT-mounted artifact; project-page serving stays reachable via the preserved --site-prefix/--site-origin-empty knobs for rollback. **Robin's manual cutover checklist (order matters):** push refactor4 → merge/deploy fires the artifact (with CNAME) → registrar DNS: CNAME record www → <github-io-user-host> (plus A/AAAA apex records if wanted) → repo Settings → Pages → custom domain = ocarina-practice.com (wait the DNS check) → enforce HTTPS once the cert provisioned → account-level Pages 'verified domains' adds + TXT-verifies the domain (the free takeover guard) → re-probe landing URLs at the domain (the boot is root-relative now — the old /Ocarina-Practice path dies by design). (next: live-domain verification of the landing matrix — his push, then this check) Remaining: richer stub content if SERP demands (thin-mass watch), absolute URLs if a domain gets pinned, sitemap.xml + robots.txt only AFTER links verify (Robin's crawl rule), Lighthouse pass, first real deploy + SERP observation. Deadline anchor: OoT Switch 2 ships in November (~5 weeks from 2026-09-24). **Decisions 2026-09-24 (refinement round):** BRANDING settled — the product STAYS "Ocarina Practice" (og:site_name already correct; no rename; the IDEAS BRANDING line is clear to delete). Domain processing still pending tonight; go-live planned tomorrow as a JOINT session — Robin's rule: the flip "has never been a success" solo, so hands-off sessions do PREP ONLY: keep this item's cutover checklist current, add a refactor4-domain (e7718bc) diff summary of what merging brings, and build live-verify tooling. SEO feature stages (robots/sitemap) are POST-switch work — and Robin's correction: the permalink contract does not become LIVE until go-live WITH robots.txt in place; nothing is crawlable before that moment, so slug/staging prep carries no permalink risk — the robots.txt push itself stays the final invite act, only after the live boot verifies. ﻿Night prep 2026-09-25 (away session, prep only by tonight's rules): - **Merge surface** â€” refactor4-domain is ONE commit (`e7718bc` over `c96965a`) touching `.github/workflows/deploy-site.yml`, new `CNAME`, `README.md`, `tests/gen_pages.py`, `tools/gen_song_pages.py`; zero overlap with what refactor4 merged (js/*, AGENTS.md, plans/) â€” clean merge expected. - **Checklist currency** â€” Robin's cutover checklist (above) stands unchanged; a push of tonight's `session5` stack also fires the artifact (served-content path trigger), so "push â†’ merge/deploy" may run BEFORE his joint session touches DNS â€” the order of DNS/Pages/HTTPS steps is unaffected. - **Live-verify tooling built + used**: `tools/verify_site.py --origin <base> [--boot N]` (not a CI step; read-only GETs). Checks: shell serves the js/app.js module entry; deployed songs.json readable; every landing stub 200 with base href / canonical / og:url agreeing on the ONE serving prefix (base href from the origin's path, so both stages hold), og:title + description present; `--boot N` boots sampled stubs (song-of-time always) in fresh contexts (SW second-navigation lesson), zero console noise beyond the manifest-declared-absent tone.json 404s, right song on the right ocarina by the ladder. - **Pre-flip state recorded**: today started on a STALE artifact (home shell predated the PWA commit: no serviceWorker string, no og on the shell) while /song/ stubs served the permalink contracts; a fresh push-triggered Actions deploy during the night refreshed the artifact, and the full probe ran GREEN before the flip (18 checks, 8/8 stubs booted clean at /Ocarina-Practice). - **Tomorrow**: same command with `--origin https://ocarina-practice.com` is the post-flip acceptance gate â€” absolute canonical/og + root `<base href="/">` + CNAME artifact; the /Ocarina-Practice mount dies by design. Flip landed by Robin's hand on main (`a2a081d`, PR #10 merge; deploy run `36117318574` green 1m54s): the domain serves the OLD artifact — seed tests red, and the verify gate names why: all 8 stubs carry `<base href="/Ocarina-Practice/">` while the domain serves at root (the workflow baked the pre-flip mount), so every runtime fetch 404s and no stub boots; robots.txt and sitemap.xml absent (not yet stage-built). The domain-switch unit closes it: workflow passes `--site-prefix /` + `--origin https://ocarina-practice.com`; the generator emits sitemap.xml (home + every stub URL, byte-deterministic, no lastmod) and an absolute og:image (og:image must be absolute; the flip pinned the origin — canonical/og:url stay origin-relative so the artifact stays mount-agnostic); robots.txt committed, timeless per Robin (no automation commentary facing the web); gen_pages mirrors ROOT serving now (old project-page mount pinned by a string-contract leg, retires with the stage); verify_site gains the robots+sitemap live legs. Sweep 31/31 + gen_pages re-run after the robots rewrite. POST-FLIP GATE GREEN (2026-09-25, merge `4f44099`, deploy run `36125302883`): 20 live checks pass against https://ocarina-practice.com — all 8 stubs boot the right song on the right ocarina at prefix `/`, robots.txt + sitemap.xml serve and enumerate home + exactly the stub set. Per Robin's rule the permalink contract is LIVE from this moment (go-live + robots.txt). The URLs/dates/etc on the served artifact are by-design: canonical/og:url origin-relative (mount-agnostic), og:image absolute, robots.txt timeless Robin-edited. REMAINING on the item: Lighthouse pass; first SERP observation (weeks — November Switch-2 anchor); Robin's Search Console domain verification + sitemap submission (his Google account, manual). The "sitemap.xml + robots.txt only AFTER links verify (Robin's crawl rule)" row is DONE by this gate; the legacy project-page mount string-leg in gen_pages now awaits its stage's retirement. On the IDEAS lifts Robin green-lit while selecting: perma-link landing navigation semantics (switches leave the deep path — root + ?vars; title click → root) and the info-screen issues link — both lifted as new §9/§7 items. **Lighthouse pass 2026-09-25 (`b023394`, session12 — live home re-audit on redeploy; stub set not passed)**: mobile P80 / A11y 100 / BP 96 / SEO 100, desktop P99; landed fixes: passive token-touch listeners (ui.js wireTokenTouch — nothing preventDefaults there, drift intends the scroll), critical paint gate inline in index.html (UA 8px body margin + the 0.67em h1 margin collapsing through the pre-CSS body = the phone flash), .inst-sel width reserved ≤760px so the late-filling instrument list cannot balloon the header — the exact 0.352 CLS shift reproduced headlessly under real throttling then driven out, local re-run has no CLS findings (expect live P to rise on redeploy). REPORT-ONLY residuals: piano block still grows ~92px late in boot (residual CLS 0.089, inside the green band — a reservation is a piano-look call, Robin's), the manifest-declared-absent tone.json 404 console error (§1's intentional state, no action), themeBtn accessible-name vs visible-text mismatch (the HiFi menu unit rewrites that button anyway), Pages 600 s cache TTL (hosting default; SW covers re-visits), unminified JS/CSS (the IDEAS minify-on-deploy line, not lifted). Robin 2026-09-25: the domain is now Search-Console-verified — a crawler is expected soonish — and the existing sitemap URLs count as PERMANENT from today: no rekeys, no path renames; the kokiri leaf-URL retirement predates the pin and was the last move of its kind Live Lighthouse re-check 2026-09-25 post-deploy (session 13, headless, Lighthouse 12): mobile perf 95 (was 80) with CLS 0 (was 0.352 — the inst-sel ballooning fix held through deploy), A11y 100 / BP 96 / SEO 100; desktop perf 99 with the same 100s; BP's 96 is the expected vintage tone.json 404 (oot-alto-c-12, the manifest-declared-absent allowlist class), A11y's quiet nit is #themeBtn's label-content-name-mismatch, and perf's drag is the render-blocking stylesheet (mobile LCP 2.5 s, speed-index 0.79) — the same CSS-addressing seam Robin's fresh-refresh IDEAS entry describes `🟨 🟠 ⚙M`~~ ✅ 2026-09-26 — TRIAGED 2026-09-26 (Robin: "I want TODO to contain what we need TODO"): everything buildable shipped across sessions 13-15 — the slug contract is enforced (tests/shipped_songs), the serving layer boots its stub set (tests/gen_pages, mounted leg incl.), the intended-instrument engine + botw exemplar are live, canonical/JSON-LD/OG routes serve, the sitemap set is frozen-permanent and the domain is Search-Console-verified. The living residue continues as its own compact §9 item.

- [x] ~~**Per-instrument loudness dial in the debug panel (Robin's ask; his batch: session-only, table of five, -3..+9 dB)** — five AUDIO_DEBUG keys mapped by instrument id through instLevelGain() = 10^(dB/20) off the loaded instrument, multiplied into all four voice masters so melody/supports/tracks all carry the offset with 0 dB untouched; the panel's volatile-row carve-out keeps the dial out of localStorage while plain rows persist; debug_panel red-first legs pin the rows, the gain math and the two-sided volatility contract (commit `7f44c98`); in live use now — his settled numbers ride back into code when he names them. `🟢 ⚪ ⚙S`~~ ✅ 2026-09-28 `7f44c98`

- [x] ~~**"Buy me a coffee" link (IDEAS; ko-fi.com/tribbin)** — not in the app yet (78b9646 only touched IDEAS.txt); add the link to the help-screen colophon beside the issues link (target=_blank rel=noopener) and pin its presence. `🟢 🟡 ⚙S`~~ ✅ 2026-09-30 `46dec09` — Landed in 46dec09: the link now sits in the help-screen colophon beside the issues link (index.html .help-meta, ko-fi.com/tribbin, target=_blank rel=noopener); both colophon links are pinned in tests/sr_hints.py's help-overlay leg (help1.links), so the presence, new-tab target and noopener survive refactors. Sweep 47/47, sw oco-pwa-v62.

> **Idle idea pool: `plans/IDEAS.txt`.** A live document Robin edits over time and ROBIN'S ALONE — the AI never writes it (it may be read, and only lifted into TODO.md when Robin explicitly asks). TODO carries no copy or summary: when an idea from it is picked up, read the FILE fresh at that moment; never rely on a remembered or transcribed version.

---

## Session log

- **2026-09-22** — Initial full review passed (all 8 JS files, CSS, tests, data). Created this TODO with ~50 items from that audit. Nothing in app code changed.
- **2026-09-22 (session 2)** — Branch `refactor1`, 4 commits (not pushed), full local suite green (practice/support/instruments + new library suite). Done:
  - `43147f5` — §1 B1+B2+B3 (library id collisions, fail-soft storage writes, corrupt-JSON backup) + new `tests/library_hardening.py` + CI step (+ drops the §6 library-tests bullet).
  - `97e86f0` — §2 R2 audio unlock: gestures only (`pointerover` dropped), resume rejection caught.
  - `c69448f` — §1 B7/B9/B10: blocks start collapsed in markup (last commit id `c69448f`), double `fitInput` trimmed, same-line fns split.
  - `9cfccfb` — §8 H1 favicon/meta/theme-color; §1 B5 reframed as intentional (chamber measurements coming — see rewritten item; NOT a bug).
  - Added "Test/fix ordering" note under How-to-use (per discussion: no blanket test push).
- **2026-09-22 (session 2, more)** — Continued on `refactor1` after the first four commits:
  - `c23f3d8` — §1 B4 instrument-switch race: `instLoadGen` guard + `tests/instrument_switch_race.py` (in CI). Hot-list row 4 ✅.
  - `4480fab` — §2 R1: voice failures recorded/surfacable (`OCA_DEBUG.voiceErrors()`), all bare `resume()` calls now `safeResume()`; `tests/voice_error_visibility.py` (in CI). Hot-list row 3 ✅.
  - Full local suite re-run after each commit: instruments / support / practice / library / switch-race / voice-visibility all green.
- **2026-09-22 (session 2, part 3)** — `3094ad7` — §7 A1/A2 keyboard accessibility of piano + token chips, `tests/keyboard_widgets.py` (in CI). Robin human-verified the first four commits on a real session (library save/collide/scenarios, collapse visuals, rapid instrument swaps, first-gesture audio, favicon) — all fine. Touch long-press listen split out as a new open item. All 7 local suites green.
- **2026-09-22 (session 2, part 4)** — Robin found Space in the token area leaked a short faint note (local Space click mashed with the global shortcut). `1d6e03e` — Space is now exclusively the global Pause/Continue shortcut; piano/token handlers intercept Enter only; `wireSpacebar` routes through `transportEngagePlay()` (matches the button's pause/resume semantics — Space previously hard-stopped a running melody). Test updated to pin the contract.
  - **Behavior change to review by ear:** Space on a playing melody now PAUSES (continuable) instead of stopping the song outright. See new item §1 B11 (normal-mode transport lacks a Stop).
  - Full local suite re-run after each commit: instruments / support / practice / library / switch-race / voice-visibility all green.
- **2026-09-22 (session 2, part 5)** — Robin: keyboard users can't hover to listen; suggested arrow-walk = hovering. `ff43eb8` — one dwell scheduler in `hoverPreview` (260 ms) now rules mouse AND arrows: highlight instant, note only when settled; skim/graze cancels; commitment keys (Enter) hush pending previews. Piano arrows stay silent (Enter audits there). Hints updated. All seven suites green.
- **2026-09-22 (session 2, part 6)** — `9cdab5d` — §6 T1 parse edge suite + two grammar data-loss fixes (multi-digit octave; inline `# tempo` line-eat). All 8 suites green. New grammar-decision TODO item for the `s`-form gotcha.
- **2026-09-22 (session 2, part 7)** — Grammar wrap-up + shipped-songs suite:
  - `81a906d` — Robin's a+b decisions: s-form grammar, junk → visible bad chips, orphan `-` → bad chip (never a rest). parse_edges extended.
  - `d9253cf` — NEW `tests/shipped_songs.py` (in CI): all 23 songs parse clean / in range for ≥1 ocarina / sane metadata. **Immediately caught a real typo**: doubled durations (`E5/8/8` etc.) in the three BOTW variants' Main theme body + repeat — Robin chose "plain typo" (a), fixed 6 spots in `d9253cf`.
  - All 9 local suites green.
- **2026-09-22 (session 3)** — Resumed from the broken tail of session 2 (it died mid-suite-run, 18:56: the run-all loop is simply minutes-long, no real failure; nothing was left red):
  - Bad-chip round 2 — pills approved by Robin: `.tok.bad` = token-shaped tan pill (`--token-neutral`, both themes; OoT override dropped) + wavy scribble, junk no longer drops a `✕` card into the fingering-chart grid (`fillFullSheet` skips `type==="bad"`), test `bad_chip_style.py` extended (2 strip chips / clean grid / tooltip) — **amended into the bad-chip commit** ("any fixes may be ammended"): `12be6c8` → `4dba1c4`. All 10 suites green (venv python only; plain `python3` has no playwright).
  - Robin asked for the wavy scribble inside the editor too, then asked for a native mechanism: none exists (textarea can't style ranges, spellcheck is dictionary-only) → overlay would be the mirror-div hack → **declined by Robin** ("if it's a hack let it be"). Chips are the scribble surface.
  - Next small pick while node/eslint stays unavailable: ~~§8 H2 hyrule.jpg → WebP~~ — done `09efb80` (609 KB jpg → 90 KB WebP 1280w q80, jpg deleted; Robin eyeballed `?oot`, fine). Hot-list row 10 fully closed.
- **2026-09-22 (session 3, continued — autonomous smalls, all suites green)** — Robin granted: fix obvious things, tests green, TODO bookkeeping, ask only functional questions. Sequence (app code commits on `refactor1`, none pushed):
  - `8c6b85a` — revoke-after-download deferred 5 s (Disk Save + Download Tabs; same pattern debug.js already used). Code comments must not reference the TODO doc (Robin) — §-refs only inside TODO.md itself.
  - `f21284f` — ocarinaSVG error text escaped via textContent round-trip; explicit `width:100%` fallback before all three round() width lines.
  - `812b25f` — global error net (test-first in voice_error_visibility): window errors (+stack frame) & unhandled rejections APPEND to #err, never clobber render/boot writers.
  - `6cc812c` — mode segment = real one-stop radiogroup: roving tabindex, arrows move focus AND selection (wrap, Home/End), tab stop follows clicks (probe in keyboard_widgets suite; the test part rode with the `812b25f` amend — noted here to keep history honest).
  - `6912f72` — support test comment: dropped the only-local handover reference.
  - `45e6921` — Robin's new favicon.svg (full ocarina drawing, valid XML) committed as-is.
  - `a130f88` — prefers-reduced-motion gates every decorative motion (range-warn/perf pulses die, zen wave opacity-only via reduce keyframes, focus-token swell freezes; gate moved to file end for cascade order). NEW `tests/reduced_motion.py` (in CI): class-chain stand-ins probed in both media modes.
  - `c985bd9` — Saria hardcode folded into manifest: svgWhen rules carry own `songTitle` regex; 3-case pin in instruments_load (id path needs `sarias-song-alto`: the plain body is out of range on the Alto — dropdown stays empty there even via ?song).
  - `57fcf70` — dead CSS removed (also .thumb — thumb exists only as id/hole attr, never class); enlargeSmallHoles got an x-gap skip for never-binding pairs.
  - **Robin's functional answers** — `567ec29` §1 B8: engine untouched (75% bar pass is play-tested and liked), test surface gets BOTH metrics (`fillPct` note-time / `creditPct` credit). `ab4ce0c` §7 A6: touch hold-to-hear, same 260 ms dwell (swallow-after-hold, tap keeps play-from-here, drift cancels; Robin's device feel-check open). `017284e`+`1f904b6` §1 B11: zen transport mirrored INTO normal mode, then refined by Robin: rounds centered in the playback box-head, text Play/Practice buttons + hear-hint removed, practice = play's size, Tempo dial flattened to Swing's alignment. `96d5f85` §2 R9: documented as accepted-by-design (README) after Robin's three don't-cares.
  - 11 suites local-green. Robin praised the run. Header-polish chain (Robin eyeballing each round): `0c58a50` — transport rounds truly centered, Loop/Tick left cluster, Lite exits the header (hidden carrier), Tempo/Swing aligned title-slider-value rows, ghost resting rounds; `591d7fb` — Loop tick-box retired (the round button owns it, hidden carrier keeps state), perf button to second seat right after the collapse chevron, Library cluster rebuilt as a centered title-over-dropdown stack. **Robin: "we're gonna tackle the buttons of that section next"** — the Library block's ghost buttons (Save to library/Remove/Save file/Load file/Clear) are the next design target — WAIT for Robin's direction. `fc9fe67` — header final pass: empty pianoBlock twin removed (the thin line), INPUT/(type notes here) title retired, "Song Library" as the section's important title (shared `.head-label` style, accent rule), "Playback Control" title over the centered transport bundle (`.t-wrap`), OoT inactive round glyphs → white ink. `ecc6fce` — playback head containment (1fr-auto-1fr center column replaces the overflowing absolute float; `.head-left` cluster; perf-insert anchoring fixed — the typo'd anchor crashed every render and surfaced Robin's pasted #err text), OoT head labels back to clay. `1c7514b` — Library actions final: Clear next to the collapse chevron and hidden while collapsed, Save to Library/Remove from Library + Save File/Load File as equal-width stacked pairs, OoT errors bright salmon. `c1725c5` — input head also gets the 1fr-auto-1fr center-column grid (Song Library cluster truly centered like Playback Control; collapse+Clear the left column, the button stacks the right one) and Remove from Library wears the destructive accent (OoT salmon). `5878885` — perf button renames to "Audio Performance" (name span + separate readout slot), the headroom badge ticks off audio's existing 500 ms watchdog cadence even with the pop closed (was click-only), OoT meter colors brightened, and the ocarina picker centers over the sticky header (1fr-auto-1fr). `b47012f` — Audio/Performance stacked on two lines, badge in level convention (`-6.0 dB`), Piano head joins the centered `.head-label` style. `4419763` — **the button's dB readout retired altogether** (Robin: with the limiter in place and the pop's full meters, a lone number — session-peak or live — was more confusion than value): watchdog beat hook + badge machinery removed (the popup meter rows stay), "Play tick at bars" (renamed from Tick) now stacks under the Audio Performance button in the head's left column. Header polish round 4+ (all suites green, Robin eyeballing each): perf/x/share/print/download went glyph-only (`f27297c` chain: icon-btn ghost rounds with stroke SVGs), fullscreen moved to a panel-corner window control, "Tick" became the pressed `Play tick at bars` ghost button (hidden `#tickMel` carrier — library round-trips the flag), Song Library title/bigger 22px song-title section head, dropdown widened to 20em with centered selection, toolbar rows reorganized (Zen's own centered row, buttons row on the card-grid's exact slot width — left/right clusters aligned to the card edges, grid|scroll|single on the centerline), gap-based card grid (trailing margins retired: cards separated by `gap`, sheet width − one gap so rows end flush BOTH edges), and bars ride that gap (negative left margin, mid-gap line, scroll band titles re-aligned `f27297c`), and the song-library button label survives the range filter (keeps the loaded song's name when the list drops it; muted "No song selected" placeholder otherwise — `dff5b66`), and the visit defaults flipped to Robin's home setup: Hyrule look, 12-hole Alto C (manifest `default`) and Song of Storms (alto), `?plain` opts back to the classic theme — README documents the params (`cb3cc62`; render_pin now boots the Triple Bass explicitly to keep its calibrated chambers).
- **2026-09-22 (session 3, wrap-up for the night)** — Branch `refactor1`: **39 commits on top of main** (`2655acf..refactor1`), none pushed, **12 suites local-green** (CI workflow lists 11 — reduced_motion & render_pin registered; make sure CI covers 12). All TODO bookkeeping current at time of writing.
  - **Next session picks up here:**
    1. §4 P1 per-keystroke render debounce (🟧🟠⚙L) — the guardrail pin is landed (`tests/render_pin.py`), so the refactor can start straight away. Read the pin before touching `render()`/`drawTokens`/`fillFullSheet`.
    2. Robin may open with Library-block button design work (his agenda: "the buttons of that section") — header/polish rounds first, then P1.
    3. Remaining smalls (seek Robin or do under the standing autonomy): §5 duplicate prompts, unused `hidden` flag doc, cache-busting `?v=`, debug naming (§8 H4). eslint (§6 T5) still blocked locally (no node) — CI-only.
  - **Conventions locked this session:** shipped code references NO local docs (no §-refs in comments; code-to-code refs fine); commit titles informative, §-refs only inside TODO.md; red→green or pin-first for behavior changes; run all 12 suites via `.venv/bin/python3 tests/<name>.py` (plain `python3` has no playwright); amends on this branch are fine (all unpushed) — `git add -A && git commit --amend` only when the change is the same concern as HEAD.
  - **If this session breaks:** everything above is committed except TODO edits themselves (gitignored). Resume at item 1.
- **2026-09-23 (session 4)** — Robin confirmed the Library-block buttons are done (his "buttons of that section" agenda closed), then parked while he's at work and granted a batch with pre-answered questions: §4 P1 depth = **debounce + SVG cache**; `hidden` flag = document with his semantics (unfinished songs kept in Git); cache-busting = **defer to the PWA**; eslint = land it (CI-only); debug naming = **OCA_DEBUG**; the 39 refactor1 commits are pushed & merged already (PR #3 — refactor1's remote branch still exists on origin, Robin's to prune, not ours). Branch `refactor2` (main + 6 commits, unpushed), **14 suites green local** (12 old + 2 new; CI workflow now lists 14 steps + eslint).
  - `18e1ef3` — §4 P1 pin-first: `tests/render_pin.py` gains a freshness wait for typed input probes + the **debounce contract** (red pre-fix); NEW `tests/svg_cache.py` freezes card-clone coordinates (same-input ⇒ same svg, big-holes view toggles, instrument swap and back — green pre-fix pin); `tests/bad_chip_style.py` injection made async-safe for the settled render; both new suites registered in CI.
  - `842d004` — **§4 P1 done (red→green + pin):** `#src` input coalesces one render per settle — Robin chose "debounce + SVG cache", then overrode my 60 ms first flight as un-human → **200 ms** (`73eeea4`, the human hush between typed units; half-parsed bursts never flash). Practice-session invalidation stays synchronous; programmatic loads — library/clear/piano/instrument — keep direct renders. ocarinaSVG memoizes clone output: key = template-generation · chamber · covered-set · big-holes view; wholesale invalidation on every template install (ocarina.js) AND fingering install (app.js, typeof-guarded); 512-entry bulk cap. The pin and svg_cache stayed green through both halves; switch-race/instruments/library/keyboard suites re-run green per step.
  - `1c82c80` — §5 M6: `libPrompt`/`libConfirm` share one `libModal` core (identical open/close/keys semantics, exactly-once closing).
  - `4da683d` — §5 M7: README documents `hidden: true` as Robin's WIP-in-Git carrier (dropdown hides until "Show hidden songs").
  - `1058657` — §8 H3+H4, red→green: debug panel is now **built on first open only** (`buildPanel()`; plain visits create zero DOM) and **OCA_DEBUG is the one public handle** (OCO_DEBUG alias retired, DEBUG=1/0 knob stays); NEW `tests/debug_panel.py` (in CI) pins all of it.
  - `62d056d` — §6 T5: flat `eslint.config.js` eslint 9 + CI step (setup-node 22, `npx eslint@9 js/`). No no-undef (classic globals are the module system); `no-unused-vars` at warn → tighten after CI's first counts. **Never ran locally (no node) — the branch's first push reveals any red.**
  - Housekeeping: `tests/__pycache__` removed; TODO hot list refreshed (all ten originals closed) — new picks: §5 M3 support cut-bus, §9 F1 PWA, §9 F2 section looping, §2 R4 schema validation, §4 P2 autocorrelation Worker, small batch (M4/A7/M8).
  - **Next session picks up here:** (1) push `refactor2` (first CI flight: eslint step + 14 steps — watch the eslint/never-ran-locally caveat), (2) hot-list pick (Robin's call — support cut-bus vs PWA vs section looping), (3) Robin's real-device feel-check for touch hold-to-hear (§7 A6) still open.
- **2026-09-23 (session 4, continued — Robin live during the afternoon)** — Robin's Q&A round: **input settle 60 → 200 ms** (`73eeea4`, he called 60 machine-short — "un-human"; 200 = the hush between typed units, half-parsed bursts never flash; render_pin/bad_chip green). Then "what's next" → Robin picked **PWA/offline** off the refreshed hot list (kept §5 M3 support cut-bus held for ears — it changes audible support behavior and he wasn't at the mic).
  - `54d1832` — **§9 F1 done (red→green + suite):** `tests/offline_pwa.py` written first (red: no SW → `serviceWorker.controller` never appears), then `sw.js` + best-effort registration from app.js on load + `manifest.webmanifest` + generated icons + README feature line + CI step + eslint file list gains `sw.js`. Design: CORE shell hand-listed; instrument fingerings/template(s) (incl. svgWhen overrides like the saria template) DERIVED from instruments.json at install; only OK responses cached (tone.json 404 = "no recordings yet", never cached); nav network-first w/ cached-shell fallback; rest SWR + background refresh; skipWaiting+claim; `VERSION` in sw.js is the manual lever for forcing old-cache flushes.
  - **Suite-side finding while landing it:** `instruments_load` svgWhen leg raced the boot tail (BOOT_WAIT fires at fingerings install; `#scale/#src` fill only after the tone-model round-trip inside loadInstrument) — the SW's extra hop widened the window enough to make it 2-of-3 flaky. Suite now waits for the library tail (`#scale.value === 'sarias-song-alto'`); assertion unchanged. 5 consecutive green runs after.
  - **15 suites now green local** (12 + svg_cache + debug_panel + offline_pwa); CI workflow lists 15 steps + eslint. refactor2 = main + 8 commits, unpushed.
  - **Next:** push `refactor2` (NOW carries the first eslint flight + offline suite in CI too), hot-list pick (section looping next by formula), Robin-device checks stack: touch hold-to-hear feel, PWA install + airplane-mode run.
- **2026-09-23 (session 4, part 3 — Robin parks section looping, picks §4 P2)** — Robin: looping idea "aside for now, want to think about it"; picked the **practice autocorrelation → Worker** off the hot list instead.
  - `08f40e6` — **§4 P2 done (red→green along the way + new suite):** `js/pitch-dsp.js` now IS the single detector source (consts became PITCH_MIN_HZ/PITCH_MAX_HZ there, classic script added before practice.js in index.html + SW CORE); `js/pitch-ac-worker.js` (importScripts, transfer-in/compute/post-back) runs per-frame; practice.js splits `readFrame(done)` (rms + dispatch; finishFrame = range guard → hzSm → signal → zone scoring → `done()`) from `advanceFrame(t, dt, dg)` (the whole state machine, guarded against stopped/paused sessions). pause/stop clear `acJobs`. Surface adds `testACAsync` + `usingWorker()`; testAC refactored onto a shared `probeBuffer`. NEW `tests/ac_worker.py` (in CI): worker ≡ sync bit-identical on a 13-tone battery, concurrent request pairing ordered, `Worker = undefined` page reports the fallback honestly. **The split initially stranded its continuation** (finishFrame counted scoring, never called done) — the practice acceptance suite caught it 3-case-red within one run; one-line fix, all green again. Full 15-suite sweep green twice over before commit; ac_worker registered → workflow now 16 steps.
  - **Next:** push `refactor2` (9 commits; first eslint flight), hear-check for the worker path on a real session (Robin: does practice feel the same? the state machine is result-paced now), then the small batch M4/A7/M8 or schema-validation reintent (hot list row 4).
- **2026-09-23 (session 4, part 4 — mic verified, small batch)** — Robin confirmed the practice-mic path works with the worker (his feel-check §4 P2 done); CI history all green including the **first eslint flight** (he's been pushing refactor2 along the way — origin/refactor2 == 08f40e6). Robin then picked the **M4/A7/M8 small batch** off the hot list.
  - `3bb5bfa` — three closes in one batch commit: **M4** integer 96th-grid scheduler position (`melodyPos96`, exact `swungBeats`, round-regridded loop restarts, `OCA_DEBUG.melodyPos96()`, `tests/swing_grid.py` live pin); **A7** shared `#sr-gesture-hints` aria-describedby block for chips/piano keys/junk pills + oor chips self-describing labels (`tests/sr_hints.py`); **M8** boot reports duplicated manifest ids + unknown ?inst into `#err` fail-soft (instruments_load diagnostics legs).
  - **The batch's real find:** render() had been textContent-wiping every appended `#err` line on every render — the append-vs-overwrite seam between the global error net and the true render writer, exposed by the boot diagnostics being invisible. render now owns one persistent `.err-render` child (hidden when empty); appended divs survive all renders. voice_error_visibility + render_pin confirm the contracts intact.
  - 18 suites local-green (added swing_grid, sr_hints; CI workflow lists 18 steps). refactor2 = 10 commits unpushed (origin at 08f40e6).
  - **Next:** hot list is nearly clear — remaining: §5 M3 (held for ears), §2 R4 reintent, §4 P3-P6 perf smalls, §5 M1 ES-modules (tests first), §9 features (Robin thinking re: section looping), innerHTML audit (§3). Feel-check stack for Robin: touch hold-to-hear, PWA install/airplane practice, 200 ms typing.
- **2026-09-23 (session 4, part 5 — CI link + triple batch)** — Robin linked a red CI run (PR from refactor2 → main): `instrument layout tests` failed in CI with the duplicate-manifest report missing. Two real findings in one link: (1) **the SW hides route interception** — the service worker installed during leg 1 of the shared browser context serves its precached `instruments.json`, so `page.route` never reaches the app; the diagnostics leg now runs in a FRESH context (svg_sanitized's per-leg contexts dodge it by construction — pattern worth remembering for every future route-intercepting test); (2) the perf edit referenced `queueHighlight` before it existed — an editor-mid-flight hazard, caught BEFORE any push by reading the CI failure with fresh eyes.
  - `2326c5b` — **§6 T3 done:** `tests/transport_schedule.py` — onset gaps == the swung 96th-grid arithmetic recomputed outside the scheduler, staccato/tie exactness, auto-stop, loop-wrap parity, CUT-BUS lifecycle (during/retire-within-horizon/fresh-replay/no-zombies-with-support), Lite voice strictly-less machinery. OCA_DEBUG gained `melodyAlive()`/`busAudit()`. M3 and ES-modules are now de-risked by this same suite.
  - `0d4be18` — **§3 hardening:** `sanitizeSvgTemplate` at the install choke point + `ensureOcarinaTemplate` marks failed paths consumed (no live-lock) + `escHtml` for the range warning; `tests/svg_sanitized.py` drives hostile template / unparsable template / poisoned manifest through real boots. Audit verdict on the remaining ~35 innerHTML uses: parser-constrained or self-text — documented in §3.
  - `4d9dd9b` — **§4 P3+P4:** the shared `highlightPlan` (one timer/rAF pair, dropped on stop/pause) replaces per-token setTimeouts; `tokByI`/`cardByI` per-render indexes replace highlightToken's per-note sweeps (the keyboard suite's focus pin caught the string/number Map-key mismatch on token 0 mid-flight — a pin doing its job). P5 (WAV tap → AudioWorklet) reframed to ⚪ backlog; P6 (reverb impulse) closed under the accepted-by-design paragraph.
  - **20 suites local-green** (added transport_schedule + svg_sanitized; CI workflow lists 20 steps). refactor2 = 13 commits, origin at 08f40e6 — the PR to main needs the new commits pushed by Robin.
  - **Next:** strategy pick among the unlocked big ones (ES modules, M3-with-ears, section looping), or §9 feature work (practice history / transpose / MIDI import). Feel-check stack for Robin unchanged plus a playback-eyeball of the new highlight plan on a real session.
- **2026-09-23 (session 4, part 6 — Robin's field notes + the migration)** — Robin's live notes drove real fixes: the `?` help card showed nothing inside the collapsed input block's display:none subtree (overlay + gesture hints moved to body root; sr_hints now asserts VISIBILITY — it had waved that straight through, red→green after the relocation); the interface mangled report caught a DUPLICATE `</div>` my regex splice left behind (piano/`#err` leaked out of their section) → repaired by hand and **html-validate landed in CI** (structural rules only: endtag/no-dup-attr/attr-value-quotes/void, minimal `.htmlvalidate.json`); theme + help buttons moved to the page-title bar's right column per Robin; the dev-panel footer line inside the help card removed ("not for end-users").
  - Landed in this stretch: theme toggle beside Clear (`077a432`, persisted, ?plain/?oot outrank), shortcut overlay (`f2ba16e`, button + `?` key + Escape/focus-restore), practice history (`177e9ff` — completed-run records {ts, wipes, mean-cents, sec} per song, panel line, `OCA_PRACTICE.history()`), M3 cut-bus routing (`9f91eab`), SW scheme hardening (`d0f4d16` + fetch-handler guard after Robin's file-scheme reports), practice-acceptance arbiter flake fix (`b516d2b` — same-SHA push-red/PR-green was the arbiter's start race), the practice-history arbiter pattern, and the **ES-modules migration** (`57de8cb`, 19/20 green — see §5 M1 live item; transport_schedule stalls at Playwright TEARDOWN only, all four legs green — first task next session).
  - **Robin's VS Code preview forensics (recorded):** his `file:///` 504s + file-scheme SW errors are the PREVIEW's fetch path dying (tests run their own throwaway HTTP server + isolated Chromium — zero shared state with his preview). Verify app changes via `python3 -m http.server` + a normal tab.
  - **Standing rule from Robin:** stop attributing CI/g pushes to actors — report SHA/trigger/job only. (He corrected me on this twice today.)
  - **Fresh session picks:** (1) transport_schedule teardown hang (all legs green; suspect bus-leg's `createOscillator` instance patch interacting with close, or the module worker's importScripts-era cache entry), (2) full 20-suite green under modules + the eslint/html-validate first flights on push, (3) Robin's ear stack: M3 support cut-bus audition, theme/help/title-bar eyeball, history line, touch hold-to-hear, PWA offline, 200 ms typing.

- **2026-09-23 (session 5 — the compat-surface debts paid)** — Robin linked the push run at `57de8cb` (run #42, job `practice tests`, trigger push/PR): **failed in 16 s at the "Validate HTML structure" step, before any suite ran** — html-validate@8 reported "Definition for rule 'endtag' / 'attr-value-quotes' / 'void' was not found" (the config's first CI flight; the rule names were pre-v7 spellings, validated nowhere because no node exists locally). While triaging that, reproduced the transport stall locally and it resolved into the real task list:
  - `28eadd8` — **transport_schedule "teardown hang" SOLVED, root corrected:** it was never a teardown/browser-close hang — leg 4's `page.evaluate` never settles. `audioCtx` was a classic-script top-level `let` (visible to `page.evaluate` through the shared global lexical scope) but is a module-scoped `let` (invisible); the leg's inner promise rejected on the missing global and nothing settled the outer promise. Fix: compat block mirrors `audioCtx` through a **live getter** (`Object.defineProperty`; a plain assignment would freeze the lazy-creation `undefined`) + `window.sharedAudioCtx`; the leg reads `audioCtx || sharedAudioCtx()` so it stands alone. Probe harness at /tmp/opencode/probe_leg4.py proved `typeof audioCtx -> undefined` in-page. Also restored `OCA_PRACTICE.usingWorker()` — dropped from the object when `history:` was spliced in at `177e9ff` (splice casualty #2; survived because no full sweep ran after that commit and CI died at html-validate first). ac_worker, transport_schedule green.
  - `500d9e2` — instrument suite flake hardening: (1) typed probes now wait through the 200 ms settle for the typed song's own title (the debounce made the sync-probe a driver-latency coin flip); (2) the svgWhen typed leg pins the boot's library tail (`#scale.value === 'song-of-storms-alto'`) before typing, so `loadLibraryItem(home)` can't clobber `#src` mid-probe; (3) the duplicated-id diagnostics leg got its OWN fresh context — the bogus99 leg in the same context had installed the SW, whose precache (real instruments.json) claims the second navigation and hides the doctored route. **Standing pattern now recorded twice: every route-doctoring leg = one fresh context.** 3× consecutive green.
  - `fd01691` — .htmlvalidate.json: renamed rules to v8 spellings (`close-order`, `attr-quotes`, `void-content`; `no-dup-attr` unchanged), no extends needed (html5 metadata loads by default). Verified locally: index.html passes; a broken-markup sample still fires all four (stray end tag / dup attr / unquoted value / void content). First flight happy.
  - Tooling note: node 22 tarball (v22.14.0) downloaded into /tmp/opencode (system untouched; standard npx cache at ~/.npm/_npx as a side effect) — eslint + html-validate now runnable locally; eslint local = 0 errors / 4 known warn-level warnings, unchanged by these commits.
  - Sweep: **22/22 suites green** (after triaging the two reds above). Housekeeping: tests/__pycache__ removed after runs.
  - Bookkeeping: §5 M1 fully closed; §9 late strikes (practice history `177e9ff`, theme toggle `077a432`, shortcut overlay `f2ba16e` — landed in session 4 part 6, never marked); suite counts updated (workflow = 22 suite steps + eslint + html-validate).
  - **Next:** (1) push `refactor2` — the full first flight (eslint + html-validate + 22 steps) finally exercises everything; (2) Robin's ear stack: **M3 support cut-bus audition first** (the deciding pass), then the rest of the feel checks; (3) strategy pick afterwards: section looping (§9 F2), or §9 feature work (transpose / MIDI import / recording), or §2 R4 schema-validation reintent (Robin's hand-tuned data → confirm intent first).
- **2026-09-23 (session 5, continued — practice fixes before the merge)** — Robin play-tested and gave two practice-session fixes wanted before merging refactor2, plus one live bug report:
  - `7dd3e96` — **(a) separate-note dip gate:** two unlinked notes were coverable by one continuous hold (Song of Storms' long-A5 → short-A5). The next bar now parks in a "dip" state when the completed bar's tone could continue straight into it (pitch within `transientCents` of `doneHz`); legato between genuinely different pitches stays free, chains/ties never gate, rests produce their own gap. **Robin field-tested round 1 and demanded shorter/shallower** → retuned to "a full stop OR a notch to `dipFrac` (50%) of an `holdRms` EMA of the current hold level", sustained ~one detection frame (60 ms) — a tongued articulation now counts while a mic wobble cannot fake the referenced drop. dipMs/dipFrac live on the debug panel (AUG pattern). **(b) zen-return seat:** closing + re-entering Zen mid-session rebuilt the live card at the song's FIRST tone while the tuner stayed mid-song (`liveIdx=-1` seed fell back to `firstSoundIdx`; practice only highlighted on its own events). The live tab now seeds from an active practice session (`OCA_PRACTICE.spot()` → frontier zone token; module-scope trampoline like the other surfaces) — card AND focus strip; idle falls back to the first note. Red→green both: `tests/practice_dip.py` (5 cases: hold-through blocked w/ seg0==0, silence dip, legato free, 75% duck shut, 40% dip w/o silence) and `tests/practice_zen_return.py` (card '0' vs spot 2 red pre-fix) — both registered in CI (24 suite steps now).
  - **Gotcha recorded:** module-scope `export {}` cannot name IIFE-internal bindings — the first `practiceSpot` export threw "Export 'practiceSpot' is not defined in module" (Robin caught it in his preview: practice.js:1431). Fixed with the house trampoline pattern. Also: the suite's own early-resolve `holdMs=0` fired instantly (0 > 0 immediately true) — gated on `holdMs > 0`.
  - `157c444` — **zen entry reset the practice seat** (Robin's field report, with the decisive observation: exit → single shows the RIGHT card; RE-ENTRY → first note): the fullscreen sync's `stopMelody()` tail re-cued playback's pickup — `clearHighlight(); cueFirstNote()` to token 0 — which also rewrote the same `liveIdx` the card seeds from. The real-fullscreen path was unreachable in headless (fullscreen refused → CSS fallback → the call never ran), which is why every synthetic zen round-trip probe looked clean while the real fast track lost it. `cueFirstNote` now cues the active session's `liveSpotIdx` (practice-aware pickup — the tuners' cue semantics: first note only when nothing is running). `tests/practice_zen_return.py` gained the stopMelody leg (red verified). **SW VERSION bumped v2** — this deploy's changes must land on the FIRST reload, not SWR's second visit (answers Robin's stale-cache question: served pages were serving the previous cache mid-afternoon; file:// has no SW).
  - `2351bad` — **the in-card tuner band is Zen's mechanic (Robin's design call):** practice engaged outside Zen then flipped to single absorbed the tuner into the card's meta strip (scale+track only, no face — read as "overlay disappeared"). The seat decision now requires a zen-covered layout (real fullscreen / focus class / CSS fallback zen); grid/scroll/plain-single keep the floating overlay face; entering fallback zen re-seats in-card, leaving restores the float. Overlay-seat leg added to the zen suite (red pre-fix).
  - Sweep: **24/24 green** after every step (the practice family re-ran standalone-first twice). eslint 0 errors / 4 warnings; html-validate clean. Note: the practice suites' boot-default displayMode is NOT single — suite probes starting in a non-live view must `setDisplayMode('single')` before reading live-card state (bit the stopMelody leg once — card None because it read a non-live sheet).
  - **Next:** push (first full CI flight: eslint + html-validate + 24 suites), then **merge refactor2 → main** and start the new branch Robin announced; M3 ear-check + the rest of the feel stack can ride on the merge.
- **2026-09-23 (session 5, part 3)** — **M3 support cut-bus audition passed**: Robin played a bracket-drone song through Zen with Stop/replay cycles — "no problems with the support"; the routed cut path is ear-confirmed. M3 fully closed (the last held-for-ears item). Hot list now carries only §9 F2 section looping (waiting on Robin's think) and the feel-stack leftovers (PWA install/airplane, theme/help/title bar, history line, highlight-plan eyeball, dip retune). refactor2 tip = `98fbd45` (Robin's "Update Saria's ocarina." tuning-data commit) on top of the session's 16 (`28eadd8..2351bad`: compat repairs, html-validate fix, practice dip/seat/overlay work), unpushed — Robin merges to main and opens a fresh branch next.
- **2026-09-23 (session 6 — refactor3 opens, working docs + agent rules land)** — `4bde7d9` merged refactor2 (run #4 push/PR flight: green incl. the first full 24-suite CI). Robin opened `refactor3` and set the agenda: working docs + agent rules into Git. Landed:
  - `6a2d9b3` — **plans/ becomes the committed progress/plans home** (TODO.md + IDEAS.txt moved out of the gitignored `research/` work-files dir; `research/` keeps the recordings/FFT/tone work files). TODO header reworded; IDEAS ownership locked in-page (Robin's file — AI never writes it; read fresh at pickup). **AGENTS.md at the repo root** — the distilled contract: board-first opening, batch-questions-then-self-sustained sessions (numbered multi-choice with recommended pick + free wording; new forks "held for Robin"), attribution by SHA/trigger/job, commit/PR styles, red→green, sweep-before-claiming, test-hardening lessons, sw VERSION rule, node-less lint tooling note, preview isolation, and the **context-budget line (glm53@vibe: watch ~300K, act/wrap ~350K, end early past 400K — Robin's observed quality decay)**.
  - `b828b94` — **console-hygiene boot check** (`tests/console_hygiene.py`, CI step right after Playwright install): 4 real boots must land with zero console errors/page errors/unhandled rejections except the manifest-derived tone 404 allowlist. Built exactly for diagnosis ORDERING (Robin's correction on the rationale): a sick page fails THIS check first with a named console error, instead of cryptic unit failures + phantom-cause theorizing. Synthetic tripwire verified; every real boot today leaves exactly one allowed miss.
  - Rule-14 wording reworked per Robin after the first draft ("green output while page is sick" had the direction backwards — the history was suites-failing → long theorizing with the F12 error sitting in view).
  - First sweep on refactor3: 24/25 (practice_accepts strict case 2 failed "did not complete/timed out" once under sweep load; console was CLEAN on the case when re-diagnosed, standalone double-green + diag run reached done-state — load-timing flake, watch).
  - Next: refactor3 CI first flight (push = Robin's), then section looping / transpose / MIDI import per the fresh-board picks; PR description for refactor3 is drafted (conversation) and follows the ?-refactor2 shape.
- **2026-09-23 (session 6, continued — skills + sweep runner)** — Robin's answers folded in: lint/sweep are commands, not research-prevention skills — lint is documented per OS in AGENTS.md, the sweep became **`tests/run_all.py`** (committed `a739a96`: auto-discovers suites, PASS/FAIL + timing per suite, fail-tails, substring filter, pycache cleanup; 25/25 green in one command). **`skills/` joins the repo** (`17bac0b`, agent-neutral): README concept + the two proven grok-workspace skills copied in (`midi-to-ocarina-tab` + stdlib `mid2tab.py`, `ocarina-melodies`) and the pending `wav-sound-profile` entry — **that skill is hosted on the Windows partition; Robin to copy it into skills/ on the partition**, then the §1 B5 chamber-fitting work and §9 F6 (MIDI import) open with their research pre-done. `.grok/` itself untouched (hitting Robin's private workspace stays his). Rule 16 of AGENTS.md is now the skills pointer (read the SKILL.md before redoing specialized research; refine in place). refactor3 tip: `a739a96`.
- **2026-09-23 (session 6, continued — the context meter)** — the 300K/350K rule was unenforceable by introspection (the model has no token meter), so the enforcement path changed: **`.opencode/plugins/context-meter.js`** (committed, SDK-neutral, syntax-checked under node 22; field-shape defensive because message accounting shapes drifted between opencode versions) writes `.opencode/context-usage.json` after every assistant message — `.opencode/*` in .gitignore got the plugins exception, the usage file itself stays untracked. AGENTS rule 18 now reads the meter. **Robin validates on next session start: the file must appear with zone ok.**
- **2026-09-23 (session 6, wrap — the meter is validated)** — `cf4386e`(+flight) landed the logging/calibration pass; Robin restarted opencode and **the meter files appeared on the first post-restart reply: context_est 317188 = tokens.total exactly, zone "watch" — the session was already past the 300K line, matching Robin's decay observations.** Stream facts (calibration dump): message.updated → properties.info with tokens {total, input, output, reasoning, cache{read,write}}; the vibe endpoint reports cache counts as 0; decoder now prefers tokens.total (fallback sum kept). **Rule 18 self-enforcement is real: any session can `cat .opencode/context-usage.json`.** Session 6 ends at zone watch per the rule: all work committed (plans/, AGENTS.md, console-hygiene, skills/, run_all, meter), TODO current. Next session's picks stand (§9 F2/section looping, transpose, MIDI import with the skills preloaded; Robin to copy the wav-sound-profile skill from the Windows partition into skills/).
- **2026-09-23 (session 7 — Windows partition re-commissioned)** — the toolchain audit on this partition after the Linux refactor stretch. Meter validated first — the rule-18 file appears with zone ok on the first replies here, so the session-6 milestone now holds on a second OS too. Store Python 3.12 discovered to have NO `py` launcher (`python`/`python3` resolve; AGENTS Windows section led with `py` and would have failed every session here) → AGENTS Commands rewritten to the partition's real facts with the sweep assuming `.venv\Scripts\python.exe`; `.gitattributes` commits the LF duality (`* text=auto eol=lf`, binaries `-text`-pinned) so the working tree renders LF on BOTH machines — before this, the partition's system `core.autocrlf=true` checkout-rendered CRLF and LF-inserting editing produced `w/mixed` files (the runner itself got caught mixed in the first audit pass), and a delete-tracked-files + re-checkout landed the whole tree uniformly `w/lf`; the full sweep then ran 25/25 green at ~204 s (first pass was 24/25 — support_accepts_brackets died on its own cp1252 encode of '≡' before a single probe; the runner injects UTF-8 into child env now: `2abfb45`). Lint pair green locally (eslint 0 errors/4 known warns, html-validate clean) with node 24 vs CI's pinned 22 (tool majors identical via npx). readme/instruments-README/skills docs audited: platform-neutral, mid2tab docs' `python3` resolves here; the `.opencode` skills already carry their own per-OS traps (song-transposing documents the PowerShell 5.1 no-multiline-`node -e` rule; tone-analysis scripts point at `C:\Program Files\Google\Chrome\Application\chrome.exe`, verified present). **Incident honestly logged:** the IDEAS scratchpad additions Robin had edited here (uncommitted) were lost by my delete+checkout LF-flip sequence after being un-staged — restored byte-for-byte from the captured diff and committed as `8460940` (his content, my recovery). The wav-sound-profile skill copy remains pending Robin's hands (skills/README placeholder in place). Commits this session: `85e34cd` (gitattributes), `8460940` (IDEAS restore), `2abfb45` (runner UTF-8), plus this bookkeeping log entry. Sweeps: first Windows pass 24/25; post-fix full sweep 25/25. **Next:** nothing Windows-blocked remains — lint/sweep/bootstrap/skills/docs all partition-verified; the session picks are still §9 F2 section looping + features per session 6's board. **Topology corrected en route:** the earlier sessions' "laptop" wording was an assumption Robin corrected at session start — the working docs are now timeless: environment facts only, no device story, nothing says which machine/partition runs anything (people reading the Git history need not know where any device lives), so all location mentions in AGENTS.md/plans/skills-README are re-anchored to neutral wording.
- **2026-09-23 (session 7, wrap — CI flight + the check-run lesson)** — push at `5f505cc`, run #54 (push/PR trigger, job "practice accepts the play output"): **green** — the first full CI flight for the Windows-readiness chain (eslint + html-validate + all 24 suite steps + console-hygiene). Robin greenlit a scoped command-fact in AGENTS.md's Windows section: CI failure checks are a one-query diagnostic (`gh run view <id> --log-failed` with fresh eyes), NOT run-watching — mid-flight runs get left alone (or asked for a re-run), because long silent poll commands in this shell read as stuck to a human seat (this session's actual lesson: one bogus flag — invented `--convertFromJson` — plus one ~20-min buffered-output poll that was alive but looked frozen). Repo state noted: origin still points at the pre-rename slug; GitHub redirects keep fetch/push/CI links working (old `Triple-Bass-in-C-Ocarina-Tab-Maker` name → `Ocarina-Practice`). Session ends partition-verified with the board's next picks unchanged: §9 F2 section looping, then the §9 feature stack (Robin to copy the wav-sound-profile skill into skills/ first when that work starts).
- **2026-09-23 (session 7, continued — skills inventory + tone-analysis lands in skills/)** — Robin asked for a machine-wide inventory of audio/music skills: the four committed keepers (midi-to-ocarina-tab, ocarina-melodies, song-transposing, tone-analysis) plus the discovery that the pending `wav-sound-profile` skill never existed as a file anywhere on this machine — the workflow existed only embodied (tone-analysis's fastloop scripts + tuned_params.json + the staged stageA–E artifacts in Temp\opencode, reproducible). Robin's resolution: the pending slot IS tone-analysis (he prefers that name), so `.opencode/skills/tone-analysis/` (gitignored opencode registration) was copied byte-identical into the committed canonical home `skills/tone-analysis/` (SKILL.md + 16 scripts incl. the five replica_*.wav calibration references, ~1 MB). skills/README: placeholder entry replaced with the real one and a canonical-home rule added (`.opencode/skills/` mirrors must be refreshed whenever skills/ changes). Concerning Hobbits question answered en route: the MIDI reader of that Linux success was always `mid2tab.py` (now `skills/midi-to-ocarina-tab/scripts/`), per the SKILL.md's Cello-channel + `A5/16t B5/16t A5/16t` case study matching the shipped `concerning-hobbits-short` body. Temp\opencode scratch (tone-fit outputs, one-off probes, superseded song drafts) judged burnable — untouched pending Robin's nod.
- **2026-09-23 (session 7, continued — the transposer rewritten + a suite)** — Robin suspected the song-transposing skill was outdated; the honest verdict was worse: the ES-modules migration (`57de8cb`) had KILLED it outright (bare `eval()` of a now-ES `js/parse.js` died on the first `export` token). Robin's cheap-unit-test idea (reuse the JS input-syntax check) materialized as `tests/transpose_skill.py` — pure stdlib, drives the real scripts over a synthetic songs.json sandbox (no browser), skips named where node or scripts are absent — and it caught the dead loader on its first prior red. Fixes to `skills/song-transposing/scripts/` (now the CANONICAL committed home; `.opencode/skills/` is the refreshed byte-identical runtime mirror, CI sees the committed copy): loader strips multi-line export blocks and reads parse.js THROUGH its windowed compat block (shim `var window`, then `window.parse` — robust against const-trapped vs leaked declarations, guard fails loudly if the surface moves); bracket masking now stashes every `[...]` span wholesale (the old sentinel-around style still let the rewrite regex reach `C2` inside `[C2/4.]` — it only ever survived because plain-text labels rarely look like notes); s-form accents transpose and re-spell sharp; written entries spread-inherit ALL source fields (tempo/tick/swing/hidden) overriding name/group/body; transpose fails loudly on bad chips; verify_song gates on bad chips too. Robin locked the semantics + a chart-pair invariant: supports (labels/bar/inline/[-/2]/[~..]) stay VERBATIM as instrument-pinned chambers; the `dummy-bass-c-double` (A3–C6, 28) ↔ `stein-double-alto-c` (A4–C7, 28) pair maps by a guaranteed +12 up / −12 down — the alto chart IS the bass-double chart one octave up, so window math is unnecessary for that pair; suite pins both directions on real charts. CI gains the step (run_all discovers automatically); skills/README index gains the skill; SKILL.md rewritten (charts table incl. pair invariant, locked semantics, updated loader/masking traps, usage paths → skills/, suite listed in the checklist). Suite green post-fix; full sweep re-run to claim green. No shipped app behavior touched — sw.js VERSION stays. Robin also weighed removing `skills/ocarina-melodies/` (felt redundant): kept + reframed instead — its notation/ranges/entry-shape parts ARE covered by the song-transposing rewrite, but the hand-transcription craft (bar balancing, tie-split token rule, loop rests, `# swing` loader behavior, chamber-jump octave choice, staccato semantics) is unique and the midi skill depends on it; skills/README's bullet now names the craft instead of the redundant grammar summary.
- **2026-09-23 (session 7, continued — ocarina-melodies up to toolkit truth)** — per Robin's directive ("up-to-date truth where it concerns our features in writing music — not theory, tool application") the SKILL.md was rewritten to the current toolset: full notation table (s-forms, ties/slides/staccato/dots/triplets/bad-chip gate), the WHOLE support-bracket family with its Zen-only playback and never-transposed rationale, `tick` semantics confirmed from library.js (per-song metronome state; `"tick": false`), `hidden` as the WIP carrier, `# tempo` mid-song lines, section labels; fit table generalized across all five charts incl. the dummy/stein +12 pair and the chamber-jump octave rule; transcription craft preserved verbatim in spirit; a new "Player-facing formatting conventions" section defines the house target Robin planted — **barline OPENS the wrapped line** (`| A4/4 B4/4 ...`), cosmetic today since the parser reads `|` positionally (shipped bodies bar-at-line-end parse identically) — and TODO §9 gains the standardization pass item (later stage, player-facing, suites as gates). skills/README bullet reframed second time (craft + notation truth).
- **2026-09-24 (session 8 opens — urgency readout + the SEO lift)** — Robin asked what is urgent across TODO + IDEAS (both read fresh): the verdict — the ONLY deadline-bound item is the SEO perma-link scheme (November Switch-2 OoT launch ≈ 5 weeks; his own rule: good permanent links BEFORE crawlers are invited), with the 12-hole completeness coupled by dependency and the push/CI loop + eslint tighten actionable immediately. Robin then lifted the SEO block explicitly: **refined into TODO §9** (slug freeze as the link contract → per-song static stubs with 12-hole-first targeting → og/meta song-title theming → crawlers invited only after links verify → Lighthouse as the audit) and joined the hot list as row 10; the rest of the pool stayed self-scheduled (section looping, feel stack, UX batch, themes, small-screens, pre-caching). IDEAS.txt untouched per the rule.
- **2026-09-24 (session 8, continued — the slug contract locked + enforced)** — Robin answered the naming forks and added the category dimension: URL = `/song/<category>/<base-slug>` (12-hole C alto is the default player when only a song is given; future ocarina families — single/double/triple/quadruple, soprano — extend markers, never rename bases), closed suffix list, and public links carry the CATEGORY so per-category theming keys off it (zelda → Hyrule; the "Zelda on Bass"/"Zelda on Alto" groups collapse to one token; others default to Plain/new). Landed: `tests/shipped_songs.py` gained the slug-contract leg (grammar + closed suffix set + chain rule: every variant strips ONE suffix and must name an existing key; tripwire proven inline against synthetic bads since the shipped corpus is expected clean) — its red run immediately corrected the design: `concerning-hobbits-short` is a BASE (content words are base material, not suffixes), `short` left the suffix list, suite green; the `-alt`/`-alto` spell split fixed pre-index with zero code references (major-alto/chromatic-alto renamed in songs.json only); the frozen contract documented in `skills/ocarina-melodies/SKILL.md` (new "Song slugs" section), SEO TODO bullet updated to progress-tracking shape. The static-stub generator + og/meta + robots stages remain open, deadline ~5 weeks.
- **2026-09-24 (session 8, part 3 — the serving layer)** — Robin corrected the substrate: main HAS been the served site from the start (the /plans 404 on probe was misleading), and "I want Actions/scripts to decide what to deploy — include only the stuff that should be served and keep such a nasty dir structure out of Git". The debate covered crawler mechanics first (?song= URLs are distinct and JS-renderable by Googlebot but preview bots read raw head tags only, discovery needs links/sitemaps, duplicate param combos need canonicals — why paths were chosen over params) and the stub approach's own cons (freshness vs git churn, thin-content mass, no-server-redirects, category tokens as a second freeze) — landing on: **Actions artifact deploy with an explicit content allowlist** (the workflow file IS the allowlist: only app content + the generated song tree serve; docs/plans/tests never publish), stubs generated at build time and git-ignored (site/), Pages source flip to "GitHub Actions" is Robin's manual one-time cutover, deploy triggers = served-content paths + manual dispatch. Landed: `tools/gen_song_pages.py` (shell-only v1 per Robin's pick; one real fix found during review: relative canonical would double-nest under the stub's document base — canonical/og:url now carry the site prefix `/Ocarina-Practice/` matching the verified live URL; description replaced not duplicated), `tests/gen_pages.py` (stub-set exactness vs songs.json, seed/canonical/og/roots contracts, byte-determinism; CI-registered), README's Deployment paragraph rewritten. App code untouched ⇒ no sw VERSION bump. Cutover order: push → Robin flips Pages source → watch the run at the deployment URL.
- **2026-09-24 (session 8 wrap, on the new refactor4 branch — Robin asleep, evening work authorized)** — Robin forked refactor4 (origin main at the merged PR #6/#7 chain), removed the C-major/chromatic "songs" from songs.json with the direction "they generate on-the-fly for the selected instrument, default 12-hole" and left low-risk evening picks authorized. Landed in three commits: (1) `8524e0e` the family re-key — clean bases now carry ladder-default arrangements, bass bodies in -bass keys, -alto aliases gone; home-default hardcoded id + the svgWhen/practice/ship suite references retargeted (the saria id-path leg pins an exact-id match now); (2) `b8f0b98` **scales become generated tools**: library.js `refreshGeneratedScales` synthesizes BUILTIN.major/chromatic per loaded chart (major = minus black-key ids, s→# display, tempo 120) on every fingerings install; the boot-order inversion (refresh mutating the pre-initBuiltin object, wiped by the swap — caught with a probe counter) fixed by initializing BUILTIN before the first loadInstrument; red→green pin in instruments_load (exact bodies on the default + regeneration after switching to the stein); shipped_songs waits for the synthesized pair; gen_pages drops the nine scale services and suppresses family -bass members (leaf -bass keys keep theirs); (3) this commit — **eslint no-unused-vars tightened warn→error** with the last four names out (app.js's unused parse import, audio.js's dead rewindMelody and its then-orphaned firstSoundIdx import, practice.js's unused dg, ui.js's unused perf import — the sweep's first CI counts settled long ago, §6 note resolved); **sw.js VERSION → oco-pwa-v3** (rule 15: app runtime changed, first-visit caches must flush); skill takes the generated-scales note; full sweep 27/27 green. Held for Robin: his fresh unstaged IDEAS.txt edits; the "wrong song of time"-class landing re-verification on the redeployed site; the -contrabass marker rule (no shipped body needs it yet).
- **2026-09-24 (session 8, part 4 — the live URL teaches the serving layer its real lesson)** — first live landing stubs deployed; Robin probed `/song/zelda/song-of-time/?song=…&inst=…`. Raw head verified (stub title/og serve correctly) but the headless boot check exposed what string contracts never could: **runtime fetches resolve against the page, not the site root** — `songs.json`/`instruments.json`/css-text/manifest-driven instrument files 404'd two directories deep and boot died. The `<base href>` fix re-roots everything (attrs, modules, runtime fetches, SW registration) with zero `js/` changes; the root-absolute alternative was rejected deliberately (needs the baked `/Ocarina-Practice` prefix in head AND app code so the artifact stops being relocatable). Nothing was green on faith: the same check showed `#scale.value` empty on a booted stub — Song of Time's bass body is out of range on the 12-hole, so the dropdown cannot represent it; Robin corrected the landing-default design on the spot into the ordered ladder (12-hole > double alto > triple bass > contrabass; Song of Time lands on the triple, playable, no range marks). `tests/gen_pages.py` now boots a REAL artifact (suite assembles the workflow's allowlist, serves it under the /Ocarina-Practice mount, playwright boots the stub): right song, right instrument, zero `.card.oor`, cards/chips rendered, body head present, console clean except 404s that must ALL be tone.json — and the fix taught the allowlist's true shape: a tone miss is *permitted*, never *required* (the triple's tone.json exists; a healthy boot may have zero 404s). Both files committed; next verification is the redeploy of the corrected generator (push fires the content-path trigger; Robin can also dispatch manually) and re-probing the live URL.
- **2026-09-24 (session 8, part 5 — the wrong-song fix + the every-URL boot)** — live probing showed the Song-of-Time landing booting the BASS body (the base slug seeded regardless of fit). Robin's calls, implemented: (1) landing seeds the FAMILY member that fits the ladder's chosen instrument (base slug preferred when it fits: `/song/zelda/song-of-time/` boots `song-of-time-alto` on the 12-hole; BotW's alto arrangement clears only the double alto's range so it lands one ladder step down — exactly why the ladder walks families, not just bodies); (2) `zelda-lullaby`/`kokiri-forest` become `zelda-lullaby-bass`/`kokiri-forest-bass` NOW (Robin: `-bass` for everything below the 12-hole, `-contrabass` when lower is needed — the leaf bass songs rename cleanly since nothing chains through them; mixed families keep their heads until the grace-period naming wave, and `-bass`/`-contrabass` stay UNREGISTERED suffixes until then, documented as planned markers in the skill contract section). The suite red run caught a real liar on the way: `body_note_ids` emitted DISPLAY sharps (`F#5`) while chart ids are s-spelled (`Fs5`) — every accidental note failed chart membership, only the all-white-key Song-of-Time-alto boot masked it; the spell fix turned the matrix honest (10/10 landing boots: right arrangement, zero `.card.oor`, clean console). Suite rewritten as Robin requested — **every base-name URL must boot with no out-of-range error** — plus the computational ladder table printed and pinned through the imported picker. TODO note: a splice error during this entry briefly ate session 7's Next sentence mid-entry; repaired in place.
- **2026-09-24 (session 9 — Robin at work; the mojibake sweep)** — Robin committed the IDEAS note asking to fix the `â€`/`Â` mojibake "that got committed by AI that replaced non-standard dashes" (`b6374aa` 08:30) and left autonomy to pick up work. Picked exactly that: a repo-wide scan (all 96 tracked files) found 161 mojibake tokens in 4 files — js/audio.js comments (132), tests/practice_accepts_melody.py (19), tests/shipped_songs.py (6), tests/transpose_skill.py (3) — 11 distinct tokens (— → – · × ≈ − ↔ ± ≡ …), each the classic UTF-8-read-as-cp1252 double-encoding of dash/arrow/metric glyphs. Fixed with the exact cp1252→UTF-8 round-trip token map (no other bytes touched); post-scan finds zero remaining; diff verified comment/string-only (144/144 line exchanges); lint pair + full 27-suite sweep green (218 s). `e10d49b`. plans/IDEAS.txt untouched (Robin's own note names the artifacts literally — the fix never needs to edit his file). **Held for Robin → RESOLVED 2026-09-24:** Robin — "don't care as long as it does not affect functionality" — the restored proper glyphs stand (his division of labor on file: he writes ideas, the AI refines them into TODO entries and implements). Suite-stdio note: the fixed strings now print real glyphs again, which is exactly what the runner's UTF-8 child-env was built for; standalone runs keep needing PYTHONUTF8="1".
- **2026-09-24 (session 9, continued — og/meta stage + the sweep-load rendezvous)** — autonomous units on refactor4, all unpushed (pushes are Robin's):
  - `89a39f0` — **§9 perma-links: the og/meta stage of the plan completed.** gen_pages red first (5 new tags × 8 stubs), then the generator: og:type website, og:site_name "Ocarina Practice", og:description sharing the meta description's wording (the one-description rule holds), og:image on the already-generated icon-512 with width/height/alt, twitter:card summary. Injection moved to the END of `<head>` (the shell's charset/meta keep their first-KB positions). Byte-deterministic; all 8 stubs still boot ladder-correct, zero out-of-range, clean console. URLs remain site-prefix PATH form for canonical/og:url/og:image (relocatable; fully-absolute held until a domain is pinned — noted on the plan line). Nothing here deploys from the branch: live evidence still needs Robin's merge/push + redeploy verification.
  - `335c4b4` — **support_accepts sweep-load flake cured the honest way.** The full sweep failed the mixed-song leg twice with an identical signature (events stopping just past the first support boundary; melody tail gone) while standalone and filtered runs were green every time — load-rate, not playback (console-hygiene was clean inside those sweeps). Diagnosis: fixed wall-clock read window meeting audio-clock lag under sweep CPU contention. Hardened test-side only: per-event wall-fire stamp + audio-clock snapshot at read (any future red names the lag plainly) and the read became a REAL rendezvous (hardening convention): historical wait stays as floor → 250 ms poll until the scheduler's auto-stop (loop cases: their expected support fire-counts) → +30 s ceiling. Sweeps 27/27 twice after; healthy-run duration unchanged (69-70 s); no weakening — a tail-cutting bug or a hang still fails, just slower and louder. Suites pass only via the runner (UTF-8 child env).
  - `75c5f0a` — **§6 T4 closed** (last open test item): two boot-flow legs in `tests/instruments_load.py` — a bare `?song=eponas-song` must boot the arrangement on the manifest default, stay in GRID and out of zen; `?song=eponas-song&zen&nofs=1` must land in the pinned CSS-fallback zen with the single view armed (and never a partial zen state). Both assert the loaded title, the `#src` body head, zero `.card.oor` on the 12-hole and exactly one checked mode radio — the deep-link paths the landing stubs and shared zen links ride (their `?song=…&inst=…` seeded form already had gen_pages' real-boot coverage). Green on first run; full sweep 27/27 after (222 s). A duplicated diagnostics comment in the same file left with the edit.
- **2026-09-24 (session 9, part 4 — the spike watch ships)** — the away-work pick after the batch answers: the tick hunt's detector, test-first. `tests/spike_watch.py` (red on the missing surface) → `17fae24`: the pure classifier module in audio.js (its TWO real step shapes were a mid-flight discovery — a value-step to a new level is ONE delta, a single-sample excursion is a mirrored pair; the first draft's isoldation rule rejected the real step and was rewritten), the 20 ms sampler over the post-limiter analyser (overlapping windows = full coverage; dedupe 200 ms per event; sysSound windows subtracted), state cards + the 'Signal spikes (ticks)' perf row + spikeFake() for suite probes; playNoteAt gains a recent-onset ring feeding the cards; sw VERSION → v4; CI step registered; lint + full sweep 28/28. **Suite-tooling lesson recorded:** a Playwright wait_for_function predicate must yield a SERIALIZED value — a predicate that returns an AudioParam-style module FUNCTION object serializes to null and the wait never fires (the probe returned truthy while evaluateHandle held the object); the spike suite's BOOT_WAIT now compares typeof === "function" explicitly. Also noted in evidence: the late-scheduling guard at playNoteAt (audio.js:1053-1058) already documents one collapse-to-step class with its 15 ms live-lead mitigation — part of the same neighborhood the card will discriminate against the re-anchor suspects.
- **2026-09-24 (session 9, part 5 — Robin returns; M1 cluster 1)** — Robin home, steering confirmed, M1 answered-then-proceeded. Landed `a6b15c0`: `js/music-math.js` (midiOf/freqOf, one source), audio re-exports the binding (ESM + windowed seams intact), ui's noteMidi wraps it with the 69 fallback, practice's freqOfId duplicate with its typeof guard deleted, parse.js's copy kept DELIBERATE (the transposer skill's raw window-shim eval cannot carry imports — documented at the shared site); sw precache takes the new module + VERSION → v5; sweep 28/28 + eslint clean. Clusters queued next on the same item: grid-beats (audio vs practice), quarter-seconds (ui vs audio), play/pause DOM writes (audio vs ui).
- **2026-09-24 (session 9, part 7 — the domain + R5)** — Landed `8c3c89b` — §2 R5 CLOSED (red→green, `tests/audio_state.py` in CI, all six creation sites watched; the first draft's attach-wrapped-new rewiring recreated contexts and paused every melody — caught by the transport sweep red, fixed, 29/29 sweep green). The custom domain `ocarina-practice.com` is registered along the forever-perma rule (registrar and registration details stay out of this public repo on Robin's call) and hosting remains GitHub Pages — going custom is only DNS records + a Pages settings flip + a CNAME file in the deploy artifact, nothing else moves.
- **2026-09-24 (session 9, part 6 — the scales order fix + the rename batch posted)** — Robin home. Priorities from him: SCALES first, tick hunt PARKED until he researches actual devices, website rename HIGH-priority questions asked up front (his IDEAS BRANDING note ponders "Robin's Ocarina Practice"), lifecycle + M1 clusters authorized, no §9 features, feel-checks tomorrow; a follow-up session will split completed tasks into a separate DONE file. Landed `bee525c`: the scales dropdown fix (red→green, library suite leg). The rename question batch went out in-channel.
- **2026-09-24 (session 9, part 8 — domain groundwork + the serving-contract switch)** — `ocarina-practice.com` bought. Privacy facts worth keeping: public whois carries GDPR-redacted registrant data (EU registrars must redact — no paid privacy product needed) and the free GitHub domain verification is the takeover guard, so a paid 'domain guard' bundle is not required. Landed `e7718bc`: CNAME in the artifact, `--site-origin` in the generator (default the domain) with absolute canonical/og and root base href, suite re-pinned against a root mount; README names the domain. Robin's cutover checklist (push → deploy → DNS → Pages flip → HTTPS → verify domain → re-probe) logged in the plan item. Fall-back to project-page serving preserved behind the old knobs. Standing convention: purchasing details (registrars, prices) never enter commits or the board — this public repo serves strangers too.
- **2026-09-24 (session 9 wrap — the privacy rewrite + the parked domain branch + M1 finished)** — (1) Robin: purchasing details had entered the domain commits' titles and board text — the four-commit tail (0f811ae..21c84bf) was REWRITTEN (all own unpushed commits): IDEAS.txt stashed both times, tree reset to 8c3c89b, the tail replayed as c96965a (sanitized part 7) → e7718bc (the domain serving contract, labels identical) → fd9f6dd/rebased + AGENTS rule-7 purchasing-privacy rule. Lesson harder than the LF incident: the reset --hard ATE the uncommitted M1 cluster 2/3 edits (the snapshot covered TODO/CNAME/workflow/tools/tests/README but not js/*) — rebuilt exactly from the session's own edit record and re-verified 29/29; NEVER reset a dirty tree without a full-diff snapshot. (2) Execution order on Robin's "you decide": the domain serving contract is PARKED on branch `refactor4-domain` (tip `e7718bc`) — refactor4 (tip `938bc6f`, five commits ahead) is mergeable NOW and keeps the live landing stubs healthy at the /Ocarina-Practice path while the .com finishes provisioning; the domain branch merges right before (or with) the Pages custom-domain flip. Old amended-away commits linger only in local reflog until expiry, never pushed. (3) Suite state: 29/29 on the rebased tip; gen_pages pins the project-page contract on this branch and the root/domain contract on the parked branch. (4) Robin's next session: refinement pass + a DONE-file split of completed TODO items.
- **2026-09-24 (session 9, part 3 — the batch answers + the tick hunt)** — Robin's steering round folded in: (1) mojibake restore confirmed unnecessary to flatten ("don't care as long as it does not affect functionality"), held item RESOLVED on the board; (2) **§9 F2 section looping DECLINED**, entry kept for a possible revival; (3) robots/sitemap staging re-explained in-channel (doors stay shut until the corrected stubs verify live — his crawl rule); (4) §2 R5 AudioContext lifecycle explained in-channel (suspension mid-session stalls the audio clock while the scheduler keeps timing against it — UI keeps claiming playback), still awaiting his build/no-build call; (5) his field reports of **sporadic single-frame ticks (current note silenced after each, Lite-invariant on his phone, perf screen always silent)** became a NEW §2 item with a ranked suspect list (AudioParam event-timeline re-anchoring of a live envelope first — the cancel/implicit-ramp neighborhoods with their real-hardware history) and a debug-only spike detector plan that will name the seam once Robin catches the next one. (Field confirms 2026-09-24: playback CONTINUES at the next note — voice-seam class; the same song does NOT reproduce consistently — a timing race, not a per-note mapping error; observed on MAIN — pre-existing shipped behavior, independent of the refactor4 chain; repro ~every 2 playbacks of Concerning Hobbits short in Google Chrome, not reproducible in VS Code's embedded browser — an engine-timing sensitive race.) No app code this part; board only.

- **2026-09-24 (session 10 opens — the DONE-file split, rename-first)** — Robin pulled
  main (refactor4 merged at `df6a3c0`) and forked `session5`; the logged DONE-file split
  executed with his rename-first refinement: the OLD TODO.md wholesale became
  `plans/DONE.md` (byte-identical snapshot — only the H1 heading and a preamble changed;
  the session log through session 9 and every struck item preserved with zero reassembly
  risk, including frozen declared-non-authoritative copies of the 17 then-open items),
  and the open work was extracted back out into this fresh TODO (17 open items, standing
  conventions + color legend, a 4-row hot list renumbered). Batch answers applied: full
  purge on the TODO side, DONE as sections+log mirror, cross-refs point back, AGENTS
  rule 1 now names DONE.md. Future convention: a completed item moves into DONE.md at
  the same bookkeeping moment it completes; this log retires entries once the next
  session has opened from them. Plans-only commit — no app code touched, no sw VERSION
  bump, suites not run.
- Next (session 9's logged shape): the refinement pass across the open board; then the
  feel-check stack (hot row 2), §9 feature picks (row 3), and the SEO deadline row 4.
- **2026-09-24 (session 10, part 2 — the board went scriptable)** — Spar with Robin
  folded into `tools/board.py` (stdlib, both partitions) owning the structural moves:
  `complete` (strike + ✅ date/SHA + insert into DONE's matching § head, refuses
  ambiguous or absent title prefixes and strikethrough-marked bodies), `add`
  (single-line item, before §9's standing blockquote, duplicate-title guard), `note`
  (in-place finding before the trailing tag span), `tag` (ASCII words —
  severe/moderate/minor/cosmetic/measure × next/soon/later/idle × s/m/l — re-score the
  span), `log-add`, `log-retire` (moves all but the newest entry into DONE's log), and
  `verify` (single-line items + tags grammar, no corpse in TODO / no frozen open item
  in DONE, heads 1–9 both files, unnumbered hot rows, log stub present). DONE lost its
  17 frozen open-item copies (the rename-first cost — completing R4 would have collided
  with its own twin); the hot list dropped row numbers (no renumber obligation); the
  log stub went generic; AGENTS rule 3 synced to move-at-completion and names the tool;
  `verify` + `tests/board_tool.py` (8 pure-stdlib sandbox cases) registered in CI
  before the Playwright install. First dogfood ran green: A6 long-press's missing tag
  span set to `🟨 🟠 ⚙S` via the tool. First real tool bugs caught by the same setup:
  `_items` used an undefined list name, the test registry's decorator returned the
  wrapper function (0/0 cases until spotted). CRLF/`\r` inputs refused everywhere.
- Next: refinement pass across the open board may lean on the tool everywhere; new
  findings ride `note`, re-scorings ride `tag`, completions ride `complete` (TODO line
  leaves, DONE gains the struck archive row).
- **2026-09-24 (session 10, part 3 — refinement round + tonight's hands-off orders)** —
  Robin live on the batch: (1) BRANDING settled — the product stays "Ocarina Practice"
  (og:site_name already right); the "branch or stash" holding the code-switch he
  remembers is `refactor4-domain` (tip `e7718bc`, parked until the flip). (2) §2 R4
  re-framed to the CI-side validator shape — item text updated. (3) The IDEAS BUGS
  block lifted into §2 R10 via `board note` (orientation-flip repro on the phone,
  multi-tick bursts, visual-processing suspicion, the waveform question; the spike
  watch has not met the phone yet) — that IDEAS block is now clear for Robin to delete,
  as are its SEO block, Lighthouse line and BRANDING line. (4) New §9 F-items lifted:
  instrument switch auto-selects the in-range song (approved build) and the
  octave/transpose twin-bodies dedup (Robin's "nice touch" — SURVEY-only tooling first).
  (5) TONIGHT'S HANDS-OFF ORDERS, run until the context rule says wrap: no pushes
  (Robin's ops); no MIDI implementation (tooling-for-Robin only); no SEO feature stages
  (robots/sitemap wait until the domain-switch WORK finishes; the switch itself is
  TOMORROW'S JOINT session — Robin: the flip has never succeeded solo, so nights prep
  only). Unit order: (a) instrument-switch auto-select song, built + pinned; (b) the
  R4 CI-side data validator suite (pure stdlib, registered in CI); (c) refactor4-domain
  diff summary + the F8 cutover checklist kept current + a live-verify tooling probe
  (prep for tomorrow's joint switch); (d) the octave-twin dedup audit tooling (report
  only, no song-data edits). Every unit: red→green where behavior changes, full sweep
  before claiming green, board current per unit, session log per unit, all helds
  respected (no audible changes; tick hunt parked until Robin's phone research;
  feel-checks need his devices).
- **2026-09-24 (session 10, part 4 — the night's queue extended)** — Robin confirmed
  the extension since the four ordered units may finish early: after the ordered list
  the night continues with (5) §5 M9's last cluster (play/pause DOM-writes dedupe —
  mechanical, suite-covered), (6) the rule-15 sw-VERSION audit (sweep commits since
  `oco-pwa-v5` for shipped behavior, bump if stale, offline suite green), (7) §4 P7
  enlargeSmallHoles precompute, (8) §3 print-popup `document.write` → DOM injection,
  re-checking the eslint warning count as a rider on whatever code unit touches.
  Stretch pick with hours left: §9 F6 transpose (inaudible, suite-covered). §9 F4
  standardization is HELD for its later-stage pass by Robin's call. Unchanged holds:
  no pushes, no MIDI implementation, no robots/sitemap, tick hunt parked,
  measurements/feel-checks need Robin.

- **2026-09-25 (night session 11 opens; unit a — the wet-switch song jump)** — the ordered
  away-work ran: instrument switches now auto-select the in-range family member (§9,
  Robin-approved build). Red→green five-leg battery added to tests/instruments_load.py
  (jump alto→bass, stay-when-fitting, jump bass→alto, no-fit-keeps-the-editor, typed-text
  untouched; every leg also pins isMelodyPlaying() false — no transport starts from a wet
  switch). Implementation: library.js songFitsChart (every melody token id must be ON the
  chart — stricter than the OOR badge's compass count) + the load-path tracker
  lastLoadedId/loadedLibraryId (loadLibraryItem writes; clearLibrarySelection clears —
  the ?song deep-link case needs it because a range-hidden song sits in the editor with
  the dropdown silently unselected, which is exactly where the first green attempt
  stalled); app.js songFamilyRoot/songFamily walk the landing-stub family from the
  SHORTEST existing prefix id and switchInstrument jumps on fillLibrary→loadLibraryItem
  order, staying put when the current member fits or nothing fits. Member order mirrors
  tools/gen_song_pages.py: base slug, then variants alphabetically. sw VERSION → v6
  (rule 15). Sweep note: the full 30-suite sweep ran 29/30 with board_tool red on a
  day-rollover time bomb (its own assertion hardcoded ✅ 2026-09-24, green for the last
  time yesterday), defused by injecting complete's --date; board_tool 8/8 after; the
  night's true app suites all green (instruments_load, library_hardening,
  instrument_switch_race, render_pin...). Lint clean. Commit `4ddeb1f`.
- Next (night queue): unit b — the R4 CI-side data validator suite; unit c — refactor4-domain
  cutover prep; unit d — octave-twin audit tooling; then the extension items
  (play/pause DOM-writes dedupe, sw VERSION audit, enlargeSmallHoles, print popup).

- **2026-09-25 (night session 11, unit b — the R4 data validator lands)** — the reframed
  §2 validator is built: tests/data_validator.py (pure stdlib, no browser, no runtime
  gate) — a sandbox battery of 12 named defect classes (good corpus clean; duplicate
  JSON keys via an object_pairs_hook refusing the silent last-wins collapse; unique
  instrument ids; missing declared fingerings/svg files named with their declarer;
  note-id grammar fronting the s-spelling convention ('Fs4' never 'F#4') with octave
  required; duplicate note ids; strict ascending chart pitch; covered arrays resolving
  real holes; tone.json present-but-corrupt caught while the deliberate-404 declarations
  stay allowed; svgWhen rows pinned to svg + a song/songTitle anchor; songs.json
  name+body presence with typed scalars; bad default id) and the shipped real corpus
  running clean. Deliberately NOT duplicated here: the slug/suffix/chain contract
  (tests/shipped_songs.py owns it) and any body-grammar parsing (parse.js owns it).
  Registered in CI in the stdlib region beside board_tool, before the Playwright
  install. Commit `f62ede5`.

- **2026-09-25 (night session 11, unit c — cutover prep for tomorrow's joint flip)** — the
  three prep deliverables for the domain switch landed on the SEO item as a note: the
  refactor4-domain merge-surface summary (one commit `e7718bc` over `c96965a`; five
  files: deploy-site.yml, new CNAME, README, gen_pages suite+generator; zero overlap
  with refactor4's merged files → clean merge), the checklist currency statement
  (unchanged; tonight's session5 stack pushes also fire the artifact on served-content
  paths, DNS/HTTPS order unaffected), and the brand-new live-verify tooling
  `tools/verify_site.py` built, debugged and used: it reads the DEPLOYED songs.json
  (never local), checks the shell/js-app entry, every stub's base-href/canonical/og:url
  agreement on one serving prefix (prefix derived from --origin, so pre- and
  post-flip stages share the contract) and playwright-boots sampled stubs from fresh
  contexts. Tool-build findings worth keeping: (1) today's initial live state was a
  STALE artifact — home shell predated the PWA commit while /song/ stubs served; a
  push-triggered Actions deploy during the night refreshed it; (2) the boot leg hit
  the SW-claims-the-second-navigation hazard → fresh context per boot (the AGENTS
  rule-13 lesson now lives in the tool); (3) og:title's separator is an EM DASH
  (U+2014), the title-strip regex handles both — and Chromium's resource-404 console
  text is generic, so the tone.json allowlist reads m.location's URL, not message
  text; (4) stub enumeration must mirror the serving suppression (registered-suffix
  variants and -bass siblings of existing bases never get stubs; leaf -bass keys
  keep theirs). Pre-flip probe RESULT (after the redeploy): 18 checks green — 8/8
  landing stubs 200 with coherent heads, all 8 booted the right song on the right
  ocarina with clean console at /Ocarina-Practice. Commit `a62dc97`. Tomorrow's gate:
  the same tool with `--origin https://ocarina-practice.com`.

- **2026-09-25 (night session 11, unit d — the octave-twin survey is PROVEN)** —
  tools/audit_twins.py (report-only, self-check-battery-first, bodies untouched) walks
  every family pair + cross pair in songs.json: a pair classifies TWIN only on
  one-to-one token alignment with uniform melody deltas and every non-pitch token
  carried verbatim; unreadable tokens (the kokiri stray `g4/4`) refuse the verdict by
  construction rather than guess. FINDINGS: five octave twins (all four -bass bodies
  sit exactly one octave below their alto bases; botw-theme-vs-down3 too), three
  uniform non-octave twins (hobbits -c at -2, botw -bass at -9, botw -bass at -3 from
  -down3), zero other twins across the whole corpus. The derive-at-load question
  (variants keep hand-written bodies or derive from base) stays HELD for Robin with
  the report on the item; keys/URLs stay frozen in any case (permalink contract).
  Commit `33bd3fa`. The night queue advances to the extension units; meter said
  ~232K after this unit's read.

- **2026-09-25 (night session 11, unit 5 + 6 — M1 closes; sw VERSION audit clean)** —
  unit 5: the play/pause DOM-writes cluster resolved as a deletion (the #playMel
  element does not exist anywhere; the round mirror replaced the header's text
  squares — keyboard_widgets's squaresGone leg has pinned that absence all along),
  all four vestigial textContent writes left audio.js; targeted suites green +
  eslint. On the same unit the board tool itself gained its fix + pin: complete's
  --notes-file payload flag reaches the payload reader now (it only ever looked at
  the generic --file flag — refused complete's own flag in real use; sandbox case
  t9 pins both shapes). Board: the M1 dedup item strikes into DONE with the closing
  cluster shelf now EMPTY. Commits `504b42d` + `9a2ae0b`.
  Unit 6 (the rule-15 audit): the four ordered units + unit 5 land across commits —
  shipped-behavior changes since oco-pwa-v5: ONLY the wet-switch auto-select (unit a,
  bumped VERSION to oco-pwa-v6 IN the same commit). Everything after v6 is tooling,
  tests, board moves and the engine-unobservable dead-write deletion — no shipped
  behavior, no further bump owed; the offline suite will verify the v6 cache on the
  night's final sweep.

- **2026-09-25 (night session 11, units 7-8 + the wrap)** — unit 7: enlargeSmallHoles
  got its O(holes²) cure as record-and-replay (the sequential pass makes a plan
  precompute impossible — an enlarged hole changes neighbors' constraints — but the
  settled attribute writes record on the first big-view miss and replay by element
  index verbatim; bit-identical because hole geometry never touches the styling pass
  and the plan keys on the same svg epoch that clears the output cache). svg_cache
  gained the replay-purity leg; exact-restore pins stayed green. Commit `7a580ee`.
  Unit 8: the print popup rides a blob URL carrying the SAME bytes Download saves —
  document.write's deprecated sink gone without losing the standards-mode doctype;
  render_pin gained the popup contract leg (red on about:blank before, green after).
  Commit `94f6ddc`. FULL SWEEP 31/31 (235 s) after all units, offline_pwa green on
  the v6 cache; eslint clean (zero warnings). The evening re-deploy Robin triggered
  landed the fresh artifact mid-night and the live probe is green (unit c). The
  stretch pick F6 transpose is HELD for Robin — text-shift vs token-shift is a
  surface/feel fork with audible consequences (the note explains it on the item), and
  the budget rule: one more unit + sweep would cross the watch line with closings
  undone. Board: §4 P7 and §3 print-popup items strike DONE (14 open items). NO
  pushes made tonight (Robin's ops) — session5 carries the whole night's stack
  (a→8): `4ddeb1f` auto-select, `6c7ef6f`, `f62ede5` validator, `9ad9142`,
  `a62dc97` verify_site, `974e91b`, `33bd3fa` twin audit, `a8726ef`, `504b42d`
  M1 close, `9a2ae0b`, `4deb6cb`, `7a580ee`, `94f6ddc` + this wrap. Next session
  (the joint flip): merge/push order is Robin's; his manual checklist lives on the
  SEO item; the post-flip gate is `python tools/verify_site.py --origin
  https://ocarina-practice.com`.

- **2026-09-25 (CLI red diagnosis — the flake family's third member, cured by the rule-13 rendezvous)** —
  Robin's push of the session5 stack CI-fired red on practice_dip's FIRST leg only
  (run `36110497803`, job 107992645371, head `a802f10`): a 15 s timeout with the session
  flat at maxIdx 0, and the four subsequent assert lines were phantom consequences of the
  blind timeout resolve. Standalone local: green — so a race, not a regression. Fresh
  diagnosis: the suite's rendezvous (OCA_PRACTICE+NOTES) unlocks INSIDE loadInstrument
  (NOTES lands at installFingerings, but ensureOcarinaTemplate + the allowlisted tone.json
  404 still pend), and boot then owes fillLibrary(home)+loadLibraryItem(home) →
  practiceInvalidate — a session engaged mid-boot is killed by the tail a beat later; under
  CI's cold load the window lost for the first time in the family's history. Repro'd at
  will with CDP Emulation network latency (throwaway, deleted after); cured test-side ONLY:
  the #scale-options tail guard appended to practice_dip's rendezvous (options are filled
  only by the tail; a rAF poll can never resolve mid-synchronous-block — so the guard proves
  loadLibraryItem completed) + a state card (started/st/ix/frames) on every resolve. Same
  tail guard rode into practice_accepts_melody, practice_zen_return (3 legs),
  practice_history, keyboard_widgets and render_pin (the last needs typed editor text to
  survive the tail, others start practice). Not touched: library_hardening (already waits
  the Scales OPTGROUP — a post-tail signal), instrument_switch_race (the race is its
  subject), playback-only suites (practiceInvalidate stops practice, never play). Red→green:
  stall under latency with the old rendezvous, healthy engage under the same latency with
  the new one. Board: §6's flake note extended, hot row 1 dropped (the validator shipped
  `f62ede5`), hot list refresh dated. Full sweep 31/31 green (227 s). No app code touched →
  NO sw VERSION bump (rule 15). Queued for Robin's next push to session5.

- **2026-09-25 (joint flip session — the domain rock, then the crawler stage)** —
  Robin: "The new domain is active" then "what is live is main without the new code" — the
  flip landed on main (PR #9/#10 merges; deploy run `36117318574`) before the serving
  layer's newest truth. The ready gate went RED exactly as designed:
  verify_site --origin https://ocarina-practice.com found all 8 stubs serving but none
  booting (the workflow's baked `--site-prefix /Ocarina-Practice` stranded `<base
  href>`/canonical one directory too deep on the root-served domain), and the fresh
  crawler-stage legs reported robots.txt/sitemap.xml 404. Robin branched `domain-switch`
  and granted the unit + what unlocks: the flip contract fix (--site-prefix / +
  --origin in deploy-site.yml), the robots stage — generator emits sitemap.xml (home +
  every stub URL, byte-deterministic, no lastmod) and an absolute og:image (disambiguated
  flag --origin: og:image must be absolute; canonical/og:url stay origin-relative so the
  artifact stays mount-agnostic, and the legacy project-page mount stays a string-contract
  leg in gen_pages until its stage retires) — robots.txt committed timeless per Robin
  ("no automation info facing the web" — dates/names of internals stay in dev files,
  nothing dated serves), verify_site = the gate again (CI red on robots/sitemap until his
  merge re-fires the deploy). Red→green: gen_pages wrote root-deploy legs first (red on
  the missing --origin + sitemap), generator carried them green (8 boots clean, sitemap 9
  locs exact). Sweep 31/31 (258 s). sw.js untouched — no VERSION bump. The discovery
  session's rule-13 lesson also landed earlier today as `3930d42` (the dip red cured,
  merged with PR #10, CI green at `36116579188`/`36117318584`).

- **2026-09-25 (post-flip stretch — the gate goes green, the IDEAS lifts land on the board)** —
  Robin merged `domain-switch` as PR #11 (`4f44099`) and re-fired the deploy
  (`36125302883`, 29 s): the post-flip acceptance gate PASSED — `verify_site --origin
  https://ocarina-practice.com --boot 8` = 20 live checks, 8/8 stubs booting right song/
  right ocarina at prefix `/`, robots.txt + sitemap.xml serving and enumerating exactly
  home + the stub set. Per Robin's rule the permalink contract is LIVE. The F7 item
  carries the gate record; its residual rows are Lighthouse, SERP observation (November
  anchor) and Robin's manual Search Console verification + sitemap submission. Robin
  updated IDEAS meanwhile (commit `521f7e2` mobile-sleep; two new flip-adjacent entries)
  and asked for the first IDEAS-cleanout check — end to end against the board/code
  nothing was done, the file untouched. Then "Check updated IDEAS and TODO and select
  some work": the two flip-adjacent IDEAS entries lifted as board items — §9 "Landed-
  crawler URL semantics: leaving a stub path never plays different content under it"
  (switches resolve to root + ?song=&inst=, seed keeps its canonical path, title click →
  root entry) and §7 "Info screen links the GitHub issues page". Hot list refreshed
  (gate-green rows retired from the wording; lifts head the stack). This bookkeeping
  batch (notes/lifts/log/hot) is plans-only; app work next on Robin's word for the
  branch.

- **2026-09-25 (session 6 branch — the two IDEAS lifts built: landed-crawler URLs + title link + issues link)** —
  built on Robin's granted `session6` placeholder (renamed by him whenever; the bookkeeping
  commit `fc70465` first moved OFF main onto session6 and main rewound to the merge tip per
  the new placeholder-branch rule, now in AGENTS rule 8). RED→GREEN: gen_pages boot legs
  first (red on all three behaviors), then the implementation — the landing SEED keeps its
  clean canonical path (pinned), the site title is `header h1 > a[href='./']` (mount-agnostic
  via <base>: root on the domain, /Ocarina-Practice on a project-page mount), a warm library
  switch resolves the URL to the SITE ROOT with ?song=&inst= (derived from the current
  pathname minus its /song/ tail — mount-agnostic by construction), a typed/cleared/file-
  loaded replacement goes to BARE root (the rewrite runs after the dropdown drops so a stale
  song name can never ride it), boot's own deep-link loads are gated by markUrlLanded() so
  they keep the landing path forever. Hooks: library.js loadLibraryItem tail +
  clearLibrarySelection (+ the idempotent root early-exit), app.js boot tail + the
  switchInstrument same-song path (instrument change alone rewrites). The help dialog gained
  the .help-meta colophon with the GitHub issues link (target=_blank rel=noopener). sw.js
  VERSION → oco-pwa-v7 (rule 15; the offline suite rode the sweep green). Lint clean
  (eslint + html-validate, node 22 restored to /tmp/opencode/node for the box). Full sweep
  31/31 (262 s).

- **2026-09-25 (intended-instrument landed; Robin's model pinned)** — the songs.json `intended` field + the intended-aware landing walk shipped red-first (sandbox v12 validator class + the BotW pin), BotW seeds the -bass body on the triple from the clean URL after merge+deploy. Robin's followups pinned the semantics on the item: the instrument-tagged entries are the versions and keep their keys (no rekey, no -bass deletion), the non-specific URL is the intended-instrument's entry point when defined, the ladder rules otherwise, and the clean page titles what plays. IDEAS line left the scratchpad; the open board item carries future per-song values as Robin's musical calls. Sweep 31/31 (262 s) covered the data+generator+validator+pins; no sw bump (data+tooling only).

- **2026-09-25 (session 11 wrap — the intended exemplars land, CI stops double-running, the next batch planted)** —
  after the PR-copy canon was pinned to Robin's named PRs (#3 sentence-tagged links, #9
  approved second shape — commit `80be46d`, the bare-SHA-plus-URL form named as the drift),
  Robin reshaped the intended-instrument story to its final understanding: the exemplar run
  needed not a body rewrite but the non-specific URL landing the intended version — BotW
  confirmed as-built (base declares intended=triple; the family walk seeds botw-theme-bass
  on the triple), and Kokiri's clean URL manufactured by REKEYING the leaf kokiri-forest-bass
  → kokiri-forest (byte-identical body; Robin kept the "(bass)" tag naming for the entry;
  intended=triple; `d99eeaa` — the old URL retires mid-trial-period, SKILL.md's leaf example
  updated, sweeps 31/31 twice). The PR pipeline's double-run diagnosed and cured: the bare
  push: trigger fired both a push and a pull_request run per PR-commit — push now rides
  main only (`cb253cb`), and Robin's fossil job-title complaint joins the board as the
  next-session item (verify taut him: a tag span must be a code span). SAME-DAY CORRECTION
  (Robin's single-run shape, `fe92c8b`): instead of push→main-only, the pull_request trigger
  is DROPPED and bare push fires the battery once per commit on every branch — an open PR
  recognizes the head SHA's run by job name; main's post-merge run is the shield; the traded
  piece is the merge-commit pre-validation. Branch session6 ends
  at `cb253cb` (10 commits) — PR copy already drafted for Robin per the canon; next session
  opens from the proposed batch in the log.
- Next (session 12 opening batch, proposed — Robin confirms/picks): (1) the phone wake-lock
  (his committed IDEAS bugs entry; Screen Wake Lock API on play/practice, release on stop;
  field-check on his phone); (2) the openers: CI fossil job-title rename + the SEO
  Lighthouse pass (both small, one commit each); (3) the 80s LED theme sketch as the fun
  centerpiece (IDEAS themes; first-pass tunable, joint design); (4) the LAYOUT quick pair
  (practice-close button + the mic-icon inform), his field-check class; (5) the 12-hole OoT
  set completion as the joint content jam (the November anchor). Helds remain: MIDI
  implementation only as tooling, robots/sitemap post-verification stages builds lean on
  the live gate.

- **2026-09-25 (session 12 — quick openers, wake-lock, layout pair, HiFi + theme menu, the general readability scan; the headless rule born)** —
 Robin picked the openers+wake-lock+layout+HiFi batch (answers: wake-lock play+
 practice; first pass palette+LED only; the theme selector is a MENU, theme named
 **HiFi**, code `hifi`). Landed on the `session12` placeholder branch: (1) `ee4e2ec`
 the CI job title names the real battery; (2) **Lighthouse pass** — mobile P80 /
 A11y 100 / BP 96 / SEO 100, desktop P99; the scanner caught the mobile CLS 0.352
 (reproduced headlessly under real throttling = the inst-sel ballooning + a
 pre-CSS flash) and the token-touch listeners went passive — `b023394`; the
 FIRST Lighthouse run opened Chrome HEADFUL on Robin's screen — the **headless
 rule** went into AGENTS rule 17 (never a window; explicit `--headless=new
 --disable-gpu` flags; asks first if unavoidable). (3) `e375203` the wake lock
 (js/wakelock.js reasons-set module; seams in audio/playMelody-family +
 practice start/pause/anchor/standby/un-press; `tests/wake_lock.py` red→green,
 the setWakeLockSource seam after three probes proved `navigator.wakeLock` is a
 readonly WebIDL getter nothing can shadow). (4) `b106cba` the layout pair —
 tuner ✕ un-presses practice + mic glyph replaces ♪ on both transports;
 Robin live-tested mid-unit (the ✕ overlapped the status glyph — row reserves
 30px; he verified the close works). (5) `bccb4f8` the theme MENU (Plain /
 Hyrule / HiFi uniform ink) + the HiFi first pass. (6) **The readability work,
 the session's centerpiece**: Robin demanded a GENERAL detector ("you'll find
 a general way for a non-human") after unspecific hints — the selector roster
 was replaced by the full-DOM scanner (every visible text/glyph element per
 state, opened-state asserts for popups, measured-count floors vs
 pass-by-nothing); the scanner then found the rest itself: HYRULE theme menu
 (his catch), HiFi light-sheet internals, the piano now-key label,
 --token-pause at 4.14, the Hyrule dbg heading — all fixed in `a529fd0`
 (chassis-painted shape verified with Robin first; sw VERSION v10→v12 across
 the batch; 34/34 sweep twice; lint clean; CI = push battery, single run).
 Board: §6 items closed (job title, a new general-readability item), §9 items
 added+closed (wake lock, layout pair, HiFi first pass), F7 note (Lighthouse
 pass + report-only residuals). Branch session12 ends this wrap; Robin pushes/
 merges (PR copy per canon handed below). Helds: his field checks (wake-lock
 phone, HiFi retune knobs, ✕/mic look, live Lighthouse re-run post-deploy).
 Robin-steered adds at the wrap: the branch is close but NOT merge-ready yet
 ("minor issues and subjective problems we'll correct later") — (a) HiFi went
 HIDDEN until finished (`4c4456c`, menu lists Plain/Hyrule only, ?hifi keeps
 exploring, sw v13; theme_toggle rewritten for the hidden contract; sweep
 34/34 green on re-run — the first sweep had ONE bad_chip oot-leg red,
 standalone green in between: the sweep-load flake family gained a member,
 watch it), (b) the subjective list stays his; his two IDEAS captures
 (`fe5c867` CSS updates, `1766fad` swing-disable-in-practice) ride the branch
 in his own hand and wait for his lifts.

- **2026-09-25 (session 13 — the board manager hardens its log rules, the stale board is corrected, the handoff gets prepped)** —
  Robin's suspicion that the board tooling was unclear proved worth fixing
  properly: the convention (append at bottom, old→new downward) is what the
  tool always assumed and what the log mostly did — EXCEPT one long-planted
  anomaly (the session-12 entry sat ABOVE the session-11 wrap's, which would
  have made `log-retire` keep the wrong end) plus a stale opening-batch
  bullet riding the oldest entry. tools/board.py now guards that class
  red-first: `tests/board_tool.py` gained a verify leg (entry dates must
  read non-decreasing downward — a newer-dated entry above an older one
  fails — and nothing open may live inside the log section); implementing
  it also caught a slice-offset in my first date grab (`l[3:13]` vs the
  `- **` prefix — every entry hashed equal, masking all order) fixed to
  `l[5:15]`; the docstring now states the append rule plainly, including
  "several sessions on one day still append — never hand-place an entry".
  The real board was normalized once by hand (session-12 block below
  session-11's), the four-session log backlog retired into plans/DONE.md,
  and the two IDEAS-lift items left the open list at their build `720373e`
  (landed-crawler URL semantics + the info-screen issues link shipped via
  PR #12 — the hot list had wrongly kept them "next build"). Board gains:
  §1 the deep-link instrument-change redirect defect (field-observed, Robin
  IDEAS; gen_pages pins the library-switch leg yet the field disagrees —
  reproduce on a live stub first), §9 the SEO-guides application pass
  (Robin's two Google docs; opener is read-then-audit, applications are his
  picks), and the permalink item carries the new pin: the domain is
  Search-Console-verified and the sitemap URLs are PERMANENT from today (no
  rekeys, no path renames; kokiri's retired leaf URL was the last move of
  its kind). Live Lighthouse re-check post-deploy rode the same note (mobile
  perf 95 / CLS 0; desktop 99; residuals: render-blocking stylesheet +
  #themeBtn label mismatch; the BP -1 is the expected §1 tone.json 404).
  This session opened package-mode per Robin (tool fix + board state +
  handoff); later field streams still pulled two units in:
  — Robin CONFIRMED the wake lock live (play AND practice kept his phone's
  screen awake — the held field check closes);
  — Robin reported the live defect that the practice-mode swing slider was
  'not disabled like tempo', which exposed my earlier mis-read — `1766fad`
  was Robin planting the IDEAS idea line, never an implementation, so the
  IDEAS-cleanup message wrongly called it shipped — and the behavior is
  NOW real: the swing row joins playback's silent-dials contract
  (`.dial-off` dim + inert beside tempo/focus-tempo) via `b86ddf3` red→green
  (`tests/practice_dials.py`, CI-registered, sw v14), completing on the
  board with his post-merge phone eyeball as the deciding pass.
  The opening batch for the fresh session is proposed below.
- Next (session 14 opening batch, proposed — Robin confirms/picks): (1) the
  §1 deep-link instrument-change redirect defect — reproduce on a live
  /song/ stub (his device or headless against the deployed site), then
  red-first; the permanent-URL pin makes it the hottest open thing; (2) the
  SEO-guides opener: read the two Google docs from IDEAS and AUDIT the
  artifact (report only; the applications are Robin's picks); (3) the
  audio-tick spike detector per §2's detection plan as the running
  centerpiece (debug-only, no shipped-audible change); (4) CSS
  fresh-on-release (version the css URL; watch the sw VERSION melody); (5)
  the tick-override semantics unit (IDEAS line; the semantics are already
  written). Helds all stand: twin-dedup verdict (kokiri stray token needs
  his eyes), transpose text-vs-token fork, shipped-songs standardization
  (later-stage pass), MIDI-as-tooling boundary, small-screens brainstorm,
  and the feel-check stack (HiFi retune knobs, ✕/mic glyph, history line,
  token chips).

- **2026-09-25 (session 14 — the deep-link contract sealed, the twins derive at load, the tick contract, the stylesheet token, the spike watch pairs the flip)** —
  Robin opened the session with a few hours and picked the full proposed
  batch (plus field checks interleaved); the batched decisions: kokiri's
  `g4/4` is a typo, derive ALL twins, the transpose fork resolves
  TOKEN-LEVEL, every feel check on today's list, headless probing allowed
  for the deep-link repro. Landed on the `session14` placeholder branch
  (Robin pushes/merges as ever):
  (1) `098115d` the kokiri typo — parse.js uppercases note letters so the
  token played identically all along; the audit goes refusal-free and
  kokiri is NOT-ALIGNED against everything (no twin), census closed at 8.
  (2) `ff53abb` the deep-link redirect defect: Robin FIELD-CONFIRMED
  mid-unit that instrument switching resolves to root+vars on the live
  site; the headless probe then exposed two LATENT holes fixed red-first
  under the new mounted boot leg (stub served under a path prefix): the
  rewrite dropped its mount prefix (STUB_PATH had no capture group;
  root-serving masked it) and, once off the deep path, ?song= stopped
  tracking the playing song — rewriteLanderUrl now refreshes the vars in
  place, extras (theme params) survive, bare root stays bare.
  (3) `56c4ae0` the spike watch pairs the flip: spike cards gain an ambient
  context ring (orientationchange legacy+spec, throttled resize; kind
  +agoMs, 4 s age-out) riding the card/probe/console warn per the flip
  evidence — the next field tick names its seam's plane, or proves the
  device level by staying silent while the phone still hops.
  (4) `eee3bbe` the twins derive AT LOAD: 5 derives records ship
  (time/-storms/-sarias bass -12, botw-theme-down3 -12, hobbits-short-c
  -2) materialized byte-equal; the byte-identity test was the instrument
  that forced the music-theory engine: OCTAVE shifts carry the base
  letter+accidental (Bb5→Bb4) after eponas' flat-side-Bb-beside-
  sharp-F#/C# orthography proved no midi respell could know per-section
  intent; botw-theme-bass (key-name labels + line split) and
  eponas-song-bass (A2 label) stay HELD hand-written (Robin's calls); the
  flats flag died in the theory run; validator owns the derives schema
  (7 sandboxed defect classes), audit prints provenance and keeps the 5+3
  census refusal-free, gen_pages boots the materialized corpus;
  tests/twin_derive.py freezes the retired bodies as fixtures so a base
  edit fails the derivation on purpose.
  (5) the SEO-guides OPENER delivered as a report (no code): the artifact
  already meets most of the guides (robots/sitemap/URLs/one-URL-per-
  content/titles/OG/mobile); three application candidates await Robin's
  picks — shell rel=canonical (recommended), JSON-LD (Breadcrumb /
  WebApplication / MusicComposition), static stub cross-links.
  (6) `53d8074` + `0685ea2` the stylesheet fresh-on-release: the <link>
  href and sw.js's precache entry carry the css token css-v1 —
  INDEPENDENT of sw VERSION after the new guard caught the coupling in
  its own first draft; an old worker misses the versioned URL and serves
  the network sheet immediately, so the first reload is fresh; boot
  re-fetches the page's own link so the at-boot replace cannot drift.
  (7) `0685ea2` the tick contract (IDEAS line): the user preference lives
  in localStorage (oco-bass-c-tick), a song's tick declaration stays a
  per-song session override that never writes it, both USER channels
  (transport button + settings carrier) write on click, programmatic
  song loads wear an autoTick guard; six-leg suite.
  Sweeps: 38/38 (the two new suites registered in CI the same commits);
  lint clean per unit; sw VERSION → oco-pwa-v19, css token → css-v1.
  Helds: Robin's feel checks (HiFi knobs ?hifi, ✕/mic glyph, history
  line, chip touch feel, small-screens brainstorm) — all unchanged;
  SEO applications = his picks; shipped-songs standardization (later-
  stage pass), MIDI-as-tooling boundary, small-screens, WAV-export
  worklet reframe, real-DSP validation all stand.

- **2026-09-25 (session 15 — the hands-off night: the SEO pair ships, the zen note bar re-seats, the board tooling hardens, two reports delivered)** —
  Robin confirmed the five-unit batch and slept; the standing rules held (no
  main commits, nothing audible/UX-visible without his field check, every unit
  green + committed + logged). Landed on the `session15` branch, five units:
  (1) `8370dd7` **SEO applications** (Robin's elected pair): shell rel=canonical
      href="/" (the pinned domain serves at root — robots.txt names the
      sitemap there) + ONE WebApplication JSON-LD (EducationalApplication,
      OS "Any", browserRequirements, a free Offer with priceCurrency,
      description VERBATIM from the shell meta — one-description policy).
      Consequence handled in-commit: build_stub copies the whole head, so
      both new elements would have ridden into every stub — the generator
      strips them (each stub keeps exactly ONE canonical, its song path, and
      ZERO JSON-LD); tests/seo_shell.py (CI-registered, pure python) pins
      the shell shape and the no-per-stub carryover against a freshly
      generated staging tree; sw v20. Not elected today: per-stub JSON-LD,
      cross-links, Breadcrumb/MusicComposition variants.
  (2) `b15d2ce` **the zen note bar re-seated** (Robin's field catch): the
      headless 6x-throttle measurement named the seat BEFORE any build —
      the browser-native smooth scroll (UA animation settles ~200 ms per
      note step, ~500 ms per jump, and every per-note re-issue restarts it
      mid-flight; the rejected trace trailed 655 px after nine 130 ms-apart
      advances). scrollFocusStripTo now keeps the sheet's proven glide
      contract (≤160 ms eased rAF, far jumps snap, a wheel grab cancels);
      the stale "smooth is cheap" comment corrected; tests/zen_notebar.py
      pins five legs red-first at a 390x844 phone viewport; app-path
      after-measure: 67 ms step settle, ~0 px trail; sw v21.
      **HELD for Robin's phone field check** — the deciding pass; the 160 ms
      bound may read too quick on the device and he retunes if so.
  (3) `a566a0e` + `24a2b2b` **the empty-lines claim VERIFIED REAL and fixed**
      (_insert_line stacked one blank per move beside an item's trailing
      blank — 11-blank runs stood in the live TODO, a 4-blank run appeared
      after three sandbox adds): writes collapse blank runs now (the
      single-blanks invariant, self-healing on every move), verify lints any
      run on both files with line numbers, the live board normalized once
      (whitespace-only diff); board_tool 12/12 with the accumulation leg and
      the run-lint leg red-first; the §8 item moved into DONE via the tool.
  (4) `c40991e` **the CI BrokenPipe noise quieted at the pattern**: all 34
      browser suites carried the byte-identical server block; the shared
      tests/suite_server.py owns it now — handle_error swallows ONLY the
      ConnectionError family (mid-response browser close, the paste of run
      36187303217 job 108243773139) and forwards everything else to the
      loud default; all 34 suites import start_server, gen_pages borrows
      the hardened server for its staged Mount handlers; tests/
      suite_hardened.py (CI-registered) pins both directions: a mid-GET
      abort stays silent and the server serves on, a real handler defect
      still prints. The migration caught its own splice casualty
      (zen_notebar's _server() def sat inside the replaced span — named by
      the unused-import scan, fixed before commit).
  (5) Report-only pair (no code): the **URL audit** (the rewriter covers the
      library truth completely — boot keeps its landing path; builtin AND
      user-saved picks land on root+?song=&inst=, user ids ride as-is and
      degrade to the fallback load cross-device; instrument switches refresh
      vars in place; typed/Clear/file-load leave bare root, typed text
      autosaves NOWHERE so bare root is honest; non-library state stays OUT
      by design — identity + theme extras is the shareable contract) and
      the **perf report** (none of the three ideas warrants a build: the
      waveform strain is already healed by ocWaveCache/chiff/windBuf + the
      Lite voice; minify claws ~25-30 KB gzip-total (387 KB JS raw → 124 KB
      gzipped transfer) and costs production stacks + console diagnostics —
      Lighthouse mobile 95-96 shows no parse pain; hole-SVG CI-gen would add
      dead files, the client assembly is live behavior). Both notes ride
      their items.
  Sweeps: 42/42 at the wrap (the migration verified across the whole set);
  lint (eslint@9 + html-validate@8) clean after each unit that touched
  html/js; board verify green throughout; sw VERSION oco-pwa-v19 → v21.
  **Morning deck for Robin:**
  - PR copy per canon below; his paste.
  - FIELD-CHECK list (the deciding passes): (a) the zen note-bar glide on
    his phone vertical screen (~67 ms step settle measured; the 160 ms
    bound may need his retune); (b) the audio-tick hunt stays his field
    work (spike cards carry the ambient ring since session 14 — the next
    flip names its plane); (c) the twin-songs ears pass (boot byte-identical,
    his ears confirm); (d) the standing stack: HiFi retune knobs (?hifi),
    tuner ✕/mic glyph look, history-line clarity, token-chip touch feel.
  - Post-merge+deploy: the shell gains rel=canonical + the JSON-LD; spot
    any stub's head for its single song-path canonical and zero JSON-LD.
  PR copy (canon #9 shape — `##` sections, dense sentences, SHA-linked):

## Shell SEO pair
- The shell gains rel=canonical "/" and one WebApplication JSON-LD (EducationalApplication, OS "Any", browserRequirements, a free Offer, description verbatim from the meta), while the stub generator strips both from every song page so each stub keeps exactly one canonical — its own song path — and zero JSON-LD ([`8370dd7`](https://github.com/tribbin/Ocarina-Practice/commit/8370dd7)).

## Zen note bar on small screens
- The focus strip stops handing its per-note centering to the browser's native smooth scroll (measured: ~200 ms settle per step, restarts trailing 655 px under sustained advances) and glides with the sheet's bounded rAF contract instead — ≤160 ms eased, far jumps snap, a wheel grab cancels ([`b15d2ce`](https://github.com/tribbin/Ocarina-Practice/commit/b15d2ce)).

## Board tooling
- The board tool stops accumulating empty lines (11-blank runs stood in the live TODO): every structural write collapses blank runs to the single-blanks invariant, verify lints any run, and the live board is normalized once ([`a566a0e`](https://github.com/tribbin/Ocarina-Practice/commit/a566a0e)).

## Suite server
- The byte-identical server block in 34 test suites moves into one hardened place whose handle_error swallows only the connection-teardown family — the BrokenPipe traceback racks under a passing battery end — and stays loud for real handler failures ([`c40991e`](https://github.com/tribbin/Ocarina-Practice/commit/c40991e)).

## Tests and infrastructure
- New suites, CI-registered in the same commits: tests/seo_shell.py (shell shape + zero per-stub JSON-LD), tests/zen_notebar.py (five glide legs at a phone viewport), tests/suite_hardened.py (teardown silent, defects loud), plus board_tool's accumulation and run-lint legs.
- Full local sweep 42/42 green at the wrap on the Linux partition; lint (eslint@9, html-validate@8) clean; the hardened suite server is exercised by every browser suite in the sweep. CI runs the same suites (a health check, not a deploy gate).

- **2026-09-26 (session 15 cont. — Robin's interactive panel: nine calls, three builds, the board drops to five opens)** —
  Robin answered the full dependence panel in one ask; the calls and lands:
  PANEL CALLS (all through the tool): the audio-tick item and intended-
  instrument item move to DONE by his word (the hunt machinery stays, he
  re-introduces when needed; the planting is his per-song hobby); SEO
  leftovers confirmed already-serving per-song crawler data (leftovers stay
  unelected); the URL extensions and the perf minify/pre-cache decline; the
  transpose build declines ("focus on C/octave — new ocarina players at the
  Zelda release are the audience"); MIDI import and recording/A-B are
  declared dropped ideas and leave the board; Real-DSP and debug.js
  coverage both close (the synth work is bespoke and moving — validating a
  moving hand-tuned engine contradicts its point; debug stays untested by
  election); the collapse-buttons misc item drops as incomprehensible
  (Robin: "I don't understand the item"); the four standing feel checks
  pass ("all good, except ..."); song-bodies standardization stays held.
  BUILDS from the same pan:
  (1) `33fc135` **the dark-amber retune** (his values + granted insight):
      one chrome face for the HiFi page-chassis buttons (#160a04 resting
      under a thin white line, #56300d engaged — seg-on, playing/looping,
      pressed, the open dropdown), the segment row + instrument select stop
      painting white on the black chassis, the zen CTA goes #b32317 with
      white text, and the LED rows fill WHOLE segments: every fill width
      now writes through one quantizing seam (10px grid under hifi,
      passthrough elsewhere; transition dead under hifi only — the plain
      keeps its .1s glide). tests/hifi_retune.py pins BOTH sides of the
      theme flip; css-v2, sw v22.
  (2) `b38a6d8` the **enlarged-holes SVG elect closes by its own
      condition**: investigated, measured (enlarged 1.53 vs flat 1.77
      ms/render headless — the epoch-memoized enlargePlan already
      amortizes the scaling; the output cache covers the rest), NOT
      BUILT — the measurement Robin asked the decision on.
  (3) `390c431` **library favorites pinning** (his election): the star per
      row (a span inside the role=option button — nested <button> is
      invalid HTML), a FIRST persisted Favorites group across both
      corpora, exactly-once rendering, reload-stable, picker stays free.
      Red-first on the missing star; the red serve also exposed a live
      ReferenceError (sel out of scope) caught by the pageerror probe.
      sw v23.
  (4) `bee0c5d` the **readability rollback** the swept suite caught: the
      star's fixed --muted/--accent paints failed the scan in HiFi (2.56
      on a light face) — the glyph now inherits the row's own face ink
      (the scanner's own shape rule for face-changing glyphs), keeps
      differentiation in the silhouette. sw v24.
  Sweeps: 44/44 twice (the second after the star-rollback); lint clean;
  board verify green; five open items remain.
  HELDS after this run: the retune batch + the favorites star are Robin's
  phone/backcat eyes (his values, built to spec — an evening eyeball pass);
  tone.json measurements, song-body standardization, the perma-link data
  planting and the library widening keep their standing forms.

- **2026-09-26 (session 16 — the multi-track pickup: the idea becomes grammar, engine, and the Outset trio)** —
  Robin's IDEAS entry "multi-track arrangement" picked up via
  research/multi-track-handover.md; the full dependence panel answered
  up front (all recommended picks): build on `outset-island`, 2-track
  proof then the trio, per-track zones with the bass audible in normal
  practice, parallel-line track blocks, shared clock with the melody's
  bars/labels, all-or-nothing v1 UI, melody tone model for bass voices.
  Landed on `outset-island` (the branch already carried `coreIdOf`):
  (1) `0e4afbe` **the grammar**: a `#track <name> [zen|audible]` header
      line opens a real second token stream; parse() stays the melody
      stream's front door (a line-based pre-pass lifts the blocks away —
      every consumer keeps its flat melody array), parseTracks() parses
      each block with the same grammar, same-name blocks append into one
      stream (newest zone word wins), and malformed headers chip without
      changing any stream boundary. tests/parse_edges carried the TRACK
      legs red-first (melody purity, zones, merges, bars in blocks,
      prose '#tracking' safety, the parse() shape).
  (2) `53e8e2b` **the engine**: the named streams walk as real second
      melodies on the shared clock (own scheduler state walked at the top
      of every melody tick — a groove enters where the melody holds, the
      thing pivot-anchored supports cannot do), the melody's exact note
      semantics + its very playNoteAt voice; zone audible plays wherever
      the melody plays (melody bag only), zone zen mirrors the support
      gating and lands in the bass bag too. Track junk and melody-syntax
      support markers chip (strip pills name the stream, clean bodies
      render none). tests/track_accepts.py (CI-registered) red-first:
      plain-view audible, zen audible, zen-zone gated, equivalence with
      the same line as melody, loop re-fires, stop-leak guard, no-track
      no-op, junk chips. A harness round-trip named the melody-voice's
      range rule cleanly (the page boots A4–F6; supports/tracks never
      range-check).
  (3) `d754a09` **the groove ship**: outset-island-with-bass drops its
      drone brackets — the melody keeps its notes and a `#track bass
      audible` block carries the entire outset-island-bassline groove
      two octaves down bar-for-bar (52 bars equal, the 5/4 da-dum, the
      final bar truncated to the melody's half-bar finale); the
      shipped-songs suite gains the corpus-wide track contract (streams
      clean + zones declared + bar sums equal per bar index); the stub
      generator's melody reader stops at '#track' headers (caught live by
      the gen_pages boot timeout when the track notes were counted as
      melody); sw oco-pwa-v27.
  (4) `b23621b` **the trio (the IDEAS example)**: melody + bass groove +
      contrabass — the old per-bar drone roots re-projected as a real
      track (bar roots, the melody-attack splits as plain mid-bar tokens,
      the 5/4 bar a tie-extended hold); three parallel walks, zero engine
      churn.
  Sweeps: 45/45 twice (the track battery inside); lint clean; board
  verify green; the field-check item lifts to §7 as the feature's
  deciding pass (Robin's ears own the balance/register/practice-tuner
  calls; the first audible draft he retunes is the expected course).

- **2026-09-26 (session 16 cont. — the mix lands, the harmonize pass becomes a tool, the MIDI unit queued)** —
  The field check began speaking: (1) hard-to-tell-apart voices → the
  header gained a trailing percent (`#track bass audible 50`,
  `#track contrabass audible 75`), parsed to a gain ratio and applied as
  ONE master multiplier inside playNoteAt; the note sink now reports the
  mix so tests/track_accepts pins the ratio exactly (0.5/0.75/default
  legs, red-first). (2) same-pitch doubling → tools/track_harmonize.py
  (the reusable idempotent pass): absolute-onset collision map (melody
  holds extend over ties cross-barline), token drops in convergence
  rounds (octave below, then a perfect fifth below, then another octave),
  durations untouched — 40 pizz tokens harmonized, zero collisions left,
  the bar-grid contract untouched. (3) the -up12 twin lives for the
  register A/B (high contrabass on the real cbc chart). Skills carry the
  volume grammar + harmonizing doctrine (`320b9aa`); sw oco-pwa-v30;
  sweep 45/45 green with this state; Robin confirmed the songs are
  NOT yet shipped (nothing public) — reshape freedom stands.
  QUEUED (next session, context meter hit the watch line here):
  the MIDI-interpreted variant Robin asked for — research/
  LoZWW_Outset_Island.mid is the source; read skills/midi-to-ocarina-tab
  fresh at pickup (scripts/mscx_dump.py exists; mscx beats re-deriving),
  build `outset-island`'s companion song with the FULL arrangement's
  bass voice interpreted from the MIDI (skill's onset-grid assembly),
  harmonized + bar-grid-aligned by the same pass, then the skills gain
  the midi-unit learnings in place.

- **2026-09-26 (session 16 cont. — the MIDI twin ships, Robin's rotation catch, the 5/4 retires, the loop seam completes)** —
  The queued MIDI-interpreted variant landed (`20f0664`): `outset-island-midi`
  = the with-bass melody verbatim + `#track bass audible 50` re-interpreted
  from the full arrangement's ch0 through the onset-grid assembly (+24
  projection, Ab1 roots a third octave up, harp-register doubles dropped,
  tail hit trimmed, the second low channel declared out; harmonize moved 31
  same-pitch attacks), bar labels 1-52 so Robin can name measures; the
  `-midi` content marker joined both suffix pins; the midi skill gained §0e;
  sw v31. Robin's field check then caught what every mechanical check had
  hidden: bar 7 and bar 33 SHOULD be in pace "in a similar way" (his
  thumbprint: "in the midi they are identical") — the raw identity test
  proved the FILE's measures 7/33 byte-identical while our track read bar 33
  as the NEXT measure's tail: the window-intersection assembly rotated every
  bar's content +1 beat past the da-dum (`bae365d` fixed it with the
  measure-content map, tools/midi_track_audit.py + its CI-registered tripwire
  suite built red-first, bar 33 ≡ bar 7 restored; sw v32).
  His M18 read then pulled the root under the rotation (`2c02f04`): the
  reduced score's 5/4 da-dum bar was ITS OWN error — the ocarina.mid's
  Eb at [72, 72.5) was the arranger's human slip (absent from the game's
  file; the game's TS metas = 4/4 with no meter change, the tune voice
  silent through [68, 72.5), the groove's bass entering exactly at 72) —
  the whole Outset corpus re-carved to the game's pure 4/4: five bodies'
  bar 18 lost the stolen Eb5/4, bar 52 COMPLETES to four beats in every
  melody, both support layers now carry the full measure-52 vamp/whole note
  so a loop lands the closing vamp straight into the opening one, the
  contrabass rows lose the leftover `/1 -` misreads, the twin re-emits from
  the audit tool with the pure-4/4 map (check green, 40 harmonize moves
  idempotent), and the odd-meter doctrine lands in both skills: an
  irregular measure is Robin's ear check against the source material, not
  an accommodating fact. His last note retires the full sweep from the
  standard set (AGENTS.md §12, board §6: sound-engine touches only).
  Affected-suite runs green throughout (shipped_songs 22/3-track, the audit
  suite, gen_pages, parse_edges); sw v31 → v33.

- **2026-09-26 (session 16 cont. — the arrangement ships as the only version:
  the derived contrabass, visible chord labels, the tidy landing)** —
  Robin's green-light made the MIDI transcription THE Outset version:
  the corpus retires the with-bass trio, its up12 twin and the bassline
  solo (19 songs now, one multi-track); `outset-island-midi` = "Outset
  Island (arrangement)" gains the derived `#track contrabass audible 75`
  built by the new root-segment rule in tools/midi_track_audit.py (bounce
  merging, longest-run measurement, the +12 sub-bass register, whole
  holds / 2+2 splits, Ab2 at the da-dum, the loop root at the finale),
  harmonize-clean from birth (0 collisions), its audit extended to BOTH
  layers. Every melody bar label = number + section + the bass's own
  chord root (Unicode flats so the caps strip reads A♭ not AB); the
  display name drops 'game'. Landing seed canonizes the arrangement:
  gen_song_pages' family order puts the content-marker variant first.
  Two loader truths found the hard way: withPlayHeaders DISCARDS the
  body's leading comment block (so user-visible notes live in LABELS;
  the tooling's head probe repointed to the first bar row), and the
  harmonize's bare split('#track ') amputates any melody whose comment
  quotes a header inline (now line-anchored). Suites green throughout:
  shipped 19/1-track, the audit battery, gen_pages (9 stubs, the family
  seeds the arrangement), parse_edges, transpose-skill shim, support,
  twin-derive. sw v34. Robin's refresh note: a stale preview showed
  doubled bar-lines; a hard reload cleared it (no fix needed).

- **2026-09-26 (session 16 cont. — the CI red on the old commit: the
  source audit becomes a local gate)** — the audit suite rode the PR's
  older head and died in CI at run `36265370463` job `108468913064` on a
  FileNotFoundError: `research/LoZWW_Outset_Island.mid` is gitignored
  (work material, Robin's), so CI can never see it while every local run
  was green. The fix reverted the day's tool churn and took the small
  shape (`fbc75d1`): the suite SKIPS with a loud note when the source is
  absent — the source audit is a LOCAL gate for machines carrying the
  research tree, and CI keeps the corpus/grid contracts green through
  shipped_songs. Verified both shapes (the file moved out = skip exit 0,
  moved back = the full battery).

- **2026-09-26 (session 17 cont. — the 12-hole recordings become per-note data: the melody-cut pipeline, the module-era offline bench, the first fitted tone.json)** —
  Robin's IDEAS 12-hole recording analysis picked up on the
  `12-hole-synth-tuning` branch (his guidance all session: tone ladder = the
  feed ("multiple single notes when cut", honest volume envelope, silence as
  the noise baseline), kokiri/storms = transition/glide context (the real
  glide is a finger-tap), melody WAVs only — the individual note takes were
  removed by his own hand, and the recordings' gain is a mic artifact while
  end-volume must keep headroom for support tracks/reverb):
  (1) **melody_cut.py** lands in the tone-analysis skill: span-adaptive
      thresholds cut a melody mid-silence to mid-silence (the same gap owned
      by both neighbors) and run every cut through tone_report.analyze with
      scalable plateau margins + guard for short cuts (tone_report gained a
      `margins=(0.22, 0.12)` parameter, defaults unchanged); attribution =
      autocorr f0 → nearest chart id, cents recorded but not forced ET.
      Ladder = 11 single-note-grade cuts; kokiri/storms measure but never
      feed per Robin's call (transients/multi-note spans).
  (2) **render_ours.py rebuilt for the module-era audio.js**: the old
      classic-script load path is dead (audio.js is ESM now). The bench
      writes a PATCHED module copy (imports absolute, module-local freqOf
      with a `window.__F0` override, reverb/lite buses swapped for dry
      outGain, air/edge/wander oscillators stubbed at their CALL sites) and
      resolves it through one import map so the whole library graph has a
      single audio instance; CORS=* on both bench servers; runs under
      Playwright in REAL time (dump-dom + virtual time never resolves
      startRendering on this chrome even for a bare oscillator).
  (3) **fit_tone.py** closes the reproduce→record loop: per-note ladder
      targets (best steady take, level anchored at the loudest fitted note,
      levelDb all ≤ 0), then offline render → same-pipeline measure →
      algebraic correction rounds. Converged round 3 on 11 rows: harmonics
      within ±2 dB (systematic small sink below the blow-variance band),
      levels ±0.3 dB, wind band-1 ±0.7 dB; open residuals: wind shape in
      bands 2-3 (chain's own LP/bump constants), wobble-depth delivery and
      attack-length delivery — all noted in the skill for the next layer.
      D5/Ds5 unfitted (no ladder coverage; loader interpolates); B4's row
      rides the ladder's re-blow blip (best-available, flagged).
  (4) **instruments/oot-alto-c-12/tone.json ships** (tone-fit-v1, 11 rows,
      chamber 1): harmonics/level/wind-band/wander/wobble/attack per note
      from measurement, osDb from take overshoot, `h` vectors + expanded
      keys keeping the loader free of new logic. Suite updates: data change,
      so tests/instruments_load's boot leg repointed (a SHIPPED tone.json
      must install as the model; declared-but-absent keeps the 404
      tolerance); data_validator + console_hygiene green untouched; no sw
      VERSION bump (data-only, precedent 8e7b1d7 / fetch rides SWR runtime
      with no prior successful copy).
  Affected suites green (data_validator, instruments_load — leg rewritten
  for the landed data, console_hygiene); the board note + this log entry
  land via tools/board.py. HELD for Robin's field check: the first fitted
  voice is an audible-behavior change — his ears (multi-layer: the notes
  themselves, the level curve inside one chamber, the wind) own the next
  step; i will re-record when kids sleep done and the improved engine gets
  re-analyzed per IDEAS (re-record double-alto-c notes).

- **2026-09-26 (session 17 cont. — the transition/glide dataset lands: the real jump is a finger-tap, the engine's carry is what's missing)** —
  glide_span.py joins the tone-analysis skill (plateau tracking at 35-cent
  tolerance, per-jump duration/cents path/dip/half-cross), the committed
  storms + kokiri WAVs measured: adjacent-step transitions 20-60 ms with a
  0.2-0.5 dB dip (the tone CARRIES through the transfer) and tongued
  kokiri joints 10-90 ms at −6..+7 dB (several mid-jump swells); the
  render_ours bench grew --seq so the ENGINE's own transitions measure in
  the same terms: 20 ms timing but a −4.2..−6.0 dB dip per note change —
  timing already finger-tap territory, the carry missing (each note
  restarts its master envelope). HELD for Robin's field check as an
  audible-behavior decision (careful: practice's dip gate EXPECTS dips —
  a carry must live behind melody semantics, not knit under practice).

- **2026-09-26 (session 17 cont. — Robin's field check round: the near-noise methodology lesson, quantified)** —

  Bob did the field check on the first fitted voice and the finds cascade:
  (1) A4 (unfitted) far too soft — root-caused to B4's row (the ladder's only
      B4 take = the opening re-blow blip at −44 dBFS H1) whose slope-extrap-
      olation drags A4 down; the fix rides the clean kokiri tail take for B4
      (field-check bridge, re-record replaces).
  (2) The noise sounds like "sand paper, not porcelain" (B5/C6 hovers) and
      Robin names it a standing MODEL defect — he had tuned the old wind layer
      down to near-inaudibility to hide it, still a defect. Measured roots:
      the engine's narrow bandpass (Q up to ~9) rings a rough whistle; and
      separably the ONSETS: the recorded tongue transient runs −40..−55 dB
      rel plateau H1 while the shipped generic chiff bursts ~25 dB hotter
      through the first 180 ms (render vs recording onset portrait).
  (3) The traditional notch-band noise metrics were measuring pollution, not
      breath: the inter-harmonic floor of the recording reads −67 dB rel H1
      at band-1 (Robin's own held-part spectrum export, F6) while the earlier
      per-frame Hann-notch pipeline read −14..−26 — the loud fundamental's
      window skirt was the "noise" the fit chased. BH-window re-measure on
      the same F6 cut reproduces the class (h2 −46/h3 −44 rel H1; floors
      −92..−122 rel H1 before the ENBW-consistent scaling correction);
      Robin points at research/analysis/12hole/F6_spectrum.txt as the
      plotted-target reference and at cuts/ladder/10_F6.wav ("good, loud
      noise") plus the short-drift-window rule.
  (4) A real glide "tap" decision: between normal notes the dip stays, but
      glide-connected notes transfer with fixed short tap length, independent
      of the note duration ( AUDIO_DEBUG.slideTapMs 0.03, transients 10-60 ms
      with a 0.2-0.5 dB dip as the target; engine edited, held for field check).
  In flight when logged: wind-shape model re-search (broad wash, non-resonant
  Q cap — analytic |H| search vs the corrected recordings, python loop timed
  out once, switched to frequency-domain analytic responses), floor-method
  re-measurement for both the recording cuts and the render side (same helper),
  onset-fit (chiff rows per note from the takes), then re-fit + publish +
  suites/full sweep. WAV data is the arbiter of truth (Robin): his texture
  adjectives steer, the numbers decide.

- **2026-09-26 (session 17 cont. — the corrected floors ship: wash profile published, hold_spectrum joins the skill, the onset sand-paper root-caused; context limit wraps the session)** —

  Robin's requests through the turn: find+generate held-tone spectra as part
  of the skill (holdspectrum built), WAV data as the sound-truth arbiter, the
  10_F6.wav cut + his own F6_spectrum.txt export as the reference case, short
  drift-free windows for the truth:
  (1) fit_tone gains the floor_bands method (Blackman-Harris held window,
      inter-harmonic floor medians, ±80 Hz harmonic exclusion, consistent on
      the RECORDING cuts AND the render side) — the fit's wind rows now ride
      the recording's true breath: floors land at −62..−68 dB rel H1 at
      band-1 (45-70 dB under the published-tabulated skirt values).
  (2) The wind-shape search (analytic |H|, no timed-out loop) picked the
      wash profile: broad non-resonant bp Q 0.4 at 1.26 f0 + gentle lp
      3.4 f0 Q 0.4 — the ENGINE caps windQ (bumpQMax 0.6, noiseLp 3.4/0.4)
      and synth_replica mirrors it; per-note wind rows re-fit landed the
      render correctness checks: floors −68..−87 across B5/C6/F6/A4 vs
      recording truths (b1 ±4 dB, b2/b3 ±4-7 dB as the shape model's
      residual; A4's render H1 −28.9 with the B4 bridge — the
      "A4 too soft" catch addressed).
  (3) hold_spectrum.py — the tool copy: finds the held tone, writes the
      txt-format spectrum + hold summary; reproduces the F6 ground truth
      class (floors −70..−100 rel H1 vs the export's −67..−96);
      documented as the arbiter when measurements disagree.
  (4) The onset sand-paper isolated: the render's onset burst survives
      zeroing air/wind/ot and the fitted chiff (the loop corrected rows to
      −43..−74 dB peak while the measured burst sat at −11 dB) — the burst
      is the ENGINE's pre-tone stage: the attacking fundamental's swept
      skirt rides at the −14.3 dB pre-tone level (measured: the cluster at
      1.01-1.05 f0 exactly at the pre-tone fraction) while the real
      recording's lead-in is a quiet 20 ms swell (−45 dB). NEXT UNIT SPEC:
      engine attack-stage fields from the recorded attacks (rows carry the
      per-take attack_to_plateau 10-30 ms — the engine floor 0.04-0.05 s
      still measures 0.07-0.1), the chiff row paths keep their onsets, then
      re-fit onsets; held for Robin's field check as audible.
  (5) Suites: full sweep 46/46 (352 s, engine touch → policy sweep) + eslint
      clean; sw VERSION → oco-pwa-v35 (rule 15 — engine js changed).
  Held for Robin: the field check on the whole round (A4 loudness, the
  porcelain wash, the onset character after the next unit's attack fields);
  the glide-tap engine constant already drafted; B4 re-record + the
  double-alto-c re-record per IDEAS when he gets hands-on time.

- **2026-09-27 (session 17 cont. — the held-spectrum night: the white-ish noise loses three roots, the wind rows re-fit, the attack-stage unit lands its first fit)** —
  Robin's directive (fresh session): focus on the spectrums of held-note parts
  (reference WAVs vs our renders). Juno's night ran unattended per the away-
  work grant; landed on `12-hole-synth-tuning` in three commits:
  (1) `79ca6e8` the previous session's attack-stage WIP reviewed fresh (it was
      from an errored >350K session) and committed as the checkpoint: engine
      atk {speak, pre} rows, fit_tone atkPre loop, refit tone.json, sw v36;
      sweep 46/46 (a one-off bad_chip_style flake passed isolated and again
      in the rerun).
  (2) `302a20f` the comparison machinery: hold_spectrum --span (cut-relative
      forced windows for the B4/D6-class wobbly holds), spectra_compare.py
      (one method both sides, per-band deltas via targets.json's on/off minus
      cutStart), render_ours --wind (constants verified through REAL renders —
      the delivered WebAudio chain deviates from the analytic RBJ 2-biquad
      model by 3-6 dB/band and the deviation drifts per candidate), the
      cross-tool floor-scale convention lesson (ton_report/hold_spectrum/
      exporter differ 2-4 dB on absolutes; F6's export stays the arbiter).
  (3) `450991f` the roots: (a) the 0.5 s wind loop was a 2 Hz-spaced LINE
      COMB — every noise line in the renders sat at k×2 Hz (isolation probes:
      tone-only silent, wobble/wander/chiff/ot/edge contribute ~nothing;
      the comb WAS the texture)— now a 4 s loop, verify renders show no comb
      lines; (b) the WIND_SHAPE mid-wall (0.6/2.6/0.8) from a rendered
      candidate matrix (delivered b1→b2 fall 4-7 dB vs the old flat 2.4);
      (c) vInterpHold — the fitted model HOLDS the nearest anchor beyond its
      range (Robin's A3/B3 catch was the clamped-slope extrapolation reading
      B4's contaminated blip row out to −13.2% wobble at 21.5 Hz, a fast
      inverted tremolo); (d) wind rows re-fit 3 rounds under the new shape:
      b1 ±0.9 dB on all 11, F6 delivered −67.4 vs Robin's export −67;
      b2/b3 keep a −8..+3 take-spread residual (skill: do not over-fit single
      takes; F6-exemplar precision would want per-note lpRatio/lpQ rows).
  Suites: full sweep 46/46 green at the commit; eslint/html-validate clean;
  sw oco-pwa-v37 (engine touch). Board: §1 noise item rewritten with the
  landed roots + open field-check list; hot list refreshed; the session's
  render/probe material lives in research/analysis/12hole/renders_v37/
  Suites: full sweep 46/46 green at the commit; eslint/html-validate clean;
  sw oco-pwa-v37 (engine touch). Board: §1 noise item rewritten with the
  landed roots + open field-check list; hot list refreshed; the session's
  render/probe material lives in research/analysis/12hole/renders_v37/
  (gitignored, regenerable from the tools).
  MORNING DECK:
  - FIELD CHECK (the deciding pass): the fitted voice's held texture (comb
    gone? porcelain?), the attack character (atk rows, pre-tone 0.19·M →
    0.01·M), the A3/B3 hold-at-anchor delivery (B4's own row now plays
    there — the 9.4 Hz/10.7% wobble reading rides it; re-record or keep).
  - The default voice picks up the 4 s buffer fix automatically (same wind
    chain); its H3 chamber-3 formant is DESIGNED doctrine (V_ANCHORS h3
    0.021 at the top retuned only by his ears).
  - If the F6 exemplar wall must be exact, the next structural build is
    per-note lpRatio/lpQ rows (candidate-matrix method in the skill).

- **2026-09-27 (session 17-cont. #2 — the held-note recordings land, the kokiri/storms rule becomes law, the puff bisects to the engine's own bloom)** —
  Robin's field catches drove the night: B4's wobble was onset-implied
  (never in his takes), F6 grit is engine-general, and the E5/F5/G5/A4 "tongue
  puff" he never recorded. His morning additions
  (research/note-recordings/12hole/*-held.wav, 8 notes) became the primary
  rows: A4/A5/C5/D5 direct anchors, the coherent wobble class 6.5-9.3% @
  2-6 Hz, and the rules landed hard — kokiri/storms NEVER note values (context
  rows interpolate/extrapolate from the fitted ladder rows), short spans
  (<0.40 s) can't imply a wobble, the burst extractor must bound the window by
  the tone's own arrival (the A4 take's rising tone once became a 200% chiff),
  and unresolvable onsets fall through to the entry take or the nearest fitted
  neighbor (the engine's generic chiff fallback was making puffs the takes
  never carried). Engine gains per-note noiseLpRatio/noiseLpQ (the 2-biquad
  family was saturated: b2 −4..−5.6 regardless; the walls now move per note),
  a row chiff delay (his swells start ~55 ms in), and sw v38. The puff's last
  root bisected clean tonight: NOT chiff/wind/air/edge/ot (profiles identical
  with each zeroed) — the tone's own level+pitch bloom (~80 ms) where the
  takes speak in ~15-20 ms; the next engine unit makes the fitted attack shape
  row-expressible. Full sweep 46/46 at both commit points; lint clean;
  `12-hole-synth-tuning` carries `79ca6e8`, `302a20f`, `450991f`, `d9826f3`.

- **2026-09-27 (session 17-cont. #3 — the field check fails the voice; the complaint spectra are the next unit's ground truth)** —
  Robin's verdict stands above everything tonight shipped: the fitted voice
  "sounds very bad currently." His IDEAS note names it precisely — the
  broadband-with-filters model sounds NOTHING like a real ocarina — and the
  complaint spectra (research/analysis/12hole/complaint/
  C5_hold_spectrum_{recording,render}.txt) measure why: the recording's noise
  is a BODY with a warm fixed pocket at 273-600 Hz (the 273 Hz bump exists in
  every recording — a physical, f0-independent cavity resonance the synth
  never had), a deep valley through 900-1800 (Robin: "very big holes in the
  real noise profile; nothing like the broadband you have"), and rough upper
  bands — while our render is a monotone shelf with its bump ABOVE the tone
  (1.26×f0) where the real pocket sits BELOW it. The held-note per-note
  walls/wobble/hold-at-edge plumbing of tonight survives (verified rows, b1
  tone accuracy, no invented extrapolation), but the NOISE SHAPE MODEL is
  the target next fresh session: full held-spectra agreement across the
  held-note set, not a few band medians. Board §1 carries the item verbatim
  from his IDEAS entry; nothing mooted, nothing executed at high context.

- **2026-09-27 (session 17-cont. #4 — the noise-body layer becomes the engine, the wall re-fit rides it, Robin's meter rule lands)** —
  The fresh session opened on the parked noise-BODY unit; four commits:
  (1) `d62aad2` **AGENTS §18**: the context-meter number is distrusted in a
      FRESH session (Robin's rule — the session-open reading confused the
      AI every single time it was trusted; the zone becomes truth again
      only once the session's own work stands behind it). This session's
      own 322K "watch" verdict was exactly that class.
  (2) `0149570` **the engine unit**: the wind chain gained the absolute
      noise-body layer ahead of the tone-tracking chain — parked pocket
      peaking 273 Hz Q2.2 (fixed-absolute, gated by tone.json's global
      `windPark` so unfitted voices stay byte-identical), warm shelf 470
      Q0.8, and the upper roughness as a PARALLEL bleed past the per-note
      lp wall (highpass 2900 Q1.1 → shelves 6000/−10 + 9500/−7 → bleed
      gain: the recording's rough bed survives to 12 kHz where the walls
      carve 700-1900 holes — one series chain cannot express both; the
      first bleed anchor rendered +30 dB raw-bed-hot and went 2400/Q0.6 →
      2900/Q1.1 + a −33 dB gain anchor through five rendered rounds).
      render_ours grew --parkDb/--warmDb/--roughDb candidate injection;
      parkDb is per-note row-expressible. C5 body matrix converged (pocket
      +0.9, warm −2.0, trough +1.8, rough2 −1.1, tail −0.4 rel-H1).
      Full sweep 46/46, lint clean, sw oco-pwa-v39.
  (3) `a73f9c9` **the data unit**: fit_tone injects the layer global into
      every candidate + draft (the wall re-fit must shape against the
      recomposed chain) and publish() keeps it; fit --rounds 3 landed
      band-1 ±1.2 dB on all 15 fitted rows; per-note parkDb rows measured
      from the eight held takes (span −13..+13: F5 nearly silent, A4 the
      loudest — the fixed bump rides per-note cavity coupling, so rows not
      set gain) written into tone.json; after the rows, pocket within ±3
      on every measured note. data_validator/instruments_load/
      console_hygiene green; sw stays v39 (data + fit tooling only).
  (4) Skill maintenance carried the method: abs_shape.py promoted (absolute
      band table, ±80 Hz harmonic exclusion, both sides one method; ±3-5 dB
      take noise per 0.74 s window doctrine), the layer's docs + the
      research-tree folderization (12hole batches now truth/v36/v37/v38/
      held/shape_candidates/isolation/ladder/early/measures with the live
      state at top level; targets.json paths untouched) noted in place.
  OPEN (§1 item rewritten): the wall-family residuals — band-2 −2..−8
  under-carved (the wall's dB-per-unit calibrations measured pre-layer),
  hole2 +10/H2zone +4 (C5), rough1 +5, per-note warm (A5 +7.4), A5-class
  bleed tail −11..−14 — plus the fit loop learning parkDb itself.
  HELD for Robin: field check on the recomposed voice (the layers are
  audible by design).

- **2026-09-27 (session 17-cont. #5 — the wall pass re-fits on the layered chain, the intermediate writer ships, Robin listens)** —
  Robin's turnback ("more out of curiosity… dying to hear some result") set
  the unit's shape: (1) the wall_cal candidate matrix re-measured the
  band-to-wall responses through real renders on the layered chain — b2
  +4.1 dB per Δratio (not the pre-layer 6.5 — the bleed refills the bands,
  which is where round-3's under-carve came from), b3 ~+3.3, Q near-inert;
  (2) the fit loop's wall leg converged via a damped dual-residual sum (0.4
  gain, ±0.9 — per-note response is not one constant; A4 swung ~11 dB per
  0.68 move under the dual ±1.2 form), round-5 landing band-1 ±1.5 and
  band-2 mostly ±4 (A4-E5 −0.2..−3.8; F5/G5/A5/F6 keep −6.9..−8.7 where the
  expressible row set bottoms out); (3) write_intermediate now puts each
  round's converged rows straight into the SHIPPED tone.json so a mid-run
  listen always hears a fully-fitted voice (per-row keys the loop never
  recomputes — parkDb/noiseLpQ — carry over from the last published state);
  (4) body-table spot check on the live state: C5 trough/rough2/tail/
  airhead within ~±2, pocket/warm/in-take class; the open residuals named
  in the item (hole depth, rough1-vs-tail per-note split, parkDb loop leg).
  Commit `6c49ef6`; data_validator/instruments_load/console_hygiene green;
  sw stays v39. Robin is playing the intermediate state — his field check
  steers the next row family.

- **2026-09-27 (session 17-cont. #6 — Robin names the white wash, the stage gate becomes default, the bleed is rescued)** —
  Robin's ear drove the unit: F5's render carries "lots of white noise,
  sustain but much much more during the onset; could it be some generic
  (not tone.json) broadband noise?" — and the doctrine: "checking the
  end-result WAV to the recording, in the sustain/hold, onset and decay
  should be part of the DEFAULT verification" during sessions like these,
  plus the held takes are the better reference (commit them, the note
  value WAV output is compared with them). Landed (`22f5711`):
  (1) the isolation probes: with windAmt=0 the sustained wash collapses
      (−113.6 hold) and the onset grossness collapses with it — NO hidden
      generic path; the white character was the bleed path itself: the raw
      highpassed white bed (every other noise path is chamber-shaped);
      (2) the bleed became a second chamber-colored lobe (bp 2.7×f0 Q0.9,
      absolute tilts retained; rough3's −9 gap closed at once, rough1/
      trough/tail still want per-note rows);
      (3) tests/tone_stages.py — the DEFAULT gate: 8 held notes ×
      onset/hold/decay, render-vs-recording, broadband + abs-band caps,
      known-open allowlist declared per defect class (the onset-swell
      leg, the bleed/wall classes, wobble-window pairs); the held wavs
      ride the COMMITTED reference set so CI runs it for real; searched
      working-set-first, loud skip absent (midi_track_audit pattern);
      (4) publish() stops stomping per-row keys (lost parkDb once);
      (5) sw v40; full sweep 47/47 with the suite inside; lint clean.
  The unit state: the stage table reads onset swell +16..+19 (C5/D5),
  pocket +20..+28 at onset, E5-tail/G5-tail classes at hold — all
  declared — and the next build is the wind-envelope attack leg + per-note
  bleed/warm rows + hole dips. Robin heard the earlier state; the new
  lobe voice (v40) rides a reload.

- **2026-09-27 (session 18 — the Helmholtz twin replaces the 12-hole's voice; Robin's field ruling restores the handoff state; the tone-analysis era closes for this ocarina)** —
  Robin's zip handoff (research/ocarina-twin-synth-handoff.zip, produced with
  Grok Expert) replaced the synth. Answers batch up front: per-instrument
  swap with easy later cleanup, the 12-hole replaced OUTRIGHT (no A/B flag —
  "our current 12-hole is even worse than before this branch started"), the
  zen pan-chorus rebuilt, work stays on `12-hole-synth-tuning`, and the stage
  gate "replaced with something better given the new info". Five commits:
  (1) `d608d18` **the skill**: skills/ocarina-twin/ (fit.py's tracked H1-H8
      subtract fitter, synth.py offline reference renderer, model.py
      ocarina-twin-v2 schema) + the first fitted chamber shipped
      (instruments/oot-alto-c-12/twin_model.json, 8 held takes A4-A5).
  (2) `3076835` **the swap**: js/helmholtz-voice.js (sine through the cavity
      bandpass + period-synced turbulence → residual/hiss/chiff routes +
      minute dry H2-H6; the 4 s crossfaded noise buffer rides the line-comb
      lesson) driven by installTwinModel; playNoteAt branches into the twin
      path (same slot arithmetic, cut bus/track mix/pan-chorus rebuilt;
      lite = the handoff's sine→bandpass shape); manifest `twin` loads like
      tone.json; README carries the swap + legacy-cleanup path; sw v41.
  (3) THE FIELD RULING — Robin hardcoded while the row-closure pass was in
      flight: "the handoff state was perfect before"; my algebraic rewiring
      (model rows rewritten to close against the renderers + a one-sine
      amp-wobble + the deepened wander) made it worse — "the wobble at A4
      is very bad... some onset noise and shit back" — and `10b76d7`
      reverted all of it: module + model byte-identical to the handoff
      again, tone_stages becomes the REGRESSION gate on the adopted
      baseline (his blessing, not my row math, defines right), the
      calibration tool never landed. A measure-and-fit finding rode the
      diagnosing: the fitter's old median*4 span guard collapsed EVERY
      span onto the 0.15/0.85 fallback (release+silence measured as
      sustain — med4/peak 2.3-3.7 on every take); the peak*0.08 fix STAYS
      in fit.py, and the shipped model stays the blessed reference even
      though fresh refits now differ (they go through his ears).
  (4) `e9dd12b` a reverted-edit leftover dropped (twin kill() disconnected
      out twice since the head-wrap edit).
  (5) `d58ef80` **tone.json retired with the swap** (Robin: "the instrument
      is twin and there is still a non-twin tone.json") — the 12-hole's
      manifest declaration and file both go (the additive voice keeps
      tone.json for stein double + contrabass); instruments_load's boot
      legs wait for BOTH model round-trips to settle; CI installs
      scipy+soundfile for the twin gate.
  New INFO: a reproduce run of run_fit.py against the 8 held takes matched
  the shipped model bit-for-bit under the old span (deterministic pipeline);
  tone_stages rebuilt = fit-row regression caps around the blessed delivery
  + stage windows (rel-H1 ratios replaced by plateau-relative release depth
  in the decay leg — the interpolant's own rel bands blow up once the
  fundamental departs). Offline-reference parity checks died with the
  calibration pass: the python reference renderer under-delivers its own
  res/hiss rows 8-18 dB (the rows are convention-relative; the web voice
  delivers them its own way and that is what his ears blessed).
  Sweeps: full 47/47 TWICE (final at `d58ef80` + tone_stages flaky-b4-slope
  cap set 7.0 from the measured flap); lint clean; board verify green;
  sw oco-pwa-v41 (engine change). MORNING DECK: FIELD CHECK the voice
  (texture/attack/glide/practice); the top register A5-F6 takes when he has
  hands-on time; the twin-skill file map lives in skills/ocarina-twin/SKILL.md
  with the first law — HIS EARS, not row math.

- **2026-09-28 (session 18 cont. — the stein's temp twin: 3 recorded notes become a two-chamber voice)** —
  Robin's ask: three recorded notes of the Focalink Stein double alto C
  (research/note-recordings/double-alto-c: C5 + its 2nd take, D6, G6 — a sep-17
  session), "a temp twin until I record more". Landed `<<twin-ste` commit(s)
  (see git log — two commits: the multi-shape engine + the temp data):
  (1) The fitter's nominal table gained G6..Cs7 — G6 had FALLEN THROUGH to
      the 500 Hz default (the NOM table topped at F6) and the whole tracked
      subtract built on a wrong octave (f0 read 557 with H2/H3 "louder than
      H1"); after the fix G6 reads f0 1566.3 (-1.7 cts of nominal).
  (2) The multi-chamber wrapper ("ocarina-twin-multi-v1" =
      chambers: {ch: {model, gain}}): installTwinModel stores per-chamber
      models + gain; playNoteAt routes EVERY NOTE by its chart chamber and a
      chamber WITHOUT a model keeps that note on the additive voice
      (temp-twin instruments may cover only part of their range; the
      chambers never lerp across V). The single 12-hole shape installs as
      chambers {"1"} — one code path, the 12-hole unaffected.
  (3) The temp data: chamber 1 = C5 (2nd take, f0 +11 cts, wander 8.8 vs the
      first take's clamped-12 tracking) + D6 (chart says chamber 1 runs
      A4-Ds6!); chamber 2 = G6 alone clamped at both ends. Per-chamber
      internal levels normalize to their own peak; the CROSS-chamber
      loudness rides the wrapper gain (ch2 0.57 = G6's raw level vs the
      chain's D6 peak — the takes' 15 dB C5-under-D6 gap stays relative,
      flagged in the file's head).
  (4) Verified: validator (multi shapes), instruments_load (multi install
      legs + a wrapper probe with a gain-less entry), the render bench
      routing three notes (clamped C5, interpolated G5, chamber-2 G6 — the
      gain math checked: predicted G5/G6 ratio 0.2 dB, measured 0.2),
      console hygiene, full sweep 47/47 twice at the wrap, lint clean,
      sw oco-pwa-v42 (engine touched for the routing). README carries the
      twin file shapes; the skill carries the multi/temp doctrine.
  HELD for Robin's field check: the temp voice's character across the wide
  unfitted spans (the whole second chamber rides one row; chamber 1
  interpolates across 2.2 octaves) — his retune/refit wording steers.

- **2026-09-28 (session 18 cont. — the CI red is a one-line artifact-path fix)** —
  CI run `36394556428` (push at `b818548`, the "Run held-note stage
  verification" step): all 8 held notes rendered and measured clean on the
  runner, then the artifact dump crashed — `research/analysis/12hole/` is
  work material, not committed, so a fresh CI checkout has no such dir
  (`json.dump` on a missing parent). Fix: `os.makedirs(OUT, exist_ok=True)`
  at main() start. Verified by simulating the CI shape locally (the dir
  tucked aside, suite green exit 0, files restored untouched). No sw bump
  (suite-only change).

- **2026-09-28 (session 19 — the Zelda melodies gain their contrabass tracks: Saria's heard green, Epona's riding)** —
  Robin's pasted improvements went verbatim into the corpus on `update_songs`:
  `sarias-song` gains `#track contrabass audible 70` (the 11-hole Lost Woods
  chord windows, 36 bars) and `eponas-song` gains `#track contrabass audible
  100` (the ranch bass, 32 bars aligned with the melody's section meter) —
  melody rows, names, tempo/swing untouched. Robin field-heard Saria's Song
  GREEN live ("must have been cache" — the SWR copy had served the pre-track
  body on his first visit; sw VERSION → v43 so deployed data lands on the
  first reload). Suites: shipped_songs (the track-stream contract across the
  corpus: streams clean, zones declared, per-bar sums equal — 4 multi-track
  songs align bar-for-bar) and gen_pages green; no js/html touched. HELD for
  Robin: the Epona contrabass at full audibility is his ears' call.
  Follow-up same unit: the identical 100-block rides `eponas-song-bass` — its
  body is literal, not a derive — so both Epona versions play the same D3-G3
  ranch contrabass. Robin then ruled "don't drop the contrabass down an
  octave" on the `sarias-song-bass` derive: library.js deriveBody now hands a
  valid `#track` stream through VERBATIM (parse.js isTrackHeader shared fold;
  melody-only shift; malformed headers change no boundary, per parse's rule),
  red→green with twin_derive's frozen fixture rewritten to the verbatim block
  as the spec — both Saria versions now play E3-G#3. The song-transposing
  SKILL's rekey rule (track rows shift on purpose) is untouched and the
  ocarina-melodies skill documents the derive doctrine. Suites green on the
  final state: twin_derive, parse_edges, shipped_songs (5 multi-track songs
  align bar-for-bar), gen_pages; eslint clean; sw oco-pwa-v44 (app js
  changed).

- **2026-09-28 (session 19 cont. — the support voices flatten; the phone's data staleness dies)** —
  Two builds on `volume-fix` (Robin renamed update_songs mid-session; PR #19
  merged to main and deployed through 9531b1e, sw v44, by SHA/job: deploy
  site run 36411531795):
  (1) `240fbe8` **the support-level flat anchor** (Robin's ear: the 12-hole's
      Epona support was softer than the oak-leaf triple's — THIS was a
      real engine asymmetry on the bass instruments, additive-generic
      support vs twin's fitted clamped level rows, measured 12.7-13.1 dB
      apart): TWIN_SUPPORT_LEVEL 0.75 — every melodyRoute bag that is not
      the melody's own (track walker both zones + playSupportAt; never the
      melody bag, never the flag-less preview voices) divides the
      interpolated level back out and plays the anchored constant × a new
      `supportLevel` debug-panel multiplier; timbre keeps the fit. The
      stein's support lifts the same +13 dB with it. Red→green
      tests/twin_support_level.py (CI-registered; the bench gained a real
      bag override __BAG__): E3/G3 twin-vs-additive within 1.5 dB, red
      carried the defect verbatim. Full sweep 48/48 at it; sw v45. HELD
      for Robin's field check: the new support balance on every
      instrument.
  (2) **the PWA data-freshness pair** (Robin: the phone couldn't reach the
      new songs by refreshing; the answer batch: data → network-first
      WITH cached fallback, resume silent re-fetch → build both, js/css
      stay SWR):
      sw.js: DATA_NETWORK_FIRST = songs.json + instruments.json + every
      instrument's tone/twin model, served network-first with cached
      fallback, fetched with `cache:"no-cache"` (the browser HTTP cache's
      heuristic freshness — 10% of the served file's age — once answered
      the worker's fetch with a stale-200 that held for over an hour);
      the install derive now precaches inst.twin beside inst.tone;
      js/app.js: on visibility→visible with nothing running (no melody,
      no practice) a silent songs.json re-fetch swaps BUILTIN + the
      generated scales + the library when the text changed (30 s rate
      gap; failures silent).
      The debug's own two traps, both lesson-class: python's
      If-Modified-Since revalidation compares mtime at WHOLE-SECOND
      precision — a file rewritten within the same wall-second as the
      previous serve revalidates as 304 with the cached body (the suite's
      sentinel rewrite raced its own freshness clock; one real clock
      second now separates the legs), and correctness demanded ∼7
      instrumentation rounds before the layer that lied (the worker
      served the HTTP cache's stale-200, not the network) was found by
      watching the server itself.
      tests/offline_pwa.py gained two supervisor legs: an online reload
      lands the released data on the FIRST reload (red carried the
      stale-while-revalidate lag), a resume re-fetch swaps the library
      (red carried the no-re-check defect). Green ×3 at the final state;
      console_hygiene + asset_versions green; eslint clean.
      HELD for his phone: one deploy cycle of refreshing/cold-starting
      with the new worker; the resumed-app library swap is idle-gated by
      design.
  QUEUED on his word: the E5/A5 mid-range stein takes (the melody's own
  balance fix, unblocks the wrapper-only paths), PR copy for the pair.

- **2026-09-28 (session 19 cont. — the transport/JOIN set: notick defaults, the loop rides the share, the Zen link goes deep)** —
  Three small shipments on `volume-fix` after the batch answers:
  (1) **notick defaults**: the five multi-track songs (sarias both, eponas
      both, outset-island-midi) carry `"tick": false` — the tick contract
      (library.js, IDEAS 2026-09-25) makes the song's own declaration the
      in-session override, so the metronome now starts OFF when an
      accompaniment carries the beat; the user's re-enable still overrides
      per session and persists nothing. tick_override green.
  (2) **the loop state is shareable** (Robin: "the loop on/off should be
      shareable"): the Zen share URL carries `?loop=1|0` — the sender's
      current setting, both values explicit — and boot applies it before
      anything plays (the change event doubles as the mirror/focus loop
      sync). practice_zen_return legs pin both directions red-first.
  (3) **the Zen share uses the per-song deep link** (Robin: social/chat
      previews must show the song's metadata): zenShareUrl points at
      `song/<category>/<base>/` (the stub's og:title/description/image)
      with `?song=<id>&inst=<inst>&zen=1&loop=<x>` riding for the app —
      the stub's own seed only fires on an empty search so it never fights
      the shared state. The path rules mirror tools/gen_song_pages.py
      exactly (registered variant suffixes and family -bass members ride
      the base page's path; hidden WIPs, the runtime-synthesized scales —
      tagged `generated: true` — and non-library content fall back to
      root+query); the URL resolves through the page's <base href> so the
      share stays correct on the mount and on a root domain. The build
      surfaced a real share hole: a song outside the current ocarina's
      picker range (the range filter hides the option) shared with NO song
      identity — zenShareUrl now reads the loaded library id instead of
      the picker. practice_zen_return deep-link + fallback legs red-first;
      shipped_songs + gen_pages + console_hygiene + tick_override green;
      eslint clean. (The notick data change rides the same unpushed v45.)

- **2026-09-28 (the test audit; dead and self-testing material removed on Robin's word)** —
  the whole battery (46 suites, one deleted since) was read with app-code cross-checks and reported;
  the verdicts: nearly all suites genuinely drive app behavior, one true tautology, one dead
  mechanism, one vacuous cap cluster, a few near-vacuous/lax legs, no purely-ritual suite. On the
  "remove what is not needed" grant: `instrument_switch_race` DELETED (its `loadText` throttle went
  inert at the ESM migration — the app's loadings resolve the module-scoped binding — so it passed
  without reproducing its race; the instLoadGen guard carries the contract untested-by-harness, a
  live re-test would need a route-doctored `loadText` seam); `parse_edges` drops the `rangeUnknown`
  leg (`isOutOfRange` asserted against the restatement of its own definition);
  `tone_stages` drops the never-failing onset/hold stage caps (`KNOWN_STAGES` exempted every pair
  the checks could reach — the decay-release leg stays gated, onset/hold bands still land in the
  artifact for eyes); `wake_lock` drops the bare-boot console leg (a laxer copy of
  console_hygiene's strict manifest allowlist); `practice_history` drops the cents-band and
  sec-floor legs (they restated the app's own caps — `Math.max(1,…)`, the 50-cent accrual cap);
  dead helpers out of `hifi_retune` (`eq`), `render_pin` (`lit`) and `library_favorites` (a no-op
  evaluate + `page.keep`). CI loses the race step (`console-hygiene + 46 suite steps`); all seven
  touched suites re-ran green standalone; test-only change, no sw VERSION bump. Kept-with-sightings
  residue landed in §6 (value-pins that fire on legitimate Robin retunes, the offline_pwa repo-file
  rewrite, the copy-pasted practice arbiter, the deliberate double owners). Deliberately KEPT:
  data_validator's checker battery (needed to prove blind-spot resistance) and spike_watch's
  spikeFake plumbing round-trip (openly declared).

- **2026-09-28 (session 20 — both alto C twins re-level from full ladder fits; the cutting pipeline hardens for edited recordings)** —
  Robin's two ladder recordings drove the session
  (research/recording/12-hole-ladder.wav, double-alto-c-ladder.wav; his
  words: the recordings "should overrule what is already there, which was a
  placeholder to proof the new synth", "the relative volume between the
  chambers for the instrument must be retained", "the max-volume for the
  instrument as a whole needs to be normalized with the 12-hole", the future
  one-take cross-instrument calibration recording stays the true arbiter,
  and "both sessions have been recorded quite similarly. So should be close
  to the end-result"). Two commits on tuning-synth-for-instruments:
  (1) `9c04a7a` **the 12-hole retune**: the ladder cuts to 11 held takes
      (C5-F6, every gap closes below -95 dBFS; one broken first
      segmentation merged two takes into a 4.2 s "A4" blob Robin then
      named - killed by git restore + stale-file cleanup), the committed
      reference recordings swap to those takes (skills/tone-analysis/
      reference-recordings/12hole re-pointed; A4/B4 retire,
      below-C5 end-clamps to the C5 row like the old top did at A5),
      run_fit refits from the canonical held names (11 rows, E6 the
      loudest), tone_stages re-anchors onto the held set (11 notes, f0
      centers derived from the shipped rows, decay leg -9.6..+4.8 inside
      its cap) with the near-constant **+6 dB engine-vs-fitter level
      convention** re-baselining the lev cap 6.0..8.0 (a global delivery
      offset, the per-note curve tracks the takes).
  (2) `4e178c7` **the stein double retune**: 17 takes cut (ch1 As4-Ds6 with
      A4 clamped up, ch2 E6-C7 - the second chamber now fully fitted where
      the temp twin rode one clamped row); per-chamber fits feed the
      multi-wrapper; the raw-peak gains land ch2 under ch1 by 2.85 dB
      (ch1 0.9565, ch2 0.6887) and BOTH fold the cross-instrument scale
      (Ds6 raw peak -0.39 dB over the 12-hole's E6, s = 0.9565) - the
      offline delivery bench verified the level chain (Ds6 -0.8 dB from
      the 12-hole peak, ch2 ratios -2.3..-3.0 delivered). Reference
      recordings commit under skills/tone-analysis/reference-recordings/
      double-alto-c.
  Tool lessons (skills/tone-analysis, in-place): melody_cut measures its
  adaptive floor over NON-digital frames (edited recordings with
  recorder-cleared gaps dropped the floor to -240 and merged neighbor
  takes into one blob), tone_report's onset portrait refuses non-concave
  noise peaks (near-flat trios in leading silence drove ±900-bin parabolas
  that crashed amp_at on every ladder cut) - both fixes ran before the
  fits. The ocarina-twin SKILL notes the new clamp doctrine + the
  cross-instrument gain doctrine. Suites green at both commits
  (tone_stages, instruments_load, data_validator, twin_support_level,
  console_hygiene); lint clean; no sw bump (data + skill tooling only,
  twin models ride DATA_NETWORK_FIRST). HELD for Robin: the field check on
  BOTH voices (including the new end-clamped bottoms), the stein's soft
  G5/A5 takes ride verbatim (A5 reads ~10 dB under its curve neighbours -
  his ears or a re-blow decide), and the one-take calibration recording
  idea stays his.

- **2026-09-28 (session 20 cont. — the second Grok handoff: the shared-air pipeline adopts wholesale; both models refit under it)** —
  Robin's handover zip (research/ocarina-twin-pipeline.zip) plus the
  adoption ruling: "Don't keep both. Grok has been very good in synth
  stuff. Only keep the chorus/reverb and the rest use Grok's stuff."
  Landed `6ce668f` on tuning-synth-for-instruments:
  (1) **the swap**: js/helmholtz-voice.js replaced by the handoff's drop-in
      (same exports/return shape, so audio.js's chorus/reverb/bag plumbing
      kept untouched: hiss HP now tracks 1.6×f0 clipped 700-3500 instead of
      the fixed 2800 that starved the top register, the hiss splits
      dry/synced by dry_hiss_frac with the fitted slope as a highshelf,
      and the cavity-breath BP Q falls with open holes).
  (2) **the package swap**: ocarina_twin adopts the handoff's air.py (the
      canonical definitions), model.py (dry_hiss globals + per-note
      noise_Q rows), fit.py (hiss measured on the same band the voice
      plays; fitted_noise_q rows), synth.py (validate-matched offline
      reference), run_fit.py + NEW validate.py. One adoption patch: the
      NOM table carries Fs6..Cs7 (the stein's second chamber reaches C7;
      a missing key rebuilt the whole subtract on a 500 Hz default -
      session-18's lesson).
  (3) **both models refit** from the committed ladder takes under the new
      air: 12-hole hiss rows land -33..-41 (the old fixed-2800 measure
      read -38..-58); noise_Q falls 11.1..6.6 with open holes; top slopes
      flatten to -2.0..-2.4. The stein refits both chambers; gains
      re-derive (ch2/ch1 -2.57 dB, cross scale s = 0.9783 = Ds6 -0.19 dB
      over the 12-hole's E6 - the sessions stay similar-class).
  (4) **the E6 exclusion**: the stein ch2's E6 take is unfittable under
      the pipeline (its 20% wobble + a fallback span slice that swallowed
      77 ms of attack slid the tracker into a wrong well: residual read
      tone level, "res -0.0"). Excluded from the fit; E6 end-clamps onto
      F6's row; its WAV stays committed reference material for a re-blow.
      The span rule is Grok's now (thr = max(peak*0.08, med*4)) - the
      ladder cuts kept the fallback mostly inside their sustains and the
      gate measured clean; the doctrine records the tell.
  Verified: validate.py within the handoff's acceptance (F6 dHiss -2.8,
  E6 -1.9 - the ~4 dB cap; C5's 1.5-2.8 kHz floor -65 vs the recording's
  -51 = quieter-than is the C5 rule and never-brighter holds); tone_stages
  green across all 11 notes with the EXISTING caps (hiss deltas -7..-13,
  slope within ±6.7, wander ≤9.4); instruments_load, data_validator,
  twin_support_level, console_hygiene green; lint clean; sw oco-pwa-v46
  (engine js changed). HELD for Robin: the field check on the new air
  (does the top register's hole-rush read right on his device now),
  plus the standing asks (both voices, end-clamps, stein's soft G5/A5).

- **2026-09-28 (session 21 — the third Grok handoff adopts wholesale: the mid-air leg replaces the shelf air, both twins refit, the stage gate re-anchors H4)** —
  Robin's package drop `research/ocarina-twin-lead.zip` (Grok's LEAD,
  2026-09-28 evening) with his standing order: Grok leads on tone
  analysis — no homegrown "learned fixes" this session. His HANDOFF
  overrides the earlier zips and names the 1.6f0/highshelf air path THE
  BUG ("extra fizz is not hole-rush" — why E6/F6 read "not airy
  enough"): E6/F6 air is a MID PEDESTAL [1.25 f0, 4 kHz], the high hiss
  [4 kHz, 12 kHz] stays quieter, per-band delivery RMS-matches against
  the tone rows ("change filters, change that helper — never add
  another EQ stage"). Landed on tuning-synth-for-instruments:
  (1) js/helmholtz-voice.js byte-identical to the handoff (audio.js's
      imports are exactly the three surviving exports; the noise
      buffer is RMS-normalized; pinkBandComp stands in for synth.py's
      post-filter RMS match; no highshelf / 2800 or 1.6f0 cutoff /
      airFade; AUDIO_DEBUG.airLevel untouched at 0; windPark stays
      only in the additive voice, outside his zip's scope).
  (2) the ocarina_twin package swaps for Grok's (air.py canonical
      three-band table; fit.py measures res [0.70,1.25]f0 + mid
      [1.25f0,4k] + hiss [4k,12k] on the tracked residual; synth.py
      real post-filter RMS matching with the hiss+6 mid fallback;
      run_fit prints a mid column), with ONE restoration: the
      Fs6..Cs7 nominal rows the zip trimmed are back in fit.py for
      the stein's chamber 2 (data scope; the 12-hole's rows sit
      inside the base table).
  (3) the 12-hole refits from the 11 committed ladder takes: mid rows
      -31..-39, hiss -43.6..-59.5 (F6 mid -34.1 / hiss -43.6, a
      9.5 dB gap = Grok's own not-one-band sanity check).
      validate.py translated to the three-band convention with his
      acceptance sub-bands: F6 syn15 -31.4 (target -32 within 3 dB ✅),
      C5 never-brighter ✅ (mid d -0.2, no 2 kHz shelf), F6 syn58
      -42.2 marginal (2.8 dB over his strict -45 line though 13 dB
      under the mid band — left untouched), D6/E6 read +6..+14 dB
      hotter than their takes (his delivery convention, named for the
      field check, not fixed).
  (4) the stein refits both chambers (ch1 11 takes, anchor Ds6; ch2 5
      takes, anchor A6; the E6 take re-probed and EXCLUDED again -
      its tracked subtract still slips, res read -0.0 - so E6 rides
      F6's row end-clamped). The wrapper gains carry VERBATIM: the
      raw takes are unchanged between fits, so the standing measured
      chain stands (ch1 0.9783, ch2 0.7277; the one-take calibration
      recording remains the arbiter). Stein validates: ch1 C5 mid d
      0.0 (no shelf), Ds6 +6.6; ch2 G6 +7.1, C7 +9.0 - the same
      synth-hotter-than-take class as the 12-hole's top.
  (5) tests/tone_stages green across the 11-note held set with the H4
      cap re-anchored 12 -> 18 on the adopted delivery (the mid
      pedestal now plays INTO the 4f0 window the starved path didn't
      reach: C5/D5 measured +14.3..+14.5 while the delivered band
      still sits about 1 dB off the take's own 1.5-2.8k floor; rise
      deltas read 0.0 everywhere). instruments_load, data_validator,
      twin_support_level, console_hygiene green; eslint@9 +
      html-validate@8 clean; README + SKILL.md carry the lead's air
      doctrine; sw oco-pwa-v47 (engine js changed).
  HELD for Robin (the deciding pass): the field check on the mid-air
  voice vs before - the top register's air character (mid pedestal vs
  the old fizz), held texture, attack/chiff, glide carry, practice
  fit, the three end-clamps; plus whether the top notes' hotter-than-
  take delivery reads punchy or fake on his device.

- **2026-09-28 (session 21 cont. — the mid-air voice is FIELD-BLESSED; Grok's guessed bass twins install for the whole fleet, supports included)** —
  Robin's field check the same evening: the 12-hole mid-air voice "it is
  VERY good. Sounds like real recordings of my ocarina, but played by a
  pro instead of me", the stein "sounds good" — the adopted baseline
  (voice module + both fitted models at 8c4f435) is the field-checked
  truth; the §1 12-hole voice item moved to DONE with his verdicts
  (board tool). The stein refit question he answered by note ("didn't
  know you already did that") — already shipped inside 8c4f435.
  Then Grok's second package `research/guessed-twins.zip` (Robin's ask:
  try it for the other instruments, supports included, until real
  recordings):
  (1) guessed twin models installed at instruments/<id>/twin_model.json
      for dummy-bass-c-double (wrapper ch1 A3-Ds5 gain 1.0 + ch2 E5-C6
      gain 0.92), ico-contrabass-11-c (flat single chamber B2-F4,
      guessed inside globals, Q_prior 38, dry-mid split retuned to
      123-349 Hz), ico-oak-leaf-bass-c-triple (ch1 A3-Ds5 + ch2 E5-C6
      0.92 + ch3 Cs6-G6 0.85). Grok scaled them from the MEASURED
      12-hole mid-air model — no WAV from these instruments; his
      HANDOFF's do-nots carried into the skill verbatim (the 4 kHz
      hiss split is still the alto split; not gospel per instrument;
      not digital twins; triple refit = three sessions one chamber
      each, then the guesses go away).
  (2) instruments.json gains the three "twin" declarations — ALL FIVE
      instruments now declare twin, so melody AND support/track voices
      play the twin engine everywhere (the anchored TWIN_SUPPORT_LEVEL
      path covers the supports; the additive machinery is dormant
      legacy kept for the support red-green comparisons and the future
      cleanup on Robin's word). Charts carry the matching chamber marks
      (dummy 1|2, oak 1|2|3, contrabass 1) so every note routes by its
      own chamber; no cross-break lerps (his wrappers are the v1 shape
      the loader already handles). Contrabass keeps its tone.json
      declaration (dormant, file exists per validator).
  (3) Verified: data_validator (guessed keys pass its notes/f0/h shape
      checks; declared files named), instruments_load (boot battery
      boots all five with their twins; multi wrapper install legs),
      twin_support_level (support anchors on the oak's guessed twin
      within 1.5 dB of the additive reference), console_hygiene (4
      boots clean), gen_pages + shipped_songs re-run for the corpus
      shapes — all green; eslint@9 + html-validate@8 clean. No sw
      VERSION bump: instruments.json + twin models ride
      DATA_NETWORK_FIRST so the new voices land on the FIRST online
      reload (data-only precedent).
  HELD for Robin: the guessed voices' field check (the contrabass hoot,
  the oak triple's bright top chamber, the dummy's mid chamber, the
  bass whoosh — Grok's alto-split caveat) and how they sit under
  multi-track practice; real held-take refits per chamber when he
  records (the guesses retire then).

- **2026-09-28 (session 21 cont. — Robin's file:// console catch: the dead tone.json declarations leave; the additive-code dismantle boards)** —
  Robin's preview (file://, no service worker) surfaced the twin-era data
  debt on instrument switch: stein-double-alto-c and ico-contrabass-11-c
  still declared "tone": paths whose FILES never shipped (twin-era
  residue) — served pages decompose the miss into the documented 404
  (the hygiene allowlist), file:// fails differently (net::ERR_UNEXPECTED
  at app.js:57's loadText fetch) and the tolerance chain still caught
  it, but the console noise stood. His ruling rode the report: "I don't
  want tone.json back. We're gonna dismantle that code path soon." So:
  (1) the two dead "tone" declarations are REMOVED from instruments.json
      (no file existed behind either; the additive voice is dormant
      behind fitted/guessed twins on every instrument; the twin-failure
      fallback contract is unchanged — a failed twin fetch still falls
      to the generic additive voice, now without tone rows);
  (2) the dynamic allowlist machinery absorbed it with no suite edits —
      instruments_load prints "(5 instruments, 0 declare tone.json)",
      console_hygiene's allowed misses fall to 0 and both boot scans
      stay green (data_validator, gen_pages re-run green);
      no sw bump (manifest is DATA_NETWORK_FIRST; no js touched).
  (3) the teardown itself boards as a §5 item (tone.json fetch + the
      additive voice path + the additive-only knobs + the test
      entanglements), queued behind the guessed-voices field check.
  HELD: nothing — the console is clean on file:// and http:// alike.

- **2026-09-28 (session 21 cont. — the instrument-loudness dial unites the debug panel)** —
  Robin's ask: tweak each instrument's loudness as a whole, fine-tunable in
  DEBUG. The answered batch: SESSION-ONLY (his words: "It is just so I can
  feed you the persistent numbers to put in code" — a tuning probe, the
  settled dB values become code constants), a TABLE OF ALL FIVE, range
  -3..+9 dB. Landed:
  (1) js/audio.js: five flat AUDIO_DEBUG keys (instOotDb/instSteinDb/
      instOakDb/instContraDb/instDummyDb, defaults 0), one INST_DB_KEYS
      map by instrument id, and instLevelGain() = 10^(dB/20) read off the
      loaded instrument (window.CURRENT_INSTRUMENT, set by app.js) —
      multiplied into ALL FOUR voice masters (twin full + twin lite +
      additive full + additive lite at the playNoteAt seats), so melody,
      supports and tracks all carry the instrument's own offset; a
      non-declared/no id reads 1 (0 dB = untouched default, so every
      existing suite baseline is unchanged).
  (2) js/debug.js: the new "Instrument level dB (session-only)" group
      with the five rows (-3..9 step 0.1) flagged volatile — the panel's
      save()/restore path now EXCLUDES volatile keys (the panel persists
      everything else to 'oco-debug-audio' as before), so the dial never
      writes or re-applies storage; doubles as the honest workflow: he
      dials, then the settling numbers land in code constants.
  (3) tests/debug_panel.py grew three legs (red-first on the baseline:
      'instLevelGain is not a function' before the js edits stashed out):
      the five rows exist with the -3/9/0.1/0 shape and the session-only
      banner, the dial gain math via window.OCA_DEBUG.instLevelGain (the
      loaded instrument's own key; +6 -> 1.9953, -3 -> 0.7079, +9 ->
      2.8184; a foreign id and null read 1), and the two-sided volatility
      contract driven through the REAL rows: an instOotDb edit must never
      enter 'oco-debug-audio' while a masterLevel edit must persist.
  (4) Suites: full sweep 46/47 with the long support_accepts_brackets
      timing out in the loaded sweep, PASS isolated, full-sweep rerun
      green (the known heavyweight-browser flake class - the practice
      arbiter family); debug_panel green; console_hygiene/
      instruments_load/data_validator in-sweep green; lint clean; sw
      oco-pwa-v48 (audio.js + debug.js changed).
  NEXT: Robin dials his five numbers, then the values become code.

- **2026-09-28 (session 21 cont. — Grok's low-note presence fix lands (Robin deployed the files): the C5-class 1.5-2.8 kHz band is un-eaten, no refit)** —
  Robin's report: "I deployed a Grok fix for low notes were some higher
  frequencies were 'eaten' on the spectrum" — the two files were already
  in the working tree (js/helmholtz-voice.js + ocarina_twin/synth.py,
  staged uncommitted; his note: replace only these, NO refit, JSON rows
  stay — noise_mid_db on C5 is already ~-34, the REDUCTION was a delivery
  shape: Q=80 tone ring + a weak mid band muffled the low notes).
  (1) The two rendered-domain changes, mirrored in BOTH renderers (the
      one-air-definition doctrine holds): playbackQ caps the tone BP
      (30 + f0*0.035 — ~48 at C5, ~79 at F6 so the fitted Q rows still
      rule the top) and the mid path multiplied by
      lowNotePresence(f0) = x2.4 at 500 Hz tilting to x1.0 at 900 Hz
      (by A5); F6's mid/hiss untouched (its stage deltas FELL: hiss
      +1.5, res -4.8 - the Q hair-cap cleaned the subtract skirt).
      synth.py carries the identical lift formula so the offline
      reference agrees with the web voice.
  (2) Verification on Grok's own tooling: validate.py — F6 syn15 -31.4
      (target -32 within 3) unchanged; C5's 1.5-2.8 kHz floor reads
      -49.5 vs the take's -51.2 = the eaten band is back (+1.7 dB over
      the take; was -55.2, 4 dB UNDER). The stage gate re-anchored on
      the new delivery (HOUSE precedent, red-first measured): C5 H4
      +18.8 (cap 18 -> 21), C5 hiss +22.4 (cap 20 -> 24), D5 H2 +6.4
      (cap 6 -> 8), D5 hiss +21.2 — the same classes, hotter by design;
      run-to-run flap class stays inside the new caps (C5 H4 17.7 on the
      rerun). instruments/validator/console boots untouched; full sweep
      47/47 first pass; lint clean; sw oco-pwa-v49 (engine js changed).
  HELD for Robin: the low-note field check (does C5/D5/E5/F5 read as
  full-bodied now rather than muffled; the Q cap's ring character),
  including on the stein (its ch1 low rows ride the same voice).

- **2026-09-28 (session 21 wrap — the shipped streak moves to DONE on Robin's field word)** —
  Robin field-checked the low-note presence fix ("Sounds perfect") and
  ordered the completed streak into DONE (board-only unit; tests scoped
  to the todo/done machinery by his instruction):
  (1) Grok's low-note presence fix -> DONE (commit `ecc5413`, his field
      verdict inside the struck line);
  (2) the per-instrument loudness dial -> DONE (commit `7f44c98`; the
      dial is in live use — his settled dB numbers ride back into code
      whenever he names them);
  (3) the dead tone.json declarations removal -> DONE (commit `b7ac225`).
  The board's open set stays honest: the guessed-voices field check, the
  one-take calibration recording, the §5 additive-path teardown, the
  chamber-fits still waiting on real recordings, and the multi-track/
  Epona/HiFi holds that are his ears' passes.

- **2026-09-28 (session 21 wrap cont. — the audit's approval forks land: both stale items vanish, the teardown stays queued)** —
  Robin's answers on the remaining forks: the §9 per-song landing
  maintenance item DELETED as obsolete (the frozen URL grammar +
  intended-planting rules live in tests/shipped_songs, gen_pages and the
  skills - the item restated what the gates enforce), the §4
  createScriptProcessor WAV-export backlog DELETED (its AudioWorklet
  trigger doesn't exist anywhere; debug.js stays untouched by election;
  the section carries the nothing-open line), and the §5 additive-path
  teardown STAYS QUEUED on his word ("Wait - keep it queued"). The open
  set drops to 5: the slim real-recording refits item (§1), the teardown
  (§5), the Outset arrangement field check (§7), and the two standing §9
  holds (shipped-songs standardization, library widening). Obsolete
  vanishes per the conventions - no DONE entries for deletions; board
  verify + board_tool 12/12 green (todo/done machinery only, per scope).

- **2026-09-28 (session 21 wrap cont. — the wrapper-embed miss fixed: the stein's mid-air rows were never in the shipped wrapper)** —
  Robin's catch: "The Stein double alto has not had the most recent
  fitting, as it is missing noise_mid_db." Confirmed and owned: the
  8c4f435 assembly script loaded the EXISTING wrapper, updated only the
  wrapper-level note, and dumped it - the freshly fitted ch1/ch2 models
  (with noise_mid_db) sat untouched in research/ocarina-twin-lead/
  while the file kept the OLD pipeline-era models. So the stein played
  the JS fallback crutch (mid = hiss + 8) through BOTH its field-check
  sessions ("Stein sounds good", "sounds perfect") PLUS the pre-lead
  globals overlay (dry_hiss 0.15/0.70 over the JS's 0.20/0.75 defaults).
  Fixed this unit with assertions this time (round-trip re-read in the
  embed: gains 0.9783/0.7277 verbatim, 11/5 rows, noise_mid_db present
  on every note; ch1 mid -31.6..-42.5, ch2 -34.5..-39.1 as fitted).
  Validations reproduce the temp-model numbers exactly (now actually
  delivered): ch1 C5 dMid +3.4 / Ds6 +6.6, ch2 G6 +7.1 / C7 +9.0, C5's
  15-band now +1.2 over the take (the same presence-lift class the
  12-hole reads). data_validator + instruments_load (boot battery with
  the wrapper) green; twin_model.json rides DATA_NETWORK_FIRST (no sw
  bump, no js touched); the full sweep did NOT run per Robin's standing
  scope (associated tests only).
  GROK-SIDE OBSERVATION (report-only, NOT touched): the lead fitter's
  JSON globals write dry_hiss 0.15/0.70 while his air.py canonical says
  0.20/0.75 - the JSON overlays the JS defaults, so the EFFECTIVE curve
  is 0.15/0.70 on every refit INCLUDING the field-blessed 12-hole
  delivery. His spec leads; flagged for the next Grok round, not fixed
  here.
  HELD for Robin: re-hear the stein (the blessed verdicts were the
  crutch delivery; the real mid rows now play - louder mid where hiss
  was quiet: ch1's A5-class rows move the most, the crutch read -41.7
  where the fit wants -34.3).

- **2026-09-29 (session 22 cont. — /js/ goes network-first; the noise hunt's serving-layer half closes)** —
  Robin's report ("site synth complete garbage, fine in the VS Code preview,
  ton of noise on the phone app") chased through the serving layers while he
  iterated Grok engine rounds on branches (main reset to before the merge by
  him, branches f2..f5 recovered; his ?v=1 voice-import cache-key fix
  55b86bb reviewed and adopted):
  (1) the cache-anatomy findings named four layers — the SW stale-while-
      revalidate hit branch, the browser HTTP cache (Pages max-age=600),
      the SW cache keyed per URL (the ?v=1 import creates a NEW key, so the
      first load after deploy cannot see old bytes), and the renderer's
      script memory-cache (served the minutes-old module on reload without
      dispatching the SW at all — why the module marker raced in the
      harness); the CORE list was ALSO missing helmholtz-voice.js (Robin
      caught) and then js/wakelock.js (the airplane leg caught).
  (2) /js/ now rides DATA_NETWORK_FIRST with cache:"no-cache" revalidation:
      online always fresh, offline the cached copy (the same contract the
      09-28 data files got). CORE completes with js/wakelock.js — network-
      first makes an incomplete CORE a hard offline 504 where stale-while-
      revalidate had self-healed through the browser HTTP cache — and the
      voice module's CORE entry carries the importer's ?v=1 token.
  (3) suites: offline_pwa's engine-freshness leg red-first (poisoned cache
      copy must lose to the network on the FIRST online fetch and the
      revalidate must overwrite it), asset_versions pins js CORE
      completeness + token lockstep (one entry per module, importer token
      == CORE token); offline_pwa, asset_versions, console_hygiene green;
      eslint + html-validate clean; sw oco-pwa-v54 (serving contract).
  HELD for Robin: deploy + re-hear on the phone (second-visit behavior no
  longer load-bearing); the resume invalidation design for instruments/
  twin models is batched for his picks (the resume hook still re-checks
  songs.json only — a resumed phone keeps the manifest and the loaded
  twin model indefinitely).

- **2026-09-29 (session 22 cont. — the deferred resume invalidation lands: instrument data joins the resume contract, the SW data branch widens)** —
  Robin merged the serving-layer streak to main through PR #29 and opened
  the door to approved/queued items; the §2 batch (his answered forks,
  recorded verbatim when boarded) was the pick. Landed on
  resume-invalidate-instruments:
  (1) app.js: the shared visibility resume slot re-checks instruments.json
      TEXT and the LOADED instrument's twin_model.json under the songs
      gates (foreground, no melody/practice, the 30 s gap, silent-offline
      catch) — a changed model reinstalls installTwinModel audio-only
      under the CURRENT_INSTRUMENT guard, the next played note rides the
      fresh fit; fingerings/template/svgWhen drift defers to the next
      reload with a console.info flag (never a mid-session chart redraw);
      cross-instrument manifest drift only feeds the next boot.
      loadInstrument tracks the twinText comparator beside both install
      paths (fresh and fallback).
  (2) sw.js: the network-first data branch widens from tone/twin_model to
      EVERY per-instrument file (fingerings/tone/twin/templates) — the
      last stale-while-revalidate data class — sw oco-pwa-v55.
  (3) tests/offline_pwa.py: the resume-request-count leg red-first (a
      changed model on disk must fire a fresh model fetch on the first
      resume dispatch — instrument-agnostic filter, because the offline
      swap leg leaves the suite carrying the oak; the if-modified-since
      whole-second trap slept 1.1 s like the songs legs) and the poisoned
      fingerings serving leg (network-first + cache heal), both verified
      red then green; the poison helper factored out for the two legs.
  Suites: offline_pwa x3 through the red/green cycle, instruments_load
  (boot battery + twin shapes + svgWhen boots), console_hygiene (4 boots),
  asset_versions, eslint + html-validate — all green.
  HELD for Robin: the reload nudge's VISUAL surface (console.info-only
  today; a on-page slot is his design call). The commit needs his PR
  merge to reach the phones; field check = a resumed phone app must pick
  up a changed twin model within the next note (his next refit is the
  natural field test).

- **2026-09-29 (session 23 — the VS Code Simple Browser leftover worker is the high-noise class again: file:// SW still intercepted after the HTTP serving fix)** —
  Robin's report: last night's engine/model desync was solved on main, then
  the same high-noise bug returned locally in the VS Code built-in browser.
  The site/HTTP half closed last night (network-first /js/ + ?v=1); the
  preview is a different origin. Evidence in this partition:
  `~/.config/Code/Partitions/vscode-browser/Service Worker` still has a
  registration for `file:///home/robin/git/Ocarina-Practice/sw.js` (dozens
  of update cycles) and CacheStorage `oco-pwa-v55` with an EMPTY cache.
  Electron allows service workers on file:// (Playwright Chromium and
  desktop Chrome do not — that is why the suites never saw this). Sep 23
  (`d0f4d16`) sat out NEW registrations and skipped install cache-fill on
  file://, but (1) never unregistered the leftover worker (it keeps
  updating on every preview navigation without register()), (2) never
  gated the fetch handler, (3) put skipWaiting BEHIND the protocol return
  so a new worker sat WAITING while the old intercept kept running. Last
  night's network-first + cache:"no-cache" then intercepted js + twin JSON
  against that empty cache; a miss 504s and loadInstrument's catch
  silently installTwinModel(null) — the additive wind stack, the same
  audible class as old-engine-plus-new-models. The pairing was never
  observable: no voice stamp, silent additive fallback.
  Landed on resume-invalidate-instruments:
  (1) sw.js fetch returns on non-HTTP(S) before any intercept; skipWaiting
      always, before the protocol return; CORE token `helmholtz-voice.js?v=2`
      so the Simple Browser module URL cannot keep last night's ?v=1;
      sw oco-pwa-v56.
  (2) app.js unregisters leftover file-scheme workers on load (skipping
      register() left them in control).
  (3) helmholtz-voice.js exports VOICE_REV "mid-air-1"; OCA_DEBUG.voiceCard()
      reports rev/protocol/twin/chambers/sw; installTwinModel console.info
      the card and console.warn on additive fallback; the debug panel
      header shows the stamp (Robin already has that panel open in the
      preview).
  Suites: asset_versions pins the three file-scheme gates + token lockstep,
  instruments_load pins voiceCard.rev and twin id on every shipped twin,
  debug_panel pins #dbgVoice, offline_pwa poison URL follows ?v=2,
  console_hygiene 4 boots clean; eslint@9 + html-validate@8 clean.
  HELD for Robin: one Simple Browser reload to let v56 skipWaiting take
  over, then a second load so unregister has run — the debug header should
  read `mid-air-1 · twin <id>` (ADDITIVE is the bug). After that, type
  `OCA_DEBUG.voiceCard()` whenever site and preview disagree.

- **2026-09-29 (session 23 cont. — ?v=1 is the release cache-bust; v2 loaded in the preview and the noise stayed)** —
  Robin's correction: `helmholtz-voice.js?v=1` exists to force a refresh
  when a release is pushed (last night that token + network-first cleared
  the desktop site and the phone). A local token bump is not that lever.
  Restored `?v=1` (importer + CORE + offline_pwa poison URL). The file-scheme
  fetch/unregister gates and VOICE_REV/voiceCard stay.
  The remaining preview noise is a different fact: Simple Browser is open
  at `file:///…/index.html?song=song-of-storms&inst=ico-oak-leaf-bass-c-triple`
  (editor memento). Storms' D6–F6 land in the oak's guessed ch3 (Cs6–G6)
  which still carries the alto 4 kHz hiss split. Phone/desktop last night
  were the 12-hole mid-air voice. The debug header still names the pair
  (`mid-air-1 · twin …` vs `ADDITIVE`).

- **2026-09-29 (session 23 cont. — F6 chamber 1 under an oak twin is the remaining mix)** —
  Robin's probe: sr 48000, Lite off, `CHAMBER.F6 === 1`. Oak fingerings.json
  puts F6 in chamber 3; the 12-hole chart puts it in 1. voiceCard now carries
  chart id, note range, F6 chamber and a twin/chart mismatch flag so one
  paste names the pair. Playing F6 through oak chamber 1 (A3–Ds5 rows at
  1397 Hz) is the high-noise class.
