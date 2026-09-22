#!/usr/bin/env python3
# Shipped-songs acceptance: every entry in songs.json must be fully playable.
# Per song:
#   - parses with ZERO "bad" chips (with junk-surfacing in place, any typo,
#     stray text or malformed token in a body shows up here)
#   - melody notes (incl. tie continuations) fit AT LEAST ONE shipped
#     ocarina's range — a song no shipped ocarina can fully play is flagged
#     (bracket/support pitches are synth drones, deliberately out of range,
#     so they are excluded from this rule)
#   - metadata sane: non-empty body (chromatic generates its own), name,
#     tempo 10–400, URL-safe id (ids are ?song= deep-link params)
#
#   python3 tests/shipped_songs.py      # headless & silent

import http.server
import socketserver
import re
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("typeof parse === 'function' && typeof BUILTIN !== 'undefined'"
        " && BUILTIN && Object.keys(BUILTIN).length > 0")

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

            if not songs:
                failures.append("no songs found in BUILTIN — initBuiltin ran?")
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
                    failures.append(f"{sid}: tempo out of 10–400: {s['tempo']!r}")
                if not re.fullmatch(r"[a-z0-9-]+", sid):
                    failures.append(f"{sid}: id not URL-safe (used in ?song=)")

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
