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

    # --- /js/ CORE completeness + ?v= token lockstep (Robin, 2026-09-29:
    # every /js/ module rides the SW network-first branch now, so a missing
    # CORE entry is no longer a lazy self-healing miss — offline boots it
    # with a 504. And a module imported with a ?v= token must be precached
    # under that exact URL: the shell caches what the page really loads.)
    core_m = re.search(r'const CORE = \[(.*?)\];', sw, re.S)
    if not core_m:
        failures.append("sw.js must carry the CORE precache array")
    else:
        core_entries = re.findall(r'"([^"]+)"', core_m.group(1))
        # tokenized import specifiers across the module graph
        # ("./helmholtz-voice.js?v=3" forms; url strings may prefix ./ or ../)
        spec_re = re.compile(
            r'["\'][./]*([A-Za-z0-9._-]+\.js)\?v=([A-Za-z0-9._-]+)["\']')
        tokens = {}
        for jsf in sorted((ROOT / "js").glob("*.js")):
            for m in spec_re.finditer(jsf.read_text(encoding="utf-8")):
                tokens[m.group(1)] = m.group(2)
        for name in sorted(p.name for p in (ROOT / "js").glob("*.js")):
            want = f"js/{name}"
            if name in tokens:
                want += f"?v={tokens[name]}"
            hits = [e for e in core_entries
                    if e == f"js/{name}" or e == want]
            if len(hits) != 1:
                failures.append(
                    f"js/{name} must have EXACTLY ONE CORE precache entry "
                    f"(expected {want!r}), found " +
                    (", ".join(hits) if hits else "none") +
                    " — every /js/ module rides network-first, so a missing "
                    "entry is a hard 504 offline (js/wakelock.js, the "
                    "2026-09-29 catch) and a stale twin entry caches the "
                    "old copy beside the fresh one")
                continue
            if hits[0] != want:
                failures.append(
                    f"CORE caches {hits[0]!r} but the page loads {want!r} — "
                    "the shell caches what the page really loads; a token "
                    "bump moves the importer and sw.js at once")

        # File-scheme leftover worker (VS Code Simple Browser, 2026-09-29):
        # Electron allows a SW on file://, install skips the precache, and
        # a fetch intercept on an empty cache 504s the twin/engine pair.
        # skipWaiting must run BEFORE the protocol return so a waiting
        # leftover cannot keep the old fetch handler; fetch itself no-ops
        # on non-HTTP; the page unregisters leftovers instead of only
        # skipping a new register() (a registered worker updates forever).
        install_block = re.search(
            r'self\.addEventListener\("install",.*?^\}\);', sw, re.S | re.M)
        if not install_block:
            failures.append("sw.js must have an install listener")
        else:
            ib = install_block.group(0)
            skip_at = ib.find("self.skipWaiting()")
            proto_at = ib.find("self.location.protocol")
            if skip_at < 0:
                failures.append("install must call skipWaiting")
            elif proto_at < 0 or skip_at > proto_at:
                failures.append(
                    "install must skipWaiting BEFORE the file-scheme "
                    "return — a leftover Simple Browser worker otherwise "
                    "stays WAITING and keeps intercepting")
        fetch_block = re.search(
            r'self\.addEventListener\("fetch",.*?^\}\);', sw, re.S | re.M)
        if not fetch_block:
            failures.append("sw.js must have a fetch listener")
        elif 'if (!/^https?:$/.test(self.location.protocol)) return;' not in fetch_block.group(0):
            failures.append(
                "fetch must return on non-HTTP(S) before intercepting — "
                "file-scheme Simple Browser workers have an empty cache "
                "and a miss becomes a 504 that drops the twin voice")
        if "r.unregister()" not in app and "r => r.unregister()" not in app:
            failures.append(
                "app.js must unregister leftover file-scheme service "
                "workers (skipping register() leaves an existing one in "
                "control of VS Code Simple Browser)")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print(f"\nPASS: stylesheet token {link_tok!r} is identical in index.html "
          "and sw.js (independent of the sw VERSION), the SW precaches the "
          "versioned URL once, boot reads the page's own link "
          "(no bare-path hard-coding left), every /js/ module has exactly "
          "one CORE entry, and tokenized imports match their CORE keys.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
