#!/usr/bin/env python3
# Generate per-song landing stub pages for the static site.
#
#   python tools/gen_song_pages.py --out site/
#
# For every BASE slug in songs.json (no registered variant suffix, not
# hidden) this writes song/<category>/<slug>/index.html derived from the
# repo root index.html: asset hrefs re-rooted for the stub's directory
# depth, a rel=canonical to itself, song-titled og/meta for preview bots,
# and a tiny pre-boot seed that turns the clean path into the app's
# existing ?song=<key>&inst=<default> query so the app boots that song
# with the 12-hole C alto by default.
#
# Output is a STAGING tree: nothing here deploys by itself. The deploy
# workflow (.github/workflows/deploy-site.yml) runs this generator and
# assembles the published artifact from an explicit allowlist — the
# staging/concept never enters Git (site/ is gitignored): the generated
# tree is pushed by Actions only.
#
# The variant-suffix contract mirrors tests/shipped_songs.py (that suite
# is the enforced source of truth; keep the two in step on purpose).

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SUFFIX = re.compile(r"-(alto|12|contrabass|c|up\d+|down\d+)$")


def category_of(group):
    g = (group or "").lower()
    if "zelda" in g:
        return "zelda"
    if "scale" in g:
        return "scales"
    if "other" in g or g == "":
        return "other"
    return re.sub(r"[^a-z0-9-]+", "-", g.split()[0]).strip("-") or "other"


def build_stub(html, key, song, cat, inst, site_prefix):
    prefix = "../" * 3  # song/<cat>/<slug>/ → site root
    for ref in ("favicon.svg", "manifest.webmanifest", "icon-192.png",
                "css/app.css", "icon-512.png"):
        html = html.replace(f'href="{ref}"', f'href="{prefix}{ref}"')
    html = html.replace('src="js/app.js"', f'src="{prefix}js/app.js"')
    name = song.get("name") or key
    desc = (f"Play {name} on the ocarina: hole-fingering tab, playback and "
            f"practice with the built-in tuner.")
    # ONE description per page: replace the shell's static one instead of
    # injecting a second (preview bots read the first they see).
    html = re.sub(r'<meta name="description" content="[^"]*" ?/>',
                  '<meta name="description" content="' + desc + '" />',
                  html, count=1)
    canonical = f"{site_prefix}/song/{cat}/{key}/"
    stub_meta = (
        f'<link rel="canonical" href="{canonical}" />\n'
        f'<meta property="og:title" content="{name} — Ocarina Practice" />\n'
        f'<meta property="og:url" content="{canonical}" />\n')
    script = "<script type=\"module\" src="
    seed = ('<script>if (!location.search) history.replaceState(null, "", '
            f'location.pathname + "?song={key}&inst={inst}");</script>\n  ')
    # static <title> tells preview bots what the page is; the app may
    # retitle after boot (runtime JS wins where it runs).
    html = re.sub(r"<title>.*?</title>",
                  f"<title>{name} — Ocarina Practice</title>", html, count=1)
    html = html.replace("<head>", "<head>\n  " + stub_meta, 1)
    html = html.replace(script, seed + script, 1)
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/")
    ap.add_argument("--site-prefix", default="/Ocarina-Practice",
                    help="site-root URL prefix of a GH Pages project site; "
                    "canonical/og:url carry it (empty = root-deployed domain)")
    args = ap.parse_args()
    site_prefix = "/" + args.site_prefix.strip("/")
    if site_prefix == "/":
        site_prefix = ""
    songs = json.loads((REPO / "songs.json").read_text(encoding="utf-8"))
    manifest = json.loads((REPO / "instruments.json").read_text(encoding="utf-8"))
    inst = manifest.get("default") or "oot-alto-c-12"
    html = (REPO / "index.html").read_text(encoding="utf-8")

    out = REPO / args.out
    written = []
    for key, song in sorted(songs.items()):
        if SUFFIX.search(key):
            continue  # variants ride the base page, not their own URL
        if song.get("hidden"):
            continue  # WIPs stay unpublished
        stub = build_stub(html, key, song, category_of(song.get("group")),
                          inst, site_prefix)
        p = out / "song" / category_of(song.get("group")) / key / "index.html"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(stub, encoding="utf-8", newline="\n")
        written.append(str(p.relative_to(out)))
    (out / ".nojekyll").write_text("", encoding="utf-8", newline="\n")
    print(f"wrote {len(written)} stub pages (+ .nojekyll) under {out}")
    for w in written:
        print("  " + w)


if __name__ == "__main__":
    main()
