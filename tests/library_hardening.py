#!/usr/bin/env python3
# Library hardening acceptance test: user-song ids and the localStorage layer
# must refuse to lose data silently:
#   - junk names ("!!!") must not slugify onto one shared id ("u-")
#   - display names that differ only in punctuation ("M:Key D4" vs "M Key D4")
#     must NOT silently overwrite each other on save; a re-save of the exact
#     same name remains a deliberate overwrite
#   - setUserLib/setShowHidden must fail gracefully when storage refuses the
#     write (quota exceeded, private mode) instead of throwing mid-click
#   - corrupt library JSON must be backed up once before being recovered,
#     so evidence survives instead of vanishing on the next save
#
#   python3 tests/library_hardening.py          # headless & silent

import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
LIB_WAIT = ("typeof slugName === 'function'"
            " && typeof userLib === 'function'"
            " && typeof setUserLib === 'function'")


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
            page.wait_for_function(LIB_WAIT)

            # --- generated scales ordering (the IDEAS lift): the whole
            # Scales group opens the dropdown — the beginner's tool set on
            # top — and inside it C major comes before Chromatic ---
            page.wait_for_function(
                "() => { const s = document.getElementById('scale');"
                " if (!s) return false;"
                " const g = [...s.children].find"
                "(n => n.tagName === 'OPTGROUP' && n.label === 'Scales');"
                " return !!(g && g.children.length >= 2); }")
            order = page.evaluate("""() => {
              const sel = document.getElementById('scale');
              const groups = [...sel.children]
                .filter(n => n.tagName === 'OPTGROUP');
              return { labels: groups.map(g => g.label),
                       scales: (groups.find(g => g.label === 'Scales') ||
                                { children: [] }).children[0]
                        ? [...groups.find(g => g.label === 'Scales')
                        .children].map(o => o.value) : [] };
            }""")
            if not order["labels"] or order["labels"][0] != "Scales":
                failures.append("library order: the Scales group must open "
                                f"the dropdown, got {order['labels']!r}")
            if order["scales"] != ["major", "chromatic"]:
                failures.append("library order: inside Scales, C major must "
                                "come before Chromatic, got "
                                f"{order['scales']!r}")

            # --- slugName: junk names must not collapse onto one id ---
            slugs = page.evaluate("""() => ({
              junk: slugName("!!!"),
              normA: slugName("M Key D4"),
              normB: slugName("M:Key D4"),
            })""")
            if slugs["junk"] == "u-":
                failures.append(
                    "slugName: junk name collapses to constant 'u-' "
                    "(dead fallback, collides with every other junk save)")
            if not str(slugs["junk"]).startswith(("u-", "song-")):
                failures.append(f"slugName: unexpected junk id shape {slugs['junk']!r}")
            # Two junk saves must never share a stored id even from a frozen
            # clock counting ms apart (the guarantee lives in uniqueUserId).
            junk_pair = page.evaluate("""() => {
              const real = Date.now;
              let k = 0;
              Date.now = () => 1700000000000 + (k++);
              try {
                const lib = {};
                const a = uniqueUserId(lib, "!!!"); lib[a] = { name: "!!!" };
                const b = uniqueUserId(lib, "###"); lib[b] = { name: "###" };
                return { a, b, distinct: a !== b };
              } finally { Date.now = real; }
            }""")
            if not junk_pair["distinct"]:
                failures.append(
                    f"junk names must not share a stored id, got "
                    f"{junk_pair['a']!r} and {junk_pair['b']!r}")

            # --- uniqueUserId: collision handling at save time ---
            if not page.evaluate("typeof uniqueUserId === 'function'"):
                failures.append("uniqueUserId helper missing from js/library.js")
            else:
                dedupe = page.evaluate("""() => {
                  const lib = { "u-m-key-d4": { name: "M:Key D4", body: "" } };
                  const a = uniqueUserId(lib, "M Key D4");
                  lib[a] = { name: "M Key D4", body: "" };
                  const b = uniqueUserId(lib, "M;Key D4");  // third spelling
                  lib[b] = { name: "M;Key D4", body: "" };
                  const c = uniqueUserId(lib, "Totally other");
                  return {
                    resave: uniqueUserId(lib, "M:Key D4"),
                    first: a, second: b, fresh: c,
                    distinct: new Set([a, b, c]).size,
                  };
                }""")
                if dedupe["resave"] != "u-m-key-d4":
                    failures.append(
                        "uniqueUserId: re-saving the exact same name must keep "
                        "the original id (deliberate overwrite)")
                if dedupe["first"] == "u-m-key-d4":
                    failures.append(
                        "uniqueUserId: punctuation-differing name would "
                        "silently overwrite the stored song")
                if dedupe["distinct"] != 3:
                    failures.append(
                        f"uniqueUserId: three distinct names produced "
                        f"{dedupe['distinct']} ids ({dedupe['first']} "
                        f"{dedupe['second']} {dedupe['fresh']})")

            # --- full save-button flow must keep both spellings ---
            page.evaluate("localStorage.removeItem('oco-bass-c-library')")
            save_flow_done = True
            for name, wait_id in (("M Key D4", "u-m-key-d4"),
                                  ("M:Key D4", "u-m-key-d4-2")):
                try:
                    page.click("#libSave")
                    page.wait_for_selector(".lib-dialog-card")
                    page.fill(".lib-dialog-input", name)
                    page.click(".lib-dialog-ok")
                    page.wait_for_function(f"""() => {{
                      const lib = JSON.parse(localStorage.getItem('oco-bass-c-library') || '{{}}');
                      const item = lib[{json.dumps(wait_id)}];
                      return !!(item && item.name);
                    }}""", timeout=15000)
                except Exception as e:
                    failures.append(
                        f"libSave: saving {name!r} did not produce id "
                        f"{wait_id!r} ({type(e).__name__}: {str(e).splitlines()[0]})")
                    save_flow_done = False
                    break
            saved = page.evaluate("""() => {
              const lib = JSON.parse(localStorage.getItem('oco-bass-c-library') || '{}');
              return { n: Object.keys(lib).length,
                       names: Object.values(lib).map(v => v.name) };
            }""")
            if save_flow_done and saved["n"] != 2:
                failures.append(
                    f"libSave: expected both 'M Key D4' and 'M:Key D4' in the "
                    f"library, got {saved['n']} entries ({saved['names']})")

            # --- storage write guards ---
            guards = page.evaluate("""() => {
              const orig = localStorage.setItem;
              try {
                localStorage.setItem = () => { throw new Error("QuotaExceeded"); };
                let sl = null;
                try { sl = setUserLib({ z: { name: "n", body: "" } }); }
                catch (e) { sl = "THREW:" + e.message; }
                let sh = null;
                try { setShowHidden(true); sh = "NO_THROW"; }
                catch (e) { sh = "THREW:" + e.message; }
                return { sl, sh };
              } finally { localStorage.setItem = orig; }
            }""")
            if guards["sl"] is not False:
                failures.append(
                    f"setUserLib must fail soft (return false) when storage "
                    f"refuses the write, got {guards['sl']!r}")
            if guards["sh"] != "NO_THROW":
                failures.append(
                    f"setShowHidden must not throw when storage refuses the "
                    f"write, got {guards['sh']!r}")
            ok = page.evaluate("setUserLib({ z: { name: 'n', body: '' } })")
            if ok is not True:
                failures.append(
                    f"setUserLib must report success as true, got {ok!r}")

            # --- corrupt library JSON: back up once, then recover ---
            corruption = page.evaluate("""() => {
              const K = "oco-bass-c-library";
              localStorage.setItem(K, "{oops");
              const first = JSON.stringify(userLib());
              userLib();  // second read on the same corrupt data
              const backups = Object.keys(localStorage)
                .filter(k => k.indexOf(K + ".corrupt-") === 0);
              return {
                first, backupCount: backups.length,
                backed: backups.length ? localStorage.getItem(backups[0]) : null,
                libNow: localStorage.getItem(K),
              };
            }""")
            if corruption["first"] != "{}":
                failures.append(
                    f"userLib must recover corrupt JSON as empty object, "
                    f"got {corruption['first']!r}")
            if corruption["backupCount"] != 1:
                failures.append(
                    f"userLib must back up corrupt library content exactly "
                    f"once, saw {corruption['backupCount']} backups")
            if corruption["backed"] != "{oops":
                failures.append(
                    f"corrupt JSON backup must contain the raw string, "
                    f"got {corruption['backed']!r}")
            if corruption["libNow"] != "{}":
                failures.append(
                    f"after corruption the library must be reset so the next "
                    f"save works, got {corruption['libNow']!r}")

            # A validly-parsed non-object must count as corrupt, not as a library
            nonobject = page.evaluate("""() => {
              const K = "oco-bass-c-library";
              localStorage.setItem(K, "[1,2]");
              const out = JSON.stringify(userLib());
              const cleaned = localStorage.getItem(K);
              return { out, cleaned };
            }""")
            if nonobject["out"] != "{}" or nonobject["cleaned"] != "{}":
                failures.append(
                    f"userLib must treat a parsed non-object ([1,2]) as corrupt, "
                    f"got out={nonobject['out']!r} lib={nonobject['cleaned']!r}")

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
    print("\nPASS: library ids can't collide silently, storage writes fail "
          "soft, corrupt JSON is backed up and recovered.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
