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
(refreshed 2026-09-27, session 18: the Helmholtz twin voices the 12-hole —
the deciding pass is Robin's ears on the new voice; the row-math revert
rides his ruling):

| Item | Section |
|---|---|
| **FIELD CHECK the twin voice — the deciding pass** — the 12-hole now plays the handoff's Helmholtz voice (Robin: the handoff state "was perfect before"; his verdict came through, the model rows are that state again). His ears name: the held-note texture vs the takes, the attack/chiff, the glide carry, how it sits under practice | §1 |
| **Top-register held takes (A5–F6) for the 12-hole refit** — the model clamps at A5; the top rides the edge row until recorded | §1 |
| **Robin's field check on the multi-track trio** — `outset-island-with-bass` now plays melody + audible bass groove (the bassline two octaves down) + contrabass root-holds; his ears name the balance, the contrabass register, the practice-session audibility and the groove's final-bar cut | §7 |
| **Robin's ears on the Epona contrabass** — `eponas-song` now carries `#track contrabass audible 100` (ranch bass bar-for-bar); Saria's Song he already heard green 2026-09-28 | §Log |
| **Robin's eyeball pass** on the panel builds: the HiFi retune batch (`?hifi` — amber buttons, dark segment row/select, deeper zen red, LED fills) and the favorites stars in the library — his values, built to spec; he retunes anything that reads off | feel checks |
| The twin-model chamber fits per remaining ocarina — recording held takes for stein double, contrabass, oak leaf when Robin gets hands-on time | §1 |
| The next audio-tick field catch names itself (spike cards carry the ambient ring); Robin re-introduces the hunt when the ticks matter | DONE (re-openable) |
| Shipped-songs standardization stays HELD for Robin's later-stage pass; the permalinks corpora ride his planting as always | §9 |
| Library widening (search, reordering beyond the pin) stays parked until Robin elects it | §9 |

---

## 1. Bugs (correctness / data loss)

- [ ] **Twin voice for the 12-hole: the adopted baseline and its open classes** — the Helmholtz twin (`js/helmholtz-voice.js` + `instruments/oot-alto-c-12/twin_model.json`, handoff from Grok via Robin) REPLACES the additive voice outright — Robin field-checked the handoff state and ruled it the baseline ("it was perfect before" as handed over; the pass that rewrote the model's noise rows algebraically was REVERTED by his ears — A4's metronomic one-sine wobble "very bad", the liked E5 wobble is the pitch wander's). Standing structure: module + model are the handoff state byte-identical (only the 4 s crossfaded noise buffer differs — the line-comb lesson), the manifest declares `twin` and tone.json is retired with the swap (removed; the additive voice still serves stein double + contrabass). OPEN classes, ears-first per the skill's first law: (a) ATTACK ring-up — the render's rise measures ~0.08 s where the model rows say 8-26 ms (the cavity Q rings up from silence; a Q-ramp assist is the held idea, audible, his word first); (b) top register A5-F6 clamps to A5's row (interpNote end-clamp) — record the top and refit; (c) NO amplitude-wobble layer persists (the module interpolates wobble_pct unused — do not "complete" it without his ask); (d) release taper: the model rel_s 0.07 reads shallower than the takes' hand releases (stage gate's decay-depth leg ~-12 dB); (e) future refits may NOT reproduce the shipped file (the peak*0.08 span fix stays in fit.py — the shipped model is the blessed reference, not "the fit"). Regression gate: tests/tone_stages fit-row caps + stage windows measured off the blessed delivery. `🟧 🔴 ⚙M`

- [ ] **Fit the twin model per chamber (Robin records held takes; the tone-analysis era closed for the 12-hole)** — skills/ocarina-twin/run_fit.py refits a chamber from held takes (one per fingering; the subtract analysis tracks f0 so the residual is real breath); the handoff model reproduced bit-for-bit from research/note-recordings/12hole's 8 held takes (A4-A5). REMAINING chambers: stein-double-alto-c now carries a TEMP twin from the sep-17 3-take session (multi-wrapper: chamber 1 = C5 2nd-take + D6 rows, chamber 2 = G6's single row clamped at both ends, the cross-chamber gain rides the wrapper) — his real refit waits on a proper held-take sweep per chamber (chambers NEVER bridge); ico-contrabass-11-c, ico-oak-leaf-bass-c-triple (declare `twin` when data lands; the additive voice + tone.json carries them until then); the 12-hole's own refit waits on his top-register recordings. The fitter's span rule is now peak*0.08 (the old median*4 guard collapsed EVERY span onto the 0.15/0.85 fallback — release+silence fitted as sustain — so historical fitted levels/wobble read through that window; the fitter's nominal table now carries G6..Cs7 — a missing key had read G6 at a 500 Hz default and the whole subtract built on a wrong octave). His hands-on work as he gets time. `🟩 ⚪ ⚙L`

## 2. Robustness / error handling

## 3. Security (low today — matters if data files become user-supplied)

## 4. Performance

- [ ] **Deprecated createScriptProcessor for WAV export** — also taps the reverb bus into a second destination chain, so the dry bus sounds at limiter-bypassed level during capture (debug-only). **Reframed ⚪ backlog**: the AudioWorklet replacement means module loading + a new file for a debug-only tool; revisit only when a worklet exists elsewhere in the app or the tap misbehaves on a real device. (debug.js WAV export) `🟨 ⚪ ⚙M`

## 5. Architecture / maintenance

## 6. Tests & CI

Currently covered (don't lose this): practice acceptance (4 cases strict+closed-loop), practice dip gate (hold-through blocked, silence/50%-notch dips pass, 75% duck shut, legato free), practice seat across view rebuilds + zen-entry stopMelody + overlay zen-only seats, console-hygiene boot scan (4 boots; allowlist = manifest-declared tone misses), support-bracket battery incl. bit-identical melody-vs-support equivalence + Zen timing/gating, instrument load/tone-model install per manifest (incl. svgWhen id/title paths + boot diagnostics in per-leg fresh contexts), render pin (chips/grid/scroll-band/highlight/focus-restore + typed-render debounce contract), svg clone coordinates, debug panel build-on-open contract, transport scheduler arithmetic/cut-bus/lite, practice history, template safety, theme toggle, offline SW boot+swap, ac worker parity, swing grid, sr hints, spike watch (the tick hunt), the session-14 batch (wake lock lifecycle, tick-override semantics, asset-version token equality, twin-derivation byte-identity, transposer skill, practice dials), the session-15 additions (SEO shell shape + zero-per-stub JSON-LD, zen note-bar glide five-legger, suite-server teardown hardening, board-tool empty-run linting), and the session-16/16-cont. additions (track acceptance battery incl. mix ratios, hifi retune, library favorites star + readability, tests/midi_track_audit = the pure-python source-measure audit with a displaced-downbeat tripwire over tools/midi_track_audit.py), and the session-17-cont. additions (tests/tone_stages = the DEFAULT stage verification after synth-code or note-value changes — rebuilt session 18 for the twin voice: fit-row regression caps + stage windows measured on the ADOPTED handoff baseline after Robin's field ruling; instruments_load pins the twin install/uninstall shapes and waits for both model round-trips; data_validator checks the twin schema; CI installs scipy+soundfile so the fitter analysis runs there;''. **Sweep policy (Robin, 2026-09-26): the full run_all sweep runs only for sound-engine touches; data/song changes run the directly-affected suites (see AGENTS.md §12)** — full sweep 47/47 at the stage-verification commit (including tone_stages) is the last under the policy (including the new audit suite). CI = push/PR/manual, explicitly not a deploy gate. (.github/workflows/practice-tests.yml — console-hygiene + 41 suite steps + eslint + html-validate + board verify; local run-all counted 42 green on the Linux partition 2026-09-25 after the suite-server migration; earlier: 38 on 2026-09-25 session 14, 34 on session 12 — see DONE) NOTE: practice_accepts flaked ONE strict case under full-sweep load 2026-09-23, green twice standalone afterward and in the diag run — watch it, the arbiter hardening already took one such race; support_accepts flaked the same class 2026-09-24 (fixed wall-clock read window vs audio-clock lag under sweep CPU contention) and got the class cure: the read is now a real rendezvous with wall-fire stamps + ctx snapshots `335c4b4`). **Third member 2026-09-25 (CLI run `36110497803`, job 107992645371): practice_dip's leg A stalled the full 15 s timeout at maxIdx 0** — same SHA the local sweep had green; a DIFFERENT injury inside the same family: the suite's rendezvous (OCA_PRACTICE+NOTES) unlocks INSIDE loadInstrument (the stretch between installFingerings and boot's tail), where fillLibrary/loadLibraryItem(home) → practiceInvalidate is still owed — a session started mid-boot died when the tail landed; the stall reproduces at will with CDP network latency, cured by the rule-13 real rendezvous: the #scale options guard (filled only by the tail; a rAF poll never resolves mid-synchronous-block) plus a state card (started/st/ix/frames) on every driver resolve so a future stall names itself. The same tail guard rode into every suite that starts practice or needs typed editor text to survive boot (practice_accepts_melody, practice_zen_return, practice_history, keyboard_widgets, render_pin); library_hardening already waited a stronger post-tail signal (the Scales OPTGROUP), instrument_switch_race covers the race as its subject, playback-only suites are immune (practiceInvalidate stops practice, never play). Full sweep 31/31 green after the cure.

## 7. Accessibility & UX

- [ ] **Field-check the game arrangement (Audible-behavior hold — Robin's ears decide)** — the Outset corpus is now ONE version: `outset-island-midi` = "Outset Island (arrangement)" (melody + `#track bass audible 50` + the derived `#track contrabass audible 75`; the with-bass trio, its up12 twin and the bassline solo retired before deploy); his pass names: the plain-view balance (bass/contra levels vs the melody at 50/75), the contra register choice (the game sub-bass +12 reading), the ♭ chord labels in the sheet's caps styling, the loop seam (the closing vamp into the opening one), and whether the layers stay audible INSIDE an active practice session (today they play; the tuner-deafening worry stands). `🟧 🔴 ⚙S`

## 8. Housekeeping

Nothing open — completed housekeeping is archived in `plans/DONE.md` §8.

## 9. Functional ideas (features)

- [ ] **Standardize shipped songs to the `skills/ocarina-melodies` conventions** (barline at wrap start, named sections where players want headers) — HELD for Robin's later-stage pass; verify/shipped_songs are the gates; no playback changes expected. `🟢 ⚪ ⚙M`

- [ ] **Library search / pinning widening** — favorites pinning SHIPPED 2026-09-26 `390c431` (star + first persisted Favorites group); the widening (search box, reordering beyond the pin, grouping options) stays parked until Robin elects it. `🟢 ⚪ ⚙S`

- [ ] **Per-song landing maintenance (the permalink residue)** — new shipped songs follow the frozen URL grammar (tests/shipped_songs pins slugs + suffix chain; tests/gen_pages boots the stub set + seed ladder); per-song `intended` values plant on Robin's word; the sitemap set stays frozen-permanent; nothing else opens here. `🟢 ⚪ ⚙S`

> **Idle idea pool: `plans/IDEAS.txt`.** A live document Robin edits over time and ROBIN'S ALONE — the AI never writes it (it may be read, and only lifted into TODO.md when Robin explicitly asks). TODO carries no copy or summary: when an idea from it is picked up, read the FILE fresh at that moment; never rely on a remembered or transcribed version.

---

## Session log

(Older entries live in `plans/DONE.md` (session log). New entries below — retire via `python tools/board.py log-retire` once another session has opened from them.)

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
  ranch contrabass; note the `sarias-song-bass` DERIVE instead shifts its
  whole body one octave down (library.js deriveBody moves track rows with the
  melody), so Saria's bass-version contrabass sits at E2-G#2 while the alto
  version's sits at E3-G#3 — his ears decide if that asymmetry stands.
