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
(refreshed 2026-09-30 late, session-28: the v45 Helmholtz pair is the
shipping voice — the mid-air upgrade stays parked in git history;
dummy/contrabass/oak ride Grok's guessed per-chamber twins until real
recordings land; the usability batch is CLOSED 2026-09-30 — all eight code
items landed (round-trip `c1ca8bc`, media-session `01adf62`, both this
session), Robin's field pass came back all good, and media-keys next/prev
stay unwired by his ruling; decisions + state in the
session-24/26/27/28 logs):

| Item | Section |
|---|---|
| **Lead/support desync fix LANDED as S1 `9ef5ca1` on fix-support-track-sync (tempo-dial move, swing-dial move and marker-straddling pause/resume all phase-lock the #track streams now; full sweep 50/50 ×2, sw oco-pwa-v94) — one hold: Robin's field check of the ≤0.35 s dial-move seam** — pickup follow-up LANDED on tempo-dial-rebase (the melody's own stale step re-scales on a live tempo-dial move, `resyncMelodyTempo`; transport_schedule leg 10 red-first, pre-fix wait 4.679 s; full sweep 50/50, lint clean, sw oco-pwa-v95); holds: the ≤0.35 s seam AND the pickup's feel at the floor (speed-up lets the stale note ring under the early onsets) | §1 |
| **USABILITY BATCH — CLOSED ✅ 2026-09-30 (approved 2026-09-30, session-24 handoff; ALL EIGHT code items landed: `3eb740d` + `f84b564` + `46dec09` + `0588d99` + `d41563a` (coffee icon + duck glyph) + `6b1a805` (duck opaque face) + `0ba4f55` (coffee line under issues) + `6a59020` (coffee cup 2.5×, middle-aligned) + song .txt round-trip `c1ca8bc` + media-session announce/keys `01adf62` (sw oco-pwa-v77); zen-chorus audit report-only; small-screen pass complete: `d77a153` → `ed31f89` + `b666034`, Robin's three phone defects pinned at `30e496d` + `2016408` + `740d637`; Robin's 2026-09-30 field pass: all good; media-keys next/prev left unwired by his ruling)** | §1/§7/§9 |
| HiFi stays UNPUBLISHED — the retune + favorites pass is accepted, but Robin holds publication for now (2026-09-30) | hold |
| Shipped-songs standardization stays HELD for Robin's later-stage pass; the permalinks corpora ride his planting as always | §9 |
| Library widening (search, reordering beyond the pin) stays parked until Robin elects it | §9 |

---

## 1. Bugs (correctness / data loss)

- [ ] **Lead/support desync on live dial moves + marker-straddling pause — three causes measured, fix approach HELD for Robin (S1 recommended)** — investigation 2026-10-05 (harness-measured, recipe inlined below; probes were /tmp/opencode/sync_probe.py, transient): root = the melody and each #track stream keep INDEPENDENT absolute-time ledgers (melodyNextTime / w.nextTime), coupled only at start/resume/wrap, while tempoSpeed() and currentSwing() are sampled LIVE at each walker's own next step — any parameter change lands on each ledger at its own next onset, and the time-gap between those onsets absorbs the change permanently. Confirmed: (a) tempo-dial 100%→50% mid-song, 8th-note melody + quarter-note 'audible 50' track, 96 bpm: track lands 0.3125 s early (= 0.5-beat gap × q × Δ(1/speed)), persistent; zero-gap control (change fired with both next onsets coincident) stays locked; (b) swing 0→100 fired exactly at an odd half-beat melody position: track lands +0.1042 s late = q/6 exactly, persistent; (c) pause/resume with an inline '# tempo 120' marker sitting between the melody's next-onset position and the track's: rebaseTrackTimes (audio.js:1563) applies ONE quarterAt(w.pos96) to the whole gap instead of integrating the tempo line — track lands 0.0625 s early = 0.5 × (q_old − q_new) exactly, persistent; no-marker control stays locked. Fix options: S1 surgical — a melody-span integration helper (piecewise over the tempo line, live speed/swing, melody token spans bound the gap) feeding rebaseTrackTimes (fixes c) AND a rebase-from-melody-ledger call wired into the two dial input handlers (ui.js:1371/1386, fixes a+b); expected ≤0.35 s one-time seam from onsets already scheduled in the old regime (unavoidable without rescheduling). S2 architecture-consistent — generalize the session-24 position-based tempo line into speedAt(pos)/swingAt(pos) lines, dial change appends an entry at the melody's next-onset position, T(P) single-valued by construction. S3 long-term — one unified walker with per-stream lanes (the support-plan pattern); parked. HELD: Robin picks the approach, then red-first — transport_schedule gains the three legs above (probe recipe: setNoteSink capture with gain split, pair each track onset to the nearest melody onset, split buckets at the perturbation ctx-time; legs (a) gate on OCA_DEBUG.melodyPos96()%96===48, (c) pauses when melodyPos96===720 against the marker at beat 8). Doc-only transients, no fix owed: onsets due inside the resume lead window clamp to now+0.02 (one-note bunch, self-heals); main-thread stall past SCHED_AHEAD (spike-watch territory); the first-note "hurries" field symptom now has a likely mechanism — a suspended-ctx start computes startWhen off the frozen clock, so after resume() the first onsets clamp to a 20 ms lead instead of 50 ms (harness never reproduces it because its ctx never suspends). Also documented, not lead/support desync: bracket supports ride melody pivots so they cannot desync, but their open-span durations divide by tempoSpeed() while their bounded holds don't (audio.js:1366/1413 vs 1415) — inconsistent under the dial. **S1 LANDED 2026-10-05 `9ef5ca1` (fix-support-track-sync)**: stepSec = the one shared per-step rule (melody walker, every track walker, span integral), melodySpanSec integrates the melody's tempo line piecewise across the rebase gap, rebaseTrackTimes(when) = when + span, and the dial setters (applyTempoPct ×2 mirrors, applySwing) call resyncTrackTimes(melodyNextTime) — the swing slider now routes through applySwing so the single #swing path resyncs too. transport_schedule legs 7–9 pinned red-first with the pre-fix failures at exactly the predicted skews; full sweep 50/50 ×2, eslint + html-validate clean; sw oco-pwa-v94. Remaining: the ≤0.35 s dial-move seam (onsets already inside the 30 ms lookahead keep their old spacing until the resync) is audible behavior — HELD FOR ROBIN'S FIELD CHECK. FOLLOW-UP LANDED (2026-10-06, branch tempo-dial-rebase): Robin's field report — dragging the tempo dial to the floor and back up waits out one whole stale step of mostly silence before the pickup — got the mirror-image fix (`resyncMelodyTempo`, the resync family aimed at the melody's OWN ledger): a live tempo-dial input re-scales the melody's pending onset (melodyNextTime) by the ratio between the speed it was paced under and the dial's new one (exact for the dial: only the speed changed), and runs BEFORE resyncTrackTimes so the #track streams re-anchor from the moved anchor. The from-speed lives in a module mirror (tempoDialSpeed) because a range input's value already holds the NEW one when its input event fires — the DOM cannot supply the from-side, which the leg caught red-first in the first cut. Pinned red-first by transport_schedule leg 10 (dial up from the 10% floor mid-stale-step: pre-fix the first post-move onset landed 4.679 s later; post-fix inside the ≤0.9 s bound, the scaled-ratio prediction ~0.47 s). Robin elected the ratio rebase with the overhanging ringing note left to decay naturally (not faded via bag fade); the slider floor stays 10% (floor raise rejected this round). HOLDS for Robin's field check: (1) still open — the ≤0.35 s dial-move seam; (2) new — the pickup's feel: a speed-up lets the stale note ring out under the early next onsets, a slow-down stretches the pending gap. Known uncovered edge, noted not owed: the swing dial's own melody remainder does not rebase (a swung step is a one-beat-class stale wait at full dial; the ratio math is not exact under swing's odd/even reweighting). Full sweep 50/50 (416 s), eslint + html-validate clean, sw oco-pwa-v95. `🟧 🟠 ⚙M`

- [ ] **Track-walker data edges: bad-chip start offset + unequal loop totals (user-typed data only)** — alignTracksToBeats (audio.js:1468) burns 0 grid beats on 'bad' chips while the live track walker burns tokenGridBeats (1 beat, the music-math fallback): a mid-song start (token click, practice→play swap) past a bad chip in a track plays that track's content k beats early, k = chips before the start point — measured: quarter-note melody, 8th-note track with 'zz' in bar 1, start at beat 2.0 anchors B4 where a from-0 run plays G4; the onsets stay on the shared clock so onset-time suites are blind to it (pitch-aware check needed). One-line fix: count bad tokens as 1 beat in the alignment walk. Separate edge: a user track whose live total ≠ the melody's total drifts per loop wrap while looping (shipped songs are pinned bar-for-bar by shipped_songs; user text is unchecked — a totals chip/warning is a feature call, not owed). No shipped song or shipped data is affected. `🟨 ⚪ ⚙S`

## 2. Robustness / error handling

## 3. Security (low today — matters if data files become user-supplied)

## 4. Performance

Nothing open — the WAV-export backlog dropped by Robin's audit 2026-09-28 (the createScriptProcessor reframe; its AudioWorklet trigger doesn't exist anywhere and debug.js stays untouched by election).

## 5. Architecture / maintenance

- [ ] **Song data split — the music moves to .txt files, songs.json keeps metadata + a file pointer** (Robin's ask, 2026-10-07): a song's body leaves songs.json and lives in its own human-editable .txt file (the web app's Save File round-trip shape, so an exported melody drops into the repo as-is); songs.json keeps group/name (authoritative even where the .txt's internal title differs)/intended etc. and points at the file; one .txt may be addressed by several entries (bass/transposed variants ride the existing derives shift on top of the fetched base text). Working notes: the loader materializes bodies from the files; sw.js adds the .txt paths to DATA_NETWORK_FIRST + the install derive; gen_song_pages, data_validator and the twin_derive fixtures follow the bodies to the files. DECIDED (Robin's addition 2026-10-07): update propagation is REQUIRED — when he updates songs, players must receive the fresh bodies, never a stale cache (the .txt files join the network-first serving regimen, and the phone-resume freshness check extends to the bodies: a .txt-only edit must be seen by a resumed app even though songs.json's own text does not change). DECIDED (Robin's answered batch, 2026-10-07 late): ① BOOT PREFETCH — every unique .txt fetched in parallel during boot (library hidden filter + ⚠ badges keep working); ③ MUSIC ATTRS MOVE TO THE .TXT — only name/group/intended (plus derives/file) stay JSON; tempo/tick/swing/meter live in the .txt headers and become text-first (loader precedence flips: the file's own header wins); ④ directory songs/ beside songs.json, songs/<id>.txt. `🟧 🔴 ⚙M`

## 6. Tests & CI

Currently covered (don't lose this): practice acceptance (4 cases strict+closed-loop), practice dip gate (hold-through blocked, silence/50%-notch dips pass, 75% duck shut, legato free), practice seat across view rebuilds + zen-entry stopMelody + overlay zen-only seats, console-hygiene boot scan (4 boots; allowlist = manifest-declared tone misses), support-bracket battery incl. bit-identical melody-vs-support equivalence + Zen timing/gating, instrument load/tone-model install per manifest (incl. svgWhen id/title paths + boot diagnostics in per-leg fresh contexts), render pin (chips/grid/scroll-band/highlight/focus-restore + typed-render debounce contract), svg clone coordinates, debug panel build-on-open contract, transport scheduler arithmetic/cut-bus/lite + the lead/support phase-lock battery (pause/resume, inline tempo change, live tempo-dial move, live swing move, marker-straddling rebase), practice history, template safety, theme toggle, offline SW boot+swap, ac worker parity, swing grid, sr hints, spike watch (the tick hunt), the session-14 batch (wake lock lifecycle, tick-override semantics, asset-version token equality, twin-derivation byte-identity, transposer skill, practice dials), the session-15 additions (SEO shell shape + zero-per-stub JSON-LD, zen note-bar glide five-legger, suite-server teardown hardening, board-tool empty-run linting), and the session-16/16-cont. additions (track acceptance battery incl. mix ratios, hifi retune, library favorites star + readability, tests/midi_track_audit = the pure-python source-measure audit with a displaced-downbeat tripwire over tools/midi_track_audit.py), and the session-17-cont. additions (tests/tone_stages = the DEFAULT stage verification after synth-code or note-value changes — rebuilt session 18 for the twin voice: fit-row regression caps + the decay-release gate measured on the ADOPTED handoff baseline after Robin's field ruling (onset/hold stage bands stay measured-for-eyes in the artifact, never gated — their caps could not survive wobble-window luck without flapping); instruments_load pins the twin install/uninstall shapes and waits for both model round-trips; data_validator checks the twin schema; CI installs scipy+soundfile so the fitter analysis runs there;''. **Sweep policy (Robin, 2026-09-26): the full run_all sweep runs only for sound-engine touches; data/song changes run the directly-affected suites (see AGENTS.md §12)** — full sweep 47/47 at the stage-verification commit (including tone_stages) is the last under the policy (including the new audit suite). CI = push/PR/manual, explicitly not a deploy gate. (.github/workflows/practice-tests.yml — console-hygiene + 46 suite steps + eslint + html-validate + board verify (46 after the 2026-09-28 audit removal; instrument_switch_race's step gone); local run-all counts 46 suites (47 before the removal); 42 green 2026-09-25 — see DONE) NOTE: practice_accepts flaked ONE strict case under full-sweep load 2026-09-23, green twice standalone afterward and in the diag run — watch it, the arbiter hardening already took one such race; support_accepts flaked the same class 2026-09-24 (fixed wall-clock read window vs audio-clock lag under sweep CPU contention) and got the class cure: the read is now a real rendezvous with wall-fire stamps + ctx snapshots `335c4b4`). **Third member 2026-09-25 (CLI run `36110497803`, job 107992645371): practice_dip's leg A stalled the full 15 s timeout at maxIdx 0** — same SHA the local sweep had green; a DIFFERENT injury inside the same family: the suite's rendezvous (OCA_PRACTICE+NOTES) unlocks INSIDE loadInstrument (the stretch between installFingerings and boot's tail), where fillLibrary/loadLibraryItem(home) → practiceInvalidate is still owed — a session started mid-boot died when the tail landed; the stall reproduces at will with CDP network latency, cured by the rule-13 real rendezvous: the #scale options guard (filled only by the tail; a rAF poll never resolves mid-synchronous-block) plus a state card (started/st/ix/frames) on every driver resolve so a future stall names itself. The same tail guard rode into every suite that starts practice or needs typed editor text to survive boot (practice_accepts_melody, practice_zen_return, practice_history, keyboard_widgets, render_pin); library_hardening already waited a stronger post-tail signal (the Scales OPTGROUP), playback-only suites are immune (practiceInvalidate stops practice, never play; the instrument-switch race suite was REMOVED 2026-09-28 — its `loadText` throttle went inert at the ESM migration because the app's loadings resolve the module-scoped binding, so it passed without reproducing its race; the app's instLoadGen guard carries the contract and a live re-test would need a route-doctored `loadText` seam). Full sweep 31/31 green after the cure. Session-28 addition: tests/song_txt_roundtrip (the .txt round-trip: Save File writes title/tempo/swing + the '# tick off' opt-out + the #track blocks, Load File / paste-into-#src restores them byte-identical, tick applies as a per-song session override that never writes the preference, legacy JSON 'tick' field leg — five legs) plus the parse_edges tick-header legs (tickFromText, titleFromText skipping, withPlayHeaders preserve/replace); and tests/media_session (the Media Session announce: metadata title 'Ocarina Practice — <song>' at boot and on song switch, playbackState none/playing/paused/none at each transport edge, hardware play/pause/stop handlers driving the real transport, next/prev pinned unwired).

> **Test-audit residue (2026-09-28 — consult before touching these):** kept-with-sightings from the full-suite audit — transport_schedule's reference walk re-encodes scheduleMelody's duration constants (dual-maintenance; the `intoSlide` regime is unmodelled and can drift silently); offline_pwa rewrites the real songs.json on disk (restored in `finally`; a hard kill leaves the tree mutated for alphabetically later suites) behind the set's only justified fixed sleep (1.1 s, the whole-second If-Modified-Since lesson); readability's per-state minimum counts, hifi_retune's exact hexes/10px grid and zen_notebar's 160 ms bound are VALUE-PINS that fire on Robin's legitimate retunes (his field passes on the HiFi batch, favorites, and the glide bound are the standing held items); transpose_skill SKIPs (exit 0, loud note) when node is absent — a green-with-asterisk locally on Linux partitions, real in CI; twin_support_level hand-builds `_trackBag`'s shape (a drift there excites a bag the app no longer builds); the derives-record contract is deliberately owned twice (data_validator battery + twin_derive census) as an independent cross-check, as is the per-stub canonical count (gen_pages presence + seo_shell count); gen_pages' `expected_stub_keys`/`category_of` mirror the generator's own filter (both-wrong-together window, backstopped by the boot legs); shipped_songs' bar-grid leg is sum-relative (onset-rotation blind — the known gap midi_track_audit covers on MIDI-bearing machines, with sequential legs that drop the tripwire when an earlier red replaces `raw_rows`); the practice feed/poll arbiter block is copy-pasted across four practice suites (same flake cure re-landed per copy).

## 7. Accessibility & UX

## 8. Housekeeping

Nothing open — completed housekeeping is archived in `plans/DONE.md` §8.

## 9. Functional ideas (features)

- [ ] **Standardize shipped songs to the `skills/ocarina-melodies` conventions** (barline at wrap start, named sections where players want headers) — HELD for Robin's later-stage pass; verify/shipped_songs are the gates; no playback changes expected. `🟢 ⚪ ⚙M`

- [ ] **Library search / pinning widening** — favorites pinning SHIPPED 2026-09-26 `390c431` (star + first persisted Favorites group); the widening (search box, reordering beyond the pin, grouping options) stays parked until Robin elects it. `🟢 ⚪ ⚙S`

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

- **2026-09-30 (session 24 cont. — zen-chorus audit closes report-only: the twin engine kept the chorus)** —
  The §1 audit item closed with no code change. The zen stereo chorus
  survived the twin-engine handoff in its gating: twChorus =
  vibratoEnabled && dur > vibDelay + 0.1 (js/audio.js:1033) — the clean
  cavity core hard LEFT, the vibrato twin hard RIGHT at ±zenPan
  (audio.js:1050–1073), bit-for-bit the legacy additive chorus gate that
  8a7d68d stripped (old lines 872–874). Zen defaults intact (vibDepth
  0.0035, vibHighFade 0.4, zenPan 0.9, vibDelay 0.35; dev-panel sliders
  intact), vibratoEnabled owned by the zen transitions (exitZen → false;
  toggleZen/sync → isFocusMode()). The lite twin voice is chorus-free,
  but the legacy lite branch skipped the vibrato layers too — a
  consistent reduction, not a loss. The item's "fix only if truly lost"
  clause does not trigger; zen+lite stays chorus-free by design.

- **2026-09-30 (session 24 cont. — context-meter note: compaction resets the budget, don't wrap on the stale number)** —
  A provider-side compaction reset the context (~28K fresh); the stale
  ~225K figure carried from the compacted handoff had already triggered
  one early wrap — the .opencode/context-usage.json zone is only truth
  once the session has its own work behind it, and a post-compaction
  reading is a fresh start, not a continuation.

- **2026-09-30 (session 24 cont. — melody-duck on/off lands; the suite's boot-tail race gets its root cause)** —
  The §7 duck item closed at `0588d99`. Corner buttons on the mirror and
  the focus play controls toggle the MAIN melody voice to the 0.2 duck
  level (MELODY_DUCK_LEVEL in audio.js, riding voiceGain in
  playNoteAt; #track streams and supports keep full volume so the
  player's ocarina leads), session-only, both mirrors in sync
  (aria-pressed + .on, pinned by the keyboard_widgets transport leg,
  now 5 controls). New track_accepts note-sink mix leg pins duck-off
  baseline 1.0, duck-on melody 0.2 / track 1.0, and the UI state across
  both transports. The new leg exposed a real suite-side race: the
  OCA_PRACTICE/NOTES boot rendezvous fires at module-eval time, but
  boot()'s async tail (loadInstrument -> loadLibraryItem) lands after,
  and loadLibraryItem's opening stopMelody() kills a probe's fresh
  playback — the second scheduled note never reached the sink (proven
  by a clearTimeout stack capture: stopMelody <- loadLibraryItem <-
  boot; no statechange, no pageerror, the context was healthy). All
  five track_accepts page setups now wait on the settled #scale
  rendezvous (the instruments_load convention) before playing.
  Verified: track_accepts x2, keyboard_widgets, asset_versions,
  console_hygiene, offline_pwa green; eslint + html-validate clean.
  sw oco-pwa-v63, css-v4. For future sessions: the same latent race
  exists in every suite that starts audio right after the module
  rendezvous (only track_accepts is hardened so far); the duck
  button's look and the 0.2 level stay held for Robin's field check.

- **2026-09-30 (session 24 cont. — small-screen first pass in, keyboard approach rejected; two IDEAS items approved; handoff prepped)** —
  `d77a153` landed the small-screen first pass on usability1: narrow
  viewports hide the editor face (expand/clear, both save/load pairs,
  textarea + legend — the Song Library picker stays, Robin: "keep the song
  library"), the playback head stacks into one centered row per control
  group, portrait drops the Hyrule backdrop, and the 42-column keyboard
  became a 32px-column scroll strip that glides to the sounding key
  (ui.js scrollKbToActive); six-leg tests/phone_layout.py in CI (phone
  face, row stack + no h-overflow, portrait backdrop, kb width both
  viewports, active-key follow, desktop regression); phone_layout/
  asset_versions/console_hygiene/render_pin/keyboard_widgets/
  reduced_motion/offline_pwa green, eslint + html-validate clean; sw
  oco-pwa-v64, css-v5. Robin then corrected the keyboard spec: the board
  scrolling during play is ANNOYING — no auto-scroll; instead the
  transparent (out-of-instrument, dimmed) keys are hidden on small
  portrait screens so the board shows only the playable keys, static.
  Also: the token strip (#tokens, "the other dropdown showing tokens") is
  hidden on small portrait too (not ergonomic there), and the three
  tab-tools rows (Enlarge small holes, Grid|Scroll|Single,
  share|print|download) each center. The §7 item stays OPEN with the
  corrected spec (board note on the item); phone_layout legs 4-5 pin the
  rejected approach and must be re-pinned. Two IDEAS entries are now
  approved and boarded in §7: the small coffee icon after "Buy me a
  coffee" (planted 7a4da56) and the duck-toggle glyph swap to a loud
  (three waves) / soft (one wave) speaker with position/colour
  fine-tuning (planted b4acd7d). Batch is now 5 of 10 — remaining:
  small-screen remainder, song .txt round-trip, media-session announce +
  media keys, coffee icon, duck speaker icon. usability1 is ahead of
  origin (push stays Robin's). Fresh context: open plans/TODO.md (AGENTS
  rule 1) and work the hot list top-down; read IDEAS.txt fresh when
  picking up the two icon items.

- **2026-09-30 (session 25 — the offline_pwa CI red was a boot-race flake; the small-screen board lands static, then uniform)** —
  CI 36707821958 red on `offline_pwa` ("the offline song must render its
  chart") with a green re-run on the same code: both boot-time legs read
  the sheet/strip right after WAIT's window.NOTES install, which
  loadInstrument completes ahead of boot's async tail (the library load,
  then the first sheet render behind the ocarina-template fetch) — a slow
  runner's probe can land in that gap. `a55b270` makes the legs wait on
  the rendered DOM itself (#tokens .tok, #sheet .card). Robin's phone
  field check on the second-pass board (ed31f89: static playable-only
  keys, no auto-scroll, #tokens hidden, tab-tools centered) caught one
  real defect — sparse octaves stretched their surviving keys, because
  each .oct kept its flex:1 share past the trim; cured at b666034 by
  dissolving .oct to display:contents so the surviving cells flex evenly,
  with the octave-group radii flattened so the board reads as one strip.
  phone_layout legs 4-5 re-pinned (contents dissolve, desktop grouped-flex
  regression, #tokens hidden with the playback block expanded). Battery
  green: phone_layout, keyboard_widgets, render_pin, console_hygiene,
  asset_versions, offline_pwa, zen_notebar, readability, theme_prepaint,
  svg_cache, reduced_motion; eslint + html-validate clean. sw
  oco-pwa-v66, css-v7. The small-screen item stays open on Robin's field
  check of the uniform board.

- **2026-09-30 (session 26 — the phone field-check trio lands pinned: titles lead their blocks, the dead chevron goes, the wrapped header keeps its edge)** —
  Picked up plans/HANDOFF.md (untracked, Robin's landing brief). Robin's phone
  pass on the b666034 board (sw oco-pwa-v66 / css-v7) caught three
  small-screen defects; all three are fixed on usability1 and pinned in
  phone_layout (now 8 legs), each commit carrying its own sw/css bump.
  (1) Section titles: "Playback Control" sat 61px below its block top while
  Song Library and Piano sat at 9px — the stacked playback head led with its
  wrapped control rows (head-left before t-wrap); a fresh-context headless
  probe measured the repro red pre-fix (playback 61px, tools flush left at
  x=20), then under 760px the t-wrap row takes the top slot (head-left order
  1, tempo-lab order 2) so every .head-label sits at the same natural
  distance from its .block top; new leg 7 pins the per-block offsets within
  2px, collapsed AND expanded. The SONG-LIBRARY-vs-PIANO distance itself
  measured equal at 9px/9px in the current build in both states — "big
  mode" is ambiguous (expanded block? Enlarge-small-holes toggle? wider
  viewport?) and did not reproduce; held for Robin's field-check words.
  (2) The playback collapse chevron is vestigial on a phone: the block's
  only content below the head is #tokens, already display:none there, so
  the toggle did nothing — #playback .collapse-btn is now display:none
  under 760px; leg 5 expands the block through classList instead of the
  click and pins chevron phone-none against desktop-visible (leg 6).
  (3) The theme/? .head-tools wrapped flush left on the phone header's
  third line; .head-tools gets margin-left:auto under 760px so the wrapped
  line keeps the header's content-edge right alignment; leg 8 pins the wrap
  order (h1 line, picker line, tools line below) + the right edge, leg 6
  guards the desktop edge. Battery: phone_layout (8 legs), asset_versions,
  console_hygiene, keyboard_widgets green; eslint + html-validate clean.
  sw oco-pwa-v69, css-v10; commits 30e496d, 2016408, 740d637. The §7
  small-screen item stays open — held for Robin's field check of the
  uniform board + these three before it closes.

- **2026-09-30 (session 27 — fresh-context continuation: opaque duck badge face, coffee line owns its own line)** —
  Picked up plans/TODO.md (rule 1); hot list had the usability batch at 7 of
  10 code-landed with Robin's field checks open. Two small visual fixes from
  Robin's fresh remarks, each its own commit with its own sw/css bump.
  (1) `6b1a805` — the duck corner badge now wears a dedicated OPAQUE face
  (Robin: the play button's rim arc and running green were shining through
  its transparent fill — "if 'play' becomes light-green (oot), duck also
  becomes light-green"). button.t-btn.duck gets a theme-opaque --duck-badge
  tone: plain #efe4d4, OoT #0a3a0a, hifi #0f0602 (its `button.t-btn.duck`
  selector ties the hifi .t-btn family rule on specificity and wins by
  source order); the zen mirror wears its already-opaque zen button face.
  Both keep that face while the host play button runs; the engaged orange
  state is untouched. Scope: the two corner ducks only — Robin's "maybe
  every such button" read as the narrower one; the other round transport
  buttons stay transparent, held for his call. keyboard_widgets pins the
  opaque fill, face stability across the running state, and no
  running-green bleed on both mirrors. (2) `0ba4f55` — the help-card coffee
  line owns its own line below the issues link (Robin: "the 'coffee' should
  wrap below issues"): .coffee-unit promoted to display:block (nowrap
  kept), the · separator dropped, trailing period moved inside the span;
  sr_hints pins display:block plus the coffee line's top below the issues
  link's bottom. Battery green after each commit: keyboard_widgets,
  sr_hints, track_accepts, console_hygiene, asset_versions, phone_layout,
  readability; eslint + html-validate clean. sw oco-pwa-v73/css-v14 then
  oco-pwa-v74/css-v15. Batch state: song .txt round-trip and
  media-session announce + media keys remain as the last two §9 code
  items; Robin's field checks (uniform board, duck colour/position, coffee
  look) stay held.

- **2026-09-30 (session 27 cont. — coffee cup enlarged 2.5x + middle-aligned, handoff refreshed for a fresh context)** —
  Fresh context picked up the board per rule 1; branch tip was 0ba4f55 with
  Robin's two remarks in flight. His new steer: the help card's coffee cup
  should be 2.5x the line text and vertically middle-aligned (at 1em riding
  the baseline it read as an afterthought). `6a59020`: .help-coffee is now
  2.5em wide/tall with vertical-align:middle (3px margin-left kept, fill
  stays currentColor); sr_hints' coffee leg now measures the icon at 2.5x
  the colophon font size and asserts its centre within 3px of the coffee
  text's centre. Verified: sr_hints, console_hygiene, asset_versions green;
  eslint + html-validate clean. sw oco-pwa-v75, css-v16. Robin also asked
  the next fresh context to pick up the remaining branch work — the hot
  list row now names the two open §9 items in order (song .txt round-trip,
  then media-session announce + media keys) and the standing field checks.
  usability1 is ahead of origin; pushing stays Robin's operation.

- **2026-09-30 (session 28 — fresh-context continuation: song .txt round-trip lands; the tick line is the one header attribute the grammar was missing)** —
  Picked up plans/TODO.md per rule 1; the hot list named the two remaining
  §9 code items, .txt round-trip first. The .txt already carried
  title/tempo/swing + the #track blocks through withPlayHeaders + the
  diskSave/diskFile pair; the gap was the metronome. Robin's semantics for
  the tick attribute (mid-session steer): ticking is the DEFAULT, so only
  "# tick off" is a real declaration — a song whose support tracks make the
  metronome pointless opts out; "# tick on" is never written by the export
  and never enforced by a load/paste. Landed `c1ca8bc` on txt-roundtrip:
  parse.js gains isTickComment + tickFromText (false only for a "# tick off"
  line, null otherwise — on and absent both leave the session state alone),
  titleFromText/withPlayHeaders treat the tick line as a first-class header
  (never read as the title; preserved through header-only rewrites, replaced
  by an explicit state); diskSave writes "# tick off" when the metronome is
  off and never an on-line; render() re-applies the text's declaration on
  every settle so a paste into #src works, with applySongTick early-returning
  when the state already matches so the 200 ms debounce path cannot thrash;
  the legacy JSON "tick" field applies on disk load. Pins: new
  tests/song_txt_roundtrip.py (5 legs: export shape with/without the opt-out,
  byte-identical load restoring title/dials/tick/#track tokens, paste-into-
  #src semantics including the never-enforced on-line, legacy JSON leg)
  registered in practice-tests.yml, plus parse_edges tick-header legs.
  Battery green: song_txt_roundtrip, parse_edges, tick_override,
  console_hygiene, asset_versions; eslint + html-validate clean. sw
  oco-pwa-v76. Next on the hot list: §9 media-session announce + media keys
  (the last usability-batch code item); Robin's field checks (uniform board,
  duck colour/position, coffee look) stay held.

- **2026-09-30 (session 28 cont. — media-session announce + media keys land; the usability batch is code-complete)** —
  Second unit of the session, on txt-roundtrip at `01adf62`. The transport
  now declares itself to the OS: mediaSessionState (ui.js) is the single
  playbackState writer, called at each audio.js state edge (stop -> none,
  play/resume -> playing, pause -> paused); syncMediaMetadata names the
  session "Ocarina Practice — <song>" from the #title on every render;
  wireUi maps the hardware play/pause/stop keys onto
  togglePlayPause/pauseMelody/stopMelody. Everything gates on
  ("mediaSession" in navigator) and no-ops silently where unsupported.
  next/prev stay unwired: their stepping target (library-order stepping vs.
  nothing) is a UX call — held for Robin, noted on the §9 item. Pinned by
  new tests/media_session.py (4 legs: boot announce, re-announce on song
  switch, playbackState at every transport edge, headset-style invocation
  of the recorded handlers driving the real transport, next/prev pinned
  unwired), registered in practice-tests.yml. Battery green: media_session,
  console_hygiene, asset_versions, render_pin, keyboard_widgets,
  song_txt_roundtrip; eslint + html-validate clean. sw oco-pwa-v77. The
  usability batch is now fully code-landed; what remains is Robin's field
  checks (uniform board, duck colour/position, coffee look) and the
  next/prev decision. The txt-roundtrip branch is ahead of origin — pushing
  stays Robin's operation.

- **2026-09-30 (session 28 cont. — Robin's end-of-session rulings close the usability batch)** —
  Robin answered the batched questions: (1) media-keys next/prev stay
  UNWIRED — the §9 media-session item closes at `01adf62` as scoped
  (announce + hardware play/pause/stop; pinned by tests/media_session.py);
  (2) the three held field checks pass on his device — the small-screen
  layout pass (`740d637`), the coffee icon (`6a59020`) and the duck icon
  (`6b1a805`) all close with field-pass notes; the hot-list usability-batch
  row is now CLOSED. Pushing/merging the txt-roundtrip branch is explicitly
  Robin's own operation — left to him, branch stays ahead of origin. What
  remains open in §9: shipped-songs standardization (held, his later pass)
  and the library widening (parked until he elects it).

- **2026-10-01 (session 29 — in-card practice-history line re-seated below the tuner bars)** —
  Robin's report: in zen mode the practice-history text appeared BESIDE the tuner,
  cutting the tuner area in half. Root cause: `.prac-panel.in-card` is a two-column
  grid (bars in column 1, empty auto column 2) and `.prac-history` carried no grid
  placement, so it auto-flowed into column 2 and rendered in-line with the
  scale/track bars. Fix: an explicit `.prac-panel.in-card .prac-history` seat on
  its own row below both bars (like the main-screen overlay's line), css/app.css;
  sw oco-pwa-v78, css-v17. Pinned red-first with new leg 6 in
  tests/practice_zen_return.py: the history rect must sit below the track's
  bottom edge and stay within the bars' horizontal span. Battery green:
  practice_zen_return (6 legs), practice_history, readability, console_hygiene,
  asset_versions; eslint + html-validate clean.

- **2026-10-02 (Ocarina of Time opening song added on alto)** —
  Added `ocarina-of-time-opening` to songs.json under Zelda on Alto at tempo
  72, with Robin's melody and contrabass audible-50 track verbatim; the title
  and initial tempo use library metadata. sw oco-pwa-v79. Verification:
  shipped_songs (including bar-for-bar track alignment), gen_pages,
  data_validator, and eslint + html-validate passed. Changes left uncommitted.

- **2026-10-02 (Ocarina of Time opening bass version added)** —
  Added `ocarina-of-time-opening-bass` under Zelda on Bass at tempo 72,
  preserving the supplied opening, lower bridge, and contrabass audible-50
  track. Prefixed the bass title with `#` at Robin's request. sw oco-pwa-v80.
  Verification: bass-triple chart fit, shipped_songs track alignment,
  gen_pages, data_validator, asset_versions, eslint and html-validate passed.
  Changes left uncommitted.

- **2026-10-02 (scale-follows-instrument — the open auto-generated scale now follows instrument switches)** —
  Robin's report: with a C-major/Chromatic tool open, switching the
  instrument left the old chart's sheet open. Root cause: switchInstrument's
  wet "stay" path — refreshGeneratedScales re-synthesizes the entry body for
  the NEW chart under the SAME id during install, so autoSongInRange saw the
  regenerated body already fitting and never ran loadLibraryItem; #src kept
  the previous ocarina's notes. Fix (js/app.js switchInstrument): when the
  open entry carries the generated flag, the switch reloads it even on the
  same id (stop-path motion, as with a family jump) — the sheet follows the
  installed chart and the dropdown keeps the tool selected. Pinned red-first
  by the new instruments_load wet-switch leg f (?song=major boot, switch to
  stein-double-alto-c: BUILTIN body regenerated AND #src carrying it,
   selection held, transport never started); sw oco-pwa-v88 → v89. Battery
  green: instruments_load (leg f red → green), asset_versions,
  console_hygiene; eslint + html-validate clean.

- **2026-10-02 (audio-state-boot-race — the audio_state suite's boot-tail race hardened)** —
  audio_state.py flaked in CI: the mid-playback suspension found the transport
  already dead (playing=False paused=False, both asserts). Root cause is the
  suite side, not the app: its BOOT_WAIT rendezvous passes at module-eval time,
  ahead of boot()'s async tail (loadInstrument -> fillLibrary ->
  loadLibraryItem), and that tail's opening stopMelody() (library.js) kills the
  probe's fresh playback whenever the fetch lands mid-setup — the same latent
  race class the session-24 log named for every suite that starts audio right
  after the module rendezvous (only track_accepts had been hardened). The suite
  now waits on the settled #scale library tail (#scale.value ===
  'song-of-storms') before the probe plays, per the instruments_load
  convention; 10/10 local runs green after the fix (the flake reproduced ~1/8
  before). Test-only change — no app code, no sw VERSION bump.

- **2026-10-03 (6-hole STL Plastic twin lands from Robin's ladder)** —
  Robin added research/recording/6-hole-ladder.wav (gitignored, 22 s) and
  reported the instrument is an STL Plastic 6-hole. fit_ladder.py cut 10
  held white-key takes (C5 D5 E5 F5 G5 A5 B5 C6 D6 E6) and wrote 17 rows to
  instruments/six-hole-c/twin_model.json; the six chromatic half-vent
  notes log-f interpolate between their white anchors, the same convention
  as the 12-hole fit, and the guessed placeholder (with its "guessed"
  flags) retires. Measured rows clamp to the -46 dB floor ceiling on every
  note (the plastic 6-hole residual floor sits ~8 dB above the 12-hole's)
  and 7 of the 10 measured air peaks (E5 and G5-E6, ~1.06-1.1x f0) land in
  the note-skirt region, so their bands ride the fitter's 1.4x-f0
  low-edge clamp — the shell class next-session.md's noise-shape work
  targets. instruments.json
  version "(dummy)" -> "STL Plastic"; the instruments/README census moves
  the six-hole into the fitted-ladder group. HELD FOR ROBIN'S FIELD CHECK
  on the audible voice. Suites: data_validator, tone_stages,
  instruments_load (all 6 instruments boot; six-hole twin installs),
  eslint + html-validate clean. No sw bump: twin + manifest are
  DATA_NETWORK_FIRST data (ed7b197 precedent). Housekeeping: removed the
  stale local __pycache__ shells under skills/tone-analysis and
  skills/ocarina-twin/ocarina_twin that tripped tone_stages' exists()
  guards on this machine.

- **2026-10-03 (six-hole chart rows follow the new template)** —
  The new six-hole template names the fingers on the elements: index holes
  sit nearer the mouthpiece, middle-finger holes farther from it, same way
  up as the OcarinaSongbook glyph (mouthpiece at the bottom). The chart had
  those rows swapped, so every note that distinguishes index from middle
  painted the other hole, and C#/D# half-vented the wrong right-hand hole.
  fingerings.json now covers the songbook holes: C# half-vents the right
  middle, D# half-vents the right index, and the diagram block records
  top row = middle fingers. svg_id notes follow the renamed elements
  (L-index, L-middle, R1-middle, thumb-left, thumb-right). The half-disc
  stays the painter's left half under the template's existing -130 degree
  hole rotation, which fills the right side of the hole; the songbook glyph
  fills the left side. Held for Robin if he wants that side flipped.
  data_validator green. No sw bump (fingerings and the template are
  DATA_NETWORK_FIRST).

- **2026-10-03 (Minuet of Forest added)** —
  Added `minuet-of-forest` to songs.json under Zelda on Alto at tempo 100.
  The body is the supplied melody plus `#track bass audible 50` and
  `#track contrabass audible 50`; title and tempo stay in the library
  metadata. Eight bars of 3/4 on every stream. No sw bump: songs.json is
  DATA_NETWORK_FIRST. Verification: data_validator, shipped_songs (the new
  song aligns bar-for-bar), gen_pages (11 stubs, the minuet landing boots
  with zero out-of-range marks), and a headless load of the library entry
  (headers prepended, triplet glyph, no bad chips, bass staccato and
  contrabass pitches present in the parsed tracks).

- **2026-10-03 (Minuet of Forest meter and bass arrangement)** —
  Both minuet entries store `"meter": "3/4"` on the record. The body stays
  notation only; load writes `# meter 3/4` on the line under `# tempo`, and
  Save File keeps a leading meter line that is already in the text. Meter
  is a label — durations still decide the bar. `minuet-of-forest-bass` is
  the supplied arrangement under Zelda on Bass: the repeated phrase is an
  octave down (D4/D5/B4, A4/B4/A4) and the tracks are unchanged. The -bass
  key rides the alto landing page, the same grace-period rule as the other
  family bass copies. No sw bump (js and songs.json are DATA_NETWORK_FIRST).
  Verification: data_validator (meter must be N/N), parse_edges,
  shipped_songs, song_txt_roundtrip, gen_pages, eslint on the two scripts,
  and a headless load of both songs (header order, one high phrase plus one
  low phrase, bass listed under Zelda on Bass on the triple).

- **2026-10-03 (tick_override waits for the library tail)** —
  tests/tick_override.py L1 failed when it read #tickMel as soon as
  BUILTIN['song-of-time'].tick was false. initBuiltin publishes that
  field before boot's await loadInstrument, and loadLibraryItem applies
  the override only at the tail, so the read saw the HTML default
  (checked). Each leg now waits until #scale holds the landed song, and
  each leg gets its own browser context so an earlier click cannot
  answer a later visit. Five local runs green. Test-only; no sw bump.

- **2026-10-05 (lead/support desync investigation — three causes confirmed by measurement, held for Robin's approach pick)** —
  Robin asked for all possible causes + solutions of lead/support out-of-sync (pause/play,
  tempo, swing). Root: melody and each #track stream keep independent absolute-time
  ledgers (melodyNextTime / w.nextTime), coupled only at start/resume/loop-wrap, while
  tempoSpeed() and currentSwing() are sampled live at each walker's own next step. Harness
  probes (8th-note melody + quarter-note 'audible 50' track, 96 bpm, setNoteSink gain split,
  track onsets paired to nearest melody onset): (a) tempo dial 100%→50% fired at an odd
  half-beat — track permanently 0.3125 s early = 0.5-beat gap × q × Δ(1/speed); fired at a
  zero-gap beat start — locked (control). (b) swing 0→100 fired at an odd half-beat — track
  permanently +0.1042 s late = q/6 exactly. (c) pause/resume with '# tempo 120' at beat 8
  and pause while the melody's next onset sits at 7.5 — rebaseTrackTimes applies one
  quarterAt(w.pos96) to the whole 7.5→8.0 gap, so the track lands 0.0625 s early =
  0.5 × (0.625−0.500) exactly; no-marker pause — locked (control). Data edges (user text
  only): alignTracksToBeats burns 0 grid on bad chips, the live walker burns 1 — a
  mid-song start past a chip plays the track's content k beats early (measured B4 where a
  from-0 run plays G4; onsets stay clock-locked, onset-time suites are blind); a user
  track whose total ≠ the melody's drifts per loop wrap (shipped songs pinned by
  shipped_songs). Transients (self-healing, no fix owed): resume clamps onsets due inside
  the 50 ms lead window to now+0.02 (one-note bunch); dial-change seam ≤ 0.35 s from
  onsets already scheduled in the old regime; main-thread stall past SCHED_AHEAD
  (spike-watch territory). The held first-note "hurries" now has a likely mechanism: a
  suspended-ctx start computes startWhen off the frozen clock, so first onsets clamp to a
  20 ms lead (harness ctx never suspends — why it stayed unreproducible). Ruled out:
  bracket supports (anchored to melody pivots; only their duration semantics are
  inconsistent under the dial — open spans ÷ tempoSpeed, bounded holds not), the tick
  (melody ledger), duck (gain only), song load / text edit / instrument switch (stop +
  restart). Fix options: S1 surgical = tempo-line span integration helper feeding
  rebaseTrackTimes + rebase-from-melody-ledger on the two dial input handlers (ui.js
  1371/1386), ~⚙M, red-first via the three probe legs; S2 = position-based
  speedAt(pos)/swingAt(pos) lines generalizing the session-24 tempo line; S3 = one
  unified walker with lanes, parked. Boarded in §1 ×2; hot list refreshed. No app code
  touched; branch fix-support-track-sync at main's tip, ready for the fix.

- **2026-10-05 (S1 lands: dial moves and marker-straddling pauses re-anchor every #track ledger from the melody's clock)** —
  Robin elected S1 (surgical rebase). Red-first: transport_schedule gained legs 7–9 —
  the live tempo-dial lock, the live swing lock and the marker-straddling-resume lock,
  each pairing every track onset with the nearest melody onset and asserting the delta
  before AND after the perturbation (the pre-bucket is the harness's own control). The
  drivers fire the dial move only when the melody's NEXT unscheduled onset sits on an
  odd half-beat (melodyPos96 % 96 === 48), the phase where the two streams' next onsets
  are a half-beat apart — the worst case the old code failed at. Pre-fix failures
  measured exactly the predicted skews (312 ms tempo dial, 104 ms swing = q/6, 62 ms
  rebase = 0.5 × (0.625 − 0.500)); the zero-gap-phase dial control (change on a beat
  start) stays green, showing the desync is gap-dependent. The fix: stepSec is now the
  ONE shared per-step rule (melody walker, every track walker, span integral) so a live
  parameter read lands identically wherever it is taken; melodySpanSec(a96, b96) walks
  the melody's token spans and integrates quarterAt/stepSec piecewise — a '# tempo'
  marker inside the gap is honored; rebaseTrackTimes(when) = when + span; and
  resyncTrackTimes() = rebaseTrackTimes(melodyNextTime) is called from applyTempoPct
  (both mirrors) and applySwing — the swing slider now routes through applySwing, so
  the dial set (library loads, share links, song loads) all funnel through the two
  setters and every live dial move re-derives all track ledgers from the melody's
  anchor. Positions clamp to the melody's grid; unequal totals stay a data-edge (§1
  item 2 unchanged). A sweep red on support_accepts_brackets turned out to be a
  pre-existing suite-side race (reproduces with the fix stashed): the plain-gating
  leg's driver played 150 ms after a debounced render, so the boot tail's
  loadLibraryItem could overwrite #src with Song of Storms mid-boot and the driver
  then played the wrong song — the E3 it "fired outside Zen" was the boot song's
  audible contrabass TRACK note, not a bracket firing (audible zones play in plain
  view by design). Both battery drivers now arm on the settled #scale library tail
  and the plain leg additionally waits for the typed case's own title ("# plain probe"
  prepended to ZEN_CASES[0] — comment lines parse to nothing); 4/4 green after.
  Full sweep 50/50 ×2 (one transient reduced_motion flake re-run clean; no CSS
  touched), eslint + html-validate clean; sw oco-pwa-v94. Board: §1 item noted, hot
  list + §6 coverage updated. Driving/waiting on Robin was his S1 pick; remaining hold
  is his field check of the dial-move seam.

- **2026-10-06 (tempo-dial pickup: the melody's stale step re-scales; the range-input lesson cost the first red)** —
  Robin's question on the field report ("moving the tempo slider all the way down
  and back up, it waits for the silence after the slow note to play out before
  increasing tempo") got traced before code: the melody walker advances token by
  token and melodyNextTime's absolute time is frozen when a step is scheduled
  (melodyNextTime += step under the CURRENT dial), the wake loop does nothing
  while it sits ≥0.3 s ahead, and the pending token's grid position is already
  the NEXT token (melodyIdx/melodyPos96 past it) — so a pickup after a move up
  from the floor waits out one whole stale step (a quarter at 10% of a 120 bpm
  song ≈ 5 s, mostly silence), while the S1 resync family had already cured the
  #track streams of the same disease. Robin elected 1a from the batch: rebase the
  melody's own pending onset by the speed ratio, overhanging ringing note left to
  decay, no slider-floor raise. Red-first: transport_schedule leg 10 fires a dial
  move to 100% at ~1.6 s into a 10%-paced song (q 0.625 → 6.25 s steps) and pins
  the pre-fix red at 4.679 s (the exact stale remainder); the leg's collection
  rides the song's own auto-stop so the 8-onset count stays a pollution detector,
  and its slow-phase pin is time-ordered (second onset must still be pending at
  move time) because a WORKING rebase legitimately rewrites that gap (post-fix
  C5→D5 = 2.039 s = 0.05 seed + 1.6 wait + 0.47 scaled remainder — the assert
  caught its own first draft on just that). The first implementation failed THE
  LEG red: snapshotting the previous dial off the DOM is impossible — a range
  input's value already holds the new one when its input event fires — so the
  from-speed became an audio-side mirror (tempoDialSpeed, adopted at every
  resyncMelodyTempo call and re-seeded when scheduleMelody reseeds
  melodyNextTime at play/resume, since the old pacing dies with the ledger).
  resyncMelodyTempo runs before resyncTrackTimes in applyTempoPct so the streams
  re-anchor from the moved anchor. Pinned green; eslint + html-validate clean;
  full sweep 50/50 (416 s); sw oco-pwa-v95. Branch tempo-dial-rebase (placeholder
  style, Robin renames). Holds: the S1 ≤0.35 s seam (still open) plus the
  pickup's own feel — speed-up lets the stale note ring under the early onsets,
  slow-down stretches the pending gap (Robin's ears decide). Noted on the §1
  item: the swing dial's melody remainder stays unrebased (one-beat-class stale
  wait at full dial; ratio math not exact under swing reweighting).

- **2026-10-07 (song-txt-files opened — Robin asks the song data split: music to .txt files, songs.json keeps metadata)** —
  Robin's ask: songs stored as .txt files referenced from songs.json (group,
  name — which can differ from the .txt's own title — intended instrument
  stay metadata); bodies retrieved/referenced per song; ONE .txt file can be
  addressed multiple times (bass-transposed versions etc.); the aim is
  human-readable editing and exported web-app files dropping in as-is
  (Save File's round-trip headers already carry title/tempo/swing/tick/
  meter + #track blocks). Fields that belong to the music rather than
  metadata MAY relocate into the .txt. Survey done (no code yet):
  library.js initBuiltin/loadLibraryItem/songOutOfRange/songFitsChart are
  the body consumers; boot loads songs.json + resume compares its text;
  sw.js DATA_NETWORK_FIRST covers songs.json and the install derive caches
  it; gen_song_pages.py reads songs[key].body for chart fit; data_validator
  and twin_derive fixtures read songs.json shapes. Robin's follow-up rules
  in update propagation (2026-10-07): players must receive updated songs,
  never stale cached bodies — the .txt files join the network-first regimen
  and the resume freshness check extends to the bodies. Remaining forks
  batched to Robin (retrieval timing, JSON-vs-.txt field placement,
  directory name); item boarded §5. Branch song-txt-files created as the
  placeholder; no app code yet.
