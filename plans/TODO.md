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
(refreshed 2026-09-24 during the DONE split):

| # | Item | Section |
|---|---|---|
| 1 | Schema validation of instruments/songs/fingerings on boot — **superseded by §9 F1** (the SW-derived precache makes a bad manifest entry break CI's offline suite; Robin may not want a loud-boot gate for his hand-tuned data) — reconfirm intent before building | §2 R4 |
| 2 | Robin-field feedback stack: PWA install + airplane-mode practice (§9 F1), theme/help/title-bar eyeball, history line, new highlight-plan playback eyeball, dip dipMs/dipFrac by ear (§4 P2's retuned gate) | feel checks |
| 3 | §9 feature stack: transpose, MIDI import, recording (section looping declined 2026-09-24 — archived in DONE §9) | §9 |
| 4 | **Search-engine perma-links BEFORE the November Switch-2 OoT launch** — the one deadline-bound item in the pool (slug freeze → per-song static stubs → og/meta → robots on verification; ~5 weeks) | §9 |

---

## 1. Bugs (correctness / data loss)

- [ ] **tone.json declared but absent — INTENTIONAL, not a bug** — instruments.json lists `tone` paths for stein-double-alto-c, oot-alto-c-12, ico-contrabass-11-c: Robin is going to measure/tune every ocarina chamber; until each tone.json is recorded the loader treats the 404 as "no data yet" (correct behaviour). REWORDED instruments/README.md to say entries may declare the field ahead of measurements ✅ 2026-09-22 `9cfccfb`. **Opens instead: the actual measurement/fitting work per chamber.** `🟩 ⚪ ⚙L`

## 2. Robustness / error handling

- [ ] **No schema validation of data files** — instruments.json / songs.json / fingerings.json fields are read directly with `||` defaults; malformed fingerings only surfaces via boot's outer catch. Validate on boot and fail loudly with the offending path. (app.js:180-217, library.js:311-326) `🟧 🟡 ⚙M`

- [ ] **Sporadic single-frame audio "ticks" — one waveform jump per tick, and the CURRENT note goes silent after it** — Robin field notes 2026-09-24: ticks on Windows AND on his phone, on the phone even with the Lite voice (rules OUT node-count/CPU pressure), the perf screen's glitch counter never fires for them (it counts audio-clock-vs-wall lag at a 0.3 s criterion, audio.js:352 — a sample-plane discontinuity never gets near it), "after such a tick, the current note seems silenced", sporadic with no identified trigger yet. Class read: this is a RENDERED-SIGNAL discontinuity, not starvation — prime suspects: (1) AudioParam event-timeline re-anchoring of a LIVE envelope: a later linearRamp's implicit anchor or a `cancelScheduledValues` path restamp the running gain to a stale event value → one step (the tick) plus a dead envelope remainder (the silenced note) — the neighborhoods audio.js:1131-1133 (non-melody bag fade) and 1671-1673 (live/hover rampFades) plus the documented implicit-event hazard (~audio.js:1363); this exact neighborhood has real-device history — cancelAndHoldAtTime "popped on real hardware" and was engineered out; (2) the DynamicsCompressor limiter pumping at multi-voice seams; (3) zen mono↔stereo anchor/pan events; (4) device-level (Windows shared-mode WASAPI) — least likely given lite-invariance. Detection plan: a debug-only spike detector on the perfAnalyser time-domain tap (single-frame |Δx| > K·system-RMS, with the markSystemSound onset/stop windows subtracted) logging timestamp + a state card (in-flight onsets, retire window, tempo move, zen in/out, lite flag) to the perf panel + OCA_DEBUG; the next field tick then names its own automation seam. **Field answers 2026-09-24:** playback CONTINUES at the next note after the silenced one → voice-seam class confirmed, context/device death ruled out; the same song does NOT reproduce consistently across replays → a timing race at event collation, not a per-note mapping error; observed on MAIN (pre-existing shipped behavior, independent of the refactor4 chain); repro rate ~every 2 playbacks of Concerning Hobbits short in Google Chrome, NOT reproducible in VS Code's embedded browser (engine-timing sensitive — different Chromium build, different event-alignment odds). (✅ 2026-09-24 `17fae24`) **the spike watch detector landed** (test-first, `tests/spike_watch.py` in CI): a pure two-shape classifier (ONE delta to a new sustained level — the jump-to-silence that kills the note — or a mirrored up-then-down pair for the single-sample excursion; N-adjacent above-threshold deltas = ramp class, rejected) reads the post-limiter analyser every 20 ms (overlapping 23 ms windows, full coverage), the markSystemSound onset/stop windows subtracted, each hit logged as a state card (audio-clock t, jump size, 96th-grid melody position, lite flag, recent playNoteAt onsets from a new ring) on the perf panel's new 'Signal spikes (ticks)' row plus a throttled console warn; `spikeFake()` lets suites probe the row; sw VERSION → v4. **Next field catch now names its own seam** — Robin reproduces in Chrome, the row/card + console line identifies the automation neighborhood; the fix itself stays held for the evidence. `🟧 🟠 ⚙M`

## 3. Security (low today — matters if data files become user-supplied)

- [ ] **Print popup `document.write(html)`** — title already HTML-escaped; keep consistent when touching. (ui.js:827-845) `🟢 ⚪ ⚙S`

## 4. Performance

- [ ] **Deprecated createScriptProcessor for WAV export** — also taps the reverb bus into a second destination chain, so the dry bus sounds at limiter-bypassed level during capture (debug-only). **Reframed ⚪ backlog**: the AudioWorklet replacement means module loading + a new file for a debug-only tool; revisit only when a worklet exists elsewhere in the app or the tap misbehaves on a real device. (debug.js WAV export) `🟨 ⚪ ⚙M`

- [ ] **enlargeSmallHoles is O(holes²) per card render** — (ocarina.js:92-110) `🟢 ⚪ ⚙S`

## 5. Architecture / maintenance

- [ ] **Deduplicate pitch/maths (4 copies each)** — CLUSTERS 1-3 ✅ 2026-09-24 (`a6b15c0` + `938bc6f`): (1) midi/frequency → `js/music-math.js` single source (audio re-exports the binding so ESM + windowed surfaces stay bound for tests/debug; ui's zen-glow noteMidi wraps it with the 69 fallback; practice's defensive freqOfId duplicate deleted; **parse.js keeps its own midiOf DELIBERATELY** — the transposer skill loads parse.js raw through a window-shim eval that strips exports but cannot carry imports); (2) grid-beats → shared tokenGridBeats, where the two copies had already DIVERGED (audio's fallback lost the 2/3 triplet factor; the parser pre-computes beats so it only bit synthetic durationless tokens — now impossible), practice's gridBeats dies with its three call sites; (3) quarter-seconds → shared quarterSecFor, ui's quarterSec keeps only its editor-reading wrapper. Remaining: PLAY/PAUSE DOM WRITES (audio.js vs ui.js) — last cluster of the item. `🟨 🟠 ⚙M`

## 6. Tests & CI

- [ ] **Real-DSP validation for autoCorrelate** — CI uses synthetic frames only; record WAV fixtures and run the classifier offline against known pitches (`OCA_PRACTICE.testAC` already hooks it, practice.js:1218-1232). `🟨 ⚪ ⚙M`

- [ ] **debug.js coverage** — nothing tested; low value. `🟢 ⚪`

Currently covered (don't lose this): practice acceptance (4 cases strict+closed-loop), practice dip gate (hold-through blocked, silence/50%-notch dips pass, 75% duck shut, legato free), practice seat across view rebuilds + zen-entry stopMelody + overlay zen-only seats, console-hygiene boot scan (4 boots; allowlist = manifest-declared tone misses), support-bracket battery incl. bit-identical melody-vs-support equivalence + Zen timing/gating, instrument load/tone-model install per manifest (incl. svgWhen id/title paths + boot diagnostics in per-leg fresh contexts), render pin (chips/grid/scroll-band/highlight/focus-restore + typed-render debounce contract), svg clone coordinates, debug panel build-on-open contract, transport scheduler arithmetic/cut-bus/lite, practice history, template safety, theme toggle, offline SW boot+swap, ac worker parity, swing grid, sr hints, spike watch (the tick hunt). CI = push/PR/manual, explicitly not a deploy gate. (.github/workflows/practice-tests.yml — console-hygiene + 24 suite steps + eslint + html-validate; local run-all counted 25 green on 2026-09-23 on the Linux partition and again on the Windows partition — partition sweep red 24/25 until the runner's UTF-8 child-env fix, see session log ~2026-09-23) NOTE: practice_accepts flaked ONE strict case under full-sweep load 2026-09-23, green twice standalone afterward and in the diag run — watch it, the arbiter hardening already took one such race; support_accepts flaked the same class 2026-09-24 (fixed wall-clock read window vs audio-clock lag under sweep CPU contention) and got the class cure: the read is now a real rendezvous with wall-fire stamps + ctx snapshots `335c4b4`)

## 7. Accessibility & UX

- [ ] **Token chips: long-press-to-listen on touch** ✅ 2026-09-22 `ab4ce0c` — hold rides the SAME 260 ms dwell as mouse/keyboard (`hoverPreview`): touch-down highlights, planted dwell auditions (once), completed hold swallows the follow-up tap (no transport start), quick taps keep native play-from-here, drift/pinch cancels silently. Pressing keeps `-webkit-touch-callout`/selection off. Pinned in `tests/keyboard_widgets.py` (touch section, playNote-call oracle — voice counts inflate from lingering nodes). Robin's feel-check on a real device still open.

- [ ] **Collapse buttons + misc** — §1 B7 was completed long ago; see `plans/DONE.md` §1 for what it covered and pick the misc remainder on touch. `🟢 🟡 ⚙S`

## 8. Housekeeping

Nothing open — completed housekeeping is archived in `plans/DONE.md` §8.

## 9. Functional ideas (features)

- [ ] **Recording & A/B compare** — record mic during practice, replay against synth reference, pitch-curve overlay (WAV tap already exists in debug export). `🟢 🟡 ⚙L`

- [ ] **Standardize shipped songs to the conventions in `skills/ocarina-melodies/SKILL.md`** — barline at the START of wrapped lines (cosmetic; parser reads `|` positionally today, so all shipped bodies bar-at-line-end parse identically), named sections where players want headers, per-song house conventions. Robin plants this as a later-stage pass — "very useful to players." Use verify/shipped_songs suites as gates; no playback changes expected. `🟢 ⚪ ⚙M`

- [ ] **MIDI import to tabs in-app** — `.grok/midi-to-ocarina-tab/scripts/mid2tab.py` already converts MIDI→tab notation; bake into "Load file" as JS. `🟢 🟡 ⚙M`

- [ ] **Transpose** — shift melody ±semitones in parse/eval to fit other-key ocarinas. `🟢 🟡 ⚙M`

- [ ] **Library search / favorites / pinning** — flat dropdown gets unwieldy as personal library grows. `🟢 🟡 ⚙M`

- [ ] **Search-engine perma-links BEFORE the Switch-2 OoT launch (November)** — lifted from IDEAS 2026-09-24 and refined with Robin's rules: per-song landing URLs where "content may change, but the link must serve what the crawl expected". URL shape locked 2026-09-24: **`/song/<category>/<base-slug>`**, default player **12-hole C alto**, category (zelda/scales/other, normalized from group; "on Bass"/"on Alto" collapse) keys per-category theming (zelda → Hyrule, else Plain/new). Progress: (✅ 2026-09-24) **slug freeze enforced** — closed suffix list + chain rule + grammar in `tests/shipped_songs.py` (CI fails on violating keys), the `-alt`/`-alto` split fixed pre-index (`major-alto`, `chromatic-alto`), the contract documented in `skills/ocarina-melodies/SKILL.md`; (✅ 2026-09-24) **serving layer built + live-boot corrected** — `tools/gen_song_pages.py` emits shell-only landing stubs per base slug: canonical + og:url on the site-prefix path, single song-specific description, `?song=<key>&inst=<chosen>` pre-boot seed, hidden/variants excluded, byte-deterministic, staging git-ignored; the LIVE URL check on the first deployed stub caught the generator-class defect string tests missed — the app's runtime fetches (`songs.json`/`instruments.json`/css text/manifest-driven instrument files; even the SW registration) resolve relative to the PAGE and 404'd two directories deep, killing boot — fixed with a `<base href="{site-prefix}/">` injection (root-absolute `/…` rejected in review: bakes the prefix everywhere, breaks relocatability, and cannot reach runtime fetches without app changes); the landing default became Robin's corrected LADDER — best-fit by 12-hole > double alto C > triple bass C > contrabass (Song of Time's bass body lands on the triple; every stub boots playable, no range marks) — and `tests/gen_pages.py` upgraded to a real-boot leg: the staging tree assembled exactly like the deploy workflow's allowlist, served under the /Ocarina-Practice mount, boot asserted for right song/right ocarina/zero out-of-range chips/rendered sheet/one description/clean console (allowlist semantics: every 404 must BE a tone.json; a healthy boot can legitimately have NO 404s — the triple's tone.json exists); `.github/workflows/deploy-site.yml` publishes on served-content path pushes + manual dispatch; (✅ 2026-09-24 `89a39f0`) **og/meta card stage complete** — og:type/og:site_name/og:description (same wording as the meta description, one description per page holds) + og:image riding the already-generated 512 icon (width/height/alt) + summary twitter:card, injected at the END of head so the shell's charset keeps its first-KB seat; URLs stay site-prefix path form (canonical/og:url/og:image consistent; fully-absolute held until a domain is pinned); gen_pages pins every tag per stub over the still-green real-boot matrix. (✅ 2026-09-24 `e7718bc`) **domain landed + serving layer switched to it** — `ocarina-practice.com` is now the site's pinned origin (registered along the forever-perma rule; registrar and registration details stay out of this public repo on Robin's call): the deploy artifact carries a CNAME file, gen_pages gained `--site-origin` (default the domain) and now emits ABSOLUTE canonical/og:url/og:image with `<base href="/">`, the gen_pages suite re-pins every contract against a ROOT-mounted artifact; project-page serving stays reachable via the preserved --site-prefix/--site-origin-empty knobs for rollback. **Robin's manual cutover checklist (order matters):** push refactor4 → merge/deploy fires the artifact (with CNAME) → registrar DNS: CNAME record www → <github-io-user-host> (plus A/AAAA apex records if wanted) → repo Settings → Pages → custom domain = ocarina-practice.com (wait the DNS check) → enforce HTTPS once the cert provisioned → account-level Pages 'verified domains' adds + TXT-verifies the domain (the free takeover guard) → re-probe landing URLs at the domain (the boot is root-relative now — the old /Ocarina-Practice path dies by design). (next: live-domain verification of the landing matrix — his push, then this check) Remaining: richer stub content if SERP demands (thin-mass watch), absolute URLs if a domain gets pinned, sitemap.xml + robots.txt only AFTER links verify (Robin's crawl rule), Lighthouse pass, first real deploy + SERP observation. Deadline anchor: OoT Switch 2 ships in November (~5 weeks from 2026-09-24). `🟨 🟠 ⚙M`

> **Idle idea pool: `plans/IDEAS.txt`.** A live document Robin edits over time and ROBIN'S ALONE — the AI never writes it (it may be read, and only lifted into TODO.md when Robin explicitly asks). TODO carries no copy or summary: when an idea from it is picked up, read the FILE fresh at that moment; never rely on a remembered or transcribed version.

---

## Session log

(Archive: sessions 1–9 live in `plans/DONE.md`. New entries below.)

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
