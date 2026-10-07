#!/usr/bin/env python3
# SEO applications (Robin, 2026-09-25 night, session 15 unit 1): the shell
# gains its rel=canonical (href="/" — the pinned domain serves at root,
# robots.txt's Sitemap: line already names https://ocarina-practice.com/)
# and ONE WebApplication JSON-LD block (applicationCategory
# EducationalApplication, operatingSystem "Any", browserRequirements,
# offers price "0", description taken VERBATIM from the shell's own meta
# description — one description policy).
#
# The stubs (Robin's SEO pass 2026-10-07): build_stub copies the whole
# shell head, so the generator must STRIP both injected shell elements
# before adding the stub's own song-path canonical — a stub page carries
# exactly ONE canonical, exactly ONE structured-data script of its own
# (MusicComposition + BreadcrumbList in a single @graph), and never the
# shell's WebApplication block.
#
#   python3 tests/seo_shell.py     # pure python: index.html + a generated
#                                  # staging tree in a temp dir
#
# Registered in .github/workflows/practice-tests.yml.

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META_DESC = re.compile(r'<meta name="description" content="([^"]*)"')
CANONICAL = re.compile(r'<link rel="canonical" href="([^"]*)"')
LD_JSON = re.compile(
    r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
    re.DOTALL)


def check_shell(failures):
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    canons = CANONICAL.findall(html)
    if len(canons) != 1:
        failures.append(f"index.html carries {len(canons)} rel=canonical "
                        "links (want exactly one)")
    elif canons[0] != "/":
        failures.append(f'shell canonical href {canons[0]!r} — want "/" '
                        "(the pinned domain serves at root)")

    blocks = LD_JSON.findall(html)
    if len(blocks) != 1:
        failures.append(f"index.html carries {len(blocks)} ld+json blocks "
                        "(want exactly one WebApplication)")
        return
    try:
        app = json.loads(blocks[0])
    except ValueError as e:
        failures.append(f"shell ld+json does not parse as JSON: {e}")
        return

    title_m = re.search(r"<title>(.*?)</title>", html)
    desc_m = META_DESC.search(html)
    if desc_m:
        if app.get("description") != desc_m.group(1):
            failures.append('JSON-LD "description" must be the shell meta '
                            "description VERBATIM (one description policy)")
    else:
        failures.append("index.html lost its meta description")

    wants = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "Any",
    }
    for field, want in wants.items():
        if app.get(field) != want:
            failures.append(f'JSON-LD {field!r} must be {want!r} '
                            f"(got {app.get(field)!r})")
    if title_m and app.get("name") != title_m.group(1):
        failures.append('JSON-LD "name" must match the <title>')
    if title_m is None:
        failures.append("index.html lost its <title>")
    br = app.get("browserRequirements")
    if not (isinstance(br, str) and br.strip()):
        failures.append('JSON-LD "browserRequirements" must be a non-empty '
                        'string')
    offers = app.get("offers") or {}
    if offers.get("@type") != "Offer":
        failures.append('JSON-LD "offers" @type must be "Offer"')
    if str(offers.get("price")) != "0":
        failures.append('JSON-LD offers.price must be "0" (the app is free)')
    if not offers.get("priceCurrency"):
        failures.append('JSON-LD offers must carry a priceCurrency '
                        "(schema.org needs the currency beside the price)")
    url = app.get("url")
    if url != "https://ocarina-practice.com/":
        failures.append(f'JSON-LD "url" {url!r} — want the sitemap\'s home '
                        '"https://ocarina-practice.com/" (absolute, '
                        "consistent with the canonical URL signal)")


def check_stubs(failures):
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "gen_song_pages.py"),
             "--out", tmp, "--site-prefix", "/",
             "--origin", "https://ocarina-practice.com"],
            capture_output=True, text=True)
        if proc.returncode != 0:
            failures.append("gen_song_pages.py failed: " +
                            (proc.stderr or proc.stdout)[-600:])
            return
        files = [p for p in sorted(Path(tmp).rglob("*")) if p.is_file()]
        if not files:
            failures.append("the staging tree produced no files")
            return
        for p in files:
            text = p.read_text(encoding="utf-8")
            rel = p.relative_to(tmp)
            if rel.name != "index.html" and "application/ld+json" in text:
                failures.append(f"{rel}: only HTML pages may carry JSON-LD")
            if "EducationalApplication" in text:
                failures.append(f"{rel}: the shell's WebApplication block "
                                "must be stripped from every generated page")
            if rel.name == "index.html" and \
                    len(rel.parts) == 4 and rel.parts[0] == "song":
                # Depth 4 = song/<cat>/<key>/index.html — a STUB. The hub
                # indexes (depth 2/3) carry a canonical but no JSON-LD by
                # design; both are refused leaked shell blocks above.
                n_canon = len(CANONICAL.findall(text))
                if n_canon != 1:
                    failures.append(
                        f"{rel}: a stub carries {n_canon} canonical links "
                        "(the shell's '/' canonical must be stripped so the "
                        "page keeps exactly one, its own song path)")
                blocks = LD_JSON.findall(text)
                if len(blocks) != 1:
                    failures.append(
                        f"{rel}: a stub carries {len(blocks)} ld+json blocks "
                        "(want exactly one MusicComposition + breadcrumb)"
                        " of its own")
                    continue
                try:
                    graph = json.loads(blocks[0])
                except ValueError as e:
                    failures.append(f"{rel}: stub ld+json does not parse: {e}")
                    continue
                n = graph.get("@graph")
                types = {x.get("@type") for x in n} if isinstance(n, list) else set()
                if graph.get("@context") != "https://schema.org" or \
                        types != {"MusicComposition", "BreadcrumbList"}:
                    failures.append(
                        f"{rel}: stub JSON-LD graph is {types or 'not a graph'}"
                        " — want one MusicComposition + BreadcrumbList of "
                        "the stub's own (a leaked shell block fails here)")


def main():
    failures = []
    check_shell(failures)
    check_stubs(failures)
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: the shell carries exactly one canonical (\"/\") and one "
          "WebApplication JSON-LD (EducationalApplication, OS \"Any\", "
          "browserRequirements, free Offer, description verbatim from the "
          "meta); every generated stub keeps exactly one canonical (its own "
          "song path) and exactly one structured-data script of its own "
          "(MusicComposition + BreadcrumbList, never the shell's block).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
