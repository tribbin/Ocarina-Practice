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
(refreshed 2026-09-30 late: the v45 Helmholtz pair is the shipping voice —
the mid-air upgrade stays parked in git history; dummy/contrabass/oak ride
Grok's guessed per-chamber twins until real recordings land; Robin's field
checks are all cleared — the usability batch below is the next session's
work; decisions + state in the session-24 log):

| Item | Section |
|---|---|
| **USABILITY BATCH (approved 2026-09-30, session-24 handoff; 3 of 8 landed `3eb740d` + `f84b564` + `46dec09`)** — small-screen layout (editor hidden on phones, vertical rows, no portrait backdrop), melody-duck on/off, song .txt round-trip, zen-chorus audit, media-session announce + media keys | §1/§7/§9 |
| HiFi stays UNPUBLISHED — the retune + favorites pass is accepted, but Robin holds publication for now (2026-09-30) | hold |
| Shipped-songs standardization stays HELD for Robin's later-stage pass; the permalinks corpora ride his planting as always | §9 |
| Library widening (search, reordering beyond the pin) stays parked until Robin elects it | §9 |

---

## 1. Bugs (correctness / data loss)

- [ ] **Zen chorus audit: did the twin engine drop the zen chorus? (IDEAS question)** — report-first: the twin path still carries the zen stereo chorus (audio.js twChorus: gated on vibOn && dur > vibDelay+0.1, depth faded by vibHighFade 0.4, zenPan 0.9) — check the zen defaults + the lite-voice path and report; fix only if truly lost (field-check class). `🟨 🟡 ⚙S`

## 2. Robustness / error handling

## 3. Security (low today — matters if data files become user-supplied)

## 4. Performance

Nothing open — the WAV-export backlog dropped by Robin's audit 2026-09-28 (the createScriptProcessor reframe; its AudioWorklet trigger doesn't exist anywhere and debug.js stays untouched by election).

## 5. Architecture / maintenance

## 6. Tests & CI

Currently covered (don't lose this): practice acceptance (4 cases strict+closed-loop), practice dip gate (hold-through blocked, silence/50%-notch dips pass, 75% duck shut, legato free), practice seat across view rebuilds + zen-entry stopMelody + overlay zen-only seats, console-hygiene boot scan (4 boots; allowlist = manifest-declared tone misses), support-bracket battery incl. bit-identical melody-vs-support equivalence + Zen timing/gating, instrument load/tone-model install per manifest (incl. svgWhen id/title paths + boot diagnostics in per-leg fresh contexts), render pin (chips/grid/scroll-band/highlight/focus-restore + typed-render debounce contract), svg clone coordinates, debug panel build-on-open contract, transport scheduler arithmetic/cut-bus/lite, practice history, template safety, theme toggle, offline SW boot+swap, ac worker parity, swing grid, sr hints, spike watch (the tick hunt), the session-14 batch (wake lock lifecycle, tick-override semantics, asset-version token equality, twin-derivation byte-identity, transposer skill, practice dials), the session-15 additions (SEO shell shape + zero-per-stub JSON-LD, zen note-bar glide five-legger, suite-server teardown hardening, board-tool empty-run linting), and the session-16/16-cont. additions (track acceptance battery incl. mix ratios, hifi retune, library favorites star + readability, tests/midi_track_audit = the pure-python source-measure audit with a displaced-downbeat tripwire over tools/midi_track_audit.py), and the session-17-cont. additions (tests/tone_stages = the DEFAULT stage verification after synth-code or note-value changes — rebuilt session 18 for the twin voice: fit-row regression caps + the decay-release gate measured on the ADOPTED handoff baseline after Robin's field ruling (onset/hold stage bands stay measured-for-eyes in the artifact, never gated — their caps could not survive wobble-window luck without flapping); instruments_load pins the twin install/uninstall shapes and waits for both model round-trips; data_validator checks the twin schema; CI installs scipy+soundfile so the fitter analysis runs there;''. **Sweep policy (Robin, 2026-09-26): the full run_all sweep runs only for sound-engine touches; data/song changes run the directly-affected suites (see AGENTS.md §12)** — full sweep 47/47 at the stage-verification commit (including tone_stages) is the last under the policy (including the new audit suite). CI = push/PR/manual, explicitly not a deploy gate. (.github/workflows/practice-tests.yml — console-hygiene + 46 suite steps + eslint + html-validate + board verify (46 after the 2026-09-28 audit removal; instrument_switch_race's step gone); local run-all counts 46 suites (47 before the removal); 42 green 2026-09-25 — see DONE) NOTE: practice_accepts flaked ONE strict case under full-sweep load 2026-09-23, green twice standalone afterward and in the diag run — watch it, the arbiter hardening already took one such race; support_accepts flaked the same class 2026-09-24 (fixed wall-clock read window vs audio-clock lag under sweep CPU contention) and got the class cure: the read is now a real rendezvous with wall-fire stamps + ctx snapshots `335c4b4`). **Third member 2026-09-25 (CLI run `36110497803`, job 107992645371): practice_dip's leg A stalled the full 15 s timeout at maxIdx 0** — same SHA the local sweep had green; a DIFFERENT injury inside the same family: the suite's rendezvous (OCA_PRACTICE+NOTES) unlocks INSIDE loadInstrument (the stretch between installFingerings and boot's tail), where fillLibrary/loadLibraryItem(home) → practiceInvalidate is still owed — a session started mid-boot died when the tail landed; the stall reproduces at will with CDP network latency, cured by the rule-13 real rendezvous: the #scale options guard (filled only by the tail; a rAF poll never resolves mid-synchronous-block) plus a state card (started/st/ix/frames) on every driver resolve so a future stall names itself. The same tail guard rode into every suite that starts practice or needs typed editor text to survive boot (practice_accepts_melody, practice_zen_return, practice_history, keyboard_widgets, render_pin); library_hardening already waited a stronger post-tail signal (the Scales OPTGROUP), playback-only suites are immune (practiceInvalidate stops practice, never play; the instrument-switch race suite was REMOVED 2026-09-28 — its `loadText` throttle went inert at the ESM migration because the app's loadings resolve the module-scoped binding, so it passed without reproducing its race; the app's instLoadGen guard carries the contract and a live re-test would need a route-doctored `loadText` seam). Full sweep 31/31 green after the cure.

> **Test-audit residue (2026-09-28 — consult before touching these):** kept-with-sightings from the full-suite audit — transport_schedule's reference walk re-encodes scheduleMelody's duration constants (dual-maintenance; the `intoSlide` regime is unmodelled and can drift silently); offline_pwa rewrites the real songs.json on disk (restored in `finally`; a hard kill leaves the tree mutated for alphabetically later suites) behind the set's only justified fixed sleep (1.1 s, the whole-second If-Modified-Since lesson); readability's per-state minimum counts, hifi_retune's exact hexes/10px grid and zen_notebar's 160 ms bound are VALUE-PINS that fire on Robin's legitimate retunes (his field passes on the HiFi batch, favorites, and the glide bound are the standing held items); transpose_skill SKIPs (exit 0, loud note) when node is absent — a green-with-asterisk locally on Linux partitions, real in CI; twin_support_level hand-builds `_trackBag`'s shape (a drift there excites a bag the app no longer builds); the derives-record contract is deliberately owned twice (data_validator battery + twin_derive census) as an independent cross-check, as is the per-stub canonical count (gen_pages presence + seo_shell count); gen_pages' `expected_stub_keys`/`category_of` mirror the generator's own filter (both-wrong-together window, backstopped by the boot legs); shipped_songs' bar-grid leg is sum-relative (onset-rotation blind — the known gap midi_track_audit covers on MIDI-bearing machines, with sequential legs that drop the tripwire when an earlier red replaces `raw_rows`); the practice feed/poll arbiter block is copy-pasted across four practice suites (same flake cure re-landed per copy).

## 7. Accessibility & UX

- [ ] **Small-screen layout pass (IDEAS: SMALL SCREENS, approved 2026-09-30)** — phones are play/practice, not editing: the editor block is HIDDEN on narrow screens, transport + controls stack into clean vertical rows (today they are "all over the place"), NO backdrop image in portrait, whole viewport functional in normal mode; zen mode stays as-is (Robin: already looks very good). `🟧 🔴 ⚙L`

- [ ] **Melody duck: on/off button during practice with support tracks (IDEAS)** — Robin: a button, not a dial; when ON the melody voice plays at ~20% while support tracks play so his ocarina leads (level tunable on his field check); rides voiceGain; pin the ratio via the note-sink mix battery + a UI leg. `🟨 🔴 ⚙S`

## 8. Housekeeping

Nothing open — completed housekeeping is archived in `plans/DONE.md` §8.

## 9. Functional ideas (features)

- [ ] **Standardize shipped songs to the `skills/ocarina-melodies` conventions** (barline at wrap start, named sections where players want headers) — HELD for Robin's later-stage pass; verify/shipped_songs are the gates; no playback changes expected. `🟢 ⚪ ⚙M`

- [ ] **Library search / pinning widening** — favorites pinning SHIPPED 2026-09-26 `390c431` (star + first persisted Favorites group); the widening (search box, reordering beyond the pin, grouping options) stays parked until Robin elects it. `🟢 ⚪ ⚙S`

- [ ] **Song .txt round-trip with all attributes (IDEAS)** — export a loaded song as .txt carrying title/tempo/tick/swing + its #track blocks, pasteable back into #src (parse.js already understands the # tempo / # title / # track / swing lines); the goal is copy-paste between src and .txt; permalink keys stay frozen. `🟨 🟡 ⚙M`

- [ ] **Media Session announce + hardware media keys (IDEAS: stop-media, scoped down)** — stopping other apps' media is infeasible from a web page (the API is declarative-only, MDN 2026-09-30); Robin approved the announce half: declare playbackState + MediaMetadata so the lock screen / media center names "Ocarina Practice — <song>", and wire hardware media keys (headset play/pause; next/prev only if they map to something sensible) to the transport; gate behind ("mediaSession" in navigator), no-op silently where unsupported; pin the announce state with a small suite leg. `🟨 🟠 ⚙M`

> **Idle idea pool: `plans/IDEAS.txt`.** A live document Robin edits over time and ROBIN'S ALONE — the AI never writes it (it may be read, and only lifted into TODO.md when Robin explicitly asks). TODO carries no copy or summary: when an idea from it is picked up, read the FILE fresh at that moment; never rely on a remembered or transcribed version.

---

## Session log

(Older entries live in `plans/DONE.md` (session log). New entries below — retire via `python tools/board.py log-retire` once another session has opened from them.)

- **2026-09-29 (session 23 — drawing board: restore the v45 pair locally, mid-air does not ship)** —
  Live ocarina-practice.com is still oco-pwa-v45 original Helmholtz (2800 Hz
  hiss, no mid band, unnormalized noise) + A4–A5 12-hole model; Pages deploy
  of PR #29 failed, so last night's merge never reached the site. That pair
  is the last known-good. Local Simple Browser was the mid-air upgrade, which
  Robin hears as high noise against the site. Restored on restore-v45-voice:
  js/helmholtz-voice.js and the 12-hole + stein twin_model.json from 240fbe8
  (VOICE_REV v45-helmholtz); oak/dummy/contrabass drop their twin declarations
  (additive, as the site); guessed mid-air JSON leaves instruments/ (copies
  under ignored research/mid-air-upgrade/). Serving-layer (network-first /js/,
  file-scheme SW gates, voiceCard) stays. helmholtz import token ?v=3 so the
  Simple Browser cannot keep the mid-air module under ?v=1. sw oco-pwa-v57.

- **2026-09-29 (session 23 — additive engine stripped; Helmholtz is the only voice)** —
  Robin: those three should use the same twin engine the 12-hole uses. Oak,
  dummy and contrabass now declare the restored v45 12-hole twin_model.json;
  playNoteAt never falls through to PeriodicWave/wind/air/edge/chiff — a
  missing chamber key uses chamber 1. tone.json load, V_ANCHORS, additive
  lite bus, and the additive debug groups are gone. twin_support_level is
  a twin-vs-twin contract. sw oco-pwa-v58. `8a7d68d`

- **2026-09-29 (session 23 — oak/dummy/contrabass get their imagined twins back on the v45 engine)** —
  Robin: they have their own chambers and imagined values; sharing the 12-hole
  file was the wrong stand-in. Restored the guessed multi-chamber JSON from
  origin/main (oak 1/2/3, dummy 1/2, contrabass single B2–F4). Helmholtz v45
  plays those rows; it ignores `noise_mid_db` (engine-side mid-air). sw v59.

- **2026-09-29 (tone_stages re-anchor on restored v45 pair)** —
  CI `tone_stages` red: the committed 12-hole takes (C5–A5 intersection
  with the A4–A5 v45 model) vs the restored original Helmholtz measured
  C5/D5 H2/H3 and E5/G5/A5 lev past the mid-air caps (H2/H3 8, lev 8).
  Caps re-anchor to that delivery + slack (H2 18, H3 22, lev 14). Local
  working takes (research/ A4–A5) still sit well inside. Voice/JSON
  unchanged — gate follows the restored pair, not the parked mid-air
  ladder offset.

- **2026-09-30 (session 24 — board tidy: three items close on Robin's sweep, the log slims down)** —
  Board-only session; no app code touched. Robin's sweep closed three
  open items into DONE: (1) §1 held-take refits — the guessed
  per-chamber twins (dummy/contrabass/oak, dfc7199) are field-checked
  and stand; real held takes, the stein E6 re-blow and the cross-
  instrument gain re-derivation only matter once he owns the
  instruments; (2) §5 engine upgrade drawing board at 3b6e0e5 (PR #30)
  — the v45 Helmholtz pair is the shipping engine, the mid-air upgrade
  stays parked, re-openable only as one A/B deploy; (3) §7 Outset
  arrangement field check at 2dbab7a — Robin cleared the multi-track
  trio (balance, contrabass register, flat labels, loop seam, in-
  practice audibility). Also cleared by his ears: the one-take
  cross-instrument calibration recording is made, Epona's contrabass
  audible-100 is heard, and the HiFi retune + favorites stars passed
  the eyeball — but HiFi stays UNPUBLISHED until he lifts the hold.
  Hot list refreshed to the HiFi publish hold + the two standing §9
  holds; 13 log entries (all of sessions 21-22 and the early session-23
  entries) retire to DONE via log-retire --keep 4, keeping the v45-
  restore tail for continuity.

- **2026-09-30 (session 24 cont. — the usability batch is approved, boarded and is this session's handoff)** —
  Board-only so far; no app code in flight. Robin's batch, with his words
  where they matter: the small-screen pass hides the editor on phones
  (phones = play/practice, not editing), stacks controls into vertical
  rows, drops the backdrop image in portrait, keeps the whole viewport
  functional in normal mode, and leaves zen as-is ("already looks very
  good"); theme no-flash = the saved oco-theme applied pre-paint; zen
  chorus = audit + report first (fix only if truly lost — the twin path
  still has it, gated on note length + high-note fade); ko-fi goes into
  the app (78b9646 was IDEAS-only); melody duck = ON/OFF button, not a
  dial (~20% when on, tunable on his field check); song .txt round-trip
  carries ALL attributes (title/tempo/tick/swing/#track); the transport
  sync bugs (pause/unpause + tempo-change desync, first-note hurries) go
  red-first in tests/transport_schedule.py, engine change ⇒ full sweep +
  his field check. Stop-other-media: MDN's Media Session API is
  declarative only (metadata + media-key handlers for the page's own
  media) — stopping other apps is NOT possible from a web page, so that
   half drops per his rule; the announce-only half (lock-screen metadata
   + media keys) is APPROVED and boarded as the 8th item. §6 confirmed:
   no open items — it is the standing coverage list + the audit-residue
   watch note only. All eight items boarded with the decisions inlined
   (§1 ×2, §7 ×3, §9 ×3); hot
  list refreshed. Fresh context: open plans/TODO.md (AGENTS rule 1) and
  work the hot list top-down.

- **2026-09-30 (session 24 cont. — transport sync lands: the tempo line is the song's one clock)** —
  The §1 transport-sync item closes on `3eb740d`. Both planted desyncs shared
  one root: a single mutable melodyQuarter that every walker mutated.
  Pause/resume: rebaseTrackTimes collapsed all track streams' next onsets
  onto the melody's anchor, throwing away each stream's beat offset — the
  track jumped by the beat gap and stayed there. Mid-song tempo: whichever
  walker consumed its '# tempo' token first owned the shared value, so a
  track's own marker could retime the melody. The fix is a position-based
  tempo line (buildTempoLine from the melody's tokens; quarterAt looks up
  the in-force quarter at a 96th-grid position); the melody's line is the
  authoritative clock and a track's own marker rides past it. Pinned
  red-first with two new transport_schedule legs: the pause leg (pause at
  +2.8 s, resume; every post-resume track onset must land on the melody's
  same-beat onset — pre-fix the track sat −0.625 s early) and the tempo
  leg (the track block carries a deliberately wrong '# tempo 60' — pre-fix
  the track ran +1.000 s late after the marker). Also hardened
  tests/bad_chip_style.py: its probe injected before boot()'s async wireUi()
  had attached the #src input listener, so the oot leg flaked with
  "no .tok.bad chip"; it now waits for the #scale boot rendezvous first
  (5/5 clean after the fix). One sweep flake traced to that same race;
  with it fixed the full sweep is 46/46 and lint green; sw oco-pwa-v60.
  The first-note "hurries" symptom stayed unreproducible in the harness —
  first-onset equality is pinned; held for Robin's field check.

- **2026-09-30 (session 24 cont. — theme no-flash lands: the head script resolves the theme pre-paint)** —
  The §7 theme item closes on `f84b564`. The index.html head script now does
  the same param > localStorage > default resolution as app.js's
  themeFromQuery (?plain/?oot/?hifi beat the saved oco-theme; a fresh
  browser defaults to Hyrule), so a saved theme lands on <html data-theme>
  before first paint instead of flashing the default look until boot()
  applied it late. Pinned red-first by the new tests/theme_prepaint.py
  (6 resolution cases; each case aborts js/app.js — the app's only module
  entry — so boot()'s applyTheme() can never mask the head script's work:
  the old head script fails 4 of 6 cases, the new one passes all).
  Registered in practice-tests.yml beside the render-behavior pin;
  console-hygiene + render-pin + lint re-verified green; sw oco-pwa-v61.

- **2026-09-30 (session 24 cont. — instruments_load race fixed, ko-fi link lands; batch 3 of 8 down)** —
  Two board items closed this stretch. First, the ko-fi item (§9) landed
  at `46dec09`: "Buy me a coffee" (ko-fi.com/tribbin, target=_blank
  rel=noopener) sits beside the issues link in the help-screen colophon,
  and the sr_hints help-overlay leg now pins both colophon links
  (help1.links) so presence, new-tab target and noopener survive
  refactors; sw oco-pwa-v62. Second, a sweep load-flake cost a real
  diagnosis: instruments_load's boot-tail wait keyed on
  OCA_DEBUG.twinModel() !== undefined, which passes on the initial null
  (TWIN_MODEL is null both pre-install and for no-twin instruments), so
  the state read raced loadInstrument's async twin fetch under sweep
  load — fixed at `0762455` by waiting on the populated #scale library
  select, which boot only fills after loadInstrument fully resolves
  (3/3 clean standalone; sr_hints and tick_override sweep reds were
  load-dependent flakiness that passed isolated). Full sweep 47/47,
  lint green.
  Remaining usability-batch work: small-screen layout (⚙L, largest),
  melody-duck on/off (⚙S), zen-chorus audit (⚙S, report-first),
  media-session announce + media keys (⚙M, announce-only per Robin),
  song .txt round-trip (⚙M). Held: the transport first-note "hurries"
  field check (Robin's ears are the deciding pass) and the
  stop-others media key (infeasible on Web MediaSession).
