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
# tone.json, the 12-hole does not).

import http.server
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import gen_song_pages as gen

SONGS = json.loads((REPO / "songs.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((REPO / "instruments.json").read_text(encoding="utf-8"))
CHARTS = {i["id"]: gen.chart_ids(i["id"], MANIFEST) for i in MANIFEST["instruments"]}

ALLOW_FILES = ["index.html", "sw.js", "manifest.webmanifest", "favicon.svg",
               "icon-192.png", "icon-512.png", "hyrule.webp",
               "songs.json", "instruments.json"]


def category_of(group):
    g = (group or "").lower()
    if "zelda" in g:
        return "zelda"
    if "scale" in g:
        return "scales"
    return "other"


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


def main():
    failures = []
    with tempfile.TemporaryDirectory(prefix="genpages-") as td:
        out1 = Path(td) / "site1"
        out2 = Path(td) / "site2"
        for out in (out1, out2):
            subprocess.run([sys.executable, str(REPO / "tools" / "gen_song_pages.py"),
                            "--out", str(out),
                            "--site-prefix", "/Ocarina-Practice"],
                           cwd=str(REPO), capture_output=True,
                           encoding="utf-8", errors="replace", timeout=60,
                           check=True)
        pages1 = sorted((out1 / "song").rglob("index.html"))

        expected = []
        for key, song in SONGS.items():
            if gen.SUFFIX.search(key) or song.get("hidden"):
                continue
            expected.append(("song", category_of(song.get("group")), key))
        expected = sorted("/".join(e) + "/index.html" for e in expected)
        got = sorted(str(p.relative_to(out1)).replace("\\", "/") for p in pages1)
        if got != expected:
            failures.append(f"stub set mismatch:\n  got {got}\n  want {expected}")

        # String contracts per stub, including the ladder-family seed.
        want_landing = {}
        for p in pages1:
            rel = str(p.relative_to(out1)).replace("\\", "/")
            key = rel.split("/")[2]
            stub = p.read_text(encoding="utf-8")
            cat = rel.split("/")[1]
            member, inst = gen.pick_landing(key, SONGS, MANIFEST, CHARTS)
            want_landing[key] = (member, inst)
            if '<base href="/Ocarina-Practice/">' not in stub:
                failures.append(f"{rel}: base href missing/wrong")
            if f'rel="canonical" href="/Ocarina-Practice/song/{cat}/{key}/"' not in stub:
                failures.append(f"{rel}: canonical missing/wrong")
            if f'<meta property="og:url" content="/Ocarina-Practice/song/{cat}/{key}/"' not in stub:
                failures.append(f"{rel}: og:url missing/wrong")
            if stub.count('meta name="description"') != 1:
                failures.append(f"{rel}: description meta not exactly one")
            if SONGS[member].get("name") not in stub:
                failures.append(f"{rel}: og/title missing the song name")
            if f'song={member}&inst={inst}' not in stub:
                failures.append(f"{rel}: seed must carry song={member}&inst={inst}")
            if "../../../" in stub:
                failures.append(f"{rel}: depth-relative refs survive under <base>")
        # Ladder pin: Song of Time's bass body never fits the 12-hole, so its
        # landing boots the alto arrangement on the 12-hole — the fix for the
        # "wrong song of time" live find.
        if want_landing.get("song-of-time") != ("song-of-time-alto", "oot-alto-c-12"):
            failures.append(f"landing pin song-of-time: {want_landing.get('song-of-time')!r} "
                            "(want (song-of-time-alto, oot-alto-c-12))")
        if not (out1 / ".nojekyll").exists():
            failures.append(".nojekyll missing from staging")

        b1 = [p.read_bytes() for p in pages1]
        b2 = [p.read_bytes() for p in sorted((out2 / "song").rglob("index.html"))]
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

            def translate_path(self, path):
                if path.startswith("/Ocarina-Practice"):
                    path = path[len("/Ocarina-Practice"):] or "/"
                return super().translate_path(path)

            def log_message(self, *a):
                pass

        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Mount)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        port = httpd.server_address[1]
        base = f"http://127.0.0.1:{port}/Ocarina-Practice"

        try:
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
                        head = (SONGS[member].get("body") or "").strip() \
                            .split("\n")[0][:30]
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
                        page.close()
                    except Exception as e:
                        failures.append(f"{key}: boot failed: {e}")
                        try:
                            page.close()
                        except Exception:
                            pass
                browser.close()
        finally:
            httpd.shutdown()

    if failures:
        print("FAIL gen_pages:", len(failures))
        for f in failures:
            print("  -", f)
        return 1
    print(f"PASS gen_pages: {len(pages1)} landing stubs — every base URL boots "
          "its ladder-chosen arrangement with ZERO out-of-range marks, clean console")
    return 0


if __name__ == "__main__":
    sys.exit(main())
