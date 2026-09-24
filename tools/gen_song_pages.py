#!/usr/bin/env python3
# Generate per-song landing stub pages for the static site.
#
#   python tools/gen_song_pages.py --out site/
#
# For every BASE slug in songs.json (no registered variant suffix, not
# hidden) this writes song/<category>/<slug>/index.html derived from the
# repo root index.html: a <base href> that re-roots every relative
# reference (head links, the module src, the app's runtime fetches AND the
# service worker), a rel=canonical to itself, song-titled og/meta for
# preview bots, and a tiny pre-boot seed that turns the clean path into
# the app's existing ?song=<key>&inst=<chosen> query. <chosen> follows the
# fitting ladder below so every landing page boots playable.
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

# Landing-page default-ocarina ladder (Robin, 2026-09-24): 12-hole > double
# alto C > triple bass C > contrabass. An instrument is seeded only when the
# body actually fits its chart; past the ladder, any other manifest
# instrument in manifest order may serve, and the manifest default is the
# last resort (the shipped-songs suite guarantees every song fits SOME
# chart, so the ladder should always land).
LADDER = ["oot-alto-c-12", "stein-double-alto-c",
          "ico-oak-leaf-bass-c-triple", "ico-contrabass-11-c"]

_N = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_NN = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def body_note_ids(body):
    # Melody-note ids (s-spelled, chart alphabet): drop comment lines and
    # every [...] bracket (supports/labels are instrument-pinned, never
    # melody), then read explicit-octave note tokens. Sufficient for
    # instrument SELECTION; the browser boot leg is the real verifier.
    lines = [ln for ln in body.split("\n") if not ln.lstrip().startswith("#")]
    flat = re.sub(r"\[[^\]]*\]", "", "\n".join(lines))
    ids = []
    for letter, acc, octv in re.findall(r"([A-G])([#bs]?)(\d)", flat):
        midi = (int(octv) + 1) * 12 + _N[letter] + (acc == "b" and -1 or acc and 1 or 0)
        ids.append(_NN[((midi % 12) + 12) % 12] + str(midi // 12 - 1))
    return ids


def chart_ids(inst_id, manifest):
    row = next((i for i in manifest["instruments"] if i["id"] == inst_id), None)
    if not row or not row.get("fingerings"):
        return None
    data = json.loads((REPO / row["fingerings"]).read_text(encoding="utf-8"))
    return {n["id"] for n in data["notes"]}


def pick_default_inst(note_ids, manifest, charts):
    manifest_insts = [i["id"] for i in manifest["instruments"]]
    fits = [i for i in manifest_insts
            if charts.get(i) and all(n in charts[i] for n in note_ids)]
    for i in LADDER:
        if i in fits:
            return i
    return fits[0] if fits else manifest_insts[0]


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
    # <base href> re-roots EVERY relative reference — head links, the module
    # src AND the app's runtime fetches (songs.json / instruments.json /
    # css text / manifest-driven instrument files) and the service-worker
    # registration. A per-depth href rewrite cannot reach runtime fetches,
    # which is exactly what the first live boot caught (songs.json 404 two
    # directories deep, boot dead).
    html = html.replace("<head>", f'<head>\n  <base href="{site_prefix}/">', 1)
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
    charts = {i["id"]: chart_ids(i["id"], manifest) for i in manifest["instruments"]}
    html = (REPO / "index.html").read_text(encoding="utf-8")

    out = REPO / args.out
    written = []
    for key, song in sorted(songs.items()):
        if SUFFIX.search(key):
            continue  # variants ride the base page, not their own URL
        if song.get("hidden"):
            continue  # WIPs stay unpublished
        inst = pick_default_inst(body_note_ids(song.get("body") or ""),
                                 manifest, charts)
        stub = build_stub(html, key, song, category_of(song.get("group")),
                          inst, site_prefix)
        p = out / "song" / category_of(song.get("group")) / key / "index.html"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(stub, encoding="utf-8", newline="\n")
        written.append(f"{p.relative_to(out)}  [{inst}]")
    (out / ".nojekyll").write_text("", encoding="utf-8", newline="\n")
    print(f"wrote {len(written)} stub pages (+ .nojekyll) under {out}")
    for w in written:
        print("  " + w)


if __name__ == "__main__":
    main()
