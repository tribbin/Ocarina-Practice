#!/usr/bin/env python3
# Shipped-songs acceptance: every entry in songs.json must be fully playable.
# Per song:
#   - parses with ZERO "bad" chips (with junk-surfacing in place, any typo,
#     stray text or malformed token in a body shows up here)
#   - melody notes (incl. tie continuations) fit AT LEAST ONE shipped
#     ocarina's range â€” a song no shipped ocarina can fully play is flagged
#     (bracket/support pitches are synth drones, deliberately out of range,
#     so they are excluded from this rule)
#   - metadata sane: non-empty body (chromatic generates its own), name,
#     tempo 10â€“400, URL-safe id (ids are ?song= deep-link params)
#   - the FROZEN slug contract (Robin, 2026-09-24): a key is a base slug
#     (lowercase-hyphen ASCII) or a variant that ends in a REGISTERED suffix
#     (arrangement/ocarina markers and content markers) and chains to an
#     existing key with that suffix stripped â€” variants hang off real bases
#     so public link space grows without ever renaming a base
#
#   python3 tests/shipped_songs.py      # headless & silent

import http.server
import socketserver
import re
import sys
import threading
from pathlib import Path

# Registered trailing suffixes (the closed list; extend ONLY here): ocarina
# markers (alto, 12, contrabass) and transposition/interval markers (c,
# upN/downN). Content-shaping words (short, part...) are part of BASE slugs â€”
# 'concerning-hobbits-short' is its own base, the -c copy chains to it.
SUFFIX = re.compile(r"-(alto|12|contrabass|c|up\d+|down\d+)$")

# Synthetic violations in the suite prove the tripwire, since the shipped
# corpus is expected to be clean.
TRIPWIRE_BAD = [
    "Song of Storms",        # not lowercase-hyphen ASCII
    "song-of-storms--alto",  # empty middle token
    "-alto",                 # variant of nothing
    "phantom-song-alto",     # registered suffix without the base it chains to
]

TRIPWIRE_OK = [
    "song-of-time",                # base
    "chromatic-contrabass",        # registered suffix, chains to a base
    "concerning-hobbits-short-c",  # content marker then interval marker
    "botw-theme-down3",            # interval marker
]

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("typeof window.parse === 'function' && typeof window.BUILTIN !== 'undefined'"
        " && BUILTIN && BUILTIN.major && BUILTIN.major.body"
        " && BUILTIN.chromatic && BUILTIN.chromatic.body")

SONGS = r"""
async () => {
  const manifest = await (await fetch('instruments.json')).json();
  const sets = [];
  for (const inst of manifest.instruments) {
    const fj = await (await fetch(inst.fingerings)).json();
    sets.push({ id: inst.id, notes: fj.notes.map(n => n.id) });
  }
  const out = {};
  for (const [id, song] of Object.entries(BUILTIN)) {
    const body = song.body != null ? String(song.body) : "";
    const toks = parse(body);
    const ids = [...new Set(toks
      .filter(t => (t.type === "note" || t.type === "tie") && t.id)
      .map(t => t.id))];
    out[id] = {
      bodyEmpty: body.trim() === "",
      bads: toks.filter(t => t.type === "bad").map(t => t.raw),
      ids,
      name: song.name || "",
      tempo: song.tempo == null ? null : +song.tempo,
      inRangeBy: sets
        .filter(s => ids.length && ids.every(x => s.notes.includes(x)))
        .map(s => s.id),
    };
  }
  return out;
}
"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass


def start_server():
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), QuietHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def slug_violation(key, all_keys, report):
    # Returns a complaint string or None; `report` maps key -> complaint for
    # the caller to sort out (second pass needs the full key set).
    if not re.fullmatch(r"[a-z0-9-]+", key):
        return "id not lowercase-hyphen ASCII (it is a public perma-link slug)"
    if "-" not in key or SUFFIX.search(key) is None:
        return None  # base slug (or a suffix-less word ending)
    # Variant shape: strip ONE trailing registered suffix; the remainder
    # must be an existing key (base or another variant).
    prefix = SUFFIX.sub("", key)
    if not prefix or prefix not in all_keys:
        return f"variant '{key}' chains to nothing ('{prefix}' is not a key)"
    return None


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(WAIT)
            songs = page.evaluate(SONGS)
            all_keys = set(songs)

            # Tripwire proof first: the checker must reject every known-bad
            # crack and admit the known-good shapes (the shipped corpus is
            # expected clean, so the synthetic legs are the red proof).
            for bad in TRIPWIRE_BAD:
                if slug_violation(bad, all_keys, {}) is None:
                    failures.append(f"slug tripwire blind to {bad!r}")
            for good in TRIPWIRE_OK:
                v = slug_violation(good, all_keys, {})
                if v:
                    failures.append(f"slug checker rejects good shape {good!r}: {v}")

            if not songs:
                failures.append("no songs found in BUILTIN â€” initBuiltin ran?")
            for sid, s in sorted(songs.items()):
                if s["bodyEmpty"]:
                    failures.append(f"{sid}: empty body (only 'chromatic' may "
                                    "generate, and it must have filled in)")
                if s["bads"]:
                    failures.append(
                        f"{sid}: {len(s['bads'])} bad token(s) in body: "
                        f"{s['bads'][:6]!r}")
                if s["ids"] and not s["inRangeBy"]:
                    failures.append(
                        f"{sid}: melody notes fit NO shipped ocarina "
                        f"({len(s['ids'])} distinct notes)")
                if not s["name"]:
                    failures.append(f"{sid}: missing display name")
                if s["tempo"] is None or not (10 <= s["tempo"] <= 400):
                    failures.append(f"{sid}: tempo out of 10â€“400: {s['tempo']!r}")
                v = slug_violation(sid, all_keys, {})
                if v:
                    failures.append(f"{sid}: {v}")

            if errs:
                failures.append(f"page errors {errs}")
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print(f"\nPASS: all {len(songs)} shipped songs parse clean (no bad chips), "
          "fit at least one shipped ocarina, and carry sane metadata.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
