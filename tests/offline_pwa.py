#!/usr/bin/env python3
# Offline (PWA) contract: after one connected visit, a reload in airplane
# mode boots the app from the service worker cache — shell, data, and the
# chosen ocarina's fingerings/template — with full practice capable flows:
# the melody renders, and swapping instruments still works offline. The
# install-time cache is derived from instruments.json, so a new ocarina in
# the manifest is covered without touching sw.js.
#
#   python3 tests/offline_pwa.py      # headless & silent

import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function'")


from suite_server import start_server


def poison_cache_js(key, mime, glued):
    """Poison one SW-cache key with a __CB_POISON marker appended to the
    cached body: the observable of the serving flavor. A fetch through the
    worker either serves the poisoned cached copy (stale-while-revalidate,
    RED contract) or the network bytes (network-first, GREEN contract) and
    the no-cache revalidate then overwrites the poison in the cache."""
    return f"""async () => {{
      const key = "{key}";
      const c = await caches.open((await caches.keys())[0]);
      const hit = await c.match(key);
      if (!hit) return "NO-HIT";
      const src = await hit.text();
      await c.put(key, new Response(src + "{glued}",
        {{ headers: {{"Content-Type": "{mime}"}}}}));
      const back = await c.match(key);
      return (await back.text()).includes("__CB_POISON") ? "POISONED" : "PUT-LOST";
    }}"""


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS,
                                        args=["--autoplay-policy=no-user-gesture-required"])
            context = browser.new_context()
            errs = []
            page = context.new_page()
            page.on("pageerror", lambda e: errs.append(str(e)))
            # The resume-invalidation observable: every page request for a
            # LOADED instrument's twin model (through the worker or not).
            # The offline swap leg below leaves the suite carrying the oak
            # triple, so the filter stays instrument-agnostic — the model
            # the resumed app re-checks is whichever ocarina it holds.
            model_fetches = []
            page.on("request", lambda r: model_fetches.append(r.url)
                    if re.search(r"/instruments/[^/]+/twin_model\.json$", r.url)
                    else None)

            # --- first (connected) visit: app boots, SW installs, cache primes ---
            page.goto(base)
            page.wait_for_function(WAIT)
            page.wait_for_function(
                "() => navigator.serviceWorker"
                " && navigator.serviceWorker.controller")
            # The install derives the instrument files from the manifest;
            # give that settle so the offline leg has its data in cache.
            page.wait_for_function(
                "() => caches.match('instruments.json').then(Boolean)",
                timeout=15000)
            page.wait_for_function(
                "() => caches.match('songs.json').then(Boolean)",
                timeout=15000)
            got = page.evaluate(
                "() => ({ inst: window.CURRENT_INSTRUMENT &&"
                        " window.CURRENT_INSTRUMENT.id,"
                        " chips: document.querySelectorAll('#tokens .tok')"
                        ".length })")
            if not got["inst"]:
                failures.append("boot must land with an instrument installed")
            if not got["chips"]:
                failures.append("boot must render the token strip")
            offline_errors = []

            # --- airplane-mode reload: the shell must boot from cache ---
            context.set_offline(True)
            page.reload()
            page.wait_for_function(WAIT, timeout=20000)
            off = page.evaluate(
                "() => ({ inst: window.CURRENT_INSTRUMENT &&"
                        " window.CURRENT_INSTRUMENT.id,"
                        " notes: (window.NOTES || []).length,"
                        " cards: document.querySelectorAll('#sheet .card')"
                        ".length })")
            if not off["inst"] or not off["notes"]:
                failures.append(
                    "an offline reload must still mount the instrument from "
                    f"cache (got {off})")
            if not off["cards"]:
                failures.append("the offline song must render its chart")

            # --- offline instrument swap: derived cache must cover it ---
            page.select_option("#instSel", "ico-oak-leaf-bass-c-triple")
            page.wait_for_function(
                "() => window.CURRENT_INSTRUMENT &&"
                " window.CURRENT_INSTRUMENT.id ==="
                " 'ico-oak-leaf-bass-c-triple'", timeout=20000)
            swapped = page.evaluate(
                "() => ({ notes: (window.NOTES || []).length,"
                        " cards: document.querySelector('#sheet')"
                        ".children.length })")
            if not swapped["notes"]:
                failures.append(
                    "an offline instrument swap must install the other "
                    "ocarina's fingerings from cache")
            if swapped["cards"] < 1:
                failures.append(
                    "an offline instrument swap must render the sheet")

            context.set_offline(False)
            # The Chromium offline→online transition leaves service-worker
            # fetches rejected for a stretch (observed: the data-freshness
            # legs below failed right after set_offline(False) while a later
            # fetch succeeded — the network-first fallback had answered their
            # requests from the cached copies). The legs' real rendezvous is
            # a fresh fetch succeeding through the worker.
            page.wait_for_function(
                "() => fetch('songs.json').then(r => r.ok)", timeout=30000)

            # --- resume invalidation leg (Robin's answered batch 2026-09-29,
            # deferred at his word to this session): a RESUMED app re-checks
            # the LOADED instrument's twin model with the songs-precedent
            # gates and the silent-offline catch. A changed model on disk
            # must fire a fresh model fetch through the worker on the first
            # resume dispatch — the request count is the observable (before
            # this contract the app never fetched the model on resume, so a
            # resumed phone kept the loaded model from its last boot
            # indefinitely).
            twin_id = page.evaluate(
                "() => window.CURRENT_INSTRUMENT &&"
                " window.CURRENT_INSTRUMENT.id") or "oot-alto-c-12"
            twin_path = (ROOT / "instruments" / twin_id /
                         "twin_model.json")
            twin_pristine = twin_path.read_bytes()
            try:
                # The If-Modified-Since trap: python's whole-second mtime
                # comparison revalidates as 304 with the pre-mutation body
                # when the rewrite lands in the same wall-second as the
                # boot's serve — one real clock second separates them.
                time.sleep(1.1)
                twin = json.loads(twin_pristine.decode("utf-8"))
                twin["robe"] = "resume-invalidation-sentinel"
                twin_path.write_text(json.dumps(twin, separators=(",", ":")),
                                     encoding="utf-8")
                before = len(model_fetches)
                page.evaluate("() => document.dispatchEvent"
                              "(new Event('visibilitychange'))")
                fire = None
                for _ in range(20):  # 10 s ceiling, then the leg says so
                    if len(model_fetches) > before:
                        fire = True
                        break
                    page.wait_for_timeout(500)
                if fire is None:
                    failures.append(
                        "a resume must re-fetch the LOADED instrument's twin "
                        "model when its bytes changed (the model request "
                        "count never moved on the resume dispatch)")
            finally:
                twin_path.write_bytes(twin_pristine)

            # --- data freshness legs (Robin, 2026-09-28: deployed songs had
            # to ride a SECOND reload under stale-while-revalidate, and a
            # phone-app resume never re-checked anything) ---
            songs_path = ROOT / "songs.json"
            pristine = songs_path.read_bytes()
            try:
                # (a) an online RELOAD lands the deployed data on the FIRST
                # reload: the same installed worker now serves the released
                # data before its cached copy (network-first with cached
                # fallback), instead of stale-while-revalidate's one-reload
                # lag.
                def with_sentinel(key):
                    import json as _json
                    data = _json.loads(pristine.decode("utf-8"))
                    data[key] = {
                        "name": "PWA Freshness Sentinel",
                        "group": "Other", "tempo": 97,
                        "body": "C4 D4 E4 | r/2.",
                    }
                    songs_path.write_text(
                        _json.dumps(data, separators=(",", ":")),
                        encoding="utf-8")
                with_sentinel("pwa-freshness-sentinel-a")
                page.reload()
                page.wait_for_function(WAIT)
                try:
                    page.wait_for_function(
                        "() => Object.keys(window.BUILTIN)"
                        ".includes('pwa-freshness-sentinel-a')", timeout=15000)
                except Exception:
                    failures.append(
                        "an online reload must land the released data on "
                        "the FIRST reload (stale-while-revalidate lag)")

                # (b) a RESUME (visibility back to visible, nothing running)
                # re-fetches the data network-first and swaps the library
                # when the bytes changed.
                # The server's conditional revalidation compares mtime at
                # whole-SECOND precision, and the sentinel rewrite lands
                # within the same wall-second as the previous serve — the
                # revalidation would answer 304 with the cached pre-mutation
                # body and the legs would race their own freshness clock.
                # One real clock-second separates the serve before any
                # rewrite.
                time.sleep(1.1)
                with_sentinel("pwa-freshness-sentinel-b")
                page.evaluate(
                    "() => document.dispatchEvent"
                    "(new Event('visibilitychange'))")
                try:
                    page.wait_for_function(
                        "() => Object.keys(window.BUILTIN)"
                        ".includes('pwa-freshness-sentinel-b')", timeout=15000)
                except Exception:
                    failures.append(
                        "an app resume must re-fetch songs.json and swap "
                        "the library when the bytes changed")
            finally:
                songs_path.write_bytes(pristine)

            # --- engine freshness leg (Robin, 2026-09-29: /js/ rides
            # network-first). The deploy that started the noise hunt served
            # the OLD synth engine one visit late while fresh twin-model
            # data arrived first — an old engine fed new models is the
            # garbled mix. A poisoned /js/ cache copy must lose to the
            # network bytes on the FIRST online fetch, and the network-first
            # no-cache revalidate must overwrite it in the cache. The
            # observable is a page-side fetch through the worker (module
            # imports would only race the renderer's script memory-cache,
            # which serves a minutes-old clean copy and skips the SW).
            poison_marker = "window.__CB_POISON = true;"
            first = page.evaluate(poison_cache_js(
                "js/helmholtz-voice.js?v=2", "text/javascript",
                "\\n" + poison_marker + "\\n"))
            if first != "POISONED":
                failures.append(
                    f"the poison must land on the cached ?v=1 voice copy "
                    f"before the freshness assertion (got {first!r}; the "
                    "reloads above should have it installed)")
            else:
                served_stale = page.evaluate("""async () =>
                    (await (await fetch('js/helmholtz-voice.js?v=2'))
                        .text()).includes('__CB_POISON')""")
                if served_stale:
                    failures.append(
                        "an online js fetch through the worker must serve "
                        "the NETWORK bytes on the FIRST request "
                        "(stale-while-revalidate lag: the poisoned cache "
                        "copy still answered)")
                cache_healed = page.evaluate("""async () => {
                  const c = await caches.open((await caches.keys())[0]);
                  const hit = await c.match('js/helmholtz-voice.js?v=2');
                  return hit ? (await hit.text())
                        .includes("__CB_POISON") : "NO-HIT";
                }""")
                if cache_healed is not False:
                    failures.append(
                        "the network-first revalidate must overwrite the "
                        "stale cache copy with the fresh bytes "
                        f"(cache kept {cache_healed!r})")

            # --- per-instrument data freshness (fork 2 a): fingerings.json
            # joins the network-first class; the poisoned-copy check mirrors
            # the engine leg above (the svg templates share the same widened
            # DATA_NETWORK_FIRST branch, so the serving flavor is one
            # handler contract rather than two).
            first = page.evaluate(poison_cache_js(
                "instruments/oot-alto-c-12/fingerings.json",
                "application/json", "\\n/*__CB_POISON*/\\n"))
            if first != "POISONED":
                failures.append(
                    "the poison must land on the cached fingerings copy "
                    f"before the freshness assertion (got {first!r})")
            else:
                served_stale = page.evaluate("""async () =>
                    (await (await fetch(
                        'instruments/oot-alto-c-12/fingerings.json'))
                        .text()).includes('__CB_POISON')""")
                if served_stale:
                    failures.append(
                        "an online instrument-data fetch through the worker "
                        "must serve the NETWORK bytes on the FIRST request "
                        "(stale-while-revalidate lag: the poisoned "
                        "fingerings copy still answered)")
                cache_healed = page.evaluate("""async () => {
                  const c = await caches.open((await caches.keys())[0]);
                  const hit = await c.match(
                    'instruments/oot-alto-c-12/fingerings.json');
                  return hit ? (await hit.text())
                        .includes("__CB_POISON") : "NO-HIT";
                }""")
                if cache_healed is not False:
                    failures.append(
                        "the network-first revalidate must overwrite the "
                        "stale fingerings copy with the fresh bytes "
                        f"(cache kept {cache_healed!r})")

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
    print("\nPASS: after one connected visit the app boots offline — shell, "
          "data, the home ocarina and even an instrument swap all come from "
          "the service worker cache.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
