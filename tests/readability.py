#!/usr/bin/env python3
# General readability gate (Robin, 2026-09-25): not a selector roster — a
# scanner. In each app STATE (base layout with the collapsed blocks open, the
# floating tuner engaged, zen with the in-card tuner, every popupable open,
# the dev panel) it walks EVERY visible element, and for anything that paints
# its own text (or a button-owned glyph shape) resolves the real computed
# color against the composited background behind it (the ancestor
# background-color chain, rgba stops blended) and holds the WCAG thresholds
# (4.5 normal text, 3.0 large text / glyph shapes). A failing state names the
# element path, what it shows, and the ratio — and every state must MEASURE
# something (a state that measures nothing fails: unreadable-by-absence is
# the blind spot this sweep exists to kill).
#
#   python3 tests/readability.py       # headless & silent

import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function' && window.OCA_PRACTICE")

SCAN = r"""
() => {
  const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'META', 'LINK',
                             'TITLE', 'HEAD', 'BR', 'OPTION', 'OPTGROUP',
                             'DATALIST', 'AREA', 'TEMPLATE']);
  const c2u = (s) => {
    if (s === 'transparent') return [0, 0, 0, 0];
    const m = s.match(/rgba?\(([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)(?:[,/ ]+([\d.]+))?\)/);
    if (!m) return [0, 0, 0, 1];
    return [ +m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4] ];
  };
  const over = (back, front) => front[3] >= 1 ? front : [
    Math.round(front[0] * front[3] + back[0] * (1 - front[3])),
    Math.round(front[1] * front[3] + back[1] * (1 - front[3])),
    Math.round(front[2] * front[3] + back[2] * (1 - front[3])), 1];
  const lum = (rgb) => {
    const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2]);
  };
  const path = (el) => {
    const bits = [];
    let n = el;
    while (n && n.nodeType === 1 && bits.length < 4) {
      let bit = n.tagName.toLowerCase();
      if (n.id) { bits.unshift(bit + '#' + n.id); break; }
      if (n.className) bit += '.' + String(n.className).trim().split(/\s+/).slice(0, 2).join('.');
      bits.unshift(bit);
      n = n.parentElement;
    }
    return bits.join(' > ');
  };
  const measured = [];
  const offenders = [];
  const dedupe = new Set();
  const els = document.querySelectorAll('body *');
  for (const el of els) {
    if (SKIP_TAGS.has(el.tagName)) continue;
    const st = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (st.display === 'none' || st.visibility === 'hidden' ||
        r.width <= 0 || r.height <= 0) continue;
    if (el.closest('[hidden]') || el.closest('.sr-only')) continue;
    const ownText = [...el.childNodes].some((n) =>
      n.nodeType === 3 && n.textContent.trim()) ||
      (el.tagName === 'SELECT' && el.options.length > 0);
    const glyph = el.matches('button') && el.querySelector(':scope > svg');
    if (!ownText && !glyph) continue;
    measured.push(el);
    const fg = c2u(st.color);
    const chain = [];
    let n = el;
    while (n && n.nodeType === 1) { chain.push(n); n = n.parentElement; }
    let back = [255, 255, 255, 1];
    for (let i = chain.length - 1; i >= 0; i--) {  // far ancestor first
      const a = c2u(getComputedStyle(chain[i]).backgroundColor);
      if (a[3] > 0) back = over(back, a);
    }
    if (fg[3] === 0) continue;
    const l1 = lum(fg), l2 = lum(back);
    let ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    const fs = parseFloat(st.fontSize);
    const big = fs >= 24 || (fs >= 18.66 && parseInt(st.fontWeight) >= 700);
    const limit = big ? 3.0 : 4.5;
    ratio = Math.round(ratio * 100) / 100;
    if (ratio >= limit) continue;
    const key = path(el) + '|' + st.color + '|' + back.join(',');
    if (dedupe.has(key)) continue;
    dedupe.add(key);
    const shown = ownText
      ? el.textContent.trim().slice(0, 26)
      : 'glyph shape';
    offenders.push({ path: path(el), shown, ratio, limit, fg: st.color,
                     back: 'rgb(' + back.join(',') + ')' });
    if (offenders.length >= 40) break;
  }
  return { measured: measured.length, offenders };
}
"""

# States the scanner walks, per look. Each state carries the minimum number
# of distinct paths the scan must MEASURE — a change that empties a state's
# real content would otherwise read as pass-by-nothing. Closers are lists of
# closing operations (zen's tuner needs both the stop and the exit).
STATES = [
    ("base", ("() => document.querySelectorAll('.block > .box-head .collapse-btn')"
              ".forEach(b => b && b.click())", None, 35)),
    ("tuner", ("() => document.getElementById('mirrorPractice').click()",
               ["() => window.OCA_PRACTICE.stop()"], 5)),
    ("zen", ("() => document.getElementById('zen').click()",
             ["() => document.getElementById('focusExit').click()"], 12)),
    ("zen+tuner", ("() => document.getElementById('practiceFocusBtn').click()",
                   ["() => window.OCA_PRACTICE.stop()",
                    "() => document.getElementById('focusExit').click()"], 15)),
    ("theme menu", ("() => document.getElementById('themeBtn').click()",
                    ["() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))"], 3)),
    ("help overlay", ("() => document.getElementById('helpBtn').click()",
                      ["() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))"], 10)),
    ("library dropdown", ("() => document.querySelector('.lib-dd-btn').click()",
                          ["() => document.getElementById('src').click()"], 5)),
    ("save dialog", ("() => document.getElementById('libSave').click()",
                     ["() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))"], 4)),
    ("audio performance pop", ("() => document.getElementById('perfBtn').click()",
                               ["() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))"], 3)),
]
# The dev panel opens on its own documented fast path (?debug=1), before the
# other surfaces.
DEBUG_BOOT = "&debug=1"


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


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    looks = [("plain", "?plain"), ("hyrule", "?oot"), ("hifi", "?hifi")]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS,
                                        args=["--autoplay-policy=no-user-gesture-required"])
            for look, param in looks:
                page = browser.new_page()
                page.goto(base + param)
                page.wait_for_function(WAIT)

                # the dev panel: its own boot (?debug=1 opens it from load)
                dbg = browser.new_page()
                dbg.set_viewport_size({"width": 1440, "height": 900})
                dbg.goto(base + param + DEBUG_BOOT)
                dbg.wait_for_function(WAIT)
                dbg.wait_for_timeout(500)
                scan(dbg, None, "debug", look, failures, 4)
                dbg.close()

                for name, (opener, closers, minimum) in STATES:
                    if opener:
                        page.evaluate(opener)
                        page.wait_for_timeout(400)
                    scan(page, None, name, look, failures, minimum)
                    for closer in (closers or []):
                        page.evaluate(closer)
                    if closers:
                        page.wait_for_timeout(350)

                page.close()
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: the full-DOM scanner measured every state (base, tuner, "
          "zen, tuners-in-zen, every popupable, the dev panel) in Plain, "
          "Hyrule and HiFi — nothing paints below the WCAG thresholds.")
    return 0


def scan(page, dbg, state, look, failures, minimum):
    """Walk one state on one page and hold its findings."""
    result = page.evaluate(SCAN)
    if result["measured"] < minimum:
        failures.append(
            f"scanner [{look}/{state}] measured {result['measured']} texted/"
            f"glyphed elements (< {minimum}) — the state starved the walk")
    for o in result["offenders"]:
        failures.append(
            f"contrast [{look}/{state}] {o['path']} — '{o['shown']}': "
            f"{o['ratio']} < {o['limit']} (fg {o['fg']} on {o['back']})")


if __name__ == "__main__":
    sys.exit(main())
