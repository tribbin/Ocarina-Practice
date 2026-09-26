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
(refreshed 2026-09-26, session 15 cont.: Robin's interactive panel answered
the whole dependence board — nine items left it, three builds shipped same
night; what remains is measurement/planting work and his eyeballs):

| Item | Section |
|---|---|
| **Robin's field check on the multi-track trio** — `outset-island-with-bass` now plays melody + audible bass groove (the bassline two octaves down) + contrabass root-holds; his ears name the balance, the contrabass register, the practice-session audibility and the groove's final-bar cut | §7 |
| **Robin's eyeball pass** on the panel builds: the HiFi retune batch (`?hifi` — amber buttons, dark segment row/select, deeper zen red, LED fills) and the favorites stars in the library — his values, built to spec; he retunes anything that reads off | feel checks |
| The tone.json measurement/fitting work per chamber (Robin's instrument data; the loader treats missing files as "no data yet") | §1 |
| The next audio-tick field catch names itself (spike cards carry the ambient ring); Robin re-introduces the hunt when the ticks matter | DONE (re-openable) |
| Shipped-songs standardization stays HELD for Robin's later-stage pass; the permalinks corpora ride his planting as always | §9 |
| Library widening (search, reordering beyond the pin) stays parked until Robin elects it | §9 |

---

## 1. Bugs (correctness / data loss)

- [ ] **Measure and fit the chambers** — Robin records tone.json per chamber (stein-double-alto-c, oot-alto-c-12, ico-contrabass-11-c declare the field ahead of data; missing files read as "no data yet"); each fitting feeds the tone engine, maybe dropping very-low-dB harmonics later. Robin's hands-on work as he gets time. `🟩 ⚪ ⚙L`

## 2. Robustness / error handling

## 3. Security (low today — matters if data files become user-supplied)

## 4. Performance

- [ ] **Deprecated createScriptProcessor for WAV export** — also taps the reverb bus into a second destination chain, so the dry bus sounds at limiter-bypassed level during capture (debug-only). **Reframed ⚪ backlog**: the AudioWorklet replacement means module loading + a new file for a debug-only tool; revisit only when a worklet exists elsewhere in the app or the tap misbehaves on a real device. (debug.js WAV export) `🟨 ⚪ ⚙M`

## 5. Architecture / maintenance

## 6. Tests & CI

Currently covered (don't lose this): practice acceptance (4 cases strict+closed-loop), practice dip gate (hold-through blocked, silence/50%-notch dips pass, 75% duck shut, legato free), practice seat across view rebuilds + zen-entry stopMelody + overlay zen-only seats, console-hygiene boot scan (4 boots; allowlist = manifest-declared tone misses), support-bracket battery incl. bit-identical melody-vs-support equivalence + Zen timing/gating, instrument load/tone-model install per manifest (incl. svgWhen id/title paths + boot diagnostics in per-leg fresh contexts), render pin (chips/grid/scroll-band/highlight/focus-restore + typed-render debounce contract), svg clone coordinates, debug panel build-on-open contract, transport scheduler arithmetic/cut-bus/lite, practice history, template safety, theme toggle, offline SW boot+swap, ac worker parity, swing grid, sr hints, spike watch (the tick hunt), the session-14 batch (wake lock lifecycle, tick-override semantics, asset-version token equality, twin-derivation byte-identity, transposer skill, practice dials), the session-15 additions (SEO shell shape + zero-per-stub JSON-LD, zen note-bar glide five-legger, suite-server teardown hardening, board-tool empty-run linting), and the session-16/16-cont. additions (track acceptance battery incl. mix ratios, hifi retune, library favorites star + readability, tests/midi_track_audit = the pure-python source-measure audit with a displaced-downbeat tripwire over tools/midi_track_audit.py). **Sweep policy (Robin, 2026-09-26): the full run_all sweep runs only for sound-engine touches; data/song changes run the directly-affected suites (see AGENTS.md §12)** — full sweep 46/46 was the last before the policy (including the new audit suite). CI = push/PR/manual, explicitly not a deploy gate. (.github/workflows/practice-tests.yml — console-hygiene + 41 suite steps + eslint + html-validate + board verify; local run-all counted 42 green on the Linux partition 2026-09-25 after the suite-server migration; earlier: 38 on 2026-09-25 session 14, 34 on session 12 — see DONE) NOTE: practice_accepts flaked ONE strict case under full-sweep load 2026-09-23, green twice standalone afterward and in the diag run — watch it, the arbiter hardening already took one such race; support_accepts flaked the same class 2026-09-24 (fixed wall-clock read window vs audio-clock lag under sweep CPU contention) and got the class cure: the read is now a real rendezvous with wall-fire stamps + ctx snapshots `335c4b4`). **Third member 2026-09-25 (CLI run `36110497803`, job 107992645371): practice_dip's leg A stalled the full 15 s timeout at maxIdx 0** — same SHA the local sweep had green; a DIFFERENT injury inside the same family: the suite's rendezvous (OCA_PRACTICE+NOTES) unlocks INSIDE loadInstrument (the stretch between installFingerings and boot's tail), where fillLibrary/loadLibraryItem(home) → practiceInvalidate is still owed — a session started mid-boot died when the tail landed; the stall reproduces at will with CDP network latency, cured by the rule-13 real rendezvous: the #scale options guard (filled only by the tail; a rAF poll never resolves mid-synchronous-block) plus a state card (started/st/ix/frames) on every driver resolve so a future stall names itself. The same tail guard rode into every suite that starts practice or needs typed editor text to survive boot (practice_accepts_melody, practice_zen_return, practice_history, keyboard_widgets, render_pin); library_hardening already waited a stronger post-tail signal (the Scales OPTGROUP), instrument_switch_race covers the race as its subject, playback-only suites are immune (practiceInvalidate stops practice, never play). Full sweep 31/31 green after the cure.

## 7. Accessibility & UX

- [ ] **Field-check the multi-track build (Audible-behavior hold — Robin's ears decide)** — the trio now ships in `outset-island-with-bass` (melody + `#track bass audible` groove = the bassline two octaves down + `#track contrabass audible` root-holds re-projected from the old drone map); his pass names: the plain-view balance (bass/contrabass levels vs the melody), the contrabass register choice, the groove's final-bar cut at the melody's half-bar finale (bus fade), and whether the groove should stay audible INSIDE an active practice session (today it plays; the tuner-deafening worry is the reason supports stay Zen-only). Plus the NEW comparison twin `outset-island-midi` (melody + the full arrangement's bass re-read measure-by-measure — his rotation catch is fixed, bar 33 ≡ bar 7 now byte-true; tools/midi_track_audit.py --check is the gate): his ears A/B it against the with-bass trio for which bass read plays, and confirm the new loop seam (the finale now completes to four beats with both supports continuing — the closing vamp runs straight into the opening one). `🟧 🔴 ⚙S`

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
