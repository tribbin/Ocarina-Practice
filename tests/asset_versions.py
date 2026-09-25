#!/usr/bin/env python3
# CSS fresh-on-release (Robin, IDEAS 2026-09-25): deep-refreshing the page
# after every deploy was the cost of the SW's stale-while-revalidate flavor
# — css/app.css sat under one cache key forever, so a release always
# served the previous stylesheet first ("live on the SECOND visit").
#
# The stylesheet URL carries its OWN release token, independent from
# sw.js's VERSION (the sheet only moves when the stylesheet changes; a
# JS/data release bumps VERSION alone):   css/app.css?v=css-vN
#   - a CSS change bumps the token in index.html's <link> href AND sw.js's
#     precache entry at once;
#   - an OLD worker (or the 10-minute GH Pages HTTP cache on sw.js) sees
#     the versioned URL for the first time, misses its cache and goes to
#     the network — the fresh stylesheet wins the very first reload, no
#     deep refresh;
#   - boot fetches whatever the page's own <link> opened (the link is the
#     single hand-maintained reference) so the at-boot sheet replace can
#     never disagree with what the page painted from.
# This suite pins the coordination: the ?v= token must be identical in
# sw.js and index.html (whatever its value), the SW precache list must
# hold the versioned URL (the offline shell caches what a page really
# loads), and app.js must not hard-code the bare path (the link owns it).
#
#   python3 tests/asset_versions.py     # pure python, no browser

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    failures = []
    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "js/app.js").read_text(encoding="utf-8")

    link_m = re.search(r'<link rel="stylesheet" href="([^"]+)"', html)
    if not link_m:
        failures.append('index.html must carry <link rel="stylesheet">')
        return 1
    href = link_m.group(1)
    link_tok = None
    hm = re.search(r"css/app\.css\?v=([A-Za-z0-9._-]+)", href)
    if hm:
        link_tok = hm.group(1)
    else:
        failures.append(f'{href!r}: the stylesheet href must carry a '
                        '"css/app.css?v=<token>" release token')

    sw_tok = None
    sm = re.search(r'"css/app\.css\?v=([A-Za-z0-9._-]+)"', sw)
    if sm:
        sw_tok = sm.group(1)
    else:
        failures.append("sw.js CORE must carry the versioned stylesheet URL "
                        "\"css/app.css?v=<token>\" — the offline shell "
                        "caches what a page really loads")
    if sw.count('css/app.css?v=') != 1:
        failures.append("sw.js must precache EXACTLY ONE stylesheet URL — a "
                        "second unversioned entry would cache the OLD sheet "
                        "beside the fresh one")
    if link_tok is not None and sw_tok is not None and link_tok != sw_tok:
        failures.append(f'stylebook token drift: index.html ?v={link_tok!r} '
                        f"vs sw.js ?v={sw_tok!r} — a release bumps both at "
                        "once")
    version = re.search(r'const VERSION = "([^"]+)";', sw)
    if not version:
        failures.append('sw.js must carry const VERSION = "..."')
    if link_tok is not None and version and link_tok == version.group(1):
        failures.append("the css token must be its OWN token (bump "
                        "VERSION for JS/data releases, the css token only "
                        "when the stylesheet changes)")

    if 'loadText("css/app.css")' in app:
        failures.append("app.js boot must not hard-code the bare css path — "
                        "boot fetches the page's own <link> href (read the "
                        "attribute) so token and served sheet cannot drift")
    if "link[rel=stylesheet]" not in app and 'link[rel="stylesheet"]' not in app:
        failures.append("app.js boot must read the page's <link rel= "
                        "stylesheet> href for the at-boot sheet replace")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print(f"\nPASS: stylesheet token {link_tok!r} is identical in index.html "
          "and sw.js (independent of the sw VERSION), the SW precaches the "
          "versioned URL once, and boot reads the page's own link "
          "(no bare-path hard-coding left).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
