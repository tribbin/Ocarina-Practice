#!/usr/bin/env python3
# Bad-chip presentation: junk the grammar cannot consume shows as a
# token-shaped pill (tan --token-neutral, like the bar chips) carrying the
# raw junk text with a wavy spell-check scribble on top. Earlier takes:
# a bare transparent chip (unreadable) and before that an opaque accent box
# (illegible on the OoT theme's grass panels). Asserts computed styles in
# BOTH themes, the tooltip, and that junk never leaks into the fingering-
# chart grid; also saves screenshots for eyeballing under /tmp (not
# asserted).
#
#   python3 tests/bad_chip_style.py      # headless & silent

import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function'")
INJECT = """async () => {
  // Typed input renders on a settle (the per-keystroke debounce): poll for
  // the strip change instead of reading the DOM synchronously.
  const ta = document.getElementById('src');
  ta.value = 'zz C4 | yy';
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  const t0 = Date.now();
  while (!document.querySelector('#tokens .tok.bad') &&
         Date.now() - t0 < 3000) {
    await new Promise(r => setTimeout(r, 15));
  }
  const el = document.querySelector('#tokens .tok.bad');
  if (!el) return null;
  const cs = getComputedStyle(el);
  const strip = [...document.querySelectorAll('#tokens .tok.bad')]
    .map(b => b.textContent);
  // Grid: junk must NOT produce chart cards — only real tokens may.
  const sheetText = document.getElementById('sheet').textContent || "";
  return {
    deco: cs.textDecorationStyle, bg: cs.backgroundColor,
    color: cs.color, text: el.textContent, title: el.title,
    stripBads: strip,
    sheetHasJunk: /zz|yy/.test(sheetText),
    sheetCards: document.getElementById('sheet').children.length,
  };
}
"""


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
    shots = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            for theme, suffix in (("", "default"), ("?oot", "oot")):
                page = browser.new_page()
                errs = []
                page.on("pageerror", lambda e, s=suffix: errs.append(s + ": " + str(e)))
                page.goto(f"{base}{theme}")
                page.wait_for_function(WAIT)
                page.evaluate("document.getElementById('playback')"
                              + ".querySelector('.collapse-btn').click()")
                r = page.evaluate(INJECT)
                if r is None:
                    failures.append(f"{suffix or 'default'}: no .tok.bad chip "
                                    "rendered from junk input 'zz … | yy'")
                else:
                    if r["deco"] != "wavy":
                        failures.append(
                            f"{suffix or 'default'}: bad chip must carry a "
                            f"wavy scribble, got {r['deco']!r}")
                    # Chip-shaped like every other token (tan pill via
                    # --token-neutral in BOTH themes), with the scribble on it.
                    if r["bg"] in ("rgba(0, 0, 0, 0)", "transparent"):
                        failures.append(
                            f"{suffix or 'default'}: bad chip must look like a "
                            f"token pill (neutral background), got transparent")
                    if r["text"] != "zz":
                        failures.append(
                            f"{suffix or 'default'}: chip must show the raw "
                            f"junk, got {r['text']!r}")
                    if "notation" not in r["title"]:
                        failures.append(
                            f"{suffix or 'default'}: chip tooltip missing, "
                            f"got {r['title']!r}")
                    if len(r["stripBads"]) != 2:
                        failures.append(
                            f"{suffix or 'default'}: expected 2 bad chips "
                            f"(zz, yy) in the strip, got {r['stripBads']!r}")
                    if r["sheetHasJunk"]:
                        failures.append(
                            f"{suffix or 'default'}: the fingering-chart grid "
                            f"must not render junk cards (zz/yy found)")
                    if r["sheetCards"] != 2:
                        failures.append(
                            f"{suffix or 'default'}: grid must keep only the "
                            f"note card and the bar (2 children), got "
                            f"{r['sheetCards']}")
                shots.append((suffix, page))
                if errs:
                    failures.append(f"page errors {errs}")
            # Screenshots for human eyeballing (not asserted here — engine
            # timing hiccups on element screenshots must never fake a red,
            # the assertions above are the contract).
            for suffix, page in shots:
                strip = page.query_selector("#tokens")
                if strip:
                    try:
                        strip.screenshot(path=f"/tmp/opencode/bad-{suffix}.png")
                    except Exception:
                        print(f"  (screenshot skipped: {suffix})")
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: bad chips are token pills (--token-neutral) with the "
          "raw junk text + wavy scribble in both themes; junk stays out of "
          "the chart grid; screenshots in /tmp/opencode/bad-*.png.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
