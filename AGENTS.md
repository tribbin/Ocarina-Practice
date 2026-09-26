# AGENTS — how to behave in this repo

Rules distilled from real sessions. They override defaults — when a
situation is not covered here, the honest move is a real question, not a
guess. `plans/TODO.md` (progress/plans) and `plans/IDEAS.txt` (Robin's
scratchpad) are committed so they follow the repo across machines; this
file sits at the repo root so every session finds it first.

## Session protocol

1. **Open every session by reading `plans/TODO.md`.** Its bookkeeping is the
   board: completed items (struck, `✅ <date> <SHA>`) move at once into
   `plans/DONE.md`, the completed-work + session-log archive, so TODO.md
   carries open work only; the hot list and the latest session-log entry say
   exactly where work stands. Never trust memory over
   the board. Check `git log` too: Robin commits his own work between and
   during sessions; the branch tip is not what you left there.
2. **`plans/IDEAS.txt` is the one file the AI never writes.** It is Robin's
   live scratchpad — read it at the moment an idea is picked up; never
   transcribe or summarize it anywhere (a stale copy is a wrong copy). Lift
   an idea into TODO.md only when Robin explicitly asks.
3. **Keep the TODO current as you go, not at the end:** completed items MOVE
   into `plans/DONE.md` (struck, `✅ <date> <SHA>`) at the moment they
   complete; findings placed in their type-sections; dated
   session-log entries describe what was done. Structural board moves
   (complete/add/note/tag/log) run through `python tools/board.py`
   (`verify` lints both files' shape); prose edits stay hand-made.
   Sessions must be able to die
   at any minute without losing a thread.

## Questions: batch early, then self-sustain

4. **Everything that changes behavior is asked up front, in one batch, and
   then the session runs unattended.** Surface the questions you can see now
   AND the ones the planned work will hit later, as numbered multi-choice
   lists with a recommended pick first — free wording always allowed. Robin
   answers between his other activities (often hours later); until then the
   session makes many small commits on the answered set.
5. A new fork that was NOT in the batch gets **documented as
   "held for Robin"** and worked around — it never brews silently and never
   interrupts. Behavior changes that must be verified by field check (sound,
   feel on his device) are always "held for field check" — his play-testing
   is the deciding pass; a first audible draft he then retunes is the
   expected course, not a failure.
6. **Granted autonomy covers**: obvious defects, suite-green changes, TODO
   bookkeeping, housekeeping. **Not covered**: audible behavior, UX/design
   pivots (e.g. which surface owns which mechanism), anything where Robin's
   intent is genuinely unknown. **Away-work continuation (Robin, 2026-09-24):
   when Robin leaves the session running with an open-ended grant (at work,
   busy elsewhere), the session does not idle after one unit — it keeps
   picking up open problems from the board (respecting every held item) and
   runs until rule 18's context limit says wrap. Robin may interject on a
   break to steer: his call lands at the next natural checkpoint — the
   current unit closes out green, committed and logged before the pivot.**

## Attribution, repo hygiene, commit style

7. **Report CI runs and pushes by SHA/trigger/job only — never attribute to
   an actor.** ("Robin pushed" is out; "push at `<sha>`, job #N" is in.)
   Purchasing details (registrars, prices, shopping context) never enter
   commits, the board or docs either — this is a public repo; registration
   facts live outside Git by Robin's call (2026-09-24).
8. Pushes, merges, PRs, branch create/delete, remote cleanup: **Robin's
   operations.** Amend only your own unpushed commits, same concern only.
   **Placeholder-branch rule (Robin, 2026-09-25): a session NEVER commits —
   not even noise-free board moves — on main.** When no branch exists for
   the work at hand, the session creates or reuses a placeholder branch in
   his naming style (session6, domain-switch, …) that Robin can rename, and
   lands the unit there; main advances only by Robin's hands. A slip that
   landed on main is rewound immediately and re-landed on the placeholder
   (working-tree state preserved, `git branch -f main origin/main` to rewind
   the pointer).
9. **Commit titles:** one dense informative sentence in the repo's style —
   describe the change and why, quotable in a PR description. No emoji.
   Shipped code comments carry **no references to the local planning docs**
   (code-to-code references are fine; TODO §-refs belong in TODO.md only).
10. PR descriptions follow the canon styling and links (canon: PR #3 —
    sentence-tagged links; PR #9 is the approved second shape — `##`
    section headings with the backticked SHA linked at the sentence's end).
    Robin pastes the text; the render must be clean on the first try, so:
    - Optional one-line tagline (no heading), then section titles as PLAIN
      lines (the #3 shape; the #9 shape instead gives each section `##`).
    - Bullets in one of the two sanctioned forms — commit URLs pasted as
      REAL markdown links (current repo slug `tribbin/Ocarina-Practice`),
      never as bare text after a SHA (the unshipped drift):
      `- [<summary sentence>](<commit URL>)` (#3 canon), or
      `- <dense sentence> ([`+`<SHA>`+`](<commit URL>))` (#9).
    - No decorations beyond those two forms; no file trees, no emoji, no
      generated-with sign-offs.
    - LAST section: `Tests and infrastructure` — suites registered or
      extended with their pins, defusals, the full-sweep statement and the
      "CI runs the same suites (a health check, not a deploy gate)" line.

## Tests & verification

11. **Test-first (red→green) or pin-first for behavior changes.** No blanket
    upfront test pushes — tests are written for exactly what changes.
12. Run suites via `.venv/bin/python3 tests/<name>.py` (plain python3 has no
    playwright). **The full sweep is NOT the standard set (Robin,
    2026-09-26):** run it only when the change touches the sound engine;
    data/song/copy changes run the directly-affected suites (shipped_songs,
    the audit suite when source-mapped data changed, gen_pages for corpus
    shapes, parse_edges for grammar, lint) plus registered CI steps. **Claim
    "all green" only after running the affected suites** — never imply from
    memory. New suites/legs are registered in
    `.github/workflows/practice-tests.yml` in the same commit; the CI run is
    a health check, not a deploy gate.
13. Test-hardening lessons that cost real debugging — treat as rules:
    - Every route-doctoring leg gets its **own fresh browser context**
      (the service worker claims the second navigation and hides the routed
      responses).
    - Probes wait for the app's **real rendezvous points** (typed song's own
      title, the library tail `#scale.value`, the 200 ms debounce settle) —
      never fixed sleeps.
    - A probe reading live-card state must `setDisplayMode('single')` first;
      the boot default view has no live card.
    - Lint gates (eslint, html-validate) exist to catch editor-mid-flight
      splice casualties (a dropped object line, a duplicate `</div>`); read
      CI reds with fresh eyes before theorizing.
14. **After the HTML lint, a console-hygiene check runs in CI**
    (currently `tests/console_hygiene.py`): the page is booted for real and
    `console.error`, uncaught exceptions and unhandled rejections must be
    empty (manifest-declared-absent tone files are the allowlist — they are
    expected 404s). Its job is to fail FIRST and name the misbehavior
    plainly: when the page is sick, unit suites fail in vague ways and the
    AI burns whole stretches theorizing phantom causes while the real error
    is one console line. A boot that silently survives a later suite is
    stronger evidence than suite green when diagnosing.

## Runtime & environment facts

15. `sw.js` `VERSION` bumps whenever shipped behavior changes — stale-
    while-revalidate otherwise serves the previous cache on the first visit.
16. **Before redoing specialized research, check `skills/`** — purpose-
    specific capabilities with their own SKILL.md (midi-to-ocarina-tab,
    ocarina-melodies, wav sound-profile fitting…). They exist precisely so
    prior work is not redone; refine them in place when a session learns
    something new. The AI never writes `plans/IDEAS.txt` (Robin's
    scratchpad) — skills/ files, in contrast, are maintained documents.
17. Test suites run their own throwaway HTTP server + isolated Chromium;
    they share nothing with Robin's preview (which is `file://` — no
    service worker, ever). Verify page behavior via `python3 -m http.server`,
    never through his preview. **Headless rule (Robin, 2026-09-25): the
    session never opens a browser window on Robin's actual screen — every
    browser launch outside the test suites (Lighthouse, tools, probes)
    must carry explicit `--headless=new --disable-gpu` chrome flags;
    anything that would unavoidably show a window needs his permission
    first.**

## Commands (split per OS)

Linux partition: no system node.
- Full local sweep: `python tests/run_all.py` from the repo root, run with
  the repo's venv (`python3.13 .venv/bin/python3 tests/run_all.py` is the
  same thing; plain `python3` on this box has no playwright). Filter:
  `tests/run_all.py <substring>`.
- Lint (none-node machines): a node-22 tarball lives under `/tmp/opencode/
  node/bin` — when freshly booted/rebooted restore it:
  `curl -fsSL https://nodejs.org/dist/v22.14.0/node-v22.14.0-linux-x64.tar.xz`
  `| tar -xJf - -C /tmp/opencode/node --strip-components=1
  mkdir-p`, then `export PATH=/tmp/opencode/node/bin:$PATH` and run
  `npx --yes eslint@9 js/ && npx --yes html-validate@8 index.html`.
  CI runs the exact same two commands (GitHub runner), so the pinned
  versions match whatever CI runs.
- One-time suite bootstrap: `python -m venv .venv` (if absent) then
  `.venv/bin/pip install playwright && .venv/bin/playwright install
  --with-deps chromium` (mirrors the CI step).
- Verify app changes by hand: `python3 -m http.server` from the repo root,
  then a normal browser tab (never Robin's file:// preview).

Windows (partition):
- Interpreter: Store Python resolves as `python` (also `python3`) — the
  `py` launcher does NOT exist on this box; say "python" everywhere on
  this machine.
- Full local sweep: `.venv\Scripts\python.exe tests\run_all.py` from the
  repo root (system python lacks playwright; the runner is pure python
  and prints PASS/FAIL per suite).
- Standalone single-suite run (not via the runner): set UTF-8 stdio
  first — PowerShell `$env:PYTHONUTF8="1"` — or musical-math prints like
  `≡` crash on cp1252 consoles (the runner already does this for its
  children).
- Lint: a system Node exists (node 24 local; CI pins node 22, but npx
  pins the same eslint@9/html-validate@8 majors): `npx --yes eslint@9
  js/ && npx --yes html-validate@8 index.html` is identical to CI.
- CI failure checks (gh is installed on this partition; one query, never
  a long silent watch): on a red or suspicious run, report by
  SHA/trigger/job (attribution rule) and read what actually failed with
  `gh run view <run-id> --log-failed` (fresh eyes over the real log, per
  the test-hardening rule). A mid-flight run is left alone — check back
  later or ask Robin to re-run; do not stream/poll it — long silent
  commands here read as stuck.
- One-time suite bootstrap: `python -m venv .venv` then
  `.venv\Scripts\pip install playwright` and
  `.venv\Scripts\playwright install chromium` (the `--with-deps` system
  packages are a Linux need only).
- Line endings: `.gitattributes` pins LF for the working tree too
  (`eol=lf`); Git-for-Windows' system `core.autocrlf=true` is harmless
  now because attributes win — leave that config alone.
- PWA service-work notes are Linux-irrelevant here: file:// previews and
  served localhost behave the same on both OSes (no service worker on
  file://).

## Context budget: wrap up before quality decays

18. **~300K tokens is the watch line; ~350K the action line** (glm53@vibe).
    The model cannot introspect its own usage — the opencode plugin
    `.opencode/plugins/context-meter.js` writes the live numbers to
    `.opencode/context-usage.json` after every assistant message (`context_est`
    plus a `zone` verdict: ok/watch/action/hard at 300/350/400K). **Read that
    file at session start and whenever length is in doubt — the zone it
    names is the truth.** At the watch line: no new large tasks — finish the
    current slice to a green, committed state. At the action line: wrap up
    regardless of what is tempting — TODO fully current (session log, next
    steps, held-for-Robin items), all work committed, then end the session.
    Past ~400K, clarity visibly degrades: prefer ending early over pushing
    through. A half-finished TODO entry must never be the only memory of
    unfinished work.
