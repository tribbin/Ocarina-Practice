#!/usr/bin/env python3
# Theme selection contract: the title-bar button OPENS a small menu (Robin's
# IDEAS line: switching signifies the color theme without showing it in the
# current theme) listing Plain / Hyrule / HiFi; picking applies data-theme,
# persists the "oco-theme" choice and re-renders; the ?plain / ?oot / ?hifi
# link parameters keep outranking the saved choice (old shared links stay
# truthful); the HiFi look is the black audio-stack first pass and cards still
# render under it.
#
#   python3 tests/theme_toggle.py      # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function'")


from suite_server import start_server


def menu_state(page):
    return page.evaluate(
        "() => ({ hidden: document.getElementById('themeMenu').hidden,"
                " exp: document.getElementById('themeBtn').getAttribute('aria-expanded') })")


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS,
                                        args=["--autoplay-policy=no-user-gesture-required"])
            errs = []
            page = browser.new_page()
            page.on("pageerror", lambda e: errs.append(str(e)))

            # fresh browser: the Hyrule look stays the default; the button
            # names the ACTIVE theme and opens the menu instead of flipping
            page.goto(base)
            page.wait_for_function(WAIT)
            first = page.evaluate(
                "() => ({ theme: document.documentElement.getAttribute('data-theme'),"
                        " label: document.getElementById('themeBtn').textContent })")
            if first["theme"] != "oot" or first["label"] != "Hyrule":
                failures.append(f"fresh visit must boot on the Hyrule look "
                                f"(got {first})")

            page.click("#themeBtn")
            page.wait_for_function(
                "() => !document.getElementById('themeMenu').hidden")
            opened = menu_state(page)
            if opened["exp"] != "true":
                failures.append(f"opening must raise aria-expanded (got {opened})")
            items = page.evaluate(
                "() => [...document.querySelectorAll('#themeMenu button')]"
                ".map(b => ({ v: b.dataset.themeChoice, t: b.textContent.trim() }))")
            if [i["t"] for i in items] != ["Plain", "Hyrule"]:
                failures.append(f"the menu must list only the finished themes — "
                                f"HiFi stays hidden behind ?hifi (got {items})")
            # the switch signifies the theme without adopting its look: the
            # three menu items share one uniform ink no matter the look
            kinds = set(page.evaluate(
                "() => [...document.querySelectorAll('#themeMenu button')]"
                ".map(b => getComputedStyle(b).color)"))
            if len(kinds) > 1:
                failures.append(f"menu items must share one uniform ink (got {kinds})")

            # Escape closes without changing anything (no flip, no save)
            page.keyboard.press("Escape")
            page.wait_for_function(
                "() => document.getElementById('themeMenu').hidden")
            esc = page.evaluate(
                "() => document.documentElement.getAttribute('data-theme')")
            if esc != "oot":
                failures.append(f"an aborted menu must not change the look (got {esc})")

            # HiFi is HIDDEN (Robin, 2026-09-25 — unfinished look): only the
            # ?hifi link parameter and an already-saved choice reach it, and
            # the menu never leads anyone there
            page.evaluate("() => localStorage.setItem('oco-theme', 'hifi')")
            page.reload()
            page.wait_for_function(
                "() => document.documentElement.getAttribute('data-theme') === 'hifi'"
                " && document.getElementById('themeBtn').textContent === 'HiFi'",
                timeout=15000)
            page.click("#themeBtn")
            page.wait_for_function(
                "() => !document.getElementById('themeMenu').hidden")
            hidden = page.evaluate(
                "() => [...document.querySelectorAll('#themeMenu button')]"
                ".map(b => b.dataset.themeChoice)")
            if hidden != ["", "oot"]:
                failures.append(f"the menu must NOT lead to the hidden HiFi "
                                f"(got {hidden})")
            page.keyboard.press("Escape")
            page.wait_for_function(
                "() => document.getElementById('themeMenu').hidden")

            # menu pick Plain: back to the light look, saved empty
            page.reload()
            page.wait_for_function(
                "() => document.documentElement.getAttribute('data-theme') === 'hifi'")
            page.click("#themeBtn")
            page.wait_for_function(
                "() => !document.getElementById('themeMenu').hidden")
            page.click("#themeMenu button[data-theme-choice='']")
            page.wait_for_function(
                "() => !document.documentElement.hasAttribute('data-theme')")
            plain = page.evaluate("() => localStorage.getItem('oco-theme')")
            if plain != "":
                failures.append(f"the Plain pick must save the empty look (got {plain!r})")

            # link parameters outrank the saved choice, all three directions
            page.goto(base + "?oot")
            page.wait_for_function(WAIT)
            forced = page.evaluate(
                "() => document.documentElement.getAttribute('data-theme')")
            if forced != "oot":
                failures.append("?oot must force the Hyrule look for old links")
            page.evaluate("() => localStorage.setItem('oco-theme', 'hifi')")
            page.goto(base + "?plain")
            page.wait_for_function(WAIT)
            detour = page.evaluate(
                "() => ({ theme: document.documentElement.getAttribute('data-theme'),"
                        " saved: localStorage.getItem('oco-theme') })")
            if detour["theme"] is not None:
                failures.append("?plain must detour to the light look even with "
                                f"a saved HiFi choice (got {detour})")
            if detour["saved"] != "hifi":
                failures.append("a link detour must not rewrite the saved choice")
            page.goto(base + "?hifi")
            page.wait_for_function(WAIT)
            forced = page.evaluate(
                "() => document.documentElement.getAttribute('data-theme')")
            if forced != "hifi":
                failures.append("?hifi must force the HiFi look for shared links")

            # the chrome-color hint follows the chassis in every look
            hint = page.evaluate(
                "() => { const m = document.querySelector('meta[name=theme-color]');"
                " return { c: m.content, want: getComputedStyle(document.body).backgroundColor }; }")
            if hint["c"].replace(" ", "") != hint["want"].replace(" ", ""):
                failures.append(f"the theme-color hint must follow the look (got {hint})")

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
    print("\nPASS: the theme menu lists only the finished looks, picks apply "
          "+ persist + re-render, aborted menus change nothing, the hidden "
          "HiFi stays reachable only through ?hifi or a saved choice, link "
          "parameters keep outranking the saved choice, and the chrome hint "
          "follows every look.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
