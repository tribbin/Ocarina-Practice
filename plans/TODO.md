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
| **Robin's eyeball pass** on the panel builds: the HiFi retune batch (`?hifi` — amber buttons, dark segment row/select, deeper zen red, LED fills) and the favorites stars in the library — his values, built to spec; he retunes anything that reads off | feel checks |
| The tone.json measurement/fitting work per chamber (Robin's instrument data; the loader treats missing files as "no data yet") | §1 |
| The next audio-tick field catch names itself (spike cards carry the ambient ring); Robin re-introduces the hunt when the ticks matter | DONE (re-openable) |
| Shipped-songs standardization stays HELD for Robin's later-stage pass; the permalinks corpora ride his planting as always | §9 |
| Library widening (search, reordering beyond the pin) stays parked until Robin elects it | §9 |

---

## 1. Bugs (correctness / data loss)

- [ ] **tone.json declared but absent — INTENTIONAL, not a bug** — instruments.json lists `tone` paths for stein-double-alto-c, oot-alto-c-12, ico-contrabass-11-c: Robin is going to measure/tune every ocarina chamber; until each tone.json is recorded the loader treats the 404 as "no data yet" (correct behaviour). REWORDED instruments/README.md to say entries may declare the field ahead of measurements ✅ 2026-09-22 `9cfccfb`. **Opens instead: the actual measurement/fitting work per chamber.** `🟩 ⚪ ⚙L`

## 2. Robustness / error handling

## 3. Security (low today — matters if data files become user-supplied)

## 4. Performance

- [ ] **Deprecated createScriptProcessor for WAV export** — also taps the reverb bus into a second destination chain, so the dry bus sounds at limiter-bypassed level during capture (debug-only). **Reframed ⚪ backlog**: the AudioWorklet replacement means module loading + a new file for a debug-only tool; revisit only when a worklet exists elsewhere in the app or the tap misbehaves on a real device. (debug.js WAV export) `🟨 ⚪ ⚙M`

## 5. Architecture / maintenance

## 6. Tests & CI

Currently covered (don't lose this): practice acceptance (4 cases strict+closed-loop), practice dip gate (hold-through blocked, silence/50%-notch dips pass, 75% duck shut, legato free), practice seat across view rebuilds + zen-entry stopMelody + overlay zen-only seats, console-hygiene boot scan (4 boots; allowlist = manifest-declared tone misses), support-bracket battery incl. bit-identical melody-vs-support equivalence + Zen timing/gating, instrument load/tone-model install per manifest (incl. svgWhen id/title paths + boot diagnostics in per-leg fresh contexts), render pin (chips/grid/scroll-band/highlight/focus-restore + typed-render debounce contract), svg clone coordinates, debug panel build-on-open contract, transport scheduler arithmetic/cut-bus/lite, practice history, template safety, theme toggle, offline SW boot+swap, ac worker parity, swing grid, sr hints, spike watch (the tick hunt), the session-14 batch (wake lock lifecycle, tick-override semantics, asset-version token equality, twin-derivation byte-identity, transposer skill, practice dials), and the session-15 additions (SEO shell shape + zero-per-stub JSON-LD, zen note-bar glide five-legger, suite-server teardown hardening, board-tool empty-run linting). CI = push/PR/manual, explicitly not a deploy gate. (.github/workflows/practice-tests.yml — console-hygiene + 41 suite steps + eslint + html-validate + board verify; local run-all counted 42 green on the Linux partition 2026-09-25 after the suite-server migration; earlier: 38 on 2026-09-25 session 14, 34 on session 12 — see DONE) NOTE: practice_accepts flaked ONE strict case under full-sweep load 2026-09-23, green twice standalone afterward and in the diag run — watch it, the arbiter hardening already took one such race; support_accepts flaked the same class 2026-09-24 (fixed wall-clock read window vs audio-clock lag under sweep CPU contention) and got the class cure: the read is now a real rendezvous with wall-fire stamps + ctx snapshots `335c4b4`). **Third member 2026-09-25 (CLI run `36110497803`, job 107992645371): practice_dip's leg A stalled the full 15 s timeout at maxIdx 0** — same SHA the local sweep had green; a DIFFERENT injury inside the same family: the suite's rendezvous (OCA_PRACTICE+NOTES) unlocks INSIDE loadInstrument (the stretch between installFingerings and boot's tail), where fillLibrary/loadLibraryItem(home) → practiceInvalidate is still owed — a session started mid-boot died when the tail landed; the stall reproduces at will with CDP network latency, cured by the rule-13 real rendezvous: the #scale options guard (filled only by the tail; a rAF poll never resolves mid-synchronous-block) plus a state card (started/st/ix/frames) on every driver resolve so a future stall names itself. The same tail guard rode into every suite that starts practice or needs typed editor text to survive boot (practice_accepts_melody, practice_zen_return, practice_history, keyboard_widgets, render_pin); library_hardening already waited a stronger post-tail signal (the Scales OPTGROUP), instrument_switch_race covers the race as its subject, playback-only suites are immune (practiceInvalidate stops practice, never play). Full sweep 31/31 green after the cure.

## 7. Accessibility & UX

## 8. Housekeeping

Nothing open — completed housekeeping is archived in `plans/DONE.md` §8.

## 9. Functional ideas (features)

- [ ] **Standardize shipped songs to the conventions in `skills/ocarina-melodies/SKILL.md`** — barline at the START of wrapped lines (cosmetic; parser reads `|` positionally today, so all shipped bodies bar-at-line-end parse identically), named sections where players want headers, per-song house conventions. Robin plants this as a later-stage pass — "very useful to players." Use verify/shipped_songs suites as gates; no playback changes expected. 2026-09-24: Robin confirmed this stays HELD for its later-stage pass — the hands-off night does not touch shipped song bodies; revisit when he wants it. `🟢 ⚪ ⚙M`

- [ ] **Library search / favorites / pinning** — flat dropdown gets unwieldy as personal library grows. Favorites SHIPPED 2026-09-26 `390c431`; the remaining widening (search, moving/reordering beyond the pin, grouping options) stays parked until Robin elects it — the favorites slice answered its own demand for now. `🟢 🟡 ⚙M`

- [ ] **Search-engine perma-links BEFORE the Switch-2 OoT launch (November)** — lifted from IDEAS 2026-09-24 and refined with Robin's rules: per-song landing URLs where "content may change, but the link must serve what the crawl expected". URL shape locked 2026-09-24: **`/song/<category>/<base-slug>`**, default player **12-hole C alto**, category (zelda/scales/other, normalized from group; "on Bass"/"on Alto" collapse) keys per-category theming (zelda → Hyrule, else Plain/new). Progress: (✅ 2026-09-24) **slug freeze enforced** — closed suffix list + chain rule + grammar in `tests/shipped_songs.py` (CI fails on violating keys), the `-alt`/`-alto` split fixed pre-index (`major-alto`, `chromatic-alto`), the contract documented in `skills/ocarina-melodies/SKILL.md`; (✅ 2026-09-24) **serving layer built + live-boot corrected** — `tools/gen_song_pages.py` emits shell-only landing stubs per base slug: canonical + og:url on the site-prefix path, single song-specific description, `?song=<key>&inst=<chosen>` pre-boot seed, hidden/variants excluded, byte-deterministic, staging git-ignored; the LIVE URL check on the first deployed stub caught the generator-class defect string tests missed — the app's runtime fetches (`songs.json`/`instruments.json`/css text/manifest-driven instrument files; even the SW registration) resolve relative to the PAGE and 404'd two directories deep, killing boot — fixed with a `<base href="{site-prefix}/">` injection (root-absolute `/…` rejected in review: bakes the prefix everywhere, breaks relocatability, and cannot reach runtime fetches without app changes); the landing default became Robin's corrected LADDER — best-fit by 12-hole > double alto C > triple bass C > contrabass (Song of Time's bass body lands on the triple; every stub boots playable, no range marks) — and `tests/gen_pages.py` upgraded to a real-boot leg: the staging tree assembled exactly like the deploy workflow's allowlist, served under the /Ocarina-Practice mount, boot asserted for right song/right ocarina/zero out-of-range chips/rendered sheet/one description/clean console (allowlist semantics: every 404 must BE a tone.json; a healthy boot can legitimately have NO 404s — the triple's tone.json exists); `.github/workflows/deploy-site.yml` publishes on served-content path pushes + manual dispatch; (✅ 2026-09-24 `89a39f0`) **og/meta card stage complete** — og:type/og:site_name/og:description (same wording as the meta description, one description per page holds) + og:image riding the already-generated 512 icon (width/height/alt) + summary twitter:card, injected at the END of head so the shell's charset keeps its first-KB seat; URLs stay site-prefix path form (canonical/og:url/og:image consistent; fully-absolute held until a domain is pinned); gen_pages pins every tag per stub over the still-green real-boot matrix. (✅ 2026-09-24 `e7718bc`) **domain landed + serving layer switched to it** — `ocarina-practice.com` is now the site's pinned origin (registered along the forever-perma rule; registrar and registration details stay out of this public repo on Robin's call): the deploy artifact carries a CNAME file, gen_pages gained `--site-origin` (default the domain) and now emits ABSOLUTE canonical/og:url/og:image with `<base href="/">`, the gen_pages suite re-pins every contract against a ROOT-mounted artifact; project-page serving stays reachable via the preserved --site-prefix/--site-origin-empty knobs for rollback. **Robin's manual cutover checklist (order matters):** push refactor4 → merge/deploy fires the artifact (with CNAME) → registrar DNS: CNAME record www → <github-io-user-host> (plus A/AAAA apex records if wanted) → repo Settings → Pages → custom domain = ocarina-practice.com (wait the DNS check) → enforce HTTPS once the cert provisioned → account-level Pages 'verified domains' adds + TXT-verifies the domain (the free takeover guard) → re-probe landing URLs at the domain (the boot is root-relative now — the old /Ocarina-Practice path dies by design). (next: live-domain verification of the landing matrix — his push, then this check) Remaining: richer stub content if SERP demands (thin-mass watch), absolute URLs if a domain gets pinned, sitemap.xml + robots.txt only AFTER links verify (Robin's crawl rule), Lighthouse pass, first real deploy + SERP observation. Deadline anchor: OoT Switch 2 ships in November (~5 weeks from 2026-09-24). **Decisions 2026-09-24 (refinement round):** BRANDING settled — the product STAYS "Ocarina Practice" (og:site_name already correct; no rename; the IDEAS BRANDING line is clear to delete). Domain processing still pending tonight; go-live planned tomorrow as a JOINT session — Robin's rule: the flip "has never been a success" solo, so hands-off sessions do PREP ONLY: keep this item's cutover checklist current, add a refactor4-domain (e7718bc) diff summary of what merging brings, and build live-verify tooling. SEO feature stages (robots/sitemap) are POST-switch work — and Robin's correction: the permalink contract does not become LIVE until go-live WITH robots.txt in place; nothing is crawlable before that moment, so slug/staging prep carries no permalink risk — the robots.txt push itself stays the final invite act, only after the live boot verifies. ﻿Night prep 2026-09-25 (away session, prep only by tonight's rules): - **Merge surface** â€” refactor4-domain is ONE commit (`e7718bc` over `c96965a`) touching `.github/workflows/deploy-site.yml`, new `CNAME`, `README.md`, `tests/gen_pages.py`, `tools/gen_song_pages.py`; zero overlap with what refactor4 merged (js/*, AGENTS.md, plans/) â€” clean merge expected. - **Checklist currency** â€” Robin's cutover checklist (above) stands unchanged; a push of tonight's `session5` stack also fires the artifact (served-content path trigger), so "push â†’ merge/deploy" may run BEFORE his joint session touches DNS â€” the order of DNS/Pages/HTTPS steps is unaffected. - **Live-verify tooling built + used**: `tools/verify_site.py --origin <base> [--boot N]` (not a CI step; read-only GETs). Checks: shell serves the js/app.js module entry; deployed songs.json readable; every landing stub 200 with base href / canonical / og:url agreeing on the ONE serving prefix (base href from the origin's path, so both stages hold), og:title + description present; `--boot N` boots sampled stubs (song-of-time always) in fresh contexts (SW second-navigation lesson), zero console noise beyond the manifest-declared-absent tone.json 404s, right song on the right ocarina by the ladder. - **Pre-flip state recorded**: today started on a STALE artifact (home shell predated the PWA commit: no serviceWorker string, no og on the shell) while /song/ stubs served the permalink contracts; a fresh push-triggered Actions deploy during the night refreshed the artifact, and the full probe ran GREEN before the flip (18 checks, 8/8 stubs booted clean at /Ocarina-Practice). - **Tomorrow**: same command with `--origin https://ocarina-practice.com` is the post-flip acceptance gate â€” absolute canonical/og + root `<base href="/">` + CNAME artifact; the /Ocarina-Practice mount dies by design. Flip landed by Robin's hand on main (`a2a081d`, PR #10 merge; deploy run `36117318574` green 1m54s): the domain serves the OLD artifact — seed tests red, and the verify gate names why: all 8 stubs carry `<base href="/Ocarina-Practice/">` while the domain serves at root (the workflow baked the pre-flip mount), so every runtime fetch 404s and no stub boots; robots.txt and sitemap.xml absent (not yet stage-built). The domain-switch unit closes it: workflow passes `--site-prefix /` + `--origin https://ocarina-practice.com`; the generator emits sitemap.xml (home + every stub URL, byte-deterministic, no lastmod) and an absolute og:image (og:image must be absolute; the flip pinned the origin — canonical/og:url stay origin-relative so the artifact stays mount-agnostic); robots.txt committed, timeless per Robin (no automation commentary facing the web); gen_pages mirrors ROOT serving now (old project-page mount pinned by a string-contract leg, retires with the stage); verify_site gains the robots+sitemap live legs. Sweep 31/31 + gen_pages re-run after the robots rewrite. POST-FLIP GATE GREEN (2026-09-25, merge `4f44099`, deploy run `36125302883`): 20 live checks pass against https://ocarina-practice.com — all 8 stubs boot the right song on the right ocarina at prefix `/`, robots.txt + sitemap.xml serve and enumerate home + exactly the stub set. Per Robin's rule the permalink contract is LIVE from this moment (go-live + robots.txt). The URLs/dates/etc on the served artifact are by-design: canonical/og:url origin-relative (mount-agnostic), og:image absolute, robots.txt timeless Robin-edited. REMAINING on the item: Lighthouse pass; first SERP observation (weeks — November Switch-2 anchor); Robin's Search Console domain verification + sitemap submission (his Google account, manual). The "sitemap.xml + robots.txt only AFTER links verify (Robin's crawl rule)" row is DONE by this gate; the legacy project-page mount string-leg in gen_pages now awaits its stage's retirement. On the IDEAS lifts Robin green-lit while selecting: perma-link landing navigation semantics (switches leave the deep path — root + ?vars; title click → root) and the info-screen issues link — both lifted as new §9/§7 items. **Lighthouse pass 2026-09-25 (`b023394`, session12 — live home re-audit on redeploy; stub set not passed)**: mobile P80 / A11y 100 / BP 96 / SEO 100, desktop P99; landed fixes: passive token-touch listeners (ui.js wireTokenTouch — nothing preventDefaults there, drift intends the scroll), critical paint gate inline in index.html (UA 8px body margin + the 0.67em h1 margin collapsing through the pre-CSS body = the phone flash), .inst-sel width reserved ≤760px so the late-filling instrument list cannot balloon the header — the exact 0.352 CLS shift reproduced headlessly under real throttling then driven out, local re-run has no CLS findings (expect live P to rise on redeploy). REPORT-ONLY residuals: piano block still grows ~92px late in boot (residual CLS 0.089, inside the green band — a reservation is a piano-look call, Robin's), the manifest-declared-absent tone.json 404 console error (§1's intentional state, no action), themeBtn accessible-name vs visible-text mismatch (the HiFi menu unit rewrites that button anyway), Pages 600 s cache TTL (hosting default; SW covers re-visits), unminified JS/CSS (the IDEAS minify-on-deploy line, not lifted). Robin 2026-09-25: the domain is now Search-Console-verified — a crawler is expected soonish — and the existing sitemap URLs count as PERMANENT from today: no rekeys, no path renames; the kokiri leaf-URL retirement predates the pin and was the last move of its kind Live Lighthouse re-check 2026-09-25 post-deploy (session 13, headless, Lighthouse 12): mobile perf 95 (was 80) with CLS 0 (was 0.352 — the inst-sel ballooning fix held through deploy), A11y 100 / BP 96 / SEO 100; desktop perf 99 with the same 100s; BP's 96 is the expected vintage tone.json 404 (oot-alto-c-12, the manifest-declared-absent allowlist class), A11y's quiet nit is #themeBtn's label-content-name-mismatch, and perf's drag is the render-blocking stylesheet (mobile LCP 2.5 s, speed-index 0.79) — the same CSS-addressing seam Robin's fresh-refresh IDEAS entry describes `🟨 🟠 ⚙M`

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
