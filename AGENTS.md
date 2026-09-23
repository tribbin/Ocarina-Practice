# AGENTS — how to behave in this repo

Rules distilled from real sessions. They override defaults — when a
situation is not covered here, the honest move is a real question, not a
guess. `plans/TODO.md` (progress/plans) and `plans/IDEAS.txt` (Robin's
scratchpad) are committed so they follow the repo across machines; this
file sits at the repo root so every session finds it first.

## Session protocol

1. **Open every session by reading `plans/TODO.md`.** Its bookkeeping is the
   board: struck items with `✅ <date> <SHA>` are done; the hot list and the
   latest session log say exactly where work stands. Never trust memory over
   the board. Check `git log` too: Robin commits his own work between and
   during sessions; the branch tip is not what you left there.
2. **`plans/IDEAS.txt` is the one file the AI never writes.** It is Robin's
   live scratchpad — read it at the moment an idea is picked up; never
   transcribe or summarize it anywhere (a stale copy is a wrong copy). Lift
   an idea into TODO.md only when Robin explicitly asks.
3. **Keep the TODO current as you go, not at the end:** completed items
   struck with date + SHA; findings placed in their type-sections; datd
   session-log entries describe what was done. Sessions must be able to die
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
   intent is genuinely unknown.

## Attribution, repo hygiene, commit style

7. **Report CI runs and pushes by SHA/trigger/job only — never attribute to
   an actor.** ("Robin pushed" is out; "push at `<sha>`, job #N" is in.)
8. Pushes, merges, PRs, branch create/delete, remote cleanup: **Robin's
   operations.** Amend only your own unpushed commits, same concern only.
9. **Commit titles:** one dense informative sentence in the repo's style —
   describe the change and why, quotable in a PR description. No emoji.
   Shipped code comments carry **no references to the local planning docs**
   (code-to-code references are fine; TODO §-refs belong in TODO.md only).
10. PR descriptions follow the established shape: `##` one-line summary,
    plain section headers, bullets as commit titles linked to their SHAs
    (current repo slug), test-infrastructure section last.

## Tests & verification

11. **Test-first (red→green) or pin-first for behavior changes.** No blanket
    upfront test pushes — tests are written for exactly what changes.
12. Run suites via `.venv/bin/python3 tests/<name>.py` (plain python3 has no
    playwright). **Claim "all green" only after running the full sweep** —
    never imply from memory. New suites/legs are registered in
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
16. No node on the system: lint locally through a node tarball under
    `/tmp/opencode/node/bin` (see the TODO session log). Tests and lint are
    verified locally before every commit statement.
17. Test suites run their own throwaway HTTP server + isolated Chromium;
    they share nothing with Robin's preview (which is `file://` — no
    service worker, ever). Verify page behavior via `python3 -m http.server`,
    never through his preview.

## Context budget: wrap up before quality decays

18. **~300K tokens is the watch line; ~350K the action line** (glm53@vibe).
    At the watch line: no new large tasks — finish the current slice to a
    green, committed state. At the action line: wrap up regardless of what
    is tempting — TODO fully current (session log, next steps, held-for-
    Robin items), all work committed, then end the session. Past ~400K,
    clarity visibly degrades: prefer ending early over pushing through. A
    half-finished TODO entry must never be the only memory of unfinished
    work.
