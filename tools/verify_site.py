#!/usr/bin/env python3
# Live-site verification probe for the ocarina-practice serving layer — the
# manual companion to tests/gen_pages.py (which pins the SAME contracts
# against a locally staged artifact). Used for the domain cutover: run it
# against the site BEFORE the flip (project pages) and AFTER (domain root);
# a green run both times with the same check list is the go-live evidence.
#
#   python tools/verify_site.py --origin https://tribbin.github.io/Ocarina-Practice
#   python tools/verify_site.py --origin https://ocarina-practice.com --boot 3
#
# Stage-agnostic contracts per landing stub (the tool reads the DEPLOYED
# songs.json, never the local one — what is published is the truth):
#   the stub URL serves 200; <base href>, rel=canonical and og:url all agree
#   on the one serving prefix; og:title names the song + the site; the page
#   carries one meta description and the app shell. --boot N playwright-loads
#   N sampled stubs (plus the Song of Time stub always): the app must boot
#   the right song on the right ocarina with zero console errors beyond the
#   manifest-declared-absent tone.json 404s.
#
# Read-only by design: only GETs. Not a CI step — it validates a live origin.
import argparse
import json
import re
import sys
import urllib.request
from urllib.parse import urlparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_song_pages as gen  # noqa: E402  (stdlib-only sibling)

UA = {"User-Agent": "ocarina-practice-site-verify/1"}


def get(url, timeout=30):
    ctx = urllib.request.build_opener()
    req = urllib.request.Request(url, headers=UA)
    with ctx.open(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


def stub_paths(songs):
    """Every landing path the deployed corpus should serve, in stable order.

    Suppression mirrors the generator's family rules: registered-suffix
    variants never get stubs, and a '-bass' sibling of an existing bare base
    rides the base's landing (leaf -bass keys keep theirs).
    """
    paths = []
    for key in songs:
        if gen.SUFFIX.search(key) or songs[key].get("hidden"):
            continue
        bare = key[:-len("-bass")] if key.endswith("-bass") else None
        if bare and songs.get(bare):
            continue
        cat = gen.category_of(songs[key].get("group"))
        paths.append("/song/" + cat + "/" + key + "/")
    return sorted(paths)


def check_stub(url, html, prefix, errors):
    base = re.search(r'<base href="([^"]*)"', html)
    canon = re.search(r'<link rel="canonical" href="([^"]*)"', html)
    ogurl = re.search(r'<meta property="og:url" content="([^"]*)"', html)
    ogtitle = re.search(r'<meta property="og:title" content="([^"]*)"', html)
    desc = re.search(r'<meta name="description" content="([^"]*)"', html)
    want_path = urlparse(url.rstrip("/")).path + "/"
    if not base or base.group(1) != prefix:
        errors.append(f"{want_path}: base href {base and base.group(1)!r} "
                      f"!= serving prefix {prefix!r}")
    if not canon or not canon.group(1).endswith(want_path):
        errors.append(f"{want_path}: canonical {canon and canon.group(1)!r} "
                      f"does not end with the stub path")
    if not ogurl or not ogurl.group(1).endswith(want_path):
        errors.append(f"{want_path}: og:url {ogurl and ogurl.group(1)!r} "
                      f"does not end with the stub path")
    if canon and ogurl and canon.group(1) != ogurl.group(1):
        errors.append(f"{want_path}: canonical and og:url disagree")
    if not ogtitle or "Ocarina Practice" not in ogtitle.group(1):
        errors.append(f"{want_path}: og:title missing or site name wrong")
    if not desc or not desc.group(1).strip():
        errors.append(f"{want_path}: meta description missing")
    return (ogtitle and ogtitle.group(1)) or ""


def boot_stub(page, url, ogtitle, errors, tag):
    errs = []
    console = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    # Chromium's resource-failure console text is generic ("Failed to load
    # resource ... 404"); the request URL arrives on m.location — the
    # manifest-declared-absent tone.json misses are the only allowed 404s.
    page.on("console", lambda m: console.append((m.text, (m.location or {}).get("url", "")
                                                 )) if m.type == "error" else None)
    page.goto(url)
    page.wait_for_function(
        "window.NOTES && window.NOTES.length"
        " && !!document.getElementById('scale').value", timeout=30000)
    # og:title/title-tag use the em-dash separator (title tag echoes it);
    # song name is the og:title with the site suffix stripped.
    song_name = re.sub(r"\s*[\u2014-]\s*Ocarina Practice\s*$", "", ogtitle)
    page.wait_for_function(
        "t => document.getElementById('title').textContent === t", arg=song_name,
        timeout=30000)
    allowed = [(t, l) for t, l in console
               if any((l or "").endswith(p) for p in ("/tone.json", "/tone.json?a=1"))
               or "tone.json" in (l or "")]
    stray = [(t, l) for t, l in console if (t, l) not in allowed]
    if stray:
        errors.append(f"{tag}: console errors: {[t for t, _ in stray[:3]]}")
    if errs:
        errors.append(f"{tag}: page errors: {errs[:3]}")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origin", required=True,
                    help="e.g. https://ocarina-practice.com or "
                         "https://tribbin.github.io/Ocarina-Practice")
    ap.add_argument("--boot", type=int, default=0,
                    help="playwright-boot this many sampled stubs (plus "
                         "Song of Time always) — needs the test venv")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    origin = args.origin.rstrip("/")
    u = urlparse(origin)
    if u.scheme not in ("https", "http") or not u.netloc:
        print("FAIL: --origin must be an absolute URL")
        return 2
    prefix = u.path.rstrip("/")  # "" at a domain root, "/Ocarina-Practice" on a project page
    # --origin is the complete serving base (the mount path included):
    # every relative URL the app fetches resolves under it directly.

    errors = []
    tests = 0

    tests += 1
    try:
        status, shell = get(origin + "/", args.timeout)
    except Exception as e:
        print(f"FAIL: cannot fetch shell {origin}/ — {e}")
        return 2
    if status != 200:
        errors.append(f"/: shell status {status}")
    elif 'src="js/app.js"' not in shell:
        # The SW registers from js/app.js's load handler (offline_pwa pins
        # that in CI) — the shell only has to serve the module entry.
        errors.append("/: the shell does not serve the js/app.js module entry")

    tests += 1
    try:
        status, songs_raw = get(origin + "/songs.json", args.timeout)
    except Exception as e:
        print(f"FAIL: cannot fetch deployed songs.json — {e}")
        return 2
    if status != 200:
        errors.append("songs.json: status " + str(status))
        songs = {}
    else:
        songs = json.loads(songs_raw)

    stubs = stub_paths(songs)

    # Crawler stage on the live contract (robots was the post-flip unlock):
    # robots.txt must serve with its Sitemap pointer, and sitemap.xml must
    # enumerate exactly home + every stub URL the deployed corpus maps —
    # nothing suppressed by the generator's family rules, nothing invented.
    tests += 1
    try:
        st, robots = get(origin + "/robots.txt", args.timeout)
        if st != 200:
            errors.append(f"robots.txt: status {st}")
        elif "Sitemap:" not in robots or "sitemap.xml" not in robots:
            errors.append("robots.txt: Sitemap pointer missing")
    except Exception as e:
        errors.append(f"robots.txt: fetch failed {e}")

    tests += 1
    try:
        st, sm = get(origin + "/sitemap.xml", args.timeout)
        if st != 200:
            errors.append(f"sitemap.xml: status {st}")
        else:
            locs = re.findall(r"<loc>([^<]*)</loc>", sm)
            want = [origin + "/"] + sorted(
                origin + "/" + p.lstrip("/") for p in stubs)
            if sorted(locs) != sorted(want):
                miss = [x for x in want if x not in locs]
                extra = [x for x in locs if x not in want]
                errors.append(f"sitemap.xml: loc mismatch (missing "
                              f"{miss[:3]}, unknown {extra[:3]})")
            else:
                print(f"   sitemap.xml 200  {len(locs)} locs")
    except Exception as e:
        errors.append(f"sitemap.xml: fetch failed {e}")

    always = [p for p in stubs if p.endswith("/song-of-time/")]
    for path in stubs:
        tests += 1
        # --origin already includes the mount path; the stub paths are
        # built from the deployed corpus relative to it (project-page and
        # domain-root stages differ only in --origin).
        full = origin + "/" + path.lstrip("/")
        try:
            status, html = get(full, args.timeout)
        except Exception as e:
            errors.append(f"{path}: fetch failed {e}")
            continue
        if status != 200:
            errors.append(f"{path}: status {status}")
            continue
        name = check_stub(full, html, prefix + "/", errors)
        print(f"   stub {path} 200  {name}")

    if args.boot > 0 and stubs:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("   --boot skipped: playwright not importable (use the test venv)")
            args.boot = 0
    if args.boot > 0 and stubs:
        sample = list(dict.fromkeys(always))
        pool = [p for p in stubs if p not in sample]
        picked = (sample + pool[: max(0, args.boot - len(sample))])[: args.boot]
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for path in picked:
                tests += 1
                ogtitle = ""
                try:
                    _s, html = get(origin + "/" + path.lstrip("/"), args.timeout)
                    ogtitle = check_stub(origin + "/" + path.lstrip("/"),
                                         html, prefix + "/", [])
                except Exception as e:
                    errors.append(f"boot {path}: fetch failed {e}")
                    continue
                try:
                    # A fresh context per boot: the first navigation installs
                    # the site's service worker, and a second navigation in
                    # the same context gets claimed by it (the recorded
                    # Playwright lesson — do not share page objects here).
                    ctx = browser.new_context()
                    page = ctx.new_page()
                    boot_stub(page, origin + "/" + path.lstrip("/"),
                              ogtitle, errors, "boot " + path)
                    print(f"   boot {path} ok")
                    page.close()
                    ctx.close()
                except Exception as e:
                    try:
                        state = page.evaluate(
                            "() => ({notes: (window.NOTES || []).length,"
                            " scale: document.getElementById('scale')"
                            " && document.getElementById('scale').value,"
                            " title: document.getElementById('title')"
                            " && document.getElementById('title').textContent,"
                            " ready: document.readyState, url: location.href"
                            " })")
                    except Exception as e2:
                        state = f"unreachable: {e2}"
                    errors.append(f"boot {path}: {e} (state {state})")
            browser.close()

    if errors:
        print("\nFAIL — live-site contract violated:", flush=True)
        for e in errors:
            print("  - " + e, flush=True)
        return 1
    print(f"\nPASS: {tests} live checks against {origin} "
          f"({len(stubs)} landing stubs, prefix {prefix or '/'!r}).", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
