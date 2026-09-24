#!/usr/bin/env python3
# Contract tests for tools/gen_song_pages.py: one stub per base slug
# (variants and hidden WIPs excluded), <base href> re-rooting (which must
# carry the app's runtime fetches, not just head links), canonical/og:url
# on the site prefix, song-titled head, the ?song/&inst= seed — plus a REAL
# BOOT leg: the staging tree is assembled exactly like the deploy
# workflow's allowlist, served under the /Ocarina-Practice mount, and the
# stub page must boot the right song on the right ocarina with a clean
# console (tone-file 404s are the manifest-declared allowlist).

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
SUFFIX = re.compile(r"-(alto|12|contrabass|c|up\d+|down\d+)$")

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
    # boot leg must serve the same artifact shape CI publishes.
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
            if SUFFIX.search(key) or song.get("hidden"):
                continue
            expected.append(("song", category_of(song.get("group")), key))
        expected = sorted("/".join(e) + "/index.html" for e in expected)
        got = sorted(str(p.relative_to(out1)).replace("\\", "/") for p in pages1)
        if got != expected:
            failures.append(f"stub set mismatch:\n  got {got}\n  want {expected}")

        seed_inst = MANIFEST.get("default") or "oot-alto-c-12"
        for p in pages1:
            rel = str(p.relative_to(out1)).replace("\\", "/")
            key = rel.split("/")[2]
            stub = p.read_text(encoding="utf-8")
            cat = rel.split("/")[1]
            want_inst = gen.pick_default_inst(
                gen.body_note_ids(SONGS[key].get("body") or ""), MANIFEST, CHARTS)
            if '<base href="/Ocarina-Practice/">' not in stub:
                failures.append(f"{rel}: base href missing/wrong")
            if f'rel="canonical" href="/Ocarina-Practice/song/{cat}/{key}/"' not in stub:
                failures.append(f"{rel}: canonical missing/wrong")
            if f'<meta property="og:url" content="/Ocarina-Practice/song/{cat}/{key}/"' not in stub:
                failures.append(f"{rel}: og:url missing/wrong")
            if stub.count('meta name="description"') != 1:
                failures.append(f"{rel}: description meta not exactly one")
            if SONGS[key].get("name") not in stub:
                failures.append(f"{rel}: og/title missing the song name")
            if f'song={key}&inst={want_inst}' not in stub:
                failures.append(f"{rel}: seed must carry inst={want_inst}")
            if "../../../" in stub:
                failures.append(f"{rel}: depth-relative refs survive under <base>")
        pin = gen.pick_default_inst(gen.body_note_ids(SONGS["song-of-time"]["body"]),
                                    MANIFEST, CHARTS)
        if pin != "ico-oak-leaf-bass-c-triple":
            failures.append(f"ladder case song-of-time picked {pin!r} "
                            "(want the triple bass C: 12-hole and double alto both too high)")
        if not (out1 / ".nojekyll").exists():
            failures.append(".nojekyll missing from staging")

        b1 = [p.read_bytes() for p in pages1]
        b2 = [p.read_bytes() for p in sorted((out2 / "song").rglob("index.html"))]
        if b1 != b2:
            failures.append("generator not byte-deterministic across runs")

        # REAL BOOT: assemble the artifact like CI does and boot one stub
        # under the /Ocarina-Practice mount.
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
        tchu = gen.pick_default_inst(gen.body_note_ids(SONGS["song-of-time"]["body"]),
                                     MANIFEST, CHARTS)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                errs, bad404 = [], []
                page.on("pageerror", lambda e: errs.append(str(e)))
                page.on("console", lambda m: errs.append("console: " + m.text)
                        if m.type == "error" else None)
                page.on("response", lambda r: bad404.append(r.url)
                        if r.status >= 400 else None)
                page.goto(f"{base}/song/zelda/song-of-time/", wait_until="load")
                page.wait_for_function(
                    "document.querySelector('#instSel') && document.querySelector('#instSel').value === '"
                    + tchu + "' && document.querySelector('#scale') && document.querySelector('#scale').value === 'song-of-time'",
                    timeout=20000)
                page.wait_for_timeout(2000)
                oor = page.evaluate("document.querySelectorAll('.card.oor').length")
                if oor:
                    failures.append(f"boot shows {oor} out-of-range marks; "
                                    f"landing default {tchu} does not fit the body")
                if page.evaluate("document.querySelectorAll('.card').length") < 5:
                    failures.append("boot rendered almost no sheet cards")
                head = SONGS["song-of-time"]["body"].strip().split("\n")[0][:30]
                src = page.evaluate("document.querySelector('#src').value")
                if head and head not in src:
                    failures.append(f"booted #src lacks the body head {head!r}")
                if page.evaluate("document.querySelectorAll('[role=button].tok').length") < 5:
                    failures.append("boot rendered almost no token chips")
                non404res = [u for u in bad404 if not u.endswith("tone.json")]
                hard = [e for e in errs if "Failed to load resource" not in e]
                if non404res:
                    failures.append(f"unexplained HTTP failures: {non404res}")
                if hard:
                    failures.append(f"boot console/page errors: {hard}")
                browser.close()
        finally:
            httpd.shutdown()

    if failures:
        print("FAIL gen_pages:", len(failures))
        for f in failures:
            print("  -", f)
        return 1
    print("PASS gen_pages: stubs contracted under <base>, boot-verified on the "
          "mounted artifact (right song, right ocarina, clean console)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
