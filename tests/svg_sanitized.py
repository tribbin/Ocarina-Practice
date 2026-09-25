#!/usr/bin/env python3
# Template-safety suite (§3): the fetched SVG template is DATA that gets used
# as markup on every card — active content (script / foreignObject / on*
# handlers / javascript: URLs) must be gone before install, drawing intact;
# unparsable template text must degrade to the clean fallback instead of
# breaking the boot. Data-file text reaching innerHTML (the range warning's
# instrument name / range label) must render as TEXT.
#
#   python3 tests/svg_sanitized.py      # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function'")

EVIL_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" onload="window.__pwnMesh=1">
  <script>document.title = 'pwned';</script>
  <foreignObject width="100" height="100">
    <body xmlns="http://www.w3.org/1999/xhtml">
      <img src="x" onerror="window.__imgBitten=1" />
    </body>
  </foreignObject>
  <a xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="javascript:window.__linkPwned=1">
    <circle cx="50" cy="50" r="40" fill="#8b3d2f"/>
  </a>
</svg>
"""

JUNK_BODY = "this is not xml at all <<<>>>"


from suite_server import start_server


def route_evil(page):
    def serve(route):
        route.fulfill(status=200, content_type="image/svg+xml", body=EVIL_SVG)
    page.route("**/ocarina-template.svg", serve)


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS,
                                        args=["--autoplay-policy=no-user-gesture-required"])

            # --- hostile template: active content stripped, drawing kept ---
            ctx = browser.new_context()
            errs = []
            page = ctx.new_page()
            page.on("pageerror", lambda e: errs.append(str(e)))
            route_evil(page)
            page.goto(base)
            page.wait_for_function(WAIT)
            page.wait_for_function(
                "() => !!document.querySelector('#sheet .card svg, #sheet svg')")
            probe = page.evaluate(r"""
              () => {
                const tpl = document.getElementById('oca-tpl');
                const svg = tpl ? tpl.content.querySelector('svg') : null;
                return {
                  hasSvg: !!svg,
                  onAttrs: svg ? svg.innerHTML.match(/ [a-z]*on[a-z]*=/g) : null,
                  scripts: svg ? svg.querySelectorAll('script').length : -1,
                  fos: svg ? svg.querySelectorAll('foreignObject').length : -1,
                  evilHrefs: svg ? [...svg.querySelectorAll('[href]')].filter(e =>
                    /^\s*javascript:/i.test(e.getAttribute('href'))).length : -1,
                  circles: svg ? svg.querySelectorAll('circle').length : -1,
                  img: svg ? svg.querySelectorAll('img').length : -1,
                };
              }
            """)
            if not probe["hasSvg"]:
                failures.append("the sanitized template must still install an "
                                "svg root for the cards")
            else:
                if probe["scripts"] or probe["fos"] or (probe["img"] or 0):
                    failures.append(
                        f"script/foreignObject/img content must be gone "
                        f"(scripts {probe['scripts']}, fos {probe['fos']}, "
                        f"img {probe['img']})")
                if probe["onAttrs"]:
                    failures.append(
                        f"on* handlers must be stripped from the template "
                        f"({probe['onAttrs'][:3]})")
                if probe["evilHrefs"]:
                    failures.append("javascript: URLs must be stripped from "
                                    "template elements")
                if not probe["circles"]:
                    failures.append("the sanitized drawing must keep its shape "
                                    "(circles are the playable auricle)")
            # the draw path consumes the sanitized node; rendered cards exist
            cards = page.evaluate(
                "() => document.querySelectorAll('#sheet .card svg').length")
            if cards < 1:
                failures.append("cards must still render from the sanitized "
                                "template")
            page.evaluate(
                "() => { const ta = document.getElementById('src');"
                " ta.value = '# harmless\\n\\nA4 C5 | A4 C5';"  
                " ta.dispatchEvent(new Event('input', { bubbles: true })); }")
            page.wait_for_function(
                "() => document.getElementById('title').textContent ==="
                " 'harmless'")
            page.wait_for_function(
                "() => document.querySelectorAll('#sheet svg').length > 1")
            ctx.close()

            # --- unparsable template: clean fallback, boot intact ---
            ctx2 = browser.new_context()
            errs2 = []
            page2 = ctx2.new_page()
            page2.on("pageerror", lambda e: errs2.append(str(e)))
            page2.route("**/ocarina-template.svg", lambda route: route.fulfill(
                status=200, content_type="image/svg+xml", body=JUNK_BODY))
            page2.goto(base)
            page2.wait_for_function(WAIT)
            page2.wait_for_function(
                "() => document.getElementById('sheet').children.length > 0",
                timeout=15000)
            fallback = page2.evaluate("""
              () => ({
                cards: document.querySelectorAll('#sheet .card').length,
                fallback:
                  (document.getElementById('sheet').textContent || "").includes("template"),
                tplSvg: !!(document.getElementById('oca-tpl') &&
                  document.getElementById('oca-tpl').content.querySelector("svg")),
              })
            """)
            if fallback["tplSvg"]:
                failures.append(
                    "unparsable template text must not install an svg root")
            if not fallback["fallback"]:
                failures.append("the sheet must carry the clean 'no template' "
                                "fallback text, not broken markup")
            if errs2:
                failures.append(f"junk-template page errors {errs2}")
            ctx2.close()

            # --- manifest text into the range warning renders as TEXT ---
            ctx3 = browser.new_context()
            errs3 = []
            page3 = ctx3.new_page()
            page3.on("pageerror", lambda e: errs3.append(str(e)))
            page3.route("**/instruments.json", lambda route: route.fulfill(
                status=200, content_type="application/json",
                body="""{"default": "oot-alto-c-12", "instruments": [
                  {"id": "oot-alto-c-12", "type": "Evil<b>alert(1)</b>", "version": "<img src=x onerror=window.__bitten=1>",
                   "fingerings": "instruments/oot-alto-c-12/fingerings.json",
                   "svg": "instruments/oot-alto-c-12/ocarina-template.svg"}
                ]}"""))
            page3.goto(base)
            page3.wait_for_function(WAIT)
            page3.evaluate(
                "() => { const ta = document.getElementById('src');"
                " ta.value = '# range warn\\n\\nB3 zz';"  
                " ta.dispatchEvent(new Event('input', { bubbles: true })); }")
            page3.wait_for_function(
                "() => !!document.getElementById('rangeWarn') &&"
                " !document.getElementById('rangeWarn').hidden")
            warn = page3.evaluate("""
              () => {
                const bar = document.getElementById('rangeWarn');
                return {
                  text: bar.textContent,
                  html: bar.innerHTML,
                  imgs: bar.querySelectorAll('img, b, script').length,
                  bitten: window.__bitten,
                };
              }
            """)
            if warn["imgs"]:
                failures.append("manifest text must not become elements in the "
                                f"warning (got {warn['imgs']})")
            if "Evil<b>alert(1)</b>" not in warn["text"]:
                failures.append("the warning text must still READ the full "
                                f"manifest name verbatim ({warn['text']!r})")
            if "&lt;b&gt;" not in warn["html"]:
                failures.append("the warning must escape hostile data-file "
                                f"text ({warn['html'][:80]!r})")
            if warn["bitten"]:
                failures.append("an onerror payload from the manifest must "
                                "never run (window.__bitten set)")
            if errs3:
                failures.append(f"page errors {errs3}")
            ctx3.close()

            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: hostile templates install clean (active content stripped, "
          "shape kept), unparsable ones degrade to the fallback, and "
          "data-file text inside the range warning renders as text only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
