#!/usr/bin/env python3
# Robin's HiFi retune batch (panel, 2026-09-26): the page-chassis button
# family walks onto one dark-amber chrome — #160a04 face with a thin white
# line while the control rests, #56300d on every engaged face; the segment
# row and the instrument select must NOT paint white on the black chassis;
# the zen call-to-action drops the bright LED red for the deeper #b32317
# with white text; and the LED rows fill in WHOLE segments — no gliding
# fill edge under ?hifi (the plum rules keep their .1s glide elsewhere).
#
# Legs assert computed styles BOTH sides (plain + ?hifi) like
# reduced_motion.py does, so a future scope break can't pass silently:
#   1. ghost / mode-seg / inst-sel faces flip to #160a04 under hifi and
#      stay as they were on plain;
#   2. engaged faces (seg .on, bigSmall aria-pressed) flip to #56300d;
#   3. the zen CTA paints #b32317 with white ink; plain keeps --accent;
#   4. .prac-fill / .prac-tok-fill transition-duration 0s under hifi,
#      0.1s on plain;
#   5. the fill-width writer (OCA_PRACTICE.fillWidth) quantizes to the
#      10px LED grid under hifi and passes through untouched on plain.
#
#   .venv/bin/python3 tests/hifi_retune.py

import sys
from pathlib import Path

from suite_server import QuietHandler, SuiteServer
import http.server
import socketserver
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BOOT_WAIT = ("window.NOTES && window.NOTES.length"
             " && typeof parse === 'function'")


def start_server():
    httpd = SuiteServer(("127.0.0.1", 0), QuietHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


PROBE = """
() => {
  // Stand-ins with the same class chains answer the same css as the real
  // (transient or stateful) controls; states are forced on themselves.
  const host = document.getElementById('inputBlock');
  const mk = (cls, parent) => {
    const d = document.createElement('div');
    d.className = cls;
    (parent || host).appendChild(d);
    return d;
  };
  const seg = mk('seg-btn on');
  const modeSeg = mk('mode-seg');
  const fill = mk('prac-fill', mk('prac-track'));
  const tokFill = document.createElement('span');
  tokFill.className = 'prac-tok-fill';
  host.appendChild(tokFill);
  const cs = (el) => {
    const s = getComputedStyle(el);
    return { bg: s.backgroundColor, col: s.color, td: s.transitionDuration };
  };
  const out = {
    seg: cs(seg), modeSeg: cs(modeSeg),
    fill: cs(fill), tokFill: cs(tokFill),
    zen: cs(document.getElementById('zen')),
    instSel: (() => {
      const el = document.getElementById('instSel');
      const s = getComputedStyle(el);
      return { bg: s.backgroundColor, isWhiteish: /rgba\\(255, ?255, ?255, ?\\.08\\)|rgb\\(255, ?255, ?255\\)/.test(s.backgroundColor) };
    })(),
    ghost: cs(document.getElementById('clear')),
  };
  // the fill-width seam: a 127px host, a half-filled edge must land on the
  // LED grid under hifi and pass through untouched on plain
  const wHost = mk('prac-track');
  wHost.style.width = '127px';
  const child = document.createElement('span');
  wHost.appendChild(child);
  window.OCA_PRACTICE.fillWidth(child, 50);
  out.fillWidthRaw = child.style.width;
  seg.remove(); modeSeg.remove(); fill.remove(); tokFill.remove(); wHost.remove();
  return out;
}
"""


def main():
    failures = []
    httpd = start_server()
    base = f"http://127.0.0.1:{httpd[1]}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            plain = page.evaluate(PROBE)
            page2 = browser.new_page()
            page2.goto(base + "?hifi")
            page2.wait_for_function(BOOT_WAIT)
            hifi = page2.evaluate(PROBE)

            def eq(a, b):
                return a is not None and b is not None and \
                    abs(sum(abs((a or 0) + sum(x or 0) - (b or 0) - 0) for a, b in zip(
                        [int(n) for n in (a or "0").replace("rgba", "rgb").replace("rgb(", "").replace(")", "").replace(",", " ").split()],
                        [int(n) for n in (b or "0").replace("rgba", "rgb").replace("rgb(", "").replace(")", "").replace(",", " ").split()
                         if n.strip()])) ) < 3

            # 1. resting faces
            want = (22, 10, 4)
            got = hifi["ghost"]["bg"] or ""
            if [int(t) for t in got.replace("rgba", "rgb").replace("rgb(", "").replace(")", "").split(",")[:3]] != list(want):
                failures.append(f"ghost face under hifi: {got} (want #160a04)")
            if plain["ghost"]["bg"] not in ("rgba(0, 0, 0, 0)", "transparent"):
                failures.append(f"plain ghost must stay transparent, got {plain['ghost']['bg']}")
            if hifi["modeSeg"]["bg"] != got:
                failures.append(f"mode-seg face under hifi: {hifi['modeSeg']['bg']} (want the same #160a04 family)")
            if hifi["instSel"]["isWhiteish"]:
                failures.append("the instrument select still paints whiteish under hifi — "
                                "no white surfaces on the black chassis")
            # 2. engaged face #56300d
            if hifi["seg"]["bg"] != "rgb(86, 48, 13)":
                failures.append(f"engaged seg face under hifi: {hifi['seg']['bg']} (want #56300d)")
            # 3. zen CTA
            if hifi["zen"]["bg"] != "rgb(179, 35, 23)":
                failures.append(f"hifi zen CTA: {hifi['zen']['bg']} (want #b32317)")
            if hifi["zen"]["col"] != "rgb(255, 255, 255)":
                failures.append(f"hifi zen CTA text: {hifi['zen']['col']} (want white)")
            # 4. glide gates: LED rows snap under hifi, keep the glide on plain
            for k, name in (("fill", ".prac-fill"), ("tokFill", ".prac-tok-fill")):
                if hifi[k]["td"] != "0s":
                    failures.append(f"{name} must not glide under hifi, transition {hifi[k]['td']}")
                if plain[k]["td"] != "0.1s":
                    failures.append(f"{name} lost its glide on plain, transition {plain[k]['td']}")
            # 5. the fill-width writer: quantized to the LED grid under hifi,
            #    a passthrough on plain (both computed by the page's own math)
            q = page2.evaluate(
                """() => {
                  const host = document.createElement('div');
                  host.className = 'prac-track'; host.style.width = '127px';
                  document.getElementById('inputBlock').appendChild(host);
                  const child = document.createElement('span');
                  host.appendChild(child);
                  window.OCA_PRACTICE.fillWidth(child, 50);
                  const w = (Math.floor(0.5 * 127 / 10) * 10 / 127) * 100;
                  const ok = Math.abs(parseFloat(child.style.width) - w) < 3;
                  host.remove();
                  return { got: child.style.width, want: w, ok };
                }""")
            if not q["ok"]:
                failures.append(
                    f"fillWidth under hifi settled at {q['got']} (want the "
                    f"{q['want']} LED-grid value)")
            if page.evaluate(
                """() => {
                  const host = document.createElement('div');
                  host.className = 'prac-track';
                  document.getElementById('inputBlock').appendChild(host);
                  const child = document.createElement('span');
                  host.appendChild(child);
                  window.OCA_PRACTICE.fillWidth(child, 50);
                  const ok = child.style.width === '50%';
                  host.remove();
                  return ok;
                }""") is not True:
                failures.append("fillWidth must be a plain passthrough "
                                "outside hifi (50 stayed 50%)")

            browser.close()
    finally:
        httpd[0].shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: HiFi walks one dark-amber chrome (#160a04 resting with a "
          "white line, #56300d engaged), the segment row and instrument "
          "select stay dark, the zen CTA reads #b32317 with white ink, and "
          "the LED rows fill whole segments while the plain keep their "
          "smooth glide.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
