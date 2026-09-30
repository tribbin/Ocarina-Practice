#!/usr/bin/env python3
# Small-screen layout pin (Robin's SMALL SCREENS spec, approved 2026-09-30):
# a phone is for play/practice, not editing. The layout pass hides the
# editor's own face on narrow screens, stacks the playback head into one
# centered row per control group, drops the Hyrule backdrop in portrait,
# and gives the 42-column keyboard a fixed column width with auto-scroll
# to the sounding key instead of crushed ~7px keys. Zen stays as-is by
# construction (every rule is scoped to the non-zen chrome; the standing
# zen_notebar suite guards the zen geometry).
#
#   1. Phone editor face: expand/clear cluster, the two save/load pairs and
#      the editor sheet + legend are display:none; the Song Library picker
#      (how a phone loads a song) stays laid out.
#   2. Playback head stacks: one row per control group, strictly
#      top-to-bottom, no page-level horizontal overflow.
#   3. Portrait: the oot-theme backdrop layer (body::before photo) is
#      display:none on a phone viewport; the theme base colour is intact.
#   4. Keyboard keeps a readable width: at the phone viewport #kb is
#      horizontally scrollable; at a desktop viewport the board fits and
#      never scrolls.
#   5. The keyboard tracks the sounding key: during a real playback run on
#      the phone viewport the .key.now highlight lands inside #kb's visible
#      window (the board glides/snaps to the active key); the desktop board
#      fits, so scrollLeft stays put.
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

            # ---------- 4: keyboard keeps a readable width ----------
            print('== keyboard width phone vs desktop', flush=True)
            phoneKb = page.evaluate("""
              () => {
                const kb = document.getElementById('kb');
                return { sw: kb.scrollWidth, cw: kb.clientWidth,
                         pkey: getComputedStyle(
                           kb.querySelector('.pkey')).width };
              }""")
            if phoneKb["sw"] <= phoneKb["cw"]:
                failures.append(
                    "on a phone the 42-column keyboard must be horizontally "
                    f"scrollable (scrollWidth {phoneKb['sw']} <= clientWidth "
                    f"{phoneKb['cw']}) — crushed ~7px keys were the point")
            ctx.close()

            ctx = browser.new_context(viewport=DESK)
            page = ctx.new_page()
            boot(page, base)
            deskKb = page.evaluate("""
              () => {
                const kb = document.getElementById('kb');
                return { sw: kb.scrollWidth, cw: kb.clientWidth };
              }""")
            if deskKb["sw"] > deskKb["cw"] + 1:
                failures.append(
                    "on a desktop the keyboard must fit its panel and never "
                    f"scroll (scrollWidth {deskKb['sw']} > clientWidth "
                    f"{deskKb['cw']})")

            # ---------- 5: keyboard tracks the sounding key ----------
            print('== keyboard follows the active key', flush=True)
            ctx, page = browser.new_context(
                viewport=PHONE, is_mobile=True, has_touch=True), None
            page = ctx.new_page()
            boot(page, base)
            track = page.evaluate("""
              () => new Promise((resolve, reject) => {
                const notes = window.NOTES;
                const low = notes[0], high = notes[notes.length - 1];
                const kb = document.getElementById('kb');
                const pre = { scroll: kb.scrollLeft,
                              fits: kb.scrollWidth <= kb.clientWidth };
                const SRC = "# phone kb\\n# tempo 120\\n| " +
                            low + "/2 " + high + "/1";
                const t0 = Date.now();
                const arm = () => {
                  document.getElementById('src').value = SRC;
                  render();
                  if (document.getElementById('title').textContent !==
                      "phone kb") {
                    if (Date.now() - t0 > 4000) {
                      reject(new Error("title never matched")); return;
                    }
                    setTimeout(arm, 30);
                    return;
                  }
                  const probe = () => {
                    const el = kb.querySelector(
                      '.key.now[data-note="' + high + '"]');
                    if (!el) {
                      if (Date.now() - t0 > 6000) {
                        reject(new Error("high note never highlighted"));
                        return;
                      }
                      setTimeout(probe, 50);
                      return;
                    }
                      setTimeout(() => {
                        // Measure BEFORE stopMelody: stopping re-cues the
                        // first note, which scrolls the board back to start.
                        const k = kb.getBoundingClientRect();
                        const c = el.getBoundingClientRect();
                        const out = {
                          pre: pre,
                          scroll: kb.scrollLeft,
                          inView: c.left >= k.left - 2 &&
                                  c.right <= k.right + 2,
                          high: high,
                        };
                        stopMelody();
                        resolve(out);
                      }, 400);
                  };
                  playMelody(0);
                  probe();
                };
                arm();
              })
            """)
            if track["pre"]["fits"]:
                failures.append(
                    f"the keyboard leg presumes a scrollable board on a "
                    f"phone (pre-check: scrollWidth fit the panel)")
            if track["pre"]["scroll"] != 0:
                failures.append(
                    f"the keyboard must start at scrollLeft 0 before play "
                    f"(got {track['pre']['scroll']})")
            if track["scroll"] <= 5:
                failures.append(
                    f"the keyboard must scroll toward the sounding high key "
                    f"{track['high']} (scrollLeft {track['scroll']})")
            if not track["inView"]:
                failures.append(
                    f"the sounding key {track['high']} must land inside the "
                    "keyboard's visible window after the auto-scroll")
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
          "stacked into rows, portrait backdrop off, keyboard keeps a "
          "readable scrollable width that follows the sounding key, and the "
          "desktop layout is untouched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
