#!/usr/bin/env python3
# Support-bracket acceptance test: the hidden contrabass/octave-support
# feature (|[C2], |["Name",C2], [C2/4.] anywhere between bars, [-/2]
# extensions, [~F/4] glides) driven in a real Chromium page.
#
# The support layer is a SECOND, PARALLEL MELODY: every marker is a note of
# that track ([C3/2] a note, [-/2] a tie extending the running chain, [~F/4]
# a glide), anchored to the melody clock at the pivot after the marker. So
# the core battery is EQUIVALENCE PAIRS: playing the bracket version must
# produce bit-identical playNoteAt calls to playing the extracted support
# line as the melody itself (same pitches, onsets, durations, glide anchors).
#
#   - Parser battery: every bracket shape → the exact tokens it must produce
#     (and the old descriptions it must keep producing).
#   - Equivalence pairs: melody run vs support run in one page, playNoteAt
#     spied, onset times normalized per run (absolute ctx start differs).
#     Deterministic 100 BPM default → 0.6 s per beat, supports ring the
#     melody's slot (0.92 taper, full slot when flowing into a ~ glide),
#     durationless markers ring the full bar-span. No wall-clock assertions.
#   - Zen battery: the mixed user-song shape, bar brackets and trailing
#     markers fire at their chain boundaries in Zen playback.
#   - Gating: supports must fire in Zen playback and never in the plain view.
#
# python3 tests/support_accepts_brackets.py          # headless & silent
# python3 tests/support_accepts_brackets.py --headed # watch it

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
# EQUIVALENCE PAIRS — the whole point: the bracket version
# must produce the same playNoteAt events as the extracted support line
# played as the melody. C5/G5: in the default Triple Bass C range so BOTH
# sides really sound.
EQUIVALENCE_PAIRS = [
    (dict(name="pair glide — C5/2 ~G5/2 ≡ [C5/2] r/2 [~G5/2] r/2",
          melody="C5/2 ~G5/2 C5/2 -/2",
          support="[C5/2] r/2 [~G5/2] r/2 [C5/2] r/2 [-/2] r/2",
          wait_ms=6500, expect=["C5", "G5", "C5"])),
    (dict(name="pair tie — C5/2 -/2 ≡ [C5/2] r/2 [-/2] r/2",
          melody="C5/2 -/2",
          support="[C5/2] r/2 [-/2] r/2",
          wait_ms=4200, expect=["C5"])),
]

# Zen battery: supports over a real melody fire at their chain boundaries.
# Durations in beats (×0.6 s at 100 BPM): a bounded support rings its slot
# (0.92 taper), a durationless one rings the full bar span.
ZEN_CASES = [
    (dict(name="mixed song — melody plays, supports ride the melody clock",
          src="E5/2 [C3/2] E5/2 [~G3/2] E5/2 [E3/2] [-/2] E5/2 r/2",
          wait_ms=7800,
          support={
              "C3": dict(count=1, beats=2.0, rel=2.0),   # full slot: flows into the glide
              "G3": dict(count=1, beats=1.84, rel=4.0, slide="C3"),
              "E3": dict(count=1, beats=3.68, rel=6.0),  # one voice: [E3/2] + [-/2]
          })),
    (dict(name="bar bracket with length — measure-length ring at the bar",
          src="E5/4 C5/4 |[C2/2] E5/4 E5/4 | E5/4",
          wait_ms=5200,
          support={"C2": dict(count=1, beats=1.84, rel=2.0)})),
    (dict(name="durationless bar bracket — rings the full span",
          src="E5/4 | [C2] E5/4 E5/4 | E5/4",
          wait_ms=5200,
          support={"C2": dict(count=1, beats=2.0, rel=1.0)})),
    (dict(name="trailing marker past the last note still rings",
          src="E5/2 [C2]",
          wait_ms=3800,
          support={"C2": dict(count=1, beats=0.8333, rel=2.0)})),
    (dict(name="loop — anchored supports re-ring every pass",
          src="E5/2 [C3/1] r/2", loop=True, wait_ms=6300,
          support={"C3": dict(count=3, beats=3.68, rels=[2.0, 6.0, 10.0])})),
    (dict(name="loop — trailing markers ring at each pass's first pivot",
          src="E5/2 r/2 [C3]", loop=True, wait_ms=6300,
          support={"C3": dict(count=2, beats=0.8333, rels=[4.0, 8.0])})),
]

# Runs one or more (src, waitMs) seasons in a single page: each sets the
# source, spies playNoteAt, plays in Zen (enterZenFromLink → ?nofs=1 fallback,
# no fullscreen permission needed) and collects the raw events. Tick 200 ms
# before play: the previous run's scheduler timers must be dead.
RUN_DRIVER = """
CASES => new Promise(resolve => {
  const runs = [];
  const orig = playNoteAt;
  let phase = 0;
  const step = () => {
    if (phase >= CASES.length) {
      playNoteAt = orig;
      resolve({ runs,
                focus: document.getElementById('tabPanel').classList.contains('focus') });
      return;
    }
    const c = CASES[phase]; phase++;
    document.getElementById('src').value = c.src;
    render();
    const cb = document.getElementById('loopMel');
    if (cb) cb.checked = !!c.loop;
    const events = [];
    playNoteAt = function (id, when, dur, bag, slideFrom, intoSlide) {
      events.push({ id, when: when == null ? -1 : when, dur,
                    slideFrom: slideFrom || null, intoSlide: !!intoSlide });
      return orig(id, when, dur, bag, slideFrom, intoSlide);
    };
    setTimeout(() => {
      playMelody();
      setTimeout(() => { runs.push(events); step(); }, c.waitMs);
    }, 200);
  };
  enterZenFromLink();
  setTimeout(step, 150);
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
    }, 3000);
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


BEAT = 0.6  # s per beat at the deterministic 100 BPM default

def normalize(events):
    """Shift a page's event list to start at its first onset (absolute ctx
    times differ between pages/runs); drop live (pressed) calls."""
    live = [e for e in events if e["when"] < 0]
    sched = [e for e in events if e["when"] >= 0]
    if not sched:
        return [], live
    t0 = min(e["when"] for e in sched)
    return [dict(e, when=round(e["when"] - t0, 4)) for e in sched], live


def norm_event(e):
    return (e["id"], round(e["when"], 3), round(e["dur"], 4),
            e["slideFrom"], int(e["intoSlide"]))


def check_support_events(name, events, wants, failures):
    """wants: {pitch: {count, beats, rel(onset beats, ±0.04), slide?}}"""
    for pitch, want in wants.items():
        hits = [e for e in events if e["id"] == pitch]
        want_count = want.get("count", 1)
        if len(hits) != want_count:
            failures.append(f"{name}: {pitch} fired {len(hits)}×, want "
                            f"{want_count} — the whole event list: "
                            f"{[norm_event(e) for e in events]}")
            if not hits:
                continue
            hits = hits[:want_count]
        beats = round(hits[0]["dur"] / BEAT, 3)
        if abs(beats - want["beats"]) > 0.02:
            failures.append(f"{name}: {pitch} dur {beats} beats != {want['beats']} "
                            f"({[round(h['dur']/BEAT, 3) for h in hits]})")
        rels = [round(h["when"] / BEAT, 3) for h in hits]
        want_rels = want.get("rels") or [want["rel"]]
        for i, want_rel in enumerate(want_rels):
            rel = rels[i]
            if abs(rel - want_rel) > 0.04:
                failures.append(f"{name}: {pitch} onset #{i + 1} at {rel} beats "
                                f"!= {want_rel} (all: {rels})")
        if "slide" in want and hits[0]["slideFrom"] != want["slide"]:
            failures.append(f"{name}: {pitch} slide anchor {hits[0]['slideFrom']!r} "
                            f"!= {want['slide']!r}")
        elif "slide" not in want and hits[0]["slideFrom"]:
            failures.append(f"{name}: {pitch} slid unexpectedly "
                            f"from {hits[0]['slideFrom']!r}")


def run_equivalence_pair(page, pair, failures):
    name = pair["name"]
    cases = [dict(src=pair["melody"], waitMs=pair["wait_ms"]),
             dict(src=pair["support"], waitMs=pair["wait_ms"])]
    result = page.evaluate(RUN_DRIVER, cases)
    errs = page.evaluate("() => window.__lastErrs || []")
    if errs:
        failures.append(f"{name}: page errors {errs}")
    if not result.get("focus"):
        failures.append(f"{name}: was not in focus mode")
    mel, spr = result["runs"]
    mel_n, _ = normalize(mel)
    spr_n, _ = normalize(spr)
    if len(mel_n) != len(pair["expect"]):
        failures.append(f"{name}: melody run has {len(mel_n)} events (want "
                        f"{len(pair['expect'])}): {[norm_event(e) for e in mel_n]}")
        return
    if [e["id"] for e in mel_n] != pair["expect"]:
        failures.append(f"{name}: melody run pitches "
                        f"{[e['id'] for e in mel_n]} != {pair['expect']}")
        return
    # The criterion: bit-identical playNoteAt calls apart from the melody's
    # own rest slots (which are silent).
    if [norm_event(e) for e in spr_n] != [norm_event(e) for e in mel_n]:
        failures.append(f"{name}: support events differ from the melody "
                        f"events\n  melody:  {[norm_event(e) for e in mel_n]}"
                        f"\n  support: {[norm_event(e) for e in spr_n]}")

# 4 — the support layer is the modelled instrument's voice: a support note
# and the same pitch pressed on the piano (playNote) must ride playNoteAt
# with identical parameters (the modelled contrabass timbre). [C2/4] = one
# notated beat, which rings 0.92 × 0.6 s under the melody-slot taper — that
# is the requested press duration.
SAME_VOICE_DRIVER = """
() => new Promise(resolve => {
  const events = [];
  const orig = playNoteAt;
  playNoteAt = function (id, when, dur, bag, slideFrom, intoSlide) {
    events.push({ id, dur: Math.round(dur * 1000) / 1000,
                  when: when == null ? "live" : Math.round(when * 1000) / 1000 });
    return orig(id, when, dur, bag, slideFrom, intoSlide);
  };
  enterZenFromLink();
  setTimeout(() => {
    playNote("C2", 0.552);            // simulated instrument press (0.92 × beat)
    document.getElementById('src').value = "E5/4 [C2/4] E5/4";
    render();
    setTimeout(() => {
      playMelody();
      setTimeout(() => { playNoteAt = orig; stopMelody(); resolve(events); }, 3200);
    }, 250);
  }, 250);
})
"""

def same_voice_case(browser, base, failures):
    page = browser.new_page()
    page.goto(base + "?nofs=1")
    page.wait_for_function(
        "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
        " && window.NOTES && window.NOTES.length")
    ev = page.evaluate(SAME_VOICE_DRIVER)
    page.close()
    pressed = [e for e in ev if e["id"] == "C2" and e["when"] == "live"]
    support = [e for e in ev if e["id"] == "C2" and e["when"] != "live"]
    if not pressed or not support:
        failures.append("same-voice: missing events "
                        f"pressed={len(pressed)} support={len(support)}")
        return
    if abs(pressed[0]["dur"] - support[0]["dur"]) > 0.01:
        failures.append("same-voice: durations differ — the support layer is "
                        "not the modelled instrument voice "
                        f"{pressed[0]['dur']} vs {support[0]['dur']}")


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

            # 2 — equivalence pairs: melody run vs support run, one page per
            # pair (the melody version plays its seasonal notes itself, the
            # support version plays them as the hidden contrabass track)
            for pair in EQUIVALENCE_PAIRS:
                print(f"== {pair['name']}", flush=True)
                page = browser.new_page()
                page.goto(base + "?nofs=1")
                page.wait_for_function(
                    "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                    " && window.NOTES && window.NOTES.length")
                page._errs = []
                page.on("pageerror", lambda e, p=page: p._errs.append(str(e)))
                run_equivalence_pair(page, pair, failures)
                if page._errs:
                    failures.append(f"{pair['name']}: page errors {page._errs}")
                page.close()

            # 3 — zen battery: the mixed user-song shape, bar brackets and
            # trailing markers (one page per case keeps the spy clean)
            for case in ZEN_CASES:
                print(f"== {case['name']}", flush=True)
                page = browser.new_page()
                page.goto(base + "?nofs=1")
                page.wait_for_function(
                    "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                    " && window.NOTES && window.NOTES.length")
                page._errs = []
                page.on("pageerror", lambda e, p=page: p._errs.append(str(e)))
                result = page.evaluate(RUN_DRIVER, [dict(src=case["src"], waitMs=case["wait_ms"],
                                                         loop=case.get("loop", False))])
                if page._errs:
                    failures.append(f"{case['name']}: page errors {page._errs}")
                if not result.get("focus"):
                    failures.append(f"{case['name']}: was not in focus mode")
                events, _ = normalize(result["runs"][0])
                check_support_events(case["name"], events, case["support"], failures)
                page.close()

# 4 — gating: the same content must never fire outside Zen
            print("== plain view stays silent", flush=True)
            page = browser.new_page()
            page.goto(base + "?nofs=1")
            page.wait_for_function(
                "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                " && window.NOTES && window.NOTES.length")
            page._errs = []
            page.on("pageerror", lambda e: page._errs.append(str(e)))
            result = page.evaluate(PLAIN_DRIVER,
                                   dict(src=ZEN_CASES[0]["src"], waitMs=6500))
            if page._errs:
                failures.append("plain view: page errors " + str(page._errs))
            if result.get("focus"):
                failures.append("plain view: unexpectedly in focus mode")
            support_hits = [e for e in result["events"] if e["id"] in ("C2", "C3", "G3", "E3")]
            if support_hits:
                failures.append("plain view: support fired outside Zen "
                                f"{support_hits}")
            page.close()

            print("== support voice == modelled instrument voice", flush=True)
            same_voice_case(browser, base, failures)
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: support brackets parse, mirror the parallel melody exactly, fire in Zen "
          "(never outside), and keep their notated lengths.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
