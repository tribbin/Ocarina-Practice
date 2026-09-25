#!/usr/bin/env python3
# CSS fresh-on-release (Robin, IDEAS 2026-09-25): deep-refreshing the page
# after every deploy was the cost of the SW's stale-while-revalidate flavor
# — css/app.css sat under one cache key forever, so a release always
# served the previous stylesheet first ("live on the SECOND visit").
# The stylesheet URL now carries the SAME token sw.js's VERSION carries:
#   - a release bumps the token in sw.js AND the <link> href at once;
#   - an OLD worker (or the 10-minute GH Pages HTTP cache on sw.js) sees
#     the versioned URL for the first time, misses its cache and goes to
#     the network — the fresh stylesheet wins the very first reload, no
#     deep refresh;
#   - boot fetches whatever the page's own <link> opened (the link is the
#     single hand-maintained reference) so the at-boot sheet replace can
#     never disagree with what the page painted from.
# This suite pins the coordination: the token must be identical in sw.js
# and index.html, the SW precache list must hold the versioned URL (the
# offline shell caches what a page really loads), and app.js must not
# hard-code the bare path (the link owns it).
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

    vm = re.search(r'const VERSION = "([^"]+)";', sw)
    if not vm:
        failures.append("sw.js must carry const VERSION = \"...\"")
        return 1
    version = vm.group(1)

    link_m = re.search(r'<link rel="stylesheet" href="([^"]+)"', html)
    if not link_m:
        failures.append('index.html must carry <link rel="stylesheet">')
    else:
        href = link_m.group(1)
        if version not in href or "app.css?v=" not in href:
            failures.append(f'{href!r}: the stylesheet href must carry the '
                            f'sw VERSION token ({version!r}) as ?v= so a '
                            'release changes both at once')
        if not href.startswith("css/"):
            failures.append(f'{href!r}: the link must stay a css/ relative '
                            'path (base-href re-rooting owns the rest)')

    if f'"css/app.css?v={version}"' not in sw:
        failures.append(f"sw.js CORE must precache the versioned URL "
                        f'"css/app.css?v={version}" — the offline shell '
                        "caches what a page really loads")
    if '"css/app.css",' in sw:
        failures.append("sw.js CORE still lists the bare css/app.css — the "
                        "unversioned entry would cache the OLD sheet next "
                        "to the fresh one")

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
    print(f"\nPASS: stylesheet token {version!r} is identical in index.html "
          "and sw.js, the SW precaches the versioned URL, and boot reads "
          "the page's own link (no bare-path hard-coding left).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
