#!/usr/bin/env python3
# Contract tests for tools/gen_song_pages.py: one stub per base slug
# (variants and hidden WIPs excluded), <base href> re-rooting (which must
# carry the app's runtime fetches, not just head links), canonical/og:url
# on the site prefix, the seed naming the ladder-chosen FAMILY member, and
# — the decisive check — EVERY landing stub boots on a mounted artifact
# with zero out-of-range marks: right song (the seeded arrangement), right
# ocarina, rendered sheet/chips, clean console. Tone-file 404s are the
# manifest-declared allowlist (a permitted miss, never a required one:
# a healthy boot may legitimately have none — the triple bass has a
# tone.json, the 12-hole does not). The mirrored deploy shape is
# DOMAIN-ROOT serving (the 2026-09-25 flip): robots.txt + generated
# sitemap.xml round out the crawler stage, and the legacy project-page
# mount stays pinned by a string-contract leg (--site-prefix's
# parameter-ness, ready to retire with its stage) PLUS its own mounted
# boot: the landed-crawler rewrites must resolve to the MOUNT root, not
# the domain root — the relocatability the <base> injection promised
# through load time must hold through the whole session (2026-09-25:
# STUB_PATH's rewrite dropped its mount prefix, invisible on the
# root-serving domain that deployed over it).

import http.server
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

# gen_pages serves a STAGING tree under scoped Mount handlers; it borrows
# only the hardened SERVER class (teardown-silent handle_error) from the
# shared helper.
from suite_server import SuiteServer
from xml.etree import ElementTree

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import gen_song_pages as gen

SONGS = json.loads((REPO / "songs.json").read_text(encoding="utf-8"))
# Deriving twins materialize first (board §9 2026-09-25): the ladder and
# every chart-fit must read the same bodies the generator materializes —
# the byte-equal loader output is pinned by tests/twin_derive.py.
from melody_transpose import materialize
materialize(SONGS)
MANIFEST = json.loads((REPO / "instruments.json").read_text(encoding="utf-8"))
CHARTS = {i["id"]: gen.chart_ids(i["id"], MANIFEST) for i in MANIFEST["instruments"]}

ALLOW_FILES = ["index.html", "sw.js", "manifest.webmanifest", "favicon.svg",
               "icon-192.png", "icon-512.png", "hyrule.webp",
               "songs.json", "instruments.json", "robots.txt"]

SITE_ORIGIN = "https://ocarina-practice.com"

SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def category_of(group):
    g = (group or "").lower()
    if "zelda" in g:
        return "zelda"
    if "scale" in g:
        return "scales"
    return "other"


def expected_stub_keys():
    keys = []
    for key, song in SONGS.items():
        if gen.SUFFIX.search(key) or song.get("hidden"):
            continue
        if key.endswith("-bass") and key[:-5] in SONGS:
            continue  # family -bass member rides its base page
        keys.append(key)
    return keys


# The hub categories mirror the emitted set (one /song/<cat>/ hub each).
HUB_CATS = sorted({category_of(SONGS[k].get("group"))
                   for k in expected_stub_keys()})


def run_gen(out, *extra):
    subprocess.run([sys.executable, str(REPO / "tools" / "gen_song_pages.py"),
                    "--out", str(out)] + list(extra),
                   cwd=str(REPO), capture_output=True,
                   encoding="utf-8", errors="replace", timeout=60,
                   check=True)


def assemble_like_the_workflow(out: Path):
    # Mirror of .github/workflows/deploy-site.yml's assemble step; the suite
    # boot legs must serve the same artifact shape CI publishes.
    for f in ALLOW_FILES:
        shutil.copy(REPO / f, out / f)
    (out / "css").mkdir()
    (out / "js").mkdir()
    shutil.copytree(REPO / "css", out / "css", dirs_exist_ok=True)
    shutil.copytree(REPO / "js", out / "js", dirs_exist_ok=True)
    shutil.copytree(REPO / "instruments", out / "instruments", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("README.md"))
    # The song .txt bodies ride the artifact too (board §5 2026-10-07):
    # every shipped song materializes its melody live from songs/<id>.txt.
    songs = json.loads((REPO / "songs.json").read_text(encoding="utf-8"))
    files = {r["file"] for r in songs.values() if isinstance(r.get("file"), str)}
    for f in sorted(files):
        (out / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / f, out / f)


def main():
    failures = []
    with tempfile.TemporaryDirectory(prefix="genpages-") as td:
        out1 = Path(td) / "site1"
        out2 = Path(td) / "site2"
        for out in (out1, out2):
            run_gen(out, "--site-prefix", "/", "--origin", SITE_ORIGIN)
        # Stub set only: the tree now also carries the hub indexes at
        # song/index.html and song/<cat>/index.html (SEO pass 2026-10-07) —
        # those ride their own legs below, never the per-stub contracts.
        def stubs_only(out):
            root_depth = len(Path(out, "song").parts)
            return sorted(p for p in Path(out, "song").rglob("index.html")
                          if len(p.parts) == root_depth + 3)
        pages1 = stubs_only(out1)

        expected = []
        for key in expected_stub_keys():
            expected.append(("song", category_of(SONGS[key].get("group")), key))
        expected = sorted("/".join(e) + "/index.html" for e in expected)
        got = sorted(str(p.relative_to(out1)).replace("\\", "/") for p in pages1)
        if got != expected:
            failures.append(f"stub set mismatch:\n  got {got}\n  want {expected}")

        # String contracts per stub, including the ladder-family seed. The
        # serving prefix is ROOT on the pinned domain: <base> re-roots from
        # /, canonical/og:url carry the clean root path and og:image is
        # fully qualified (an og:image must be absolute; the flip gave the
        # origin to pin it against).
        want_landing = {}
        for p in pages1:
            rel = str(p.relative_to(out1)).replace("\\", "/")
            key = rel.split("/")[2]
            stub = p.read_text(encoding="utf-8")
            cat = rel.split("/")[1]
            member, inst = gen.pick_landing(key, SONGS, MANIFEST, CHARTS)
            want_landing[key] = (member, inst)
            if '<base href="/">' not in stub:
                failures.append(f"{rel}: base href missing/wrong")
            if f'<link rel="canonical" href="/song/{cat}/{key}/"' not in stub:
                failures.append(f"{rel}: canonical missing/wrong")
            if f'<meta property="og:url" content="/song/{cat}/{key}/"' not in stub:
                failures.append(f"{rel}: og:url missing/wrong")
            if stub.count('meta name="description"') != 1:
                failures.append(f"{rel}: description meta not exactly one")
            if SONGS[member].get("name") not in stub:
                failures.append(f"{rel}: og/title missing the song name")
            if f'song={member}&inst={inst}' not in stub:
                failures.append(f"{rel}: seed must carry song={member}&inst={inst}")
            # The SEO pass (Robin, 2026-10-07): titles/descriptions carry
            # the base record's game + aka searches, exactly one structured
            # data script per stub (MusicComposition + breadcrumb), and a
            # visible intro block with the melody letters and links up the
            # internal directory.
            base = SONGS[key]
            aka_m = base.get("aka") or []
            game_m = base.get("game")
            desc_m = gen.page_description(
                SONGS[member].get("name") or key, aka_m, game_m)
            title_m = gen.page_title(
                SONGS[member].get("name") or key, aka_m, game_m)
            if f'<title>{title_m}</title>' not in stub:
                failures.append(f"{rel}: static title missing/wrong "
                                f"(want {title_m!r})")
            if f'<meta name="description" content="{desc_m}" />' not in stub:
                failures.append(f"{rel}: meta description missing/wrong")
            if f'<meta property="og:title" content="{title_m}" />' not in stub:
                failures.append(f"{rel}: og:title missing/wrong")
            if f'<meta property="og:description" content="{desc_m}" />' not in stub:
                failures.append(f"{rel}: og:description missing/wrong")
            # Exactly ONE structured-data script per stub: MusicComposition
            # (its alternateName only when the record declares aliases, its
            # genre only when the game is declared) riding a breadcrumb.
            ld = re.findall(
                r'<script type="application/ld\+json">(.*?)</script>',
                stub, re.DOTALL)
            if len(ld) != 1:
                failures.append(f"{rel}: per-stub JSON-LD not exactly one")
            else:
                g = json.loads(ld[0])
                _types = {n.get("@type") for n in g.get("@graph", [])}
                if g.get("@context") != "https://schema.org" or \
                        _types != {"MusicComposition", "BreadcrumbList"}:
                    failures.append(f"{rel}: stub JSON-LD graph shape "
                                    f"{_types} / context {g.get('@context')!r}")
                mc = next((n for n in g.get("@graph", [])
                           if n.get("@type") == "MusicComposition"), {})
                alt = mc.get("alternateName")
                if aka_m and alt != aka_m:
                    failures.append(f"{rel}: MusicComposition alternateName "
                                    f"{alt!r} != {aka_m!r}")
                if not aka_m and alt is not None:
                    failures.append(f"{rel}: alternateName declared without "
                                    f"data aliases")
                if game_m and mc.get("genre") != game_m:
                    failures.append(f"{rel}: MusicComposition genre "
                                    f"{mc.get('genre')!r} != {game_m!r}")
                if not game_m and mc.get("genre"):
                    failures.append(f"{rel}: genre declared without a game")
                if mc.get("name") != (SONGS[member].get("name") or key):
                    failures.append(f"{rel}: MusicComposition name mismatch")
                crumbs = next((n for n in g.get("@graph", [])
                               if n.get("@type") == "BreadcrumbList"), {})
                _chain = [i.get("name") for i in crumbs.get("itemListElement", [])
                          if isinstance(i, dict)]
                if _chain != ["Ocarina Practice", gen.category_label(cat),
                              SONGS[member].get("name") or key]:
                    failures.append(f"{rel}: breadcrumb chain {_chain!r}")
            # The intro block: visible, with the name, the letter notes and
            # the up-directory links (category hub, root hub, brand root).
            if '<section class="seo-about"' not in stub:
                failures.append(f"{rel}: intro block missing")
            else:
                _intro = stub.split('<section class="seo-about"')[1]
                if f'<a href="/song/{cat}/"' not in _intro or \
                        '<a href="/song/"' not in _intro:
                    failures.append(f"{rel}: intro hub links missing")
                if re.search(r'<span class="seo-notes">\s*</span>', _intro):
                    failures.append(f"{rel}: intro letter-note span empty")
            # The og/meta social set: every stub carries the full preview
            # card (site name/type/description + the generated icon) so a
            # bare link preview names the song AND has an image.
            if '<meta property="og:type" content="website" />' not in stub:
                failures.append(f"{rel}: og:type missing")
            if '<meta property="og:site_name" content="Ocarina Practice" />' not in stub:
                failures.append(f"{rel}: og:site_name missing")
            if ('<meta property="og:image" '
                    f'content="{SITE_ORIGIN}/icon-512.png" />') not in stub:
                failures.append(f"{rel}: og:image missing/wrong")
            if '<meta name="twitter:card" content="summary" />' not in stub:
                failures.append(f"{rel}: twitter:card missing")
            if "../../../" in stub:
                failures.append(f"{rel}: depth-relative refs survive under <base>")

        # Legacy project-page mount, string-contracts only: the flag is a
        # parameter (the pre-flip stage ran exactly these shapes; when that
        # stage is retired this leg retires with it).
        out3 = Path(td) / "site3"
        run_gen(out3, "--site-prefix", "/Ocarina-Practice",
                "--origin", "https://verify.example")
        leg = stubs_only(out3)[0]
        rel3 = str(leg.relative_to(out3)).replace("\\", "/")
        key3 = rel3.split("/")[2]
        cat3 = rel3.split("/")[1]
        stub3 = leg.read_text(encoding="utf-8")
        if '<base href="/Ocarina-Practice/">' not in stub3:
            failures.append(f"legacy leg {rel3}: base href missing/wrong")
        if (f'<link rel="canonical" '
                f'href="/Ocarina-Practice/song/{cat3}/{key3}/"') not in stub3:
            failures.append(f"legacy leg {rel3}: canonical missing/wrong")
        if ('<meta property="og:image" '
                'content="https://verify.example/Ocarina-Practice/icon-512.png" />') \
                not in stub3:
            failures.append(f"legacy leg {rel3}: og:image prefix missing")
        # The hubs honor the mount too (the directory must relocate with
        # the artifact, same promise the <base> injection kept).
        hub3 = (out3 / "song" / "index.html")
        if not hub3.exists():
            failures.append("legacy mount leg: root hub missing")
        elif '<link rel="canonical" href="/Ocarina-Practice/song/"' \
                not in hub3.read_text(encoding="utf-8"):
            failures.append("legacy mount leg: root hub canonical prefix "
                            "missing")

        # Sitemap: home + every stub URL, nothing suppressed, sorted.
        sitemap = (out1 / "sitemap.xml")
        if not sitemap.exists():
            failures.append("sitemap.xml missing from staging")
        else:
            root = ElementTree.fromstring(sitemap.read_text(encoding="utf-8"))
            locs = [el.text and el.text.strip() for el in root.iter()
                    if el.tag == SITEMAP_NS + "loc"] or \
                   [el.text and el.text.strip() for el in root.iter()
                    if el.tag.endswith("}loc")]
            want = sorted([SITE_ORIGIN + "/", SITE_ORIGIN + "/song/"]
                          + [f"{SITE_ORIGIN}/song/{c}/"
                             for c in HUB_CATS]
                          + [f"{SITE_ORIGIN}/song/"
                             f"{category_of(SONGS[k].get('group'))}/{k}/"
                             for k in expected_stub_keys()])
            if locs != want:
                failures.append("sitemap loc set mismatch:\n  got "
                                f"{locs}\n  want {want}")

        # The SEO internal directory (Robin, 2026-10-07): /song/ root hub
        # plus one hub per emitted category — static pages (zero scripts),
        # canonical on their own path, each linking EVERY landing URL
        # under its category so crawlers reach all stubs by links alone.
        if not (out1 / "song" / "index.html").exists():
            failures.append("root hub /song/ missing")
        else:
            hub = (out1 / "song" / "index.html").read_text(encoding="utf-8")
            if "<script" in hub:
                failures.append("root hub carries a script tag (static only)")
            if '<link rel="canonical" href="/song/"' not in hub:
                failures.append("root hub canonical missing/wrong")
            for k in expected_stub_keys():
                c = category_of(SONGS[k].get("group"))
                if f'href="/song/{c}/{k}/' not in hub:
                    failures.append(f"root hub misses its {k} link")
        for c in HUB_CATS:
            cp = out1 / "song" / c / "index.html"
            if not cp.exists():
                failures.append(f"{c} hub missing")
                continue
            ch = cp.read_text(encoding="utf-8")
            if "<script" in ch:
                failures.append(f"{c} hub carries a script tag")
            if f'<link rel="canonical" href="/song/{c}/"' not in ch:
                failures.append(f"{c} hub canonical missing/wrong")
            for k in expected_stub_keys():
                if category_of(SONGS[k].get("group")) == c and \
                        f'href="/song/{c}/{k}/' not in ch:
                    failures.append(f"{c} hub misses its {k} link")

        # Ladder pin: after the re-key the Song-of-Time BASE carries the
        # 12-hole-fitting arrangement (the old -alto body) and the bass body
        # lives in song-of-time-bass, so the family walk prefers the base —
        # the original "wrong song of time" live find must stay fixed.
        if want_landing.get("song-of-time") != ("song-of-time", "oot-alto-c-12"):
            failures.append(f"landing pin song-of-time: {want_landing.get('song-of-time')!r} "
                            "(want (song-of-time, oot-alto-c-12) on the re-keyed base)")
        # Intended-instrument pin (Robin, 2026-09-25): BotW is really a bass
        # piece — the declared intended instrument must OUT-RANK the ladder
        # (the alto base would otherwise win on ladder order alone) and land
        # the best family member for it.
        if want_landing.get("botw-theme") != ("botw-theme-bass",
                                              "ico-oak-leaf-bass-c-triple"):
            failures.append(f"landing pin botw-theme: {want_landing.get('botw-theme')!r} "
                            "(want (botw-theme-bass, ico-oak-leaf-bass-c-triple) — "
                            "the declared intended instrument must outrank the ladder)")
        if not (out1 / ".nojekyll").exists():
            failures.append(".nojekyll missing from staging")

        b1 = [p.read_bytes() for p in pages1]
        b2 = [p.read_bytes() for p in stubs_only(out2)]
        if b1 != b2:
            failures.append("generator not byte-deterministic across runs")

        # REAL BOOTS: assemble the artifact like CI does and boot EVERY
        # landing stub — zero out-of-range marks is the contract.
        site = Path(td) / "artifact"
        site.mkdir()
        shutil.copytree(out1, site, dirs_exist_ok=True)
        assemble_like_the_workflow(site)

        class Mount(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(site), **kw)

            def log_message(self, *a):
                pass

        httpd = SuiteServer(("127.0.0.1", 0), Mount)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        port = httpd.server_address[1]
        base = f"http://127.0.0.1:{port}"

        try:
            # The crawler stage, SERVED: robots.txt carries its Sitemap
            # pointer; the generated sitemap serves and enumerates exactly
            # home + the stub set.
            def get_local(path):
                with urllib.request.urlopen(base + path, timeout=10) as r:
                    return r.status, r.read().decode("utf-8", "replace")

            try:
                st, robots = get_local("/robots.txt")
                if st != 200:
                    failures.append(f"robots.txt status {st}")
                elif "Sitemap:" not in robots or "sitemap.xml" not in robots:
                    failures.append("robots.txt lacks the Sitemap pointer")
            except Exception as e:
                failures.append(f"robots.txt fetch failed: {e}")
            if sitemap.exists():
                try:
                    st, served = get_local("/sitemap.xml")
                    if st != 200:
                        failures.append(f"sitemap.xml status {st}")
                    else:
                        root = ElementTree.fromstring(served)
                        n = sum(1 for el in root.iter()
                                if el.tag == SITEMAP_NS + "loc"
                                or el.tag.endswith("}loc"))
                        want_n = (1 + 1 + len(HUB_CATS)
                                  + len(expected_stub_keys()))
                        if n != want_n:
                            failures.append(
                                f"served sitemap has {n} locs, want "
                                f"{want_n}")
                except Exception as e:
                    failures.append(f"sitemap.xml fetch failed: {e}")

            # The hubs SERVE (this is the crawl surface, not just staging):
            # root + every category hub answer 200 with a real grid.
            for hub_path in ("/song/",) + tuple(
                    f"/song/{c}/" for c in HUB_CATS):
                try:
                    st, served_hub = get_local(hub_path)
                    if st != 200:
                        failures.append(f"served hub {hub_path} status {st}")
                    elif "hub-grid" not in served_hub:
                        failures.append(f"served hub {hub_path} lacks the grid")
                except Exception as e:
                    failures.append(f"served hub {hub_path} fetch failed: {e}")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                for key in sorted(want_landing):
                    cat = category_of(SONGS[key].get("group"))
                    member, inst = want_landing[key]
                    page = browser.new_page()
                    errs, bad404 = [], []
                    page.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
                    page.on("console", lambda m, errs=errs: errs.append(m.text)
                            if m.type == "error" else None)
                    page.on("response", lambda r, bad=bad404: bad.append(r.url)
                            if r.status >= 400 else None)
                    try:
                        page.goto(f"{base}/song/{cat}/{key}/", wait_until="load")
                        page.wait_for_function(
                            "document.querySelector('#instSel')"
                            f" && document.querySelector('#instSel').value === '{inst}'"
                            " && document.querySelector('#scale')"
                            f" && document.querySelector('#scale').value === '{member}'",
                            timeout=20000)
                        page.wait_for_timeout(1200)
                        oor = page.evaluate(
                            "document.querySelectorAll('.card.oor').length")
                        if oor:
                            failures.append(
                                f"{key}: boot shows {oor} out-of-range marks "
                                f"(seeded {member} on {inst})")
                        if page.evaluate(
                                "document.querySelectorAll('.card').length") < 5:
                            failures.append(f"{key}: boot rendered almost no cards")
                        if page.evaluate(
                                "document.querySelectorAll('[role=button].tok').length") < 5:
                            failures.append(f"{key}: boot rendered almost no chips")
                        # The loader discards the body's own leading comment
                        # block ("# name" + "# tempo" replace it), so the
                        # head probe must be the body's first BAR ROW — the
                        # loader keeps rows verbatim (the tidy-title leak
                        # Robin's gen_pages boot caught, 2026-09-26).
                        head = next((ln.strip()[:30] for ln in
                                     (SONGS[member].get("body") or "").split("\n")
                                     if ln.strip().startswith("|")), "")
                        src = page.evaluate("document.querySelector('#src').value")
                        if head and head not in src:
                            failures.append(
                                f"{key}: booted #src lacks {member} body head")
                        non404 = [u for u in bad404 if not u.endswith("tone.json")]
                        hard = [e for e in errs
                                if "Failed to load resource" not in e]
                        if non404:
                            failures.append(f"{key}: unexplained HTTP failures {non404}")
                        if hard:
                            failures.append(f"{key}: console/page errors {hard}")
                        # Landed-crawler semantics (Robin, IDEAS 2026-09-25):
                        # the landing SEED keeps its clean canonical path;
                        # the site title is a link to the site root (the
                        # <base> re-roots "./" for every serving shape).
                        seed_path = str(page.url).split("?")[0]
                        if not seed_path.rstrip("/").endswith(
                                f"/song/{cat}/{key}"):
                            failures.append(
                                f"{key}: landing seed must keep the clean "
                                f"path (got {page.url})")
                        if page.evaluate(
                                "document.querySelector('header h1 a')"
                                " && document.querySelector('header h1 a')"
                                ".getAttribute('href') === './'") is not True:
                            failures.append(
                                f"{key}: the site title must link the site "
                                "root (header h1 > a[href='./'])")
                        page.close()
                        # A LATER library switch must never play different
                        # content under the deep path: the URL resolves to
                        # the site root with the ? GET vars.
                        page2 = browser.new_page()
                        page3 = None
                        try:
                            page2.goto(f"{base}/song/{cat}/{key}/",
                                       wait_until="load")
                            page2.wait_for_function(
                                "document.getElementById('scale')"
                                " && document.getElementById('scale').value"
                                f" === '{member}'", timeout=20000)
                            # The library select is wired by the custom menu
                            # (the visible control is the menu) — select the
                            # native option with actionability skipped.
                            page2.select_option("#scale", "major", force=True)
                            page2.wait_for_function(
                                "document.getElementById('scale').value"
                                " === 'major' && location.pathname === '/'"
                                " && location.search.indexOf('song=') >= 0"
                                " && location.search.indexOf('inst=') >= 0",
                                timeout=20000)
                            page2.close()
                            # A typed replacement (the editor body no longer
                            # the landed song) also leaves the path: bare
                            # root, no stale vars.
                            page3 = browser.new_page()
                            page3.goto(f"{base}/song/{cat}/{key}/",
                                       wait_until="load")
                            page3.wait_for_function(
                                "(function () { const s ="
                                " document.getElementById('scale');"
                                " return s && s.options.length > 0; })()",
                                timeout=20000)
                            page3.evaluate(
                                "() => { const ta ="
                                " document.getElementById('src');"
                                " ta.value = '# typed\\nA4/4 A4/4';"
                                " ta.dispatchEvent(new Event('input',"
                                " { bubbles: true })); }")
                            page3.wait_for_function(
                                "location.pathname === '/'"
                                " && location.search.indexOf('song=') < 0",
                                timeout=20000)
                            page3.close()
                        except Exception as e:
                            failures.append(f"{key}: landed-URL switch leg "
                                            f"failed: {e}")
                            for p in (page2, page3):
                                if p:
                                    try:
                                        p.close()
                                    except Exception:
                                        pass
                    except Exception as e:
                        failures.append(f"{key}: boot failed: {e}")
                        try:
                            page.close()
                        except Exception:
                            pass
                browser.close()
        finally:
            httpd.shutdown()

        # MOUNTED rewrite leg (the relocatability promise, booted): the
        # artifact serves under a path prefix exactly like the legacy GH
        # Pages project mount, its stub generated with the matching
        # --site-prefix; a later switch must land on the MOUNT root with
        # the ? GET vars — never the domain root.
        site4 = Path(td) / "artifact4"
        run_gen(out := Path(td) / "site4", "--site-prefix", "/mp",
                "--origin", SITE_ORIGIN)
        shutil.copytree(out, site4, dirs_exist_ok=True)
        assemble_like_the_workflow(site4)

        class Mounted(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(site4), **kw)

            def translate_path(self, path):
                if path.startswith("/mp/"):
                    path = path[len("/mp"):]
                return super().translate_path(path)

            def log_message(self, *a):
                pass

        httpd2 = SuiteServer(("127.0.0.1", 0), Mounted)
        threading.Thread(target=httpd2.serve_forever, daemon=True).start()
        port2 = httpd2.server_address[1]
        base2 = f"http://127.0.0.1:{port2}"

        try:
            with sync_playwright() as p2:
                browser2 = p2.chromium.launch(headless=True)
                page4 = browser2.new_page()
                try:
                    page4.goto(f"{base2}/mp/song/zelda/botw-theme/",
                               wait_until="load")
                    page4.wait_for_function(
                        "document.querySelector('#instSel')"
                        " && document.querySelector('#scale').value"
                        " === 'botw-theme-bass'", timeout=20000)
                    # instrument change: mount root + vars (not domain root)
                    page4.select_option("#instSel", "stein-double-alto-c",
                                        force=True)
                    page4.wait_for_function(
                        "location.pathname === '/mp/'"
                        " && location.search.indexOf('song=') >= 0"
                        " && location.search.indexOf('inst=') >= 0",
                        timeout=20000)
                    # library song change: same mount root, no stale vars
                    page4.select_option("#scale", "major", force=True)
                    page4.wait_for_function(
                        "location.pathname === '/mp/'"
                        " && location.search.indexOf('song=major') >= 0",
                        timeout=20000)
                    # typed replacement: bare mount root
                    page4.evaluate(
                        "() => { const ta ="
                        " document.getElementById('src');"
                        " ta.value = '# typed\\nA4/4 A4/4';"
                        " ta.dispatchEvent(new Event('input',"
                        " { bubbles: true })); }")
                    page4.wait_for_function(
                        "location.pathname === '/mp/'"
                        " && location.search.indexOf('song=') < 0",
                        timeout=20000)
                    page4.close()
                except Exception as e:
                    failures.append(f"mounted rewrite leg failed: {e}")
                    try:
                        page4.close()
                    except Exception:
                        pass
                browser2.close()
        finally:
            httpd2.shutdown()

        if failures:
            print("FAIL gen_pages:", len(failures))
            for f in failures:
                print("  -", f)
            return 1
        print(f"PASS gen_pages: {len(pages1)} landing stubs — every base URL "
              "boots its ladder-chosen arrangement with ZERO out-of-range "
              "marks, clean console; each stub carries the SEO title/"
              "description pair, exactly one structured-data script and "
              "the visible intro block; the /song/ hub + category hubs "
              "serve link-only grids that reach every stub; sitemap "
              "enumerates home + hubs + the exact stub set; robots.txt "
              "serves its Sitemap pointer; the mounted stub rewrites land "
              "on the mount root (instrument switch, song switch, typed "
              "replacement)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
