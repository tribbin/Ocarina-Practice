#!/usr/bin/env python3
# Pre-paint theme pin: <html data-theme> must already carry the resolved
# theme the moment the document loads — the index.html head script does the
# same param > localStorage > default resolution as app.js's
# themeFromQuery (?plain / ?oot / ?hifi beat the saved oco-theme; no param:
# the saved value rules; a fresh browser defaults to Hyrule). Before this
# pin the head script only honored ?oot, so a saved theme flashed the
# default look until boot() applied it later.
#
# Each case ABORTS js/app.js (the app's only module entry; every other
# module imports through it) so that boot()'s applyTheme() never runs and
# ONLY the pre-paint head script can set the attribute.
#
#   python3 tests/theme_prepaint.py      # headless & silent

import sys

from playwright.sync_api import sync_playwright

from suite_server import start_server

# (query, pre-seeded oco-theme, expected data-theme; None = attribute absent)
CASES = [
    ("", "hifi", "hifi"),        # the flash case: a saved theme, no query
    ("", "oot", "oot"),
    ("?plain", "hifi", None),    # a param beats the saved value; plain = no attribute
    ("?oot", "", "oot"),         # the original hidden-preview link keeps working
    ("?hifi", "oot", "hifi"),    # the hidden theme via link beats the saved value
    ("", None, "oot"),           # fresh browser: Hyrule is the default
]


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless="--headed" not in sys.argv)
            for i, (query, saved, want) in enumerate(CASES):
                ctx = browser.new_context()
                if saved is not None:
                    ctx.add_init_script(
                        "try { localStorage.setItem('oco-theme', "
                        + repr(saved) + "); } catch (e) {}")
                page = ctx.new_page()
                # Kill the module entry: with boot() out of the picture, only
                # the head script can touch data-theme — that IS the pin.
                page.route("**/js/app.js", lambda route: route.abort())
                page.goto(base + query)
                # The head script runs while the HTML parses, long before the
                # load event that resolves goto.
                got = page.evaluate(
                    "() => document.documentElement.getAttribute('data-theme')")
                if got != want:
                    failures.append(
                        f"case {i} (query={query or '-'}, "
                        f"saved={saved if saved is not None else 'fresh'}): "
                        f"data-theme {got!r} != {want!r} — the pre-paint "
                        "script must resolve param > saved oco-theme > "
                        "Hyrule default")
                ctx.close()
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: pre-paint data-theme follows param > saved oco-theme > "
          "Hyrule default in all six cases, with the app modules out of "
          "the picture (head script alone).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
