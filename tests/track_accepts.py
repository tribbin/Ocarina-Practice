#!/usr/bin/env python3
# Track-block audio acceptance: a "#track <name> [zen|audible]" block in the
# body parses into its own token stream (tests/parse_edges.py owns the
# grammar) and PLAYS as a second, parallel melody on the shared clock.
#
#   - The audible track is the point of the feature: it fires in the PLAIN
#     view (supports stay Zen-only — pinned in support_accepts_brackets.py)
#     and in Zen playback alike.
#   - A zen-zone track mirrors the support gating: fires in Zen, never plain.
#   - Alignment: both streams start at the same instant and each bar of the
#     track runs on the melody's clock (shared tempo, shared grid).
#   - Equivalence: a track's notes sound exactly like the same line played
#     as the melody (same playNoteAt calls, normalized onsets).
#   - Loop: the track re-fires every pass, aligned.
#   - Stop: melody-driven stop kills track voices with it (the walk never
#     schedules past the stop window).
#
#   python3 tests/track_accepts.py           # headless & silent
#   python3 tests/track_accepts.py --headed  # watch it

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv

from suite_server import start_server


BEAT = 0.6  # s per beat at the deterministic 100 BPM default (quarterSec fallback)

# Two-bar shape used by the legs: melody half-note bars (2 beats each),
# track bounce quarter+quarter per bar (same 2-beat bar sums, shared clock).
MELODY_SLOTS = "C5/2 | C5/2"
TRACK_BOUNCE = "C2/4 C3/4 | C2/4 C3/4"


# One driver, many legs: each case sets the src, spies playNoteAt, optionally
# enters/exits zen, plays, optionally stopMelody()s at stopAfterMs (capturing
# the ctx time), and polls until every wanted pitch hit its count or the
# melody died (loop cases never die) — under a +30 s ceiling past waitMs.
#
# The read is a rendezvous, never a fixed sleep; sweep-load audio-clock lag
# must SLOW the read instead of truncating it (the support suite's lesson).
RUN_DRIVER = """
CASES => new Promise(resolve => {
  const runs = [];
  let phase = 0;
  const step = () => {
    if (phase >= CASES.length) { resolve(runs); return; }
    const c = CASES[phase]; phase++;
    document.getElementById('src').value = c.src;
    render();
    const cb = document.getElementById('loopMel');
    if (cb) cb.checked = !!c.loop;
    const zenMode = c.zen != null ? c.zen : false;
    if (zenMode) {
      enterZenFromLink();
    } else if (document.body.classList.contains('zen-fallback')) {
      toggleZen(); // boot plain-fallback: leaving it forces the real plain view
    }
    const events = [];
    let t0 = 0, stopStamp = null;
    setNoteSink((id, when, dur) => {
      events.push({ id: id, dur: dur, fw: Math.round(performance.now() - t0),
                    when: when == null ? -1 : when });
    });
    setTimeout(() => {
      playMelody();
      t0 = performance.now();
      if (c.stopAfterMs != null) {
        setTimeout(() => {
          try { stopStamp = audioCtx.currentTime; } catch (e) { stopStamp = 0; }
          stopMelody();
        }, c.stopAfterMs);
      }
      const tally = () => {
        const t = {};
        for (const e of events) t[e.id] = (t[e.id] || 0) + 1;
        return t;
      };
      const melodyAlive = () => {
        try { return !!(window.OCA_DEBUG && OCA_DEBUG.melodyAlive()); }
        catch (e) { return true; }
      };
      const melodyKnown = () => {
        try { return !!(window.OCA_DEBUG && window.OCA_DEBUG.melodyAlive); }
        catch (e) { return false; }
      };
      const start = performance.now();
      const polls = () => {
        if (performance.now() - start < c.waitMs) { setTimeout(polls, 250); return; }
        const t = tally();
        const countsOk = c.counts
          ? Object.keys(c.counts).every(k => (t[k] || 0) >= c.counts[k])
          : true;
        const dead = !melodyAlive() || !melodyKnown();
        if (((c.loop || c.stopAfterMs != null) ? countsOk : (countsOk || dead)) &&
            performance.now() - start < c.waitMs + 30000) {
          runs.push({ events, focus: document
            .getElementById('tabPanel').classList.contains('focus'),
            stopStamp });
          step();
          return;
        }
        if (performance.now() - start < c.waitMs + 30000) { setTimeout(polls, 250); return; }
        runs.push({ events, focus: document
          .getElementById('tabPanel').classList.contains('focus'), stopStamp });
        step();
      };
      setTimeout(polls, 250);
    }, 200);
  };
  setTimeout(step, 150);
})
"""


def normalize(events):
    """Shift events to the first scheduled onset; keep as (id, when, dur)."""
    sched = [e for e in events if e["when"] >= 0]
    if not sched:
        return []
    base = min(e["when"] for e in sched)
    return [(e["id"], round(e["when"] - base, 3), round(e["dur"], 3))
            for e in sched]


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)

            def leg(name, driver_cases, checks, red=False):
                print(f"== {name}", flush=True)
                page = browser.new_page()
                page.goto(base + "?nofs=1")
                page.wait_for_function(
                    "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                    " && window.NOTES && window.NOTES.length")
                page._errs = []
                page.on("pageerror", lambda e, q=page: q._errs.append(str(e)))
                runs = page.evaluate(RUN_DRIVER, driver_cases)
                if page._errs:
                    failures.append(f"{name}: page errors {page._errs}")
                page.close()
                checks(runs[0], failures)

            def stack(*cases):
                return [dict(c) for c in cases]

            # 1 — the point of the feature: an audible track plays in the
            # PLAIN view (before 09-26 the only second voice was Zen-gated).
            def plain_check(run, failures):
                if run["focus"]:
                    failures.append("plain-view audible: unexpectedly in "
                                    "focus mode (supports' leg leaked?)")
                hits = [e for e in normalize(run["events"]) if e[0] == "C2"]
                if len(hits) < 2:
                    failures.append("plain-view audible: C2 never fired — "
                                    f"events: {normalize(run['events'])}")
                    return
                rels = [round(w / BEAT, 3) for _, w, _ in hits]
                # one C2 per bar at beats 0 and 2 (each bar = 2 beats)
                if abs(rels[0]) > 0.04 or abs(rels[1] - 2.0) > 0.04:
                    failures.append("plain-view audible: C2 bar onsets wrong "
                                    f"{rels} — the track is not riding the "
                                    "shared clock")

            leg("plain-view audible track fires", stack(
                dict(src=MELODY_SLOTS + "\n#track bass audible\n" + TRACK_BOUNCE,
                     counts={"C2": 2, "C3": 2}, waitMs=6500)),
                plain_check)

            # 2 — the audible track also plays in Zen (no gating for it).
            leg("zen: audible track still fires", stack(
                dict(src=MELODY_SLOTS + "\n#track bass audible\n" + TRACK_BOUNCE,
                     zen=True, counts={"C2": 2}, waitMs=6500)),
                lambda run, failures: _want_onsets(
                    "zen audible", run, "C2", [(0.0,), (2.0,)], failures))

            # 3 — a zen-zone track mirrors the support gating: fires in Zen.
            leg("zen: zen-zone track fires", stack(
                dict(src=MELODY_SLOTS + "\n#track bass zen\n" + TRACK_BOUNCE,
                     zen=True, counts={"C2": 2}, waitMs=6500)),
                lambda run, failures: _want_onsets(
                    "zen zone", run, "C2", [(0.0,), (2.0,)], failures))

            # 4 — and never in the plain view (the gating that survived).
            def zen_zone_silent(run, failures):
                hits = [e for e in normalize(run["events"]) if e[0] == "C2"]
                if run["focus"]:
                    failures.append("plain-zone: unexpectedly in focus mode")
                if hits:
                    failures.append(f"plain-zone: zen track fired {hits}")

            leg("plain: zen-zone track stays silent", stack(
                dict(src=MELODY_SLOTS + "\n#track bass zen\n" + TRACK_BOUNCE,
                     waitMs=6500)),
                zen_zone_silent)

            # 5 — equivalence pair: the same line, once as the melody, once
            # as an audible track over rests. Identical playNoteAt calls.
            # In-range pitches: the page boots an A4–F6 instrument, where the
            # melody voice range-checks (C4 never sounds) — a track voice
            # never does.
            page = browser.new_page()
            page.goto(base + "?nofs=1")
            page.wait_for_function(
                "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                " && window.NOTES && window.NOTES.length")
            page._errs = []
            page.on("pageerror", lambda e: page._errs.append(str(e)))
            print("== equivalence: track line == melody line", flush=True)
            runs = page.evaluate(RUN_DRIVER, [
                dict(src="C5/2 E5/2", counts={"C5": 1, "E5": 1}, waitMs=3500),
                dict(src="r/2 r/2\n#track bass audible\nC5/2 E5/2",
                     counts={"C5": 1, "E5": 1}, waitMs=3500),
            ])
            if page._errs:
                failures.append(f"equivalence: page errors {page._errs}")
            page.close()
            mel, trk = normalize(runs[0]["events"]), normalize(runs[1]["events"])
            mel_e = [(i, w, d) for i, w, d in mel if i in ("C5", "E5")]
            trk_e = [(i, w, d) for i, w, d in trk if i in ("C5", "E5")]
            if mel_e != trk_e:
                failures.append(f"equivalence: track events differ from the "
                                f"melody's\n  melody:  {mel_e}\n  track:   {trk_e}")

            # 6 — loop: the track re-fires each pass, aligned to the melody.
            leg("loop: track re-fires every pass", stack(
                dict(src="C5/2 C5/2\n#track bass audible\nC2/4 C3/4",
                     loop=True, counts={"C2": 3, "C3": 3}, waitMs=5600)),
                lambda run, failures: _want_onsets(
                    "loop", run, "C2", None, failures, tap="C2", taps=[0.0, 2.0, 4.0]))

            # 7 — stop: killing the melody kills the track; nothing may be
            # scheduled past the stop's scheduling window (0.3 s lookahead
            # + a small margin). Sink fires at schedule time, so already-
            # scheduled events with `when` inside the window stay legal.
            def stop_check(run, failures):
                stamp = run.get("stopStamp")
                if stamp is None:
                    failures.append("stop: no stopStamp captured")
                    return
                leaks = [e for e in run["events"]
                         if e["when"] >= 0 and e["when"] > stamp + 0.4]
                if leaks:
                    failures.append("stop: track scheduled past the stop "
                                    f"window: {[(e['id'], round(e['when'] - stamp, 3)) for e in leaks]}")

            leg("stop: track dies with the melody", stack(
                dict(src="r/2 " * 16 + "\n#track bass audible\n" +
                     " ".join(["C2/4 C3/4"] * 16),
                     stopAfterMs=1600, waitMs=3800)),
                stop_check)

            # 8 — a body without blocks opens no track behavior at all.
            leg("no tracks: melody plays alone", stack(
                dict(src=MELODY_SLOTS, counts={"C5": 2}, waitMs=6500)),
                lambda run, failures: _want_absent(
                    "no tracks", run, ("C2", "C3"), failures))

            # 9 — junk inside a track block chips in BOTH token strips: a
            # stream-name pill, then the raw junk, same .tok.bad shape as
            # melody junk (bad-chip philosophy never sleeps). A clean body
            # renders no pills at all.
            print("== track junk chips in the token strips", flush=True)
            page = browser.new_page()
            page.goto(base + "?nofs=1")
            page.wait_for_function(
                "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                " && window.NOTES && window.NOTES.length")
            page._errs = []
            page.on("pageerror", lambda e: page._errs.append(str(e)))
            pills = page.evaluate("""() => {
              const setSrc = (v) => { document.getElementById('src').value = v;
                                      window.render(); };
              const read = () => [...document.getElementById('tokens')
                    .querySelectorAll('.tok.bad')].map(e => e.textContent);
              setSrc("C5 D5");
              setSrc("C5 D5\\n#track bass\\nC2 zz");
              const pills = read();
              const focusPills = document.getElementById('focusTokens')
                    .querySelectorAll('.tok.bad').length;
              const anyRole = [...document.querySelectorAll('.tok.bad')]
                    .some(e => e.getAttribute('role') === 'button');
              setSrc("C5 D5");
              return { pills, focusPills, anyRole,
                       cleanPills: read().length };
            }""")
            if page._errs:
                failures.append(f"track junk chips: page errors {page._errs}")
            page.close()
            if "#track bass" not in (pills.get("pills") or []):
                failures.append(f"track junk chips: no stream-name pill "
                                f"{pills!r}")
            if "zz" not in (pills.get("pills") or []):
                failures.append(f"track junk chips: raw junk pill missing "
                                f"{pills!r}")
            if not pills.get("focusPills"):
                failures.append("track junk chips: the zen reading strip got "
                                f"no pills {pills!r}")
            if pills.get("anyRole"):
                failures.append("track junk chips: junk pills must stay plain "
                                "text (no button role)")
            if pills.get("cleanPills"):
                failures.append("track junk chips: a clean body must render "
                                f"no pills {pills!r}")

            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: track blocks play on the shared clock — audible in plain and "
          "Zen views, zen-zone gated, loop-aligned, stop-killed, and "
          "equivalent to the same line played as the melody.")
    return 0


def _want_onsets(name, run, pitch, want, failures, tap=None, taps=None):
    hits = [e for e in normalize(run["events"]) if e[0] == pitch]
    if not hits:
        failures.append(f"{name}: {pitch} never fired — events: "
                        f"{normalize(run['events'])}")
        return
    rels = [round(w / BEAT, 3) for _, w, _ in hits]
    target = taps if taps is not None else [t[0] for t in want]
    for i, w in enumerate(rels[:len(target)]):
        if target[i] is not None and abs(w - target[i]) > 0.04:
            failures.append(f"{name}: {pitch} rel #{i + 1} at {w} beats != "
                            f"{target[i]} (all: {rels})")


def _want_absent(name, run, pitches, failures):
    events = normalize(run["events"])
    hits = [e for e in events if e[0] in pitches]
    if hits:
        failures.append(f"{name}: unexpectedly fired {hits}")


if __name__ == "__main__":
    sys.exit(main())
