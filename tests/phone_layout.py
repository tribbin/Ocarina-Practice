#!/usr/bin/env python3
# Small-screen layout pin (Robin's SMALL SCREENS spec, approved 2026-09-30):
# a phone is for play/practice, not editing. The layout pass hides the
# editor's own face on narrow screens, stacks the playback head into one
# centered row per control group, drops the Hyrule backdrop in portrait,
# drops the token strip, centers the three tab-tools rows, and trims the
# 42-column keyboard to the instrument's playable span — out-of-range keys
# are hidden so the board fits statically, with NO auto-scroll (Robin
# rejected the scroll-follow first pass). Zen stays as-is by construction
# (every rule is scoped to the non-zen chrome; the standing zen_notebar
# suite guards the zen geometry).
#
#   1. Phone editor face: expand/clear cluster, the two save/load pairs and
#      the editor sheet + legend are display:none; the Song Library picker
#      (how a phone loads a song) stays laid out.
#   2. Playback head stacks: one row per control group, strictly
#      top-to-bottom, no page-level horizontal overflow.
#   3. Portrait: the oot-theme backdrop layer (body::before photo) is
#      display:none on a phone viewport; the theme base colour is intact.
#   4. Keyboard shows only playable keys, statically: on a phone every
#      out-of-range key (.key.oor) and its empty cell (.pkey.kb-oor) are
#      display:none, and the .oct rows dissolve to display:contents so the
#      surviving cells flex evenly as direct children of #kb — every key
#      the same width, no horizontal scrolling. On desktop the octave rows
#      keep their flex layout and every key stays visible (dimmed).
#   5. Phone chrome trims: with the playback block expanded, the token
#      strip (#tokens) is still display:none; the three tab-tools rows
#      (Enlarge / Grid|Scroll|Single / share|print|download) stack
#      top-to-bottom, each centered on the viewport.
#   6. Desktop regression: the editor face, the backdrop layer and the
#      1fr-auto-1fr playback grid are all unchanged.
#
#   python3 tests/phone_layout.py      # headless & silent

import sys

from playwright.sync_api import sync_playwright

from suite_server import start_server

HEADLESS = "--headed" not in sys.argv
PHONE = {"width": 390, "height": 844}
DESK = {"width": 1440, "height": 900}
# settled-#scale rendezvous (the instruments_load convention): boot fills
# the library select only after loadInstrument fully resolves, so the
# editor/playback faces are in their final small-screen state by then.
SCALE_READY = ("() => { const s = document.getElementById('scale');"
               " return s && s.options.length > 0; }")


def boot(page, base):
    page.goto(base)
    page.wait_for_function(SCALE_READY)
    page.wait_for_timeout(200)


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=HEADLESS,
                args=["--autoplay-policy=no-user-gesture-required"])

            # ---------- 1: phone editor face ----------
            print('== phone editor face', flush=True)
            ctx = browser.new_context(viewport=PHONE, is_mobile=True,
                                      has_touch=True)
            page = ctx.new_page()
            boot(page, base)
            face = page.evaluate("""
              () => {
                const d = sel => {
                  const el = document.querySelector(sel);
                  if (!el) return "missing";
                  const r = el.getBoundingClientRect();
                  return getComputedStyle(el).display + "/" +
                         Math.round(r.width) + "x" + Math.round(r.height);
                };
                return {
                  libBtn: d("#libDdBtn"),
                  headLeft: d("#inputBlock .head-left"),
                  libPairs: d("#inputBlock .lib-pairs"),
                  src: d("#inputBlock textarea#src"),
                  legend: d("#inputBlock .input-legend"),
                };
              }""")
            if not (face["libBtn"].startswith("inline-flex/") and
                    not face["libBtn"].endswith("0x0")):
                failures.append(
                    "the Song Library picker must stay laid out on a phone "
                    f"(got {face['libBtn']!r}) — it is how a phone loads a "
                    "song")
            for sel, key in ((".head-left", "headLeft"),
                             (".lib-pairs", "libPairs"),
                             ("textarea#src", "src"),
                             (".input-legend", "legend")):
                if not face[key].startswith("none"):
                    failures.append(
                        f"#inputBlock {sel} must be display:none on a phone "
                        f"(got {face[key]!r}) — the editor face is desktop "
                        "furniture")

            # ---------- 2: playback head stacks into rows ----------
            print('== playback head vertical rows', flush=True)
            rows = page.evaluate("""
              () => {
                const head = document.querySelector('#playback > .box-head');
                const kids = [...head.children]
                  .filter(el => getComputedStyle(el).display !== 'none')
                  .map(el => {
                    const r = el.getBoundingClientRect();
                    return { name: el.id || el.className,
                             top: r.top, bottom: r.bottom, h: r.height };
                  });
                return {
                  dir: getComputedStyle(head).flexDirection,
                  kids: kids,
                  overflow: document.documentElement.scrollWidth - innerWidth,
                };
              }""")
            if rows["dir"] != "column":
                failures.append(
                    f"the phone playback head must stack as a column "
                    f"(flex-direction {rows['dir']!r})")
            if len(rows["kids"]) != 3:
                failures.append(
                    f"the playback head must show exactly the three control "
                    f"rows, found {len(rows['kids'])}: "
                    f"{[k['name'] for k in rows['kids']]}")
            else:
                for i in range(2):
                    a, b = rows["kids"][i], rows["kids"][i + 1]
                    if b["top"] < a["bottom"] - 1:
                        failures.append(
                            f"playback rows must stack strictly top-to-"
                            f"bottom: {a['name']} (bottom {a['bottom']}) "
                            f"overlaps {b['name']} (top {b['top']})")
                    if a["h"] <= 0 or b["h"] <= 0:
                        failures.append(
                            f"every playback row must be laid out "
                            f"({a['name']} h={a['h']}, {b['name']} "
                            f"h={b['h']})")
            if rows["overflow"] > 1:
                failures.append(
                    f"the phone page must not scroll horizontally "
                    f"(document overflows the viewport by "
                    f"{rows['overflow']}px)")

            # ---------- 3: no backdrop in portrait ----------
            print('== portrait backdrop off', flush=True)
            backdrop = page.evaluate("""
              () => {
                const cs = getComputedStyle(document.body, '::before');
                return {
                  theme: document.documentElement.getAttribute('data-theme'),
                  display: cs.display,
                  bg: cs.backgroundImage,
                };
              }""")
            if backdrop["theme"] != "oot":
                failures.append(
                    f"the fresh-browser default theme must be oot for this "
                    f"leg (got {backdrop['theme']!r})")
            elif backdrop["display"] != "none":
                failures.append(
                    "the Hyrule backdrop layer must be display:none in "
                    f"portrait on a phone (got display "
                    f"{backdrop['display']!r}, background "
                    f"{backdrop['bg']!r})")

            # ---------- 4: keyboard shows only playable keys, static ----------
            print('== keyboard shows only playable keys', flush=True)
            phoneKb = page.evaluate("""
              () => {
                const kb = document.getElementById('kb');
                const oor = [...kb.querySelectorAll('.key.oor')];
                const playable = [...kb.querySelectorAll('.key[data-note]')];
                const emptyCells = [...kb.querySelectorAll('.pkey.kb-oor')];
                const octs = [...kb.querySelectorAll('.oct')];
                return {
                  sw: kb.scrollWidth, cw: kb.clientWidth,
                  oorCount: oor.length,
                  oorHidden: oor.every(
                    el => getComputedStyle(el).display === 'none'),
                  playableCount: playable.length,
                  playableVisible: playable.every(
                    el => getComputedStyle(el).display !== 'none'),
                  emptyHidden: emptyCells.every(
                    el => getComputedStyle(el).display === 'none'),
                  octsDissolved: octs.every(
                    el => getComputedStyle(el).display === 'contents'),
                };
              }""")
            if phoneKb["oorCount"] == 0:
                failures.append(
                    "the board must mark its out-of-range keys .key.oor "
                    "(none found) so the phone view can hide them by class")
            elif not phoneKb["oorHidden"]:
                failures.append(
                    "out-of-range keys must be display:none on a phone so "
                    "the board shows only the playable span")
            if phoneKb["playableCount"] == 0:
                failures.append(
                    "the phone board must keep its playable keys "
                    "(no .key[data-note] found)")
            elif not phoneKb["playableVisible"]:
                failures.append(
                    "playable keys must stay visible on a phone")
            if not phoneKb["emptyHidden"]:
                failures.append(
                    "cells holding no playable key must be display:none on "
                    "a phone, or the board keeps its full 42-column width")
            if not phoneKb["octsDissolved"]:
                failures.append(
                    "the .oct rows must dissolve to display:contents on a "
                    "phone so the surviving cells flex to equal widths "
                    "(otherwise the sparse octaves stretch their keys)")
            if phoneKb["sw"] > phoneKb["cw"] + 1:
                failures.append(
                    "the phone keyboard must fit statically, without a "
                    f"horizontal scroll strip (scrollWidth {phoneKb['sw']} "
                    f"> clientWidth {phoneKb['cw']})")
            ctx.close()

            ctx = browser.new_context(viewport=DESK)
            page = ctx.new_page()
            boot(page, base)
            page.click("#playback .collapse-btn")
            deskKb = page.evaluate("""
              () => {
                const kb = document.getElementById('kb');
                const oor = kb.querySelectorAll('.key.oor');
                const octs = [...kb.querySelectorAll('.oct')];
                return { sw: kb.scrollWidth, cw: kb.clientWidth,
                         oorVisible: oor.length > 0 &&
                           getComputedStyle(oor[0]).display !== 'none',
                         octsFlex: octs.every(
                           el => getComputedStyle(el).display === 'flex'),
                         tokens: getComputedStyle(
                           document.getElementById('tokens')).display };
              }""")
            if deskKb["sw"] > deskKb["cw"] + 1:
                failures.append(
                    "on a desktop the keyboard must fit its panel and never "
                    f"scroll (scrollWidth {deskKb['sw']} > clientWidth "
                    f"{deskKb['cw']})")
            if not deskKb["oorVisible"]:
                failures.append(
                    "on a desktop the out-of-range keys must stay visible "
                    "(dimmed, not hidden)")
            if not deskKb["octsFlex"]:
                failures.append(
                    "on a desktop the octave rows must keep their grouped "
                    "flex layout (the display:contents dissolve is a "
                    "small-screen rule only)")
            if deskKb["tokens"] == "none":
                failures.append(
                    "on a desktop the token strip must stay visible when "
                    f"the playback block is expanded (display "
                    f"{deskKb['tokens']!r})")

            # ---------- 5: phone chrome trims — token strip + tab tools ----------
            print('== token strip hidden, tab-tools centered', flush=True)
            ctx, page = browser.new_context(
                viewport=PHONE, is_mobile=True, has_touch=True), None
            page = ctx.new_page()
            boot(page, base)
            # Expand the playback block first: it boots collapsed, and the
            # collapsed state already hides #tokens via its own rule — the
            # leg must prove the SMALL-SCREEN rule hides it even when open.
            page.click("#playback .collapse-btn")
            tools = page.evaluate("""
              () => {
                const cx = el => {
                  const r = el.getBoundingClientRect();
                  return r.left + r.width / 2;
                };
                const rows = ['.tools-left', '.mode-seg', '.tools-right']
                  .map(sel => {
                    const el = document.querySelector('.tab-tools ' + sel);
                    const r = el.getBoundingClientRect();
                    return { name: sel, top: r.top, bottom: r.bottom,
                             cx: cx(el), h: r.height };
                  });
                return {
                  tokens: getComputedStyle(
                    document.getElementById('tokens')).display,
                  rows: rows, vw: innerWidth,
                };
              }""")
            if tools["tokens"] != "none":
                failures.append(
                    "the token strip (#tokens) must be display:none on a "
                    f"phone (got display {tools['tokens']!r})")
            if any(r["h"] <= 0 for r in tools["rows"]):
                failures.append(
                    "all three tab-tools rows must be laid out on a phone: "
                    f"{[(r['name'], r['h']) for r in tools['rows']]}")
            else:
                for i in range(2):
                    a, b = tools["rows"][i], tools["rows"][i + 1]
                    if b["top"] < a["bottom"] - 1:
                        failures.append(
                            f"tab-tools rows must stack top-to-bottom: "
                            f"{a['name']} (bottom {a['bottom']}) overlaps "
                            f"{b['name']} (top {b['top']})")
                for r in tools["rows"]:
                    if abs(r["cx"] - tools["vw"] / 2) > 2:
                        failures.append(
                            f"tab-tools row {r['name']} must be centered "
                            f"(center {r['cx']:.0f}px vs viewport center "
                            f"{tools['vw'] / 2:.0f}px)")
            ctx.close()

            # ---------- 6: desktop regression ----------
            print('== desktop regression', flush=True)
            ctx, page = browser.new_context(viewport=DESK), None
            page = ctx.new_page()
            boot(page, base)
            desk = page.evaluate("""
              () => {
                const d = sel => {
                  const el = document.querySelector(sel);
                  return el ? getComputedStyle(el).display : "missing";
                };
                const before = getComputedStyle(document.body, '::before');
                const head = document.querySelector('#playback > .box-head');
                const cy = el => {
                  const r = el.getBoundingClientRect();
                  return r.top + r.height / 2;
                };
                const hl = document.querySelector('#playback .head-left');
                const tw = document.querySelector('#playback .t-wrap');
                document.querySelector('#inputBlock .collapse-btn').click();
                return {
                  headLeft: d("#inputBlock .head-left"),
                  libPairs: d("#inputBlock .lib-pairs"),
                  src: d("#inputBlock textarea#src"),
                  backdrop: { display: before.display,
                              bg: before.backgroundImage },
                  grid: getComputedStyle(head).display,
                  sameRow: Math.abs(cy(hl) - cy(tw)),
                };
              }""")
            if desk["headLeft"] == "none" or desk["libPairs"] == "none":
                failures.append(
                    "the desktop editor face must stay visible (head-left "
                    f"{desk['headLeft']!r}, lib-pairs "
                    f"{desk['libPairs']!r})")
            if desk["src"] == "none":
                failures.append(
                    "expanding the desktop editor must show the textarea "
                    f"(display {desk['src']!r})")
            if "hyrule" not in desk["backdrop"]["bg"] or \
                    desk["backdrop"]["display"] == "none":
                failures.append(
                    "the desktop landscape backdrop layer must stay painted "
                    f"(display {desk['backdrop']['display']!r}, background "
                    f"{desk['backdrop']['bg']!r})")
            if desk["grid"] != "grid":
                failures.append(
                    f"the desktop playback head must keep its 1fr-auto-1fr "
                    f"grid (display {desk['grid']!r})")
            if desk["sameRow"] > 12:
                failures.append(
                    "the desktop playback head groups must sit on one row "
                    f"(head-left vs transport centerline off by "
                    f"{desk['sameRow']}px)")
            ctx.close()

            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: phone editor face hidden (library kept), playback head "
          "stacked into rows, portrait backdrop off, the keyboard shows only "
          "playable keys on a static board, the token strip stays hidden and "
          "the tab-tools rows stack centered, and the desktop layout is "
          "untouched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
