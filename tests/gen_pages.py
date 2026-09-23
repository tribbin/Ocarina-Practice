#!/usr/bin/env python3
# Contract tests for tools/gen_song_pages.py: one stub per base slug
# (variants and hidden WIPs excluded), each carrying its canonical, its
# og:title, the ?song/&inst= seed with the manifest's default instrument,
# and asset refs re-rooted for the stub's directory depth; byte-stable
# across two runs. Pure stdlib + generator subprocess â€” no browser.

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GEN = REPO / "tools" / "gen_song_pages.py"
SONGS = json.loads((REPO / "songs.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((REPO / "instruments.json").read_text(encoding="utf-8"))
SUFFIX = re.compile(r"-(alto|12|contrabass|c|up\d+|down\d+)$")


def category_of(group):
    g = (group or "").lower()
    if "zelda" in g:
        return "zelda"
    if "scale" in g:
        return "scales"
    return "other"


def main():
    failures = []
    with tempfile.TemporaryDirectory(prefix="genpages-") as td:
        out1 = Path(td) / "site1"
        out2 = Path(td) / "site2"
        for out in (out1, out2):
            subprocess.run([sys.executable, str(GEN), "--out", str(out), "--site-prefix", "/Ocarina-Practice"],
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
            if f'rel="canonical" href="/Ocarina-Practice/song/{cat}/{key}/"' not in stub:
                failures.append(f"{rel}: canonical missing/wrong")
            if f'<meta property="og:url" content="/Ocarina-Practice/song/{cat}/{key}/"' not in stub:
                failures.append(f"{rel}: og:url missing/wrong")
            if stub.count('meta name="description"') != 1:
                failures.append(f"{rel}: description meta not exactly one")
            if SONGS[key].get("name") not in stub:
                failures.append(f"{rel}: og/title missing the song name")
            if f'song={key}&inst={seed_inst}' not in stub:
                failures.append(f"{rel}: seed (?song/&inst={seed_inst}) missing")
            if 'href="css/app.css"' in stub or 'src="js/app.js"' in stub:
                failures.append(f"{rel}: un-rooted asset refs survive")
            if 'href="../../../css/app.css"' not in stub:
                failures.append(f"{rel}: rooted css ref missing")
        if not (out1 / ".nojekyll").exists():
            failures.append(".nojekyll missing from staging")

        names1 = [p.read_bytes() for p in pages1]
        names2 = [p.read_bytes() for p in sorted((out2 / "song").rglob("index.html"))]
        if names1 != names2:
            failures.append("generator not byte-deterministic across runs")

    if failures:
        print("FAIL gen_pages:", len(failures))
        for f in failures:
            print("  -", f)
        return 1
    print(f"PASS gen_pages: {len(pages1)} stubs, seed/canonical/og/roots all "
          "contracted, byte-deterministic")
    return 0


if __name__ == "__main__":
    sys.exit(main())
