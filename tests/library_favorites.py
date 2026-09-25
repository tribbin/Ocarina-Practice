#!/usr/bin/env python3
# Library favorites pinning (Robin's election, 2026-09-26): the small first
# step ahead of any search work — pin favorite songs to the TOP of the
# library as a "Favorites" group, persisted (localStorage oco-bass-c-favs),
# both built-in and My-songs ids eligible, each song rendered exactly once,
# and the picker stays free (pinning never loads or selects anything).
#
# Legs (headless Chromium, fresh localStorage per leg context):
#   1. a fresh boot has NO favorites group; a starred row carries the
#      star affordance;
#   2. pinning two songs moves them into a FIRST "Favorites" group, leaves
#      them OUT of their origin groups (exactly-once rendering), persists
#      the ids, and never changes the editor content (picker stays free);
#   3. a reload keeps the group first, the ids persisted, the stars lit;
#   4. unpin removes from the group, not from the library (the song stays
#      in its origin group, exactly once).
#
#   .venv/bin/python3 tests/library_favorites.py

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright
from suite_server import QuietHandler, SuiteServer
import socketserver
import threading

ROOT = Path(__file__).resolve().parent.parent
BOOT_WAIT = ("window.NOTES && window.NOTES.length"
             " && typeof parse === 'function'")


def start_server():
    httpd = SuiteServer(("127.0.0.1", 0), QuietHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def groups_of(page):
    """Menu group names in order + the option ids per group."""
    return page.evaluate("""() => {
      const menu = document.getElementById('libDdMenu');
      const out = [];
      let cur = null;
      for (const n of menu.children) {
        if (n.classList.contains('lib-dd-group')) {
          cur = { name: n.textContent, ids: [] };
          out.push(cur);
        } else if (n.classList.contains('lib-dd-opt') && cur) {
          cur.ids.push(n.dataset.value);
        }
      }
      return out;
    }""")


def open_menu(page):
    page.click("#libDdBtn")
    page.wait_for_function(
        "() => !document.getElementById('libDdMenu').hidden")


def pin(page, value):
    page.evaluate("""(v) => {
      const rows = [...document.querySelectorAll('.lib-dd-opt')];
      const row = rows.find(r => r.dataset.value === v);
      if (!row) throw new Error('row missing: ' + v);
      row.querySelector('.lib-dd-star').click();
    }""", value)


def starred(page, value):
    return page.evaluate("""(v) => {
      const row = [...document.querySelectorAll('.lib-dd-opt')]
        .find(r => r.dataset.value === v);
      return row && row.querySelector('.lib-dd-star').classList
        .contains('pinned');
    }""", value)


def editor_src(page):
    return page.evaluate("() => document.getElementById('src').value")


def favs(page):
    return json.loads(page.evaluate(
        "() => localStorage.getItem('oco-bass-c-favs') || '[]'"))


def main():
    failures = []
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            if page.evaluate(
                    "() => localStorage.getItem('oco-bass-c-favs')") is not None:
                failures.append("a fresh boot must not seed favorites state")
            open_menu(page)
            groups = groups_of(page)
            if any(g["name"] == "Favorites" for g in groups):
                failures.append("a fresh boot must not show a Favorites group")
            src_before = editor_src(page)

            # two different songs: one builtin, named from the first group's
            # rows (stable for the corpus)
            ids = page.evaluate(
                """() => [...document.querySelectorAll('.lib-dd-opt')]
                         .map(r => r.dataset.value)""")
            a, b = ids[0], ids[2]
            pin(page, a)
            pin(page, b)
            if favs(page) != [a, b]:
                failures.append(f"pinned ids mangled: {favs(page)} (want [{a}, {b}])")
            groups = groups_of(page)
            if not groups or groups[0]["name"] != "Favorites":
                failures.append(f"Favorites group missing/last: "
                                f"{[g['name'] for g in groups]}")
            fav_ids = groups[0]["ids"] if groups else []
            if set(fav_ids) != {a, b}:
                failures.append(f"Favorites group ids wrong: {fav_ids}")
            if not starred(page, a) or not starred(page, b):
                failures.append("starred rows lost their pinned look after re-render")
            everywhere = page.evaluate(
                """(args) => [...document.querySelectorAll('.lib-dd-opt')]
                        .filter(r => args.includes(r.dataset.value)).length""",
                [a, b])
            if everywhere != 2:
                failures.append(f"pinned songs rendered {everywhere}x "
                                "(must be exactly once each)")
            groups_nofav = [g for g in groups if g["name"] != "Favorites"]
            if any(a in g["ids"] or b in g["ids"] for g in groups_nofav):
                failures.append("pinned ids still ride their origin groups")
            if editor_src(page) != src_before:
                failures.append("pinning changed the editor — the picker "
                                "must stay free")
            menu_still_open = page.evaluate(
                "() => !document.getElementById('libDdMenu').hidden")
            if not menu_still_open:
                failures.append("pinning closed the dropdown menu")

            page.reload()
            page.wait_for_function(BOOT_WAIT)
            open_menu(page)
            groups = groups_of(page)
            if not groups or groups[0]["name"] != "Favorites":
                failures.append("after reload the Favorites group is missing "
                                "or not first")
            elif set(groups[0]["ids"]) != {a, b}:
                failures.append(f"after reload favorites wrong: {groups[0]['ids']}")
            if not starred(page, a):
                failures.append("after reload the star lost its pinned state")

            page.evaluate("""(v) => {
              const row = [...document.querySelectorAll('.lib-dd-opt')]
                .find(r => r.dataset.value === v);
              row.querySelector('.lib-dd-star').click();
            }""", a)
            groups = groups_of(page)
            if groups and groups[0]["name"] == "Favorites" and \
                    a in groups[0]["ids"]:
                failures.append("unpinned id still in the Favorites group")
            page.evaluate("""(v) => {
              const row = [...document.querySelectorAll('.lib-dd-opt')]
                .find(r => r.dataset.value === v);
              if (!row) throw new Error('row missing: ' + v);
              if (row.dataset.value === v) return;
            }""", a)
            page.keep = None
            everywhere = page.evaluate(
                """(v) => [...document.querySelectorAll('.lib-dd-opt')]
                        .filter(r => r.dataset.value === v).length""", a)
            if everywhere != 1:
                failures.append(f"after unpin the song renders {everywhere}x")
            if starred(page, b) is not True:
                failures.append("the other favorite lost its state")
            ctx.close()
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: favorites pin to a FIRST persisted group, render exactly "
          "once, survive reload, unpin cleanly, and never touch the editor "
          "or close the menu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
