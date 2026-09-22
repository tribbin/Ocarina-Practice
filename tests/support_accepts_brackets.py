#!/usr/bin/env python3
# Support-bracket acceptance test: the hidden contrabass/octave-support
# feature (|[C2], |["Name",C2], [C2/4.] anywhere between bars, [-/2]
# extensions, [~F/4] glides) driven in a real Chromium page.
#
#   - Parser battery: every bracket shape → the exact tokens it must produce
#     (and the old descriptions it must keep producing).
#   - Schedule battery: playback in Zen-fallback (?nofs=1 → CSS fallback
#     fullscreen, no fullscreen request needed) with playNoteAt spied. The
#     support voice IS the standard instrument voice, so we assert the
#     scheduler's own numbers: which pitches sound, their notated durations
#     (tempo is the deterministic 100 BPM default → 0.6 s per beat) and the
#     glide anchors. No wall-clock assertions.
#   - Gating: supports must fire in Zen playback and never in the plain view.
#
# Assertions come from the scheduler, so they are deterministic; nothing here
# listens to audio.
#
#   python3 tests/support_accepts_brackets.py          # headless & silent
#   python3 tests/support_accepts_brackets.py --headed # watch it

import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass


def start_server():
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), QuietHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


# Each case: (name, melody text, expectations as {pitch: dur_beats | {
# "slide": anchor_pitch}}, plus flags). beat × 0.6 s at the 100 BPM default.
SCHEDULE_CASES = [
    (dict(name="bar bracket — measure-length ring at the next note",
          src="E5/4 | [C2] C5/4 C5/4 | E5/4",
          support={"C2": 2})),
    (dict(name="inline marker — waits for the next note-chain end",
          src="E5/4 C5/4 [C2] D5/4 E5/4",
          support={"C2": 2})),
    (dict(name="duration — rings exactly its own length",
          src="E5/4 [C2/4.] D5/4 E5/4",
          support={"C2": 1.5})),
    (dict(name="extension — [C2/2] [-/2] rings four beats",
          src="E5/4 [C2/2] [-/2] D5/4 E5/4",
          support={"C2": 4})),
    (dict(name="glide — [~E2/2] slides from the firing support",
          src="E5/4 [C2/2] [-/2] D5/4 [~E2/2] D5/4",
          support={"C2": 4, "E2": {"beats": 2, "slide": "C2"}})),
    (dict(name="rest pivot — [C2] starts with the following rest",
          src="E5/4 [C2] r/4 E5/4",
          support={"C2": 2})),
    (dict(name="trailing marker past the last note still rings",
          src="E5/2 [C2]",
          support={"C2": 0.83})),  # 0.5 s grace floored span, / 0.6 s per beat
]

SCHEDULE_DRIVER = """
CASE => new Promise(resolve => {
  document.getElementById('src').value = CASE.src;
  render();
  const events = [];
  const orig = playNoteAt;
  playNoteAt = function (id, when, dur, bag, slideFrom, intoSlide) {
    events.push({ id, when: when == null ? -1 : when,
                  beats: Math.round(dur / 0.6 * 100) / 100,
                  slideFrom: slideFrom || null });
    return orig(id, when, dur, bag, slideFrom, intoSlide);
  };
  enterZenFromLink();  // ?nofs → CSS fallback: focus mode without fullscreen
  setTimeout(() => {
    playMelody();
    setTimeout(() => {
      playNoteAt = orig;
      resolve({ events,
                focus: document.getElementById('tabPanel').classList.contains('focus') });
    }, 3200);
  }, 150);
})
"""

PLAIN_DRIVER = """
CASE => new Promise(resolve => {
  document.getElementById('src').value = CASE.src;
  render();
  const events = [];
  const orig = playNoteAt;
  playNoteAt = function (id, when, dur, bag, slideFrom, intoSlide) {
    events.push({ id });
    return orig(id, when, dur, bag, slideFrom, intoSlide);
  };
  // Plain view: toggleZen's in-place branch would go to zen from the
  // fallback-plain state; force NON-zen by exiting the fallback first.
  if (document.body.classList.contains("zen-fallback")) toggleZen();
  setTimeout(() => {
    playMelody();
    setTimeout(() => {
      playNoteAt = orig;
      resolve({ events,
                focus: document.getElementById('tabPanel').classList.contains('focus') });
    }, 2500);
  }, 150);
})
"""

PARSER_EVAL = """() => {
  const cases = [
    // [src, expected tokens]  (bars: | + optional ~bass@beats + (desc);
    //                           markers: [ext-N], [~bass@beats], [bass@beats])
    ["E5/4|[C2] C5/4", [["|", "C2", null, null]]],
    ['E5/4|["Opening",C2] C5/4', [["|", "C2", "Opening", null]]],
    ['E5/4|["35th bar, from midi"] C5/4', [["|", null, "35th bar, from midi", null]]],
    ["C5/4 [C2] D5/4", [["bass", "C2", null, null, null, null]]],
    ["C5/4 [C2/4.] D5/4", [["bass", "C2", 1.5, null, null, null]]],
    ['C5/4 ["Chorus",C3/2] D5/4', [["bass", "C3", 2, "Chorus", null, null]]],
    ["C5/4 [-/2] D5/4", [["bass", null, null, null, 2, null]]],
    ["C5/4 |[-] D5/4", "plain-desc"],                // bare dash: old desc fallback
    ["C5/4 [foo] D5/4", []],                      // no pitch → nothing
    ["C5/4 [~E2/2] D5/4", [["bass", "E2", 2, null, null, "slide"]]],
    ['C5/4 ["Glow",~E2] D5/4', [["bass", "E2", null, "Glow", null, "slide"]]],
    ["C5/4 |[~E2] D5/4", [["|", "E2", null, "slide"]]],
    ["C5/4 |[-/2] D5/4", [["bass", null, null, null, 2, null], ["|", null, null, null]]],  // continuation passthrough
  ];
  return cases.map(([src, want]) => {
    document.getElementById('src').value = src; render();
    const toks = parse(document.getElementById('src').value)
      .filter(t => t.type === "bar" || t.type === "bass")
      .map(t => t.type === "bar"
        ? ["|", t.bass || null, t.desc || null, t.slide ? "slide" : null]
        : ["bass", t.id, t.beats, t.desc || null,
         t.ext != null ? t.ext : null, t.slide ? "slide" : null]);
    return { src, toks, want };
  });
}"""


def expect_ok(case_name, got, want, failures):
    def norm(v):
        if isinstance(v, float):
            return round(v, 4)
        if isinstance(v, (list, tuple)):
            return [norm(x) for x in v]
        return v
    if norm(got) != norm(want):
        failures.append(f"{case_name}: got {got!r}, want {want!r}")


def run_schedule_case(page, case, driver, failures):
    name = case["name"]
    result = page.evaluate(driver, case)
    errs = page.evaluate("() => window.__lastErrs || []")
    if errs:
        failures.append(f"{name}: page errors {errs}")
    if case.get("expect_focus") and not result.get("focus"):
        failures.append(f"{name}: was not in focus mode")
    for cname, want in case["support"].items():
        slides = isinstance(want, dict)
        anchor = wanted_slide = None
        if slides:
            anchor = want.get("slide")
        want_beats = want["beats"] if slides else want
        hits = [e for e in result["events"] if e["id"] == cname]
        if case["mode"] == "plain":
            if hits:
                failures.append(f"{name}: support fired outside Zen")
            continue
        if not hits:
            failures.append(f"{name}: no support note played for {cname}")
            continue
        if all(abs(h["beats"] - want_beats) > 0.01 for h in hits):
            failures.append(f"{name}: {cname} durations "
                            f"{[h['beats'] for h in hits]} != {want_beats}")
        if slides and anchor is not None:
            if not any((h["slideFrom"] or None) == anchor for h in hits):
                failures.append(f"{name}: {cname} glide anchor missing "
                                f"{[h['slideFrom'] for h in hits]} != {anchor}")
        elif slides:
            if any(h["slideFrom"] for h in hits):
                failures.append(f"{name}: {cname} slid unexpectedly")


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            page = browser.new_page()
            page.goto(base + "?nofs=1")
            page.wait_for_function(
                "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                " && window.NOTES && window.NOTES.length")
            errs = []
            page.on("pageerror", lambda e, errs=errs: errs.append(str(e)))

            # 1 — parser battery
            print("== bracket parser battery", flush=True)
            rows = page.evaluate(PARSER_EVAL)
            for r in rows:
                if r["want"] == "plain-desc":
                    # junk dash content: the old desc-only fallback must win
                    src = r["src"]
                    bars = [t for t in r["toks"] if t[0] == "|"]
                    if not bars or not isinstance(bars[0][2], str):
                        failures.append(f"parser {src!r}: desc fallback lost")
                    continue
                # strip the melody-only positional padding
                expect_ok("parser " + r["src"], r["toks"], r["want"], failures)
            page.close()

            # 2 — schedule battery (one page per case keeps the spy clean)
            for case in SCHEDULE_CASES:
                print(f"== {case['name']}", flush=True)
                page = browser.new_page()
                page.goto(base + "?nofs=1")
                page.wait_for_function(
                    "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                    " && window.NOTES && window.NOTES.length")
                page.on("pageerror", lambda e: page._errs.append(str(e)))
                page._errs = []
                case = dict(case, src=case["src"], mode="zen", expect_focus=True)
                run_schedule_case(page, case, SCHEDULE_DRIVER, failures)
                if page._errs:
                    failures.append(f"{case['name']}: page errors {page._errs}")
                page.close()

            # 3 — gating: the same content must never fire outside Zen
            print("== plain view stays silent", flush=True)
            page = browser.new_page()
            page.goto(base + "?nofs=1")
            page.wait_for_function(
                "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                " && window.NOTES && window.NOTES.length")
            case = dict(SCHEDULE_CASES[0], mode="plain")
            run_schedule_case(page, case, PLAIN_DRIVER, failures)
            page.close()
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: support brackets parse, fire in Zen (never outside), and keep their notated lengths.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
