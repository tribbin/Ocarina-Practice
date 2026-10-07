#!/usr/bin/env python3
# Generate per-song landing stub pages for the static site.
#
#   python tools/gen_song_pages.py --out site/ --site-prefix / --origin \
#       https://ocarina-practice.com
#
# For every BASE slug in songs.json (no registered variant suffix, not
# hidden) this writes song/<category>/<slug>/index.html derived from the
# repo root index.html: a <base href> that re-roots every relative
# reference (head links, the module src, the app's runtime fetches AND the
# service worker), a rel=canonical to itself, song-titled og/meta for
# preview bots, and a tiny pre-boot seed that turns the clean path into
# the app's existing ?song=<key>&inst=<chosen> query. <chosen> follows the
# fitting ladder below so every landing page boots playable: the seed
# names the FAMILY member that fits the ladder's chosen instrument (the
# base slug when it fits, else the first variant that does).
# A sitemap.xml lands beside it: home + every emitted URL, nothing
# suppressed, byte-deterministic (no lastmod — the serving tree's truth
# is the corpus, and pages themselves may be worth a recrawl as-is).
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
SUFFIX = re.compile(r"-(alto|12|contrabass|c|up\d+|down\d+|midi)$")

# Landing-page default-ocarina ladder (Robin, 2026-09-24): 12-hole > double
# alto C > triple bass C > contrabass. An instrument is seeded only when the
# body actually fits its chart; past the ladder, any other manifest
# instrument in manifest order may serve, and the manifest default is the
# last resort (the shipped-songs suite guarantees every song fits SOME
# chart, so the ladder should always land).
LADDER = ["oot-alto-c-12", "stein-double-alto-c",
          "ico-oak-leaf-bass-c-triple", "ico-contrabass-11-c"]

_N = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
# Chart ids are s-spelled (Fs4/As4) — emitting display sharps ('F#4') made
# every accidental note fail the chart membership test (the all-white-key
# Song of Time-alto boot masked the bug until the every-URL boot read).
_NN = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]


def body_note_ids(body):
    # Melody-note ids (s-spelled, chart alphabet): drop comment lines and
    # every [...] bracket (supports/labels are instrument-pinned, never
    # melody), then read explicit-octave note tokens. Track blocks ("#track"
    # headers onward) are arrangement layers, not the melody — the landing
    #/chart-fit question is about the melody the player fingers. Sufficient
    # for instrument SELECTION; the browser boot leg is the real verifier.
    lines = []
    for ln in body.split("\n"):
        if re.match(r"#[ \t]*track\b", ln, re.I):
            break
        if not ln.lstrip().startswith("#"):
            lines.append(ln)
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


def family_members(key, songs):
    # A song family: the base slug plus every registered-suffix variant
    # that chains to it. The CANON ARRANGEMENT seeds the landing when it
    # fits (the content-marker variant — the family's own interpretation of
    # the piece, Robin 2026-09-26: "our MIDI transcription version the only
    # version"), the base boots when it fits but no arrangement does, and
    # other instruments/interval variants fill in behind, alphabetically.
    fam = [k for k in songs if k == key or k.startswith(key + "-")]
    def rank(k):
        if k.endswith("-midi"):      # the content-marker arrangement leads
            return 0
        return 1 if k == key else 2
    return sorted(fam, key=lambda k: (rank(k), k))


def fits_chart(key, body, inst, charts):
    ids = body_note_ids(body or "")
    chart = charts.get(inst)
    return bool(chart) and all(n in chart for n in ids)


def pick_landing(key, songs, manifest, charts):
    # Robin's intended-instrument override (2026-09-25): a song may declare
    # the ocarina it was WRITTEN for ("some songs are really not made for
    # the alto") — songs.json's `intended` field. When the declared chart is
    # in the manifest and ANY family member fits it, that instrument lands
    # with its best member (base first, then variants alphabetically). The
    # ladder walk below still rules everything else — and any song whose
    # intended chart fits nothing in the family (a bad id is validated away)
    # falls back to the ladder, never dead-ends.
    members = family_members(key, songs)
    manifest_insts = [i["id"] for i in manifest["instruments"]]
    intended = (songs.get(key) or {}).get("intended")
    if intended and intended in manifest_insts:
        for m in members:
            if fits_chart(m, songs[m].get("body"), intended, charts):
                return m, intended
    for inst in [i for i in LADDER if i in manifest_insts] + \
                [i for i in manifest_insts if i not in LADDER]:
        for m in members:
            if fits_chart(m, songs[m].get("body"), inst, charts):
                return m, inst
    default_id = next((i["id"] for i in manifest["instruments"]
                       if i["id"] == manifest.get("default")),
                      manifest["instruments"][0]["id"])
    return members[0], default_id


def page_title(song, key):
    # The <title>/og:title shape (Robin's SEO pass 2026-10-07): the song's
    # searched name first (with its first alias in parens), the source game
    # when the data declares one — "Ocarina of Time" is the phrase most of
    # this catalog rides — then the tabs phrase and the brand.
    name = song.get("name") or key
    aka = song.get("aka") or []
    head = name + (f" ({aka[0]})" if aka else "")
    game = song.get("game")
    return head + (f" — {game} Ocarina Tabs" if game
                   else " — Ocarina Tabs") + " | Ocarina Practice"


def page_description(song, key):
    # One description per page, <= ~160 chars: name + aliases + game +
    # the tab words people search. Dropped aliases when the string runs
    # long (the name and the first alias never drop).
    aka = list(song.get("aka") or [])
    game = song.get("game")

    def build(keep):
        lead = ", ".join([song.get("name") or key] + aka[:keep])
        core = lead + " ocarina tabs"
        if game:
            core += f" from {game}"
        return (core + ": letter notes, hole-by-hole fingerings, "
                "playback and practice tuner.")

    desc = build(len(aka))
    while len(desc) > 160 and len(aka) > 1:
        aka.pop()
        desc = build(len(aka))
    return desc


def display_ids(ids):
    # The letters people search: display sharps for humans ('F#4' — chart
    # IDs stay s-spelled, the same gen lesson the membership test learned).
    return [i.replace("s", "#", 1) if i[1:2] == "s" else i for i in ids]


def category_of(group):
    g = (group or "").lower()
    if "zelda" in g:
        return "zelda"
    if "scale" in g:
        return "scales"
    if "other" in g or g == "":
        return "other"
    return re.sub(r"[^a-z0-9-]+", "-", g.split()[0]).strip("-") or "other"


def page_title(name, aka, game):
    # The <title>/og:title shape (Robin's SEO pass 2026-10-07): the song's
    # searched name first (with its first alias in parens), the source game
    # when the data declares one — "Ocarina of Time" is the phrase most of
    # this catalog rides — then the tabs phrase and the brand. A game whose
    # own name carries "Ocarina" skips the doubled word ("Ocarina of Time
    # Tabs", never "Ocarina of Time Ocarina Tabs").
    head = name + (f" ({aka[0]})" if aka else "")
    if game:
        mid = f" — {game} Tabs" if "ocarina" in game.lower() \
            else f" — {game} Ocarina Tabs"
    else:
        mid = " — Ocarina Tabs"
    return head + mid + " | Ocarina Practice"


def page_description(name, aka, game):
    # One description per page, <= ~160 chars: name + aliases + game +
    # the tab words people search. Aliases drop tail-first when the
    # string runs long (name and first alias never drop).
    aka = list(aka)
    game = game if game else None

    def build(keep):
        lead = ", ".join([name] + aka[:keep])
        core = lead + " ocarina tabs"
        if game:
            core += f" from {game}"
        return (core + ": letter notes, hole-by-hole fingerings, "
                "playback and practice tuner.")

    desc = build(len(aka))
    while len(desc) > 160 and len(aka) > 1:
        aka.pop()
        desc = build(len(aka))
    return desc


def member_label(member, key):
    # The grid cell text for a family member: human words, not the raw
    # registered suffix (the "-c" class is an octave C variant, "down3"
    # a thirds-down derivation, "-midi" the content-marker arrangement).
    if member == key:
        return "main"
    suf = member[len(key) + 1:]
    named = {"bass": "bass", "midi": "arrangement", "c": "in C",
             "alto": "alto", "contrabass": "contrabass", "12": "12-hole"}
    if suf in named:
        return named[suf]
    m = re.match(r"^(up|down)(\d+)$", suf)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return suf


def _aka_clause(aka):
    return f" (also known as {', '.join(aka)})" if aka else ""


def _game_clause(game):
    return f"from {game}: " if game else ""


def intro_block(key, base, body, cat, site_prefix):
    # The crawlable content Google can rank without rendered JS: what this
    # tab is (name + aliases + game, the exact words people search), the
    # melody as plain letter notes, and links UP the internal directory
    # (stubs → category hub → root hub). Visible text, no hidden tricks.
    name = base.get("name") or key
    aka = base.get("aka") or []
    game = base.get("game")
    letters = display_ids(body_note_ids(body or ""))
    return (
        f'<section class="seo-about" style="max-width:860px;margin:24px '
        f'auto 40px;padding:0 20px;line-height:1.55">\n'
        f'  <h2 style="font-size:1.15em;margin:0 0 .4em">{name}'
        + (f" ({aka[0]}) ocarina tab" if aka else " ocarina tab")
        + '</h2>\n'
        f'  <p style="margin:0 0 .8em">{name}{_aka_clause(aka)} ocarina tab'
        f' — {_game_clause(game)}letter notes with the hole-by-hole '
        f'fingerings, real playback and a tuner to play along.</p>\n'
        f'  <p style="margin:0 0 .8em;font-size:.95em">'
        f'<b>Melody letter notes:</b> '
        f'<span class="seo-notes">{" ".join(letters)}</span></p>\n'
        f'  <nav style="font-size:.9em">\n'
        f'    <a href="{site_prefix}/song/{cat}/">{category_label(cat)}'
        f' ocarina tabs</a> ·\n'
        f'    <a href="{site_prefix}/song/">All songs</a> ·\n'
        f'    <a href="{site_prefix}/">Ocarina Practice</a>\n'
        f'  </nav>\n'
        '</section>\n')


def stub_jsonld(name, aka, game, desc, cat, key, site_prefix, origin):
    node = {"@type": "MusicComposition", "name": name, "description": desc,
            "url": f"{origin}{site_prefix}/song/{cat}/{key}/",
            "image": f"{origin}{site_prefix}/icon-512.png",
            "inLanguage": "en"}
    if aka:
        node["alternateName"] = list(aka)
    if game:
        node["genre"] = game
    graph = [node,
             {"@type": "BreadcrumbList", "itemListElement": [
                 {"@type": "ListItem", "position": 1, "name": "Ocarina"
                  " Practice", "item": f"{origin}{site_prefix}/"},
                 {"@type": "ListItem", "position": 2, "name":
                  category_label(cat), "item":
                  f"{origin}{site_prefix}/song/{cat}/"},
                 {"@type": "ListItem", "position": 3, "name": name, "item":
                  f"{origin}{site_prefix}/song/{cat}/{key}/"}]}]
    payload = json.dumps({"@context": "https://schema.org", "@graph": graph},
                         ensure_ascii=False, separators=(",", ":"))
    return (f'<script type="application/ld+json">{payload}</script>\n')


def category_label(cat):
    return {"zelda": "Zelda", "scales": "Scales"}.get(cat, "More songs")


def hub_grid(entries, songs, manifest, charts, site_prefix):
    # Robin's grid: instruments vs songs-with-their-variations — a cell
    # lists every family member that fits that instrument's chart, each
    # deep-linking the landing page seeded for exactly that pairing.
    cols = manifest["instruments"]
    out = ['<table class="hub-grid" style="border-collapse:collapse;'
           'width:100%;margin:16px 0">',
           '<thead><tr><th scope="col" style="text-align:left;border:1px'
           ' solid #d8cfc0;padding:8px 10px;background:#f6efe6">Song'
           '</th>']
    for c in cols:
        out.append(f'<th scope="col" style="text-align:left;border:1px'
                   f' solid #d8cfc0;padding:8px 10px;background:#f6efe6">'
                   f'{c.get("type") or c["id"]}</th>')
    out.append('</tr></thead><tbody>')
    for cat, key in entries:
        base = songs[key]
        name = base.get("name") or key
        cells = []
        for c in cols:
            inst = c["id"]
            links = []
            for m in family_members(key, songs):
                if fits_chart(m, songs[m].get("body"), inst, charts):
                    links.append(
                        f'<a href="{site_prefix}/song/{cat}/{key}/'
                        f'?song={m}&amp;inst={inst}">'
                        f'{member_label(m, key)}</a>')
            cells.append(" · ".join(links) if links else "—")
        out.append(
            f'<tr><th scope="row" style="text-align:left;border:1px solid '
            f'#d8cfc0;background:#f6efe6">{name}</th>'
            + "".join(f'<td style="border:1px solid #d8cfc0;padding:8px '
                      f'10px">{c}</td>' for c in cells)
            + '</tr>')
    out.append('</tbody></table>')
    return "".join(out)


def hub_page(title, desc, canonical, crumbs, h1, intro, grids, site_prefix):
    crumb_links = " &gt; ".join(
        f'<a href="{href}">{label}</a>' if href else label
        for label, href in crumbs)
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        f'<meta name="description" content="{desc}" />\n'
        f'<link rel="canonical" href="{canonical}" />\n'
        f'<title>{title}</title>\n'
        '<style>body{font-family:system-ui,Segoe UI,Roboto,sans-serif;'
        'margin:24px auto;padding:0 20px;max-width:1000px;color:#222;'
        'background:#fffdf8}a{color:#0a5ba4}.crumbs{font-size:.85em}'
        '</style>\n</head>\n<body>\n'
        f'<p class="crumbs">{crumb_links}</p>\n'
        f'<h1>{h1}</h1>\n'
        f'<p>{intro}</p>\n{grids}\n'
        f'<p style="font-size:.9em">Every linked song boots as a'
        f' play-along ocarina tab on <a href="{site_prefix}/">Ocarina'
        f' Practice</a>.</p>\n'
        '</body>\n</html>\n')


def build_stub(html, key, song, member, base, cat, inst, site_prefix, origin):
    # The shell's OWN SEO pair (canonical "/" + the WebApplication JSON-LD)
    # must not ride along: build_stub copies the whole head, and a stub
    # page keeps exactly ONE canonical (its song path) and ZERO JSON-LD
    # (no per-stub application block). Strip both before the stub block
    # below re-adds them in the stub's shape.
    html = re.sub(r'<link rel="canonical" href="[^"]*" ?/>\s*\n?', "", html,
                  count=1)
    html = re.sub(r'<script type="application/ld\+json">.*?</script>\n?',
                  "", html, count=1, flags=re.DOTALL)
    # <base href> re-roots EVERY relative reference — head links, the module
    # src AND the app's runtime fetches (songs.json / instruments.json /
    # css text / manifest-driven instrument files) and the service-worker
    # registration. A per-depth href rewrite cannot reach runtime fetches,
    # which is exactly what the first live boot caught (songs.json 404 two
    # directories deep, boot dead). The value is the SERVING prefix — the
    # project-page mount pre-flip, root on the pinned domain after it.
    html = html.replace("<head>", f'<head>\n  <base href="{site_prefix}/">', 1)
    # Naming: the member's display name (the arrangement the page boots)
    # with the BASE record's searchable game/aka metadata (the aliases and
    # the source game belong to the song, every arrangement of it).
    name = song.get("name") or key
    aka = base.get("aka") or []
    game = base.get("game")
    desc = page_description(name, aka, game)
    # ONE description per page: replace the shell's static one instead of
    # injecting a second (preview bots read the first they see).
    html = re.sub(r'<meta name="description" content="[^"]*" ?/>',
                  '<meta name="description" content="' + desc + '" />',
                  html, count=1)
    canonical = f"{site_prefix}/song/{cat}/{key}/"
    # The full preview-card set: og:type/site_name/description give bots the
    # surrounding identity, og:image (the generated PWA icon, sized) gives
    # link previews something to render, twitter:card pins the summary
    # layout. og:image is fully qualified — bots require an absolute URL,
    # and the flip pinned the serving origin; --origin is the deploy's
    # scheme+host (the site root), never including the prefix itself. The
    # prefix-carrying URLs (canonical/og:url, <base>) stay origin-relative
    # so the artifact keeps serving from any mount.
    stub_meta = (
        f'<link rel="canonical" href="{canonical}" />\n'
        f'<meta property="og:title" content="'
        + page_title(name, aka, game) + '" />\n'
        f'<meta property="og:url" content="{canonical}" />\n'
        f'<meta property="og:type" content="website" />\n'
        f'<meta property="og:site_name" content="Ocarina Practice" />\n'
        f'<meta property="og:description" content="{desc}" />\n'
        f'<meta property="og:image" content="{origin}{site_prefix}/icon-512.png" />\n'
        f'<meta property="og:image:width" content="512" />\n'
        f'<meta property="og:image:height" content="512" />\n'
        f'<meta property="og:image:alt" content="Ocarina Practice icon" />\n'
        f'<meta name="twitter:card" content="summary" />\n'
        + stub_jsonld(name, aka, game, desc, cat, key, site_prefix, origin))
    script = "<script type=\"module\" src="
    seed = ('<script>if (!location.search) history.replaceState(null, "", '
            f'location.pathname + "?song={member}&inst={inst}");</script>\n  ')
    # static <title> tells preview bots what the page is; the app may
    # retitle after boot (runtime JS wins where it runs).
    html = re.sub(r"<title>.*?</title>",
                  f"<title>{page_title(name, aka, game)}</title>", html, count=1)
    # og block sits at the END of <head>: the shell's charset/meta keep
    # their original head-start positions (charset stays in the first KB).
    html = html.replace("</head>", "  " + stub_meta + "</head>", 1)
    html = html.replace(script, seed + script, 1)
    # The crawlable intro rides at the very bottom: real text (name,
    # aliases, game, letter notes) with links up the internal directory.
    html = html.replace("</body>",
                        intro_block(key, base, song.get("body"), cat,
                                    site_prefix) + "</body>", 1)
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/")
    ap.add_argument("--site-prefix", default="/Ocarina-Practice",
                    help="site-root URL prefix of a GH Pages project site; "
                    "canonical/og:url carry it (empty = root-deployed domain)")
    ap.add_argument("--origin", default="https://ocarina-practice.com",
                    help="serving origin (scheme + host, the SITE root, "
                    "pathless): used for sitemap <loc> entries and the "
                    "og:image absolute URL only")
    args = ap.parse_args()
    site_prefix = "/" + args.site_prefix.strip("/")
    if site_prefix == "/":
        site_prefix = ""
    origin = args.origin.rstrip("/")
    songs = json.loads((REPO / "songs.json").read_text(encoding="utf-8"))
    # Deriving twins materialize first (board §9 2026-09-25): the family
    # walk and every chart-fit read the variant's body — byte-equal to the
    # hand transcription the loader generates at boot (tests/twin_derive).
    from melody_transpose import materialize
    materialize(songs)
    manifest = json.loads((REPO / "instruments.json").read_text(encoding="utf-8"))
    charts = {i["id"]: chart_ids(i["id"], manifest) for i in manifest["instruments"]}
    html = (REPO / "index.html").read_text(encoding="utf-8")

    out = REPO / args.out
    written = []
    urls = []
    emitted = []          # (cat, key) pairs of the stub set, for the hubs
    for key, song in sorted(songs.items()):
        if SUFFIX.search(key):
            continue  # variants ride the base page, not their own URL
        if song.get("hidden"):
            continue  # WIPs stay unpublished
        if key.endswith("-bass") and key[:-5] in songs:
            continue  # a family -bass member rides its base page (grace
                      # period: unregistered marker); leaf -bass keys keep
                      # their own page
        cat = category_of(song.get("group"))
        member, inst = pick_landing(key, songs, manifest, charts)
        stub = build_stub(html, key, songs[member], member, song,
                          cat, inst, site_prefix, origin)
        p = out / "song" / cat / key / "index.html"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(stub, encoding="utf-8", newline="\n")
        # Sitemap URLs: absolute (the sitemap protocol's <loc> requires
        # it), origin + serving prefix + stub path; home leads the set.
        urls.append(f"{origin}{site_prefix}/song/{cat}/{key}/")
        written.append(f"{p.relative_to(out)}  [{inst}]")
        emitted.append((cat, key))

    # Internal directory (Robin's SEO pass 2026-10-07): the /song/ root hub
    # and one hub per category, each with the instruments-vs-variations
    # grid linking every landing URL. Static pages — no app, no scripts;
    # crawlers reach every stub through internal links, not the sitemap
    # alone.
    cats = sorted({c for c, _ in emitted})
    grid_all = hub_grid(emitted, songs, manifest, charts, site_prefix)
    root_desc = ("Every song below is a play-along ocarina tab: letter"
                 " notes, hole-by-hole fingerings and a tuner - pick your"
                 " ocarina on any song page.")
    (out / "song" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "song" / "index.html").write_text(
        hub_page("Song library — Ocarina Tabs | Ocarina Practice",
                 root_desc, f"{site_prefix}/song/",
                 [("Ocarina Practice", site_prefix + "/"), ("Song library",
                                                           None)],
                 "Song library", root_desc,
                 "".join(
                     f'<h2>{category_label(c)} ocarina tabs</h2>\n'
                     f'<p><a href="{site_prefix}/song/{c}/">All'
                     f' {category_label(c)} tabs</a></p>\n'
                     + hub_grid([e for e in emitted if e[0] == c], songs,
                                manifest, charts, site_prefix)
                     for c in cats),
                 site_prefix),
        encoding="utf-8", newline="\n")
    for c in cats:
        d = out / "song" / c
        d.mkdir(parents=True, exist_ok=True)
        title = f"{category_label(c)} ocarina tabs — Ocarina Practice"
        (d / "index.html").write_text(
            hub_page(title, root_desc, f"{site_prefix}/song/{c}/",
                     [("Ocarina Practice", site_prefix + "/"),
                      ("Song library", site_prefix + "/song/"),
                      (category_label(c), None)],
                     title.split(" — ")[0], root_desc,
                     hub_grid([e for e in emitted if e[0] == c], songs,
                              manifest, charts, site_prefix),
                     site_prefix),
            encoding="utf-8", newline="\n")
    hub_urls = ([(f"{origin}{site_prefix}/song/")]
                + [f"{origin}{site_prefix}/song/{c}/" for c in cats])
    written.append("song/index.html  [hub]")
    for c in cats:
        written.append(f"song/{c}/index.html  [hub]")
    (out / ".nojekyll").write_text("", encoding="utf-8", newline="\n")
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               ('<urlset xmlns="http://www.sitemaps.org/schemas/'
                'sitemap/0.9">')]
    for loc in [f"{origin}{site_prefix}/"] + sorted(hub_urls + urls):
        sitemap.append("  <url>")
        sitemap.append(f"    <loc>{loc}</loc>")
        sitemap.append("  </url>")
    sitemap.append("</urlset>")
    (out / "sitemap.xml").write_text("\n".join(sitemap) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"wrote {len(written)} pages incl. {1 + len(cats)} hub pages "
          f"(+ .nojekyll, sitemap.xml with {len(hub_urls) + len(urls) + 1} "
          f"entries) under {out}")
    for w in written:
        print("  " + w)


if __name__ == "__main__":
    main()
