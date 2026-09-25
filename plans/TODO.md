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
(refreshed 2026-09-25, session 13: the two lift items shipped via PR #12 and
left the hot list; the sitemap URLs went PERMANENT with Search Console
verified — redirect correctness is the hot edge; handoff prepped below):

| Item | Section |
|---|---|
| Deep-link instrument change must redirect to root+vars (field defect §1; reproduce on a live /song/ stub first) + SEO-guides audit opener (read IDEAS' two Google docs, report what applies) — the crawler is coming | §1 / §9 |
| Audio-tick spike detector per §2's detection plan (debug-only instrumentation; the next field tick then names its own seam) | §2 |
| Small app units from IDEAS: CSS fresh-on-release (version the css URL; it is also perf's render-blocking drag), tick-override semantics (semantics written in IDEAS) | IDEAS |
| §9 decisions waiting on Robin: octave-twin dedup verdict (5 proven + 3 shift-derivable; kokiri stray token needs his eyes), transpose text-vs-token fork, recording / library search when he wants them | §9 |
| Feel checks on his phone/device: HiFi retune knobs (?hifi), tuner ✕/mic glyph, history-line clarity, token-chips touch feel; small-screens brainstorm when he's near (wake-lock play+practice CONFIRMED live 2026-09-25 — screen stayed awake; wake-lock's held check closes) | feel checks |

---

## 1. Bugs (correctness / data loss)

- [ ] **tone.json declared but absent — INTENTIONAL, not a bug** — instruments.json lists `tone` paths for stein-double-alto-c, oot-alto-c-12, ico-contrabass-11-c: Robin is going to measure/tune every ocarina chamber; until each tone.json is recorded the loader treats the 404 as "no data yet" (correct behaviour). REWORDED instruments/README.md to say entries may declare the field ahead of measurements ✅ 2026-09-22 `9cfccfb`. **Opens instead: the actual measurement/fitting work per chamber.** `🟩 ⚪ ⚙L`


## 2. Robustness / error handling

- [ ] **Sporadic single-frame audio "ticks" — one waveform jump per tick, and the CURRENT note goes silent after it** — Robin field notes 2026-09-24: ticks on Windows AND on his phone, on the phone even with the Lite voice (rules OUT node-count/CPU pressure), the perf screen's glitch counter never fires for them (it counts audio-clock-vs-wall lag at a 0.3 s criterion, audio.js:352 — a sample-plane discontinuity never gets near it), "after such a tick, the current note seems silenced", sporadic with no identified trigger yet. Class read: this is a RENDERED-SIGNAL discontinuity, not starvation — prime suspects: (1) AudioParam event-timeline re-anchoring of a LIVE envelope: a later linearRamp's implicit anchor or a `cancelScheduledValues` path restamp the running gain to a stale event value → one step (the tick) plus a dead envelope remainder (the silenced note) — the neighborhoods audio.js:1131-1133 (non-melody bag fade) and 1671-1673 (live/hover rampFades) plus the documented implicit-event hazard (~audio.js:1363); this exact neighborhood has real-device history — cancelAndHoldAtTime "popped on real hardware" and was engineered out; (2) the DynamicsCompressor limiter pumping at multi-voice seams; (3) zen mono↔stereo anchor/pan events; (4) device-level (Windows shared-mode WASAPI) — least likely given lite-invariance. Detection plan: a debug-only spike detector on the perfAnalyser time-domain tap (single-frame |Δx| > K·system-RMS, with the markSystemSound onset/stop windows subtracted) logging timestamp + a state card (in-flight onsets, retire window, tempo move, zen in/out, lite flag) to the perf panel + OCA_DEBUG; the next field tick then names its own automation seam. **Field answers 2026-09-24:** playback CONTINUES at the next note after the silenced one → voice-seam class confirmed, context/device death ruled out; the same song does NOT reproduce consistently across replays → a timing race at event collation, not a per-note mapping error; observed on MAIN (pre-existing shipped behavior, independent of the refactor4 chain); repro rate ~every 2 playbacks of Concerning Hobbits short in Google Chrome, NOT reproducible in VS Code's embedded browser (engine-timing sensitive — different Chromium build, different event-alignment odds). (✅ 2026-09-24 `17fae24`) **the spike watch detector landed** (test-first, `tests/spike_watch.py` in CI): a pure two-shape classifier (ONE delta to a new sustained level — the jump-to-silence that kills the note — or a mirrored up-then-down pair for the single-sample excursion; N-adjacent above-threshold deltas = ramp class, rejected) reads the post-limiter analyser every 20 ms (overlapping 23 ms windows, full coverage), the markSystemSound onset/stop windows subtracted, each hit logged as a state card (audio-clock t, jump size, 96th-grid melody position, lite flag, recent playNoteAt onsets from a new ring) on the perf panel's new 'Signal spikes (ticks)' row plus a throttled console warn; `spikeFake()` lets suites probe the row; sw VERSION → v4. **Next field catch now names its own seam** — Robin reproduces in Chrome, the row/card + console line identifies the automation neighborhood; the fix itself stays held for the evidence. **Field evidence lifted from IDEAS 2026-09-24:** on the phone the three perf counters stay at 0 while ticks happen — now described as MULTIPLE consecutive ticks, not yet a buzz — and a screen-orientation flip ALWAYS triggers them ("seems related to the visual processing"); not reproducible on the Windows desktop as of now (earlier Windows reports stand, so repro availability drifts by device/build). Robin's open questions: can background visuals freeze in Zen (and Zen visuals in normal)? Can audio be prioritized over visuals? Would pre-calculating waveforms on song selection even help (this ties the IDEAS PERF waveform idea to the hunt)? The shipped spike watch ("Signal spikes (ticks)" perf row) has NOT yet met the phone — after his next orientation-flip session, whether THAT detector fires while the counters stay silent will itself name the plane the discontinuity lives on. 2026-09-25 56c4ae0: spike cards gain an ambient context ring beside the onsets — orientationchange (legacy + screen.orientation) and a throttled resize burst record kind+agoMs (4 s age-out), riding the state cards, the spikeFake probe and the throttled console warn; the newest field evidence (flip ALWAYS triggers, counters stay 0, ticks run) now pairs itself — a card near a flip names the seam plane, continued silence while the phone still hops proves the device level; detector-side done, the FIX stays held for the evidence. `🟧 🟠 ⚙M`

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

- [ ] **Search-engine perma-links BEFORE the Switch-2 OoT launch (November)** — lifted from IDEAS 2026-09-24 and refined with Robin's rules: per-song landing URLs where "content may change, but the link must serve what the crawl expected". URL shape locked 2026-09-24: **`/song/<category>/<base-slug>`**, default player **12-hole C alto**, category (zelda/scales/other, normalized from group; "on Bass"/"on Alto" collapse) keys per-category theming (zelda → Hyrule, else Plain/new). Progress: (✅ 2026-09-24) **slug freeze enforced** — closed suffix list + chain rule + grammar in `tests/shipped_songs.py` (CI fails on violating keys), the `-alt`/`-alto` split fixed pre-index (`major-alto`, `chromatic-alto`), the contract documented in `skills/ocarina-melodies/SKILL.md`; (✅ 2026-09-24) **serving layer built + live-boot corrected** — `tools/gen_song_pages.py` emits shell-only landing stubs per base slug: canonical + og:url on the site-prefix path, single song-specific description, `?song=<key>&inst=<chosen>` pre-boot seed, hidden/variants excluded, byte-deterministic, staging git-ignored; the LIVE URL check on the first deployed stub caught the generator-class defect string tests missed — the app's runtime fetches (`songs.json`/`instruments.json`/css text/manifest-driven instrument files; even the SW registration) resolve relative to the PAGE and 404'd two directories deep, killing boot — fixed with a `<base href="{site-prefix}/">` injection (root-absolute `/…` rejected in review: bakes the prefix everywhere, breaks relocatability, and cannot reach runtime fetches without app changes); the landing default became Robin's corrected LADDER — best-fit by 12-hole > double alto C > triple bass C > contrabass (Song of Time's bass body lands on the triple; every stub boots playable, no range marks) — and `tests/gen_pages.py` upgraded to a real-boot leg: the staging tree assembled exactly like the deploy workflow's allowlist, served under the /Ocarina-Practice mount, boot asserted for right song/right ocarina/zero out-of-range chips/rendered sheet/one description/clean console (allowlist semantics: every 404 must BE a tone.json; a healthy boot can legitimately have NO 404s — the triple's tone.json exists); `.github/workflows/deploy-site.yml` publishes on served-content path pushes + manual dispatch; (✅ 2026-09-24 `89a39f0`) **og/meta card stage complete** — og:type/og:site_name/og:description (same wording as the meta description, one description per page holds) + og:image riding the already-generated 512 icon (width/height/alt) + summary twitter:card, injected at the END of head so the shell's charset keeps its first-KB seat; URLs stay site-prefix path form (canonical/og:url/og:image consistent; fully-absolute held until a domain is pinned); gen_pages pins every tag per stub over the still-green real-boot matrix. (✅ 2026-09-24 `e7718bc`) **domain landed + serving layer switched to it** — `ocarina-practice.com` is now the site's pinned origin (registered along the forever-perma rule; registrar and registration details stay out of this public repo on Robin's call): the deploy artifact carries a CNAME file, gen_pages gained `--site-origin` (default the domain) and now emits ABSOLUTE canonical/og:url/og:image with `<base href="/">`, the gen_pages suite re-pins every contract against a ROOT-mounted artifact; project-page serving stays reachable via the preserved --site-prefix/--site-origin-empty knobs for rollback. **Robin's manual cutover checklist (order matters):** push refactor4 → merge/deploy fires the artifact (with CNAME) → registrar DNS: CNAME record www → <github-io-user-host> (plus A/AAAA apex records if wanted) → repo Settings → Pages → custom domain = ocarina-practice.com (wait the DNS check) → enforce HTTPS once the cert provisioned → account-level Pages 'verified domains' adds + TXT-verifies the domain (the free takeover guard) → re-probe landing URLs at the domain (the boot is root-relative now — the old /Ocarina-Practice path dies by design). (next: live-domain verification of the landing matrix — his push, then this check) Remaining: richer stub content if SERP demands (thin-mass watch), absolute URLs if a domain gets pinned, sitemap.xml + robots.txt only AFTER links verify (Robin's crawl rule), Lighthouse pass, first real deploy + SERP observation. Deadline anchor: OoT Switch 2 ships in November (~5 weeks from 2026-09-24). **Decisions 2026-09-24 (refinement round):** BRANDING settled — the product STAYS "Ocarina Practice" (og:site_name already correct; no rename; the IDEAS BRANDING line is clear to delete). Domain processing still pending tonight; go-live planned tomorrow as a JOINT session — Robin's rule: the flip "has never been a success" solo, so hands-off sessions do PREP ONLY: keep this item's cutover checklist current, add a refactor4-domain (e7718bc) diff summary of what merging brings, and build live-verify tooling. SEO feature stages (robots/sitemap) are POST-switch work — and Robin's correction: the permalink contract does not become LIVE until go-live WITH robots.txt in place; nothing is crawlable before that moment, so slug/staging prep carries no permalink risk — the robots.txt push itself stays the final invite act, only after the live boot verifies. ﻿Night prep 2026-09-25 (away session, prep only by tonight's rules): - **Merge surface** â€” refactor4-domain is ONE commit (`e7718bc` over `c96965a`) touching `.github/workflows/deploy-site.yml`, new `CNAME`, `README.md`, `tests/gen_pages.py`, `tools/gen_song_pages.py`; zero overlap with what refactor4 merged (js/*, AGENTS.md, plans/) â€” clean merge expected. - **Checklist currency** â€” Robin's cutover checklist (above) stands unchanged; a push of tonight's `session5` stack also fires the artifact (served-content path trigger), so "push â†’ merge/deploy" may run BEFORE his joint session touches DNS â€” the order of DNS/Pages/HTTPS steps is unaffected. - **Live-verify tooling built + used**: `tools/verify_site.py --origin <base> [--boot N]` (not a CI step; read-only GETs). Checks: shell serves the js/app.js module entry; deployed songs.json readable; every landing stub 200 with base href / canonical / og:url agreeing on the ONE serving prefix (base href from the origin's path, so both stages hold), og:title + description present; `--boot N` boots sampled stubs (song-of-time always) in fresh contexts (SW second-navigation lesson), zero console noise beyond the manifest-declared-absent tone.json 404s, right song on the right ocarina by the ladder. - **Pre-flip state recorded**: today started on a STALE artifact (home shell predated the PWA commit: no serviceWorker string, no og on the shell) while /song/ stubs served the permalink contracts; a fresh push-triggered Actions deploy during the night refreshed the artifact, and the full probe ran GREEN before the flip (18 checks, 8/8 stubs booted clean at /Ocarina-Practice). - **Tomorrow**: same command with `--origin https://ocarina-practice.com` is the post-flip acceptance gate â€” absolute canonical/og + root `<base href="/">` + CNAME artifact; the /Ocarina-Practice mount dies by design. Flip landed by Robin's hand on main (`a2a081d`, PR #10 merge; deploy run `36117318574` green 1m54s): the domain serves the OLD artifact — seed tests red, and the verify gate names why: all 8 stubs carry `<base href="/Ocarina-Practice/">` while the domain serves at root (the workflow baked the pre-flip mount), so every runtime fetch 404s and no stub boots; robots.txt and sitemap.xml absent (not yet stage-built). The domain-switch unit closes it: workflow passes `--site-prefix /` + `--origin https://ocarina-practice.com`; the generator emits sitemap.xml (home + every stub URL, byte-deterministic, no lastmod) and an absolute og:image (og:image must be absolute; the flip pinned the origin — canonical/og:url stay origin-relative so the artifact stays mount-agnostic); robots.txt committed, timeless per Robin (no automation commentary facing the web); gen_pages mirrors ROOT serving now (old project-page mount pinned by a string-contract leg, retires with the stage); verify_site gains the robots+sitemap live legs. Sweep 31/31 + gen_pages re-run after the robots rewrite. POST-FLIP GATE GREEN (2026-09-25, merge `4f44099`, deploy run `36125302883`): 20 live checks pass against https://ocarina-practice.com — all 8 stubs boot the right song on the right ocarina at prefix `/`, robots.txt + sitemap.xml serve and enumerate home + exactly the stub set. Per Robin's rule the permalink contract is LIVE from this moment (go-live + robots.txt). The URLs/dates/etc on the served artifact are by-design: canonical/og:url origin-relative (mount-agnostic), og:image absolute, robots.txt timeless Robin-edited. REMAINING on the item: Lighthouse pass; first SERP observation (weeks — November Switch-2 anchor); Robin's Search Console domain verification + sitemap submission (his Google account, manual). The "sitemap.xml + robots.txt only AFTER links verify (Robin's crawl rule)" row is DONE by this gate; the legacy project-page mount string-leg in gen_pages now awaits its stage's retirement. On the IDEAS lifts Robin green-lit while selecting: perma-link landing navigation semantics (switches leave the deep path — root + ?vars; title click → root) and the info-screen issues link — both lifted as new §9/§7 items. **Lighthouse pass 2026-09-25 (`b023394`, session12 — live home re-audit on redeploy; stub set not passed)**: mobile P80 / A11y 100 / BP 96 / SEO 100, desktop P99; landed fixes: passive token-touch listeners (ui.js wireTokenTouch — nothing preventDefaults there, drift intends the scroll), critical paint gate inline in index.html (UA 8px body margin + the 0.67em h1 margin collapsing through the pre-CSS body = the phone flash), .inst-sel width reserved ≤760px so the late-filling instrument list cannot balloon the header — the exact 0.352 CLS shift reproduced headlessly under real throttling then driven out, local re-run has no CLS findings (expect live P to rise on redeploy). REPORT-ONLY residuals: piano block still grows ~92px late in boot (residual CLS 0.089, inside the green band — a reservation is a piano-look call, Robin's), the manifest-declared-absent tone.json 404 console error (§1's intentional state, no action), themeBtn accessible-name vs visible-text mismatch (the HiFi menu unit rewrites that button anyway), Pages 600 s cache TTL (hosting default; SW covers re-visits), unminified JS/CSS (the IDEAS minify-on-deploy line, not lifted). Robin 2026-09-25: the domain is now Search-Console-verified — a crawler is expected soonish — and the existing sitemap URLs count as PERMANENT from today: no rekeys, no path renames; the kokiri leaf-URL retirement predates the pin and was the last move of its kind Live Lighthouse re-check 2026-09-25 post-deploy (session 13, headless, Lighthouse 12): mobile perf 95 (was 80) with CLS 0 (was 0.352 — the inst-sel ballooning fix held through deploy), A11y 100 / BP 96 / SEO 100; desktop perf 99 with the same 100s; BP's 96 is the expected vintage tone.json 404 (oot-alto-c-12, the manifest-declared-absent allowlist class), A11y's quiet nit is #themeBtn's label-content-name-mismatch, and perf's drag is the render-blocking stylesheet (mobile LCP 2.5 s, speed-index 0.79) — the same CSS-addressing seam Robin's fresh-refresh IDEAS entry describes `🟨 🟠 ⚙M`

- [ ] **Deduplicate octave/transpose-twinned song bodies (survey first)** — Robin: "Deduplicating songs (that only differ in octave/transpose) would be a nice touch." FIRST step is tooling only (his MIDI-boundary rule: no song-data work unsupervised): a `tools/` audit that proves which songs.json variants are exact octave shifts of one another (the dummy↔stein +12 pair is the precedent — see skills/song-transposing). Report the twin classes + per-class divergence spots; then decide WITH Robin whether variants keep hand-written bodies or derive from a base body at load (keys/URLs MUST stay frozen either way — the permalink contract). ﻿Night survey 2026-09-25 (tools/audit_twins.py `33bd3fa`, report-only, no bodies touched): **5 octave twins** â€” song-of-time/-bass, song-of-storms/-bass, sarias-song/-bass, eponas-song/-bass (every -bass arrangement is its alto base's melody one octave DOWN, modulo nothing: barlines, rests, continuations, slides, durations and accents all carried over) and botw-theme/-down3 (also -12). **3 uniform non-octave twins** â€” concerning-hobbits-short/-c (shift -2), botw-theme/-bass (shift -9), botw-theme-bass/-down3 (shift -3; the two bass arrangements are a uniform -3 apart). **No other twins**: all cross pairs are NOT-ALIGNED (different token counts), and kokiri-forest-bass refuses every verdict until its stray lowercase `g4/4` token is resolved (tool refuses on unreadable shapes by construction). So: the four -bass bodies and botw's -down3 are PROVEN derivable-at-load candidates (keys/URLs stay frozen either way per the permalink contract); the three non-octave twins are shift-derivable too; kokiri is a potential fifth body once its stray token is explained â€” that one needs Robin's eyes before any claim. Kokiri held verdict resolved 2026-09-25 at 098115d: the stray lowercase g4/4 was a typo (parse.js uppercases note letters — it played identically all along); the audit now runs refusal-free across all 15 shipped songs and kokiri-forest is NOT-ALIGNED against everything (the renamed leaf is no twin), so the census stands at 8 proven twins. Robin calls 2026-09-25: DERIVE ALL 8 at load (five octave twins + three uniform non-octave shifts), keys/URLs frozen; transpose fork resolves TOKEN-LEVEL (editor text untouched, display/playback shifted). Remaining: the at-load derivation build. `🟨 🟡 ⚙M`

- [ ] **Intended-instrument per-song landing default** — Robin, IDEAS 2026-09-25: "Some songs are really not made for the alto, but were added because not many people have a bass ocarina." — `songs.json` may declare `"intended": "<instrument-id>"` on a base song; the landing seed then prefers that instrument over Robin's ladder WHEN any family member fits its chart, falling back to the ladder otherwise (a member of the family must fit: the seed never boots a dead display). SHIPPED exemplar 2026-09-25: botw-theme → ico-oak-leaf-bass-c-triple (members -bass/-down3 fit the triple; the alto base won the ladder order today; the live /song/zelda/botw-theme/ stub now seeds the bass body on the triple after merge+deploy). The data_validator owns the field (optional, string, manifest-known — sandbox v12); the gen_pages botw pin freezes the outcome (want (botw-theme-bass, triple)). REMAINING: per-song values are Robin's musical calls to plant over time — nothing else declared yet; the field changes nothing in-app (the picker stays free, the wet-switch auto-select ignores it). Robin settles the model (2026-09-25, live): BOTH instrument-tagged versions keep existing as entries (the alto-named base is the alto version; -bass named "(bass)" stays — the deletion proposal is declined), and the user lands on the intended instrument — WHEN the base declares it — via the NON-SPECIFIC (clean) URL: the base's own body needs no fit; the first family member (base first, then variants alphabetically) that fits the intended chart is the seed. No field → the ladder rules. The clean page's og/title reads the LANDED version's name (what actually plays). Do not rekey entries for this; do not strip the parenthetical tags; the field's semantics is the family walk, never a body rewrite. Second exemplar per Robin's live call (2026-09-25): the corpus had NO kokiri-forest base — the bass-c transcription sat on the leaf key kokiri-forest-bass with its own stub URL. Robin wants the non-specific URL to exist and land the bass version: the key was re-titled kokiri-forest-bass → kokiri-forest (byte-identical body; name "Kokiri Forest (bass)" — Robin explicitly kept the committed tag naming for the entry; group/tempo untouched; introduced "intended": ico-oak-leaf-bass-c-triple) so /song/zelda/kokiri-forest/ is the canonical landing — the old kokiri-forest-bass URL retires in the trial period (nothing indexed; the sitemap/stub set stays 8, the kokiri path becomes the clean one). The only kokiri reference outside data was the SKILL.md leaf example, updated in place. BotW semantics ruling stands (versions keep their keys; only the non-specific URL moves). `🟢 ⚪ ⚙S`

- [ ] **SEO guides application pass** — Robin IDEAS 2026-09-25: "Read this and apply where appropriate" — https://support.google.com/webmasters/answer/9128669 and https://developers.google.com/search/docs/fundamentals/seo-starter-guide. Opener = read-then-audit against the artifact (robots.txt/sitemap.xml/song stubs/og tabs already serving; the sitemap set is now frozen-permanent, the domain Search-Console-verified), reporting what applies (title/meta/OG policy, structured data, internal linking, crawl directives) — Robin picks the applications. `🟨 🟠 ⚙M`









> **Idle idea pool: `plans/IDEAS.txt`.** A live document Robin edits over time and ROBIN'S ALONE — the AI never writes it (it may be read, and only lifted into TODO.md when Robin explicitly asks). TODO carries no copy or summary: when an idea from it is picked up, read the FILE fresh at that moment; never rely on a remembered or transcribed version.

---

## Session log

(Older entries live in `plans/DONE.md` (session log). New entries below — retire via `python tools/board.py log-retire` once another session has opened from them.)

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
