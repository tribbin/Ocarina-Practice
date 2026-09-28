# Ocarina Practice — Working TODO

Working doc for tracking improvements between AI sessions, committed under
`plans/` so it follows the repo across every machine, partition and clone. It carries
working notes, not shipped documentation. Completed items and retired session-log
entries move beside it into `plans/DONE.md` the moment they complete; the idle idea
pool lives in `plans/IDEAS.txt` — see the note in §9.

## How to use this file (conventions)

- Every item is a `- [ ]` checkbox line.
- **When done:** the whole item MOVES into `plans/DONE.md` — this file carries no
  struck corpses; DONE.md's archive keeps the struck text with its ✅ date + SHA.
- **New findings** go into the matching type section, sorted by importance
  (risk first, then urgency, then effort).
- **Session log:** append a dated entry at the bottom describing what was done to
  app code and to this file.
- Re-check stale items every few sessions: delete anything obsolete (obsolete
  vanishes; done moves to DONE.md).

### Test/fix ordering (agreed 2026-09-22)

No blanket upfront test push — the existing Playwright suites already cover the
dangerous flows. Instead: **write tests for exactly what you change, ideally
before it** (red → green proves the fix); new suites register in
`.github/workflows/practice-tests.yml` in the same commit. The completed
per-item ordering notes are archived in `plans/DONE.md`.

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

Picks for the next session(s), roughly damage × imminence ÷ effort
(refreshed 2026-09-28 late: the mid-air lead is FIELD-BLESSED — 12-hole
"VERY good ... played by a pro", stein "sounds good"; the open ear-decides
front is the guessed bass voices):

| Item | Section |
|---|---|
| **FIELD CHECK the guessed bass twins — draft voices by design, his ears decide what ships beneath them** — dummy C double, ICO contrabass 11, ICO oak leaf triple now declare Grok's guessed twin models (scaled from the measured 12-hole mid-air model, `guessed: true`, `research/guessed-twins.zip`; NO WAV from these instruments was used): support tracks included — every support/track voice on twin-declaring instruments rides the twin engine at the anchored TWIN_SUPPORT_LEVEL 0.75 path. His ears name: the contrabass "hoot" class (lowest V: Q 38, most halo, least hiss), the oak triple's small bright top chamber (ch3 Cs6-G6), the dummy's mid chamber ≈ alto, the bass whoosh (Grok: the 4 kHz hiss split is STILL THE ALTO SPLIT on these — a real bass rush is lower), and how they sit under multi-track practice. Refit per chamber from real held takes when he records (triple wants three sessions, one per chamber; then the guesses go away) | §1 |
| **Robin's dedicated one-take cross-instrument calibration recording** — the true relative volume between instruments (both ladder sessions "recorded quite similarly, should be close to the end-result"; the stein's land normalizes its max-volume −0.39 dB to the 12-hole's chain peak) | §1 |
| **Robin's field check on the multi-track trio** — `outset-island-with-bass` now plays melody + audible bass groove (the bassline two octaves down) + contrabass root-holds; his ears name the balance, the contrabass register, the practice-session audibility and the groove's final-bar cut | §7 |
| **Robin's ears on the Epona contrabass** — `eponas-song` now carries `#track contrabass audible 100` (ranch bass bar-for-bar); Saria's Song he already heard green 2026-09-28 | §Log |
| **Robin's eyeball pass** on the panel builds: the HiFi retune batch (`?hifi` — amber buttons, dark segment row/select, deeper zen red, LED fills) and the favorites stars in the library — his values, built to spec; he retunes anything that reads off | feel checks |
| The twin-model chamber fits per remaining ocarina — recording held takes for the contrabass, oak leaf and dummy when Robin gets hands-on time (all three now play GUESSED twins until then; the stein double + the 12-hole carry their full ladder fits, field-blessed) | §1 |
| The next audio-tick field catch names itself (spike cards carry the ambient ring); Robin re-introduces the hunt when the ticks matter | DONE (re-openable) |
| Shipped-songs standardization stays HELD for Robin's later-stage pass; the permalinks corpora ride his planting as always | §9 |
| Library widening (search, reordering beyond the pin) stays parked until Robin elects it | §9 |

---

## 1. Bugs (correctness / data loss)

- [ ] **Record real held takes -> refit per chamber (the only remaining twin-fitting work; the guessed twins carry every instrument until then)** — dummy-bass-c-double ch1 A3-Ds5 + ch2 E5-C6; ico-oak-leaf-bass-c-triple ch1+ch2+ch3 (Grok: THREE short sessions, one chamber per session, normal blow only); ico-contrabass-11-c one session B2-F4 (its guessed model even retunes the dry-mid split to the instrument's own f0 range — the refit replaces that guess with a measured split). PLUS the stein ch2's E6 re-blow for a fittable take (two fails: res -0.0 both times — tracker slips on that wobble's attack slice); then the wrapper gains re-derive from the raw peaks. The cross-chamber/cross-instrument gain doctrine + refit loop live in skills/ocarina-twin/SKILL.md; refits go through Grok's lead fitter unchanged. `🟨 🟡 ⚙M`

## 2. Robustness / error handling

## 3. Security (low today — matters if data files become user-supplied)

## 4. Performance

Nothing open — the WAV-export backlog dropped by Robin's audit 2026-09-28 (the createScriptProcessor reframe; its AudioWorklet trigger doesn't exist anywhere and debug.js stays untouched by election).

## 5. Architecture / maintenance

- [ ] **Dismantle the additive/tone.json voice path (Robin's call 2026-09-28: "I don't want tone.json back. We're gonna dismantle that code path soon")** — the additive machinery is dormant since all five instruments declare `twin` (fitted or guessed). The teardown: installToneModel/TONE_MODEL + the tone.json fetch in loadInstrument (app.js) + voiceProfileFor + the V_ANCHORS/wind chain (windPark/warm/rough, air*, edge*, chiff*, ot* — the additive-only debug rows in js/debug.js retire too) + the additive lite voice (the twin has its own lite branch). Known entanglements: tests/twin_support_level uses the additive engine as its red-green comparison leg (rework to a twin-only anchored contract); instruments_load's "tone model install / interpolate / fallback" legs retire with the path; instruments/README.md's voice-swap + tone file-shapes sections rewrite. Order of play: after the guessed voices' field check + any last additive-backed comparisons — the tone.json DECLARATIONS are already gone (2026-09-28, the file:// console-noise unit), only the code remains. `🟨 🟡 ⚙M`

## 6. Tests & CI

Currently covered (don't lose this): practice acceptance (4 cases strict+closed-loop), practice dip gate (hold-through blocked, silence/50%-notch dips pass, 75% duck shut, legato free), practice seat across view rebuilds + zen-entry stopMelody + overlay zen-only seats, console-hygiene boot scan (4 boots; allowlist = manifest-declared tone misses), support-bracket battery incl. bit-identical melody-vs-support equivalence + Zen timing/gating, instrument load/tone-model install per manifest (incl. svgWhen id/title paths + boot diagnostics in per-leg fresh contexts), render pin (chips/grid/scroll-band/highlight/focus-restore + typed-render debounce contract), svg clone coordinates, debug panel build-on-open contract, transport scheduler arithmetic/cut-bus/lite, practice history, template safety, theme toggle, offline SW boot+swap, ac worker parity, swing grid, sr hints, spike watch (the tick hunt), the session-14 batch (wake lock lifecycle, tick-override semantics, asset-version token equality, twin-derivation byte-identity, transposer skill, practice dials), the session-15 additions (SEO shell shape + zero-per-stub JSON-LD, zen note-bar glide five-legger, suite-server teardown hardening, board-tool empty-run linting), and the session-16/16-cont. additions (track acceptance battery incl. mix ratios, hifi retune, library favorites star + readability, tests/midi_track_audit = the pure-python source-measure audit with a displaced-downbeat tripwire over tools/midi_track_audit.py), and the session-17-cont. additions (tests/tone_stages = the DEFAULT stage verification after synth-code or note-value changes — rebuilt session 18 for the twin voice: fit-row regression caps + the decay-release gate measured on the ADOPTED handoff baseline after Robin's field ruling (onset/hold stage bands stay measured-for-eyes in the artifact, never gated — their caps could not survive wobble-window luck without flapping); instruments_load pins the twin install/uninstall shapes and waits for both model round-trips; data_validator checks the twin schema; CI installs scipy+soundfile so the fitter analysis runs there;''. **Sweep policy (Robin, 2026-09-26): the full run_all sweep runs only for sound-engine touches; data/song changes run the directly-affected suites (see AGENTS.md §12)** — full sweep 47/47 at the stage-verification commit (including tone_stages) is the last under the policy (including the new audit suite). CI = push/PR/manual, explicitly not a deploy gate. (.github/workflows/practice-tests.yml — console-hygiene + 46 suite steps + eslint + html-validate + board verify (46 after the 2026-09-28 audit removal; instrument_switch_race's step gone); local run-all counts 46 suites (47 before the removal); 42 green 2026-09-25 — see DONE) NOTE: practice_accepts flaked ONE strict case under full-sweep load 2026-09-23, green twice standalone afterward and in the diag run — watch it, the arbiter hardening already took one such race; support_accepts flaked the same class 2026-09-24 (fixed wall-clock read window vs audio-clock lag under sweep CPU contention) and got the class cure: the read is now a real rendezvous with wall-fire stamps + ctx snapshots `335c4b4`). **Third member 2026-09-25 (CLI run `36110497803`, job 107992645371): practice_dip's leg A stalled the full 15 s timeout at maxIdx 0** — same SHA the local sweep had green; a DIFFERENT injury inside the same family: the suite's rendezvous (OCA_PRACTICE+NOTES) unlocks INSIDE loadInstrument (the stretch between installFingerings and boot's tail), where fillLibrary/loadLibraryItem(home) → practiceInvalidate is still owed — a session started mid-boot died when the tail landed; the stall reproduces at will with CDP network latency, cured by the rule-13 real rendezvous: the #scale options guard (filled only by the tail; a rAF poll never resolves mid-synchronous-block) plus a state card (started/st/ix/frames) on every driver resolve so a future stall names itself. The same tail guard rode into every suite that starts practice or needs typed editor text to survive boot (practice_accepts_melody, practice_zen_return, practice_history, keyboard_widgets, render_pin); library_hardening already waited a stronger post-tail signal (the Scales OPTGROUP), playback-only suites are immune (practiceInvalidate stops practice, never play; the instrument-switch race suite was REMOVED 2026-09-28 — its `loadText` throttle went inert at the ESM migration because the app's loadings resolve the module-scoped binding, so it passed without reproducing its race; the app's instLoadGen guard carries the contract and a live re-test would need a route-doctored `loadText` seam). Full sweep 31/31 green after the cure.

> **Test-audit residue (2026-09-28 — consult before touching these):** kept-with-sightings from the full-suite audit — transport_schedule's reference walk re-encodes scheduleMelody's duration constants (dual-maintenance; the `intoSlide` regime is unmodelled and can drift silently); offline_pwa rewrites the real songs.json on disk (restored in `finally`; a hard kill leaves the tree mutated for alphabetically later suites) behind the set's only justified fixed sleep (1.1 s, the whole-second If-Modified-Since lesson); readability's per-state minimum counts, hifi_retune's exact hexes/10px grid and zen_notebar's 160 ms bound are VALUE-PINS that fire on Robin's legitimate retunes (his field passes on the HiFi batch, favorites, and the glide bound are the standing held items); transpose_skill SKIPs (exit 0, loud note) when node is absent — a green-with-asterisk locally on Linux partitions, real in CI; twin_support_level hand-builds `_trackBag`'s shape (a drift there excites a bag the app no longer builds); the derives-record contract is deliberately owned twice (data_validator battery + twin_derive census) as an independent cross-check, as is the per-stub canonical count (gen_pages presence + seo_shell count); gen_pages' `expected_stub_keys`/`category_of` mirror the generator's own filter (both-wrong-together window, backstopped by the boot legs); shipped_songs' bar-grid leg is sum-relative (onset-rotation blind — the known gap midi_track_audit covers on MIDI-bearing machines, with sequential legs that drop the tripwire when an earlier red replaces `raw_rows`); the practice feed/poll arbiter block is copy-pasted across four practice suites (same flake cure re-landed per copy).

## 7. Accessibility & UX

- [ ] **Field-check the game arrangement (Audible-behavior hold — Robin's ears decide)** — the Outset corpus is now ONE version: `outset-island-midi` = "Outset Island (arrangement)" (melody + `#track bass audible 50` + the derived `#track contrabass audible 75`; the with-bass trio, its up12 twin and the bassline solo retired before deploy); his pass names: the plain-view balance (bass/contra levels vs the melody at 50/75), the contra register choice (the game sub-bass +12 reading), the ♭ chord labels in the sheet's caps styling, the loop seam (the closing vamp into the opening one), and whether the layers stay audible INSIDE an active practice session (today they play; the tuner-deafening worry stands). `🟧 🔴 ⚙S`

## 8. Housekeeping

Nothing open — completed housekeeping is archived in `plans/DONE.md` §8.

## 9. Functional ideas (features)

- [ ] **Standardize shipped songs to the `skills/ocarina-melodies` conventions** (barline at wrap start, named sections where players want headers) — HELD for Robin's later-stage pass; verify/shipped_songs are the gates; no playback changes expected. `🟢 ⚪ ⚙M`

- [ ] **Library search / pinning widening** — favorites pinning SHIPPED 2026-09-26 `390c431` (star + first persisted Favorites group); the widening (search box, reordering beyond the pin, grouping options) stays parked until Robin elects it. `🟢 ⚪ ⚙S`

> **Idle idea pool: `plans/IDEAS.txt`.** A live document Robin edits over time and ROBIN'S ALONE — the AI never writes it (it may be read, and only lifted into TODO.md when Robin explicitly asks). TODO carries no copy or summary: when an idea from it is picked up, read the FILE fresh at that moment; never rely on a remembered or transcribed version.

---

## Session log

(Older entries live in `plans/DONE.md` (session log). New entries below — retire via `python tools/board.py log-retire` once another session has opened from them.)

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
