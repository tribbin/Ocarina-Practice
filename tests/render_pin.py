#!/usr/bin/env python3
# Render-behaviour pin (guardrail for the pending per-keystroke render
# refactor): the refactor must NOT move any of these bits, so they are frozen
# here before it starts —
#   * the token strip chips (order, classes, raw text, data-i, roles)
#   * the fingering-chart grid composition (cards with data-i, sec-head for
#     named bars, tab-bar lines, tab-tempo chips, bad chips ABSENT)
#   * the scroll band difference (a named bar keeps its tagged line instead
#     of a header row) and the live/single sheet target
#   * highlightToken's .now propagation across both strips and the sheet card
#   * the token strip's focus-restore across a rebuild
#   * the typed-input debounce contract (stale during the settle, fresh after)
#
#   python3 tests/render_pin.py      # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
# Tail guard: a typed body typed before boot's tail lands gets REPLACED by
# loadLibraryItem's home song (the practice_dip 2026-09-25 red class) — so
# wait until #scale options exist (filled only by the tail) before probing.
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function'"
        " && (function () { const s = document.getElementById('scale');"
        " return s && s.options.length > 0; })()")

# Pinned against the Triple Bass C explicitly: the default instrument now
# boots the 12-hole Alto C (the app's home instrument), whose A4–F6 range
# would turn most of the pin melody into out-of-range cards. The Triple Bass
# covers the melody AND spans all three chamber colors the spec calibrates.
PIN_INST = "ico-oak-leaf-bass-c-triple"

MELODY = ("# Pin\n"
          "# tempo 120\n"
          '|["A",C2] C4 D4/2 zz\n'
          "# tempo 90\n"
          "| E4 -/2 F4 G4 ~ C5 r/2")

# chip = (class-prefix parts, text, data-i) walking BOTH strips in DOM order.

STRIP_SPEC = [
    (("bar has-note", "|", "0"), True),      # named bar chip
    (("ch1", "C₄ 𝅘𝅥", "1"), True),
    (("ch1", "D₄ 𝅗𝅥", "2"), True),
    (("bad", "zz", "3"), False),             # junk chip: plain span, no role
    (("tempo", "♩=90", "4"), True),
    (("bar", "|", "5"), True),
    (("ch1", "E₄ 𝅘𝅥", "6"), True),
    (("tie ch1", "– 𝅗𝅥", "7"), True),
    (("ch1", "F₄ 𝅘𝅥", "8"), True),
    (("ch1", "G₄ 𝅘𝅥", "9"), True),
    (("slide ch1", "⇝C₅ 𝅘𝅥", "10"), True),
    (("pause", "r 𝅗𝅥", "11"), True),
]

SHEET_SPEC = [
    ("sec-head", "A", None),
    ("card ch1", "", "1"),
    ("card ch1", "", "2"),
    ("tab-tempo", "♩=90", "4"),
    ("tab-bar", "", None),
    ("card ch1", "", "6"),
    ("card rest tie ch1", "– – 𝅗𝅥", "7"),
    ("card ch1", "", "8"),
    ("card ch1", "", "9"),
    ("card ch1", "", "10"),
    ("card rest", "rest 𝅗𝅥", "11"),
]

PROBE = """
async (SRC) => {
  // Typed input renders on a short settle (the per-keystroke debounce): the
  // probe reports the FIRST render whose title matches the typed melody.
  const expect = String(SRC).split("\\n").find(l =>
    /^#/.test(l) && !/^#\\s*tempo\\b/.test(l) && !/^#\\s*swing\\b/.test(l));
  const wantTitle = expect ? expect.replace(/^#\\s*/, "") : "";
  const ta = document.getElementById('src');
  ta.value = SRC;
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  const t0 = Date.now();
  while (document.getElementById('title').textContent !== wantTitle &&
         Date.now() - t0 < 3000) {
    await new Promise(r => setTimeout(r, 15));
  }
  const stripRows = [...document.querySelectorAll('#tokens > .tok')].map(el => ({
    cls: el.className,
    text: (el.textContent || '').replace(/\\s+/g, ' ').trim(),
    di: el.dataset.i != null ? el.dataset.i : null,
    role: el.getAttribute('role') || null,
    label: el.getAttribute('aria-label') || null,
    title: el.title || null,
  }));
  const focusRows = [...document.querySelectorAll('#focusTokens > .tok')].map(el => ({
    cls: el.className, text: (el.textContent || '').replace(/\\s+/g, ' ').trim(),
    di: el.dataset.i != null ? el.dataset.i : null,
  }));
  const sheetRows = [...document.getElementById('sheet').children].map(el => ({
    cls: el.className.replace('tok', '').trim(),
    text: (el.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 24),
    di: el.dataset ? (el.dataset.i != null ? el.dataset.i : null) : null,
  }));
  return { stripRows, focusRows, sheetRows,
           sheetMode: document.getElementById('sheet').className };
}
"""

HIGHLIGHT = """
(I) => {
  highlightToken(I, null, undefined, false);
  const lit = (scope) => [...document.querySelectorAll(scope)].map(el => el.dataset ? el.dataset.i : el.getAttribute('data-i') || el.className.includes('now') ? (el.dataset.i ?? '') : '').filter(x => x !== '');
  const inStrip = [...document.querySelectorAll('#tokens .tok.now')].map(el => el.dataset.i);
  const inFocus = [...document.querySelectorAll('#focusTokens .tok.now')].map(el => el.dataset.i);
  const inSheet = [...document.querySelectorAll('#sheet .now')].map(el => el.dataset.i);
  const anywhere = document.querySelectorAll('.now').length;
  return { inStrip, inFocus, inSheet, anywhere };
}
"""

FOCUS_RESTORE = """
() => {
  const first = [...document.querySelectorAll('#tokens .tok[role="button"]')]
    .find(el => el.dataset.i === '1');
  first.focus();
  render();
  const strip = [...document.querySelectorAll('#tokens .tok[role="button"]')];
  return { focused: document.activeElement.dataset.i || null,
           tabStops: strip.filter(el => el.tabIndex === 0).length,
           onFocused: document.activeElement.dataset.i };
}
"""

# Debounce contract: typed edits coalesce into one render per settle — during
# the settle window the previous render stays on screen (title and strip both
# keep showing the old content), and the fresh render appears by the next
# beat. The 20 ms early read is deliberately under the debounce budget so an
# immediate render fails here; the 900 ms late read is ~15x over it so even a
# slow CI machine is served.
DEBOUNCE_SRC = "# Debounced\n\nC6 D6 E6"
DEBOUNCE = """
async (SRC) => {
  const ta = document.getElementById('src');
  const tokens = document.getElementById('tokens');
  const beforeTitle = document.getElementById('title').textContent;
  const beforeText = (tokens.textContent || '').replace(/\\s+/g, ' ').trim();
  ta.value = SRC;
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  await new Promise(r => setTimeout(r, 20));
  const earlyTitle = document.getElementById('title').textContent;
  const earlyText = (tokens.textContent || '').replace(/\\s+/g, ' ').trim();
  await new Promise(r => setTimeout(r, 900));
  const lateTitle = document.getElementById('title').textContent;
  const lateText = (tokens.textContent || '').replace(/\\s+/g, ' ').trim();
  return { beforeTitle, earlyTitle, lateTitle,
           beforeText, earlyText, lateText };
}
"""


from suite_server import start_server


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS,
                                        args=["--autoplay-policy=no-user-gesture-required"])
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(f"{base}?inst={PIN_INST}")
            page.wait_for_function(WAIT)
            page.evaluate(
                "() => { const b = document.getElementById('playback');"
                " b.querySelector('.collapse-btn').click(); }")
            r = page.evaluate(PROBE, MELODY)

            # --- token strip (and the zen reading strip get the same chips)
            if len(r["stripRows"]) != len(STRIP_SPEC):
                failures.append(
                    f"strip: expected {len(STRIP_SPEC)} chips, got "
                    f"{len(r['stripRows'])}:\n    "
                    + "\n    ".join(f"{x['cls']!r} {x['text']!r} i={x['di']}"
                                    for x in r["stripRows"]))
            else:
                for got, (want, role) in zip(r["stripRows"], STRIP_SPEC):
                    cls_prefix, text, di = want
                    cls = got["cls"].split()
                    prefix = cls_prefix.split()
                    if not all(p in cls for p in prefix):
                        failures.append(
                            f"strip: chip i={di} class prefix mismatch — "
                            f"need {prefix} in {got['cls']!r}")
                    if got["text"] != text:
                        failures.append(
                            f"strip: chip i={di} text {got['text']!r} != "
                            f"{text!r}")
                    if role and got["role"] != "button":
                        failures.append(
                            f"strip: chip i={di} must be role=button (click/"
                            f"Enter), got role={got['role']!r}")
                    if not role and got["role"] is not None:
                        failures.append(
                            f"strip: chip i={di} must NOT be a button")
                    if got["di"] != di:
                        failures.append(
                            f"strip: chip data-i {got['di']} != {di}")

            if len(r["focusRows"]) != len(STRIP_SPEC):
                failures.append(
                    f"focus strip: expected {len(STRIP_SPEC)} chips, got "
                    f"{len(r['focusRows'])}")

            # --- sheet composition
            if len(r["sheetRows"]) != len(SHEET_SPEC):
                failures.append(
                    f"sheet: expected {len(SHEET_SPEC)} children, got "
                    f"{len(r['sheetRows'])}:\n    "
                    + "\n    ".join(f"{x['cls']!r} {x['text']!r}"
                                    for x in r["sheetRows"]))
            else:
                for got, (cls_prefix, text, di) in zip(r["sheetRows"],
                                                       SHEET_SPEC):
                    prefix = cls_prefix.split()
                    cls = got["cls"].split()
                    for want in prefix:
                        if want not in cls:
                            failures.append(
                                f"sheet: class {want!r} missing from "
                                f"{got['cls']!r} at data-i={di}")
                    if text and got["text"] != text:
                        failures.append(
                            f"sheet: text {got['text']!r} != {text!r}")
                    if got["di"] != di:
                        failures.append(
                            f"sheet: data-i {got['di']} != {di}")

            # bad junk must never reach the grid
            grid_text = page.evaluate(
                "() => document.getElementById('sheet').textContent")
            if "zz" in grid_text:
                failures.append("sheet: junk ('zz') must not leak into the grid")

            # --- scroll band: the named bar keeps its tagged line
            page.evaluate("setDisplayMode('scroll')")
            r2 = page.evaluate(PROBE, MELODY)
            heads_scroll = [row["cls"] for row in r2["sheetRows"]
                            if "sec-head" in row["cls"]]
            bars_scroll = [row for row in r2["sheetRows"]
                           if "tab-bar" in row["cls"]]
            if heads_scroll:
                failures.append(
                    "scroll: the band must not grow header rows "
                    f"(found {heads_scroll})")
            if not any("has-note" in row["cls"] for row in bars_scroll):
                failures.append(
                    "scroll: the named bar must keep a tagged line "
                    "(tab-bar has-note)")
            page.evaluate("setDisplayMode('grid')")

            # --- highlightToken propagation
            h = page.evaluate(HIGHLIGHT, "10")
            if h["inStrip"] != ["10"] or h["inFocus"] != ["10"] or \
                    h["inSheet"] != ["10"]:
                failures.append(
                    f"highlight: .now must land on data-i=10 in strip, focus "
                    f"strip and sheet, got strip {h['inStrip']} focus "
                    f"{h['inFocus']} sheet {h['inSheet']}")
            if h["anywhere"] != 3:
                failures.append(
                    f"highlight: old .now marks must clear (found "
                    f"{h['anywhere']} marked elements, want 3)")

            # --- focus restores across the rebuild
            fr = page.evaluate(FOCUS_RESTORE)
            if fr["focused"] != "1" or fr["onFocused"] != "1":
                failures.append(
                    f"rebuild: the focused token must keep focus across a "
                    f"restore (got focused {fr['focused']!r})")
            if fr["tabStops"] != 1:
                failures.append(
                    f"rebuild: exactly one roving tab stop must survive "
                    f"(got {fr['tabStops']})")

            # --- typed edits coalesce into one render per settle ---
            d = page.evaluate(DEBOUNCE, DEBOUNCE_SRC)
            if d["earlyTitle"] != d["beforeTitle"] or \
                    d["earlyText"] != d["beforeText"]:
                failures.append(
                    "debounce: within the settle window the previous render "
                    f"must stay on screen (title {d['beforeTitle']!r}->"
                    f"{d['earlyTitle']!r}, strip changed="
                    f"{d['earlyText'] != d['beforeText']})")
            if d["lateTitle"] != "Debounced":
                failures.append(
                    "debounce: after the settle the new render must be on " +
                    f"screen (title {d['lateTitle']!r} != 'Debounced')")
            if d["lateText"] == d["beforeText"]:
                failures.append(
                    "debounce: after the settle the strip must reflect the "
                    "typed melody (it still reads the old one)")

            # --- print popup: the popup carries the printable document
            # (title, sheet, blob origin) — the same bytes the Download
            # button saves, whatever sink produces it.
            with page.expect_popup() as pop:
                page.evaluate("() => document.getElementById('print').click()")
            popup = pop.value
            try:
                popup.wait_for_load_state("load", timeout=15000)
                if not popup.url.startswith("blob:") and \
                        "file" not in popup.url:
                    failures.append(
                        f"print: popup origin unexpected ({popup.url})")
                ptitle = popup.title()
                psheet = popup.evaluate(
                    "() => ({sheet: !!document.getElementById('sheet'),"
                    " cards: document.querySelectorAll('#sheet .card').length,"
                    " h1: (document.querySelector('h1') || {textContent:''})"
                    " .textContent})")
                if not psheet["sheet"]:
                    failures.append(f"print: popup lacks the sheet ({psheet})")
                elif psheet["cards"] <= 0:
                    failures.append("print: popup sheet has no cards")
                if "Debounced" not in ptitle:
                    failures.append(
                        f"print: popup title {ptitle!r} lacks the song title")
                if psheet["h1"] != ptitle:
                    failures.append(
                        f"print: popup heading {psheet['h1']!r} != doc title "
                        f"{ptitle!r}")
            except Exception as e:
                failures.append(f"print: popup probe failed {e}")
            finally:
                popup.close()

            if errs:
                failures.append(f"page errors {errs}")
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: the render path's chips, grid composition, scroll-band "
          "difference, highlight propagation and focus restore are pinned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
