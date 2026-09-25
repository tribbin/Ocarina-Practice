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
(refreshed 2026-09-25: hot row 1's schema-validation question closed when the
reframed R4 data validator shipped `f62ede5`; the flake family's third member
got its class cure the same day):

| Item | Section |
|---|---|
| Robin-field feedback stack: PWA install + airplane-mode practice (§9 F1), theme/help/title-bar eyeball, history line, new highlight-plan playback eyeball, dip dipMs/dipFrac by ear (§4 P2's retuned gate) | feel checks |
| §9 feature stack: octave-twin dedup decision (survey done, held for Robin), transpose (held for Robin — text-vs-token fork on the item), recording — MIDI work only as tooling supporting Robin (section looping declined 2026-09-24 — archived in DONE §9; robots/sitemap are the post-switch invite — the permalink contract is not live until go-live + robots.txt) | §9 |
| **Search-engine perma-links BEFORE the November Switch-2 OoT launch** — the one deadline-bound item in the pool (slug freeze → per-song static stubs → og/meta → robots on verification; ~5 weeks) | §9 |

---

## 1. Bugs (correctness / data loss)

- [ ] **tone.json declared but absent — INTENTIONAL, not a bug** — instruments.json lists `tone` paths for stein-double-alto-c, oot-alto-c-12, ico-contrabass-11-c: Robin is going to measure/tune every ocarina chamber; until each tone.json is recorded the loader treats the 404 as "no data yet" (correct behaviour). REWORDED instruments/README.md to say entries may declare the field ahead of measurements ✅ 2026-09-22 `9cfccfb`. **Opens instead: the actual measurement/fitting work per chamber.** `🟩 ⚪ ⚙L`

## 2. Robustness / error handling

- [ ] **Sporadic single-frame audio "ticks" — one waveform jump per tick, and the CURRENT note goes silent after it** — Robin field notes 2026-09-24: ticks on Windows AND on his phone, on the phone even with the Lite voice (rules OUT node-count/CPU pressure), the perf screen's glitch counter never fires for them (it counts audio-clock-vs-wall lag at a 0.3 s criterion, audio.js:352 — a sample-plane discontinuity never gets near it), "after such a tick, the current note seems silenced", sporadic with no identified trigger yet. Class read: this is a RENDERED-SIGNAL discontinuity, not starvation — prime suspects: (1) AudioParam event-timeline re-anchoring of a LIVE envelope: a later linearRamp's implicit anchor or a `cancelScheduledValues` path restamp the running gain to a stale event value → one step (the tick) plus a dead envelope remainder (the silenced note) — the neighborhoods audio.js:1131-1133 (non-melody bag fade) and 1671-1673 (live/hover rampFades) plus the documented implicit-event hazard (~audio.js:1363); this exact neighborhood has real-device history — cancelAndHoldAtTime "popped on real hardware" and was engineered out; (2) the DynamicsCompressor limiter pumping at multi-voice seams; (3) zen mono↔stereo anchor/pan events; (4) device-level (Windows shared-mode WASAPI) — least likely given lite-invariance. Detection plan: a debug-only spike detector on the perfAnalyser time-domain tap (single-frame |Δx| > K·system-RMS, with the markSystemSound onset/stop windows subtracted) logging timestamp + a state card (in-flight onsets, retire window, tempo move, zen in/out, lite flag) to the perf panel + OCA_DEBUG; the next field tick then names its own automation seam. **Field answers 2026-09-24:** playback CONTINUES at the next note after the silenced one → voice-seam class confirmed, context/device death ruled out; the same song does NOT reproduce consistently across replays → a timing race at event collation, not a per-note mapping error; observed on MAIN (pre-existing shipped behavior, independent of the refactor4 chain); repro rate ~every 2 playbacks of Concerning Hobbits short in Google Chrome, NOT reproducible in VS Code's embedded browser (engine-timing sensitive — different Chromium build, different event-alignment odds). (✅ 2026-09-24 `17fae24`) **the spike watch detector landed** (test-first, `tests/spike_watch.py` in CI): a pure two-shape classifier (ONE delta to a new sustained level — the jump-to-silence that kills the note — or a mirrored up-then-down pair for the single-sample excursion; N-adjacent above-threshold deltas = ramp class, rejected) reads the post-limiter analyser every 20 ms (overlapping 23 ms windows, full coverage), the markSystemSound onset/stop windows subtracted, each hit logged as a state card (audio-clock t, jump size, 96th-grid melody position, lite flag, recent playNoteAt onsets from a new ring) on the perf panel's new 'Signal spikes (ticks)' row plus a throttled console warn; `spikeFake()` lets suites probe the row; sw VERSION → v4. **Next field catch now names its own seam** — Robin reproduces in Chrome, the row/card + console line identifies the automation neighborhood; the fix itself stays held for the evidence. **Field evidence lifted from IDEAS 2026-09-24:** on the phone the three perf counters stay at 0 while ticks happen — now described as MULTIPLE consecutive ticks, not yet a buzz — and a screen-orientation flip ALWAYS triggers them ("seems related to the visual processing"); not reproducible on the Windows desktop as of now (earlier Windows reports stand, so repro availability drifts by device/build). Robin's open questions: can background visuals freeze in Zen (and Zen visuals in normal)? Can audio be prioritized over visuals? Would pre-calculating waveforms on song selection even help (this ties the IDEAS PERF waveform idea to the hunt)? The shipped spike watch ("Signal spikes (ticks)" perf row) has NOT yet met the phone — after his next orientation-flip session, whether THAT detector fires while the counters stay silent will itself name the plane the discontinuity lives on. `🟧 🟠 ⚙M`

## 3. Security (low today — matters if data files become user-supplied)

## 4. Performance

- [ ] **Deprecated createScriptProcessor for WAV export** — also taps the reverb bus into a second destination chain, so the dry bus sounds at limiter-bypassed level during capture (debug-only). **Reframed ⚪ backlog**: the AudioWorklet replacement means module loading + a new file for a debug-only tool; revisit only when a worklet exists elsewhere in the app or the tap misbehaves on a real device. (debug.js WAV export) `🟨 ⚪ ⚙M`

## 5. Architecture / maintenance

## 6. Tests & CI

- [ ] **Real-DSP validation for autoCorrelate** — CI uses synthetic frames only; record WAV fixtures and run the classifier offline against known pitches (`OCA_PRACTICE.testAC` already hooks it, practice.js:1218-1232). `🟨 ⚪ ⚙M`

- [ ] **debug.js coverage** — nothing tested; low value. `🟢 ⚪`

Currently covered (don't lose this): practice acceptance (4 cases strict+closed-loop), practice dip gate (hold-through blocked, silence/50%-notch dips pass, 75% duck shut, legato free), practice seat across view rebuilds + zen-entry stopMelody + overlay zen-only seats, console-hygiene boot scan (4 boots; allowlist = manifest-declared tone misses), support-bracket battery incl. bit-identical melody-vs-support equivalence + Zen timing/gating, instrument load/tone-model install per manifest (incl. svgWhen id/title paths + boot diagnostics in per-leg fresh contexts), render pin (chips/grid/scroll-band/highlight/focus-restore + typed-render debounce contract), svg clone coordinates, debug panel build-on-open contract, transport scheduler arithmetic/cut-bus/lite, practice history, template safety, theme toggle, offline SW boot+swap, ac worker parity, swing grid, sr hints, spike watch (the tick hunt). CI = push/PR/manual, explicitly not a deploy gate. (.github/workflows/practice-tests.yml — console-hygiene + 24 suite steps + eslint + html-validate; local run-all counted 25 green on 2026-09-23 on the Linux partition and again on the Windows partition — partition sweep red 24/25 until the runner's UTF-8 child-env fix, see session log ~2026-09-23) NOTE: practice_accepts flaked ONE strict case under full-sweep load 2026-09-23, green twice standalone afterward and in the diag run — watch it, the arbiter hardening already took one such race; support_accepts flaked the same class 2026-09-24 (fixed wall-clock read window vs audio-clock lag under sweep CPU contention) and got the class cure: the read is now a real rendezvous with wall-fire stamps + ctx snapshots `335c4b4`). **Third member 2026-09-25 (CLI run `36110497803`, job 107992645371): practice_dip's leg A stalled the full 15 s timeout at maxIdx 0** — same SHA the local sweep had green; a DIFFERENT injury inside the same family: the suite's rendezvous (OCA_PRACTICE+NOTES) unlocks INSIDE loadInstrument (the stretch between installFingerings and boot's tail), where fillLibrary/loadLibraryItem(home) → practiceInvalidate is still owed — a session started mid-boot died when the tail landed; the stall reproduces at will with CDP network latency, cured by the rule-13 real rendezvous: the #scale options guard (filled only by the tail; a rAF poll never resolves mid-synchronous-block) plus a state card (started/st/ix/frames) on every driver resolve so a future stall names itself. The same tail guard rode into every suite that starts practice or needs typed editor text to survive boot (practice_accepts_melody, practice_zen_return, practice_history, keyboard_widgets, render_pin); library_hardening already waited a stronger post-tail signal (the Scales OPTGROUP), instrument_switch_race covers the race as its subject, playback-only suites are immune (practiceInvalidate stops practice, never play). Full sweep 31/31 green after the cure.

## 7. Accessibility & UX

- [ ] **Token chips: long-press-to-listen on touch** ✅ 2026-09-22 `ab4ce0c` — hold rides the SAME 260 ms dwell as mouse/keyboard (`hoverPreview`): touch-down highlights, planted dwell auditions (once), completed hold swallows the follow-up tap (no transport start), quick taps keep native play-from-here, drift/pinch cancels silently. Pressing keeps `-webkit-touch-callout`/selection off. Pinned in `tests/keyboard_widgets.py` (touch section, playNote-call oracle — voice counts inflate from lingering nodes). Robin's feel-check on a real device still open. `🟨 🟠 ⚙S`

- [ ] **Collapse buttons + misc** — §1 B7 was completed long ago; see `plans/DONE.md` §1 for what it covered and pick the misc remainder on touch. `🟢 🟡 ⚙S`

## 8. Housekeeping

Nothing open — completed housekeeping is archived in `plans/DONE.md` §8.

## 9. Functional ideas (features)

- [ ] **Recording & A/B compare** — record mic during practice, replay against synth reference, pitch-curve overlay (WAV tap already exists in debug export). `🟢 🟡 ⚙L`

- [ ] **Standardize shipped songs to the conventions in `skills/ocarina-melodies/SKILL.md`** — barline at the START of wrapped lines (cosmetic; parser reads `|` positionally today, so all shipped bodies bar-at-line-end parse identically), named sections where players want headers, per-song house conventions. Robin plants this as a later-stage pass — "very useful to players." Use verify/shipped_songs suites as gates; no playback changes expected. 2026-09-24: Robin confirmed this stays HELD for its later-stage pass — the hands-off night does not touch shipped song bodies; revisit when he wants it. `🟢 ⚪ ⚙M`

- [ ] **MIDI import to tabs in-app** — `.grok/midi-to-ocarina-tab/scripts/mid2tab.py` already converts MIDI→tab notation; bake into "Load file" as JS. `🟢 🟡 ⚙M`

- [ ] **Transpose** — shift melody ±semitones in parse/eval to fit other-key ocarinas. ﻿Stretch pick F6 transpose HELD for Robin 2026-09-25 (night): the placement was the granted call, but building touched a mid-flight fork the night cannot decide â€” text-level shift (the transposer skill's proven semantics reused on the editor text) vs a token-level shift inside parse/eval (original text untouched, displayed/rendered tokens moved): the second changes what the user SEES vs what the editor HOLDS while saved bodies keep original pitches â€” a surface/feel decision with audible consequences, exactly Robin's field-check class. Budget ruled too: one more unit + full sweep would have hit the watch line with the closing bookkeeping unlanded (rule 18). Worked around: nothing blocks on it; the twin-survey report (Dedup item, same night) plus the transposer skill already carry the shift semantics for any future build. `🟢 🟡 ⚙M`

- [ ] **Library search / favorites / pinning** — flat dropdown gets unwieldy as personal library grows. `🟢 🟡 ⚙M`

- [ ] **Search-engine perma-links BEFORE the Switch-2 OoT launch (November)** — lifted from IDEAS 2026-09-24 and refined with Robin's rules: per-song landing URLs where "content may change, but the link must serve what the crawl expected". URL shape locked 2026-09-24: **`/song/<category>/<base-slug>`**, default player **12-hole C alto**, category (zelda/scales/other, normalized from group; "on Bass"/"on Alto" collapse) keys per-category theming (zelda → Hyrule, else Plain/new). Progress: (✅ 2026-09-24) **slug freeze enforced** — closed suffix list + chain rule + grammar in `tests/shipped_songs.py` (CI fails on violating keys), the `-alt`/`-alto` split fixed pre-index (`major-alto`, `chromatic-alto`), the contract documented in `skills/ocarina-melodies/SKILL.md`; (✅ 2026-09-24) **serving layer built + live-boot corrected** — `tools/gen_song_pages.py` emits shell-only landing stubs per base slug: canonical + og:url on the site-prefix path, single song-specific description, `?song=<key>&inst=<chosen>` pre-boot seed, hidden/variants excluded, byte-deterministic, staging git-ignored; the LIVE URL check on the first deployed stub caught the generator-class defect string tests missed — the app's runtime fetches (`songs.json`/`instruments.json`/css text/manifest-driven instrument files; even the SW registration) resolve relative to the PAGE and 404'd two directories deep, killing boot — fixed with a `<base href="{site-prefix}/">` injection (root-absolute `/…` rejected in review: bakes the prefix everywhere, breaks relocatability, and cannot reach runtime fetches without app changes); the landing default became Robin's corrected LADDER — best-fit by 12-hole > double alto C > triple bass C > contrabass (Song of Time's bass body lands on the triple; every stub boots playable, no range marks) — and `tests/gen_pages.py` upgraded to a real-boot leg: the staging tree assembled exactly like the deploy workflow's allowlist, served under the /Ocarina-Practice mount, boot asserted for right song/right ocarina/zero out-of-range chips/rendered sheet/one description/clean console (allowlist semantics: every 404 must BE a tone.json; a healthy boot can legitimately have NO 404s — the triple's tone.json exists); `.github/workflows/deploy-site.yml` publishes on served-content path pushes + manual dispatch; (✅ 2026-09-24 `89a39f0`) **og/meta card stage complete** — og:type/og:site_name/og:description (same wording as the meta description, one description per page holds) + og:image riding the already-generated 512 icon (width/height/alt) + summary twitter:card, injected at the END of head so the shell's charset keeps its first-KB seat; URLs stay site-prefix path form (canonical/og:url/og:image consistent; fully-absolute held until a domain is pinned); gen_pages pins every tag per stub over the still-green real-boot matrix. (✅ 2026-09-24 `e7718bc`) **domain landed + serving layer switched to it** — `ocarina-practice.com` is now the site's pinned origin (registered along the forever-perma rule; registrar and registration details stay out of this public repo on Robin's call): the deploy artifact carries a CNAME file, gen_pages gained `--site-origin` (default the domain) and now emits ABSOLUTE canonical/og:url/og:image with `<base href="/">`, the gen_pages suite re-pins every contract against a ROOT-mounted artifact; project-page serving stays reachable via the preserved --site-prefix/--site-origin-empty knobs for rollback. **Robin's manual cutover checklist (order matters):** push refactor4 → merge/deploy fires the artifact (with CNAME) → registrar DNS: CNAME record www → <github-io-user-host> (plus A/AAAA apex records if wanted) → repo Settings → Pages → custom domain = ocarina-practice.com (wait the DNS check) → enforce HTTPS once the cert provisioned → account-level Pages 'verified domains' adds + TXT-verifies the domain (the free takeover guard) → re-probe landing URLs at the domain (the boot is root-relative now — the old /Ocarina-Practice path dies by design). (next: live-domain verification of the landing matrix — his push, then this check) Remaining: richer stub content if SERP demands (thin-mass watch), absolute URLs if a domain gets pinned, sitemap.xml + robots.txt only AFTER links verify (Robin's crawl rule), Lighthouse pass, first real deploy + SERP observation. Deadline anchor: OoT Switch 2 ships in November (~5 weeks from 2026-09-24). **Decisions 2026-09-24 (refinement round):** BRANDING settled — the product STAYS "Ocarina Practice" (og:site_name already correct; no rename; the IDEAS BRANDING line is clear to delete). Domain processing still pending tonight; go-live planned tomorrow as a JOINT session — Robin's rule: the flip "has never been a success" solo, so hands-off sessions do PREP ONLY: keep this item's cutover checklist current, add a refactor4-domain (e7718bc) diff summary of what merging brings, and build live-verify tooling. SEO feature stages (robots/sitemap) are POST-switch work — and Robin's correction: the permalink contract does not become LIVE until go-live WITH robots.txt in place; nothing is crawlable before that moment, so slug/staging prep carries no permalink risk — the robots.txt push itself stays the final invite act, only after the live boot verifies. ﻿Night prep 2026-09-25 (away session, prep only by tonight's rules): - **Merge surface** â€” refactor4-domain is ONE commit (`e7718bc` over `c96965a`) touching `.github/workflows/deploy-site.yml`, new `CNAME`, `README.md`, `tests/gen_pages.py`, `tools/gen_song_pages.py`; zero overlap with what refactor4 merged (js/*, AGENTS.md, plans/) â€” clean merge expected. - **Checklist currency** â€” Robin's cutover checklist (above) stands unchanged; a push of tonight's `session5` stack also fires the artifact (served-content path trigger), so "push â†’ merge/deploy" may run BEFORE his joint session touches DNS â€” the order of DNS/Pages/HTTPS steps is unaffected. - **Live-verify tooling built + used**: `tools/verify_site.py --origin <base> [--boot N]` (not a CI step; read-only GETs). Checks: shell serves the js/app.js module entry; deployed songs.json readable; every landing stub 200 with base href / canonical / og:url agreeing on the ONE serving prefix (base href from the origin's path, so both stages hold), og:title + description present; `--boot N` boots sampled stubs (song-of-time always) in fresh contexts (SW second-navigation lesson), zero console noise beyond the manifest-declared-absent tone.json 404s, right song on the right ocarina by the ladder. - **Pre-flip state recorded**: today started on a STALE artifact (home shell predated the PWA commit: no serviceWorker string, no og on the shell) while /song/ stubs served the permalink contracts; a fresh push-triggered Actions deploy during the night refreshed the artifact, and the full probe ran GREEN before the flip (18 checks, 8/8 stubs booted clean at /Ocarina-Practice). - **Tomorrow**: same command with `--origin https://ocarina-practice.com` is the post-flip acceptance gate â€” absolute canonical/og + root `<base href="/">` + CNAME artifact; the /Ocarina-Practice mount dies by design. `🟨 🟠 ⚙M`

- [ ] **Deduplicate octave/transpose-twinned song bodies (survey first)** — Robin: "Deduplicating songs (that only differ in octave/transpose) would be a nice touch." FIRST step is tooling only (his MIDI-boundary rule: no song-data work unsupervised): a `tools/` audit that proves which songs.json variants are exact octave shifts of one another (the dummy↔stein +12 pair is the precedent — see skills/song-transposing). Report the twin classes + per-class divergence spots; then decide WITH Robin whether variants keep hand-written bodies or derive from a base body at load (keys/URLs MUST stay frozen either way — the permalink contract). ﻿Night survey 2026-09-25 (tools/audit_twins.py `33bd3fa`, report-only, no bodies touched): **5 octave twins** â€” song-of-time/-bass, song-of-storms/-bass, sarias-song/-bass, eponas-song/-bass (every -bass arrangement is its alto base's melody one octave DOWN, modulo nothing: barlines, rests, continuations, slides, durations and accents all carried over) and botw-theme/-down3 (also -12). **3 uniform non-octave twins** â€” concerning-hobbits-short/-c (shift -2), botw-theme/-bass (shift -9), botw-theme-bass/-down3 (shift -3; the two bass arrangements are a uniform -3 apart). **No other twins**: all cross pairs are NOT-ALIGNED (different token counts), and kokiri-forest-bass refuses every verdict until its stray lowercase `g4/4` token is resolved (tool refuses on unreadable shapes by construction). So: the four -bass bodies and botw's -down3 are PROVEN derivable-at-load candidates (keys/URLs stay frozen either way per the permalink contract); the three non-octave twins are shift-derivable too; kokiri is a potential fifth body once its stray token is explained â€” that one needs Robin's eyes before any claim. `🟨 🟡 ⚙M`



> **Idle idea pool: `plans/IDEAS.txt`.** A live document Robin edits over time and ROBIN'S ALONE — the AI never writes it (it may be read, and only lifted into TODO.md when Robin explicitly asks). TODO carries no copy or summary: when an idea from it is picked up, read the FILE fresh at that moment; never rely on a remembered or transcribed version.

---

## Session log

(Older entries live in `plans/DONE.md` (session log). New entries below — retire via `python tools/board.py log-retire` once another session has opened from them.)

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
