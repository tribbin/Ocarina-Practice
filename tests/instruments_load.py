#!/usr/bin/env python3
# Instrument layout acceptance test: every ocarina in instruments.json must
# boot from its own folder (fingerings + template) with no page errors, and
# the per-ocarina tone model plumbing must behave:
#   - a missing / corrupt tone.json must not break boot (generic model, tone null)
#   - a fitted chamber interpolates its anchors in log-f; the expected numbers
#     are computed in-page from the same vInterp/db2lin the generic path uses,
#     so what's really under test is the key→point MAPPING
#   - fallbacks: per-field (a row without a key keeps the generic value),
#     single-point chambers (constant), bare rows, corrupt shapes uninstall
#   - generic parity: uninstalling restores the generic profile bit-for-bit
#
#   python3 tests/instruments_load.py          # headless & silent

import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv


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


BOOT_WAIT = ("typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
             " && window.NOTES && window.NOTES.length")


def boot_instrument(browser, base, inst_id, failures, tag):
    """Boots ?inst=<id> and asserts the folder data came up."""
    page = browser.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(f"{base}?inst={inst_id}")
    page.wait_for_function(BOOT_WAIT)
    state = page.evaluate("""() => ({
      notes: window.NOTES.length,
      fingered: !!(window.FING && window.FING.notes && window.FING.notes.length)
                && window.FING.notes[0].id === window.NOTES[0],
      templated: !!(window.CURRENT_INSTRUMENT && window.CURRENT_INSTRUMENT.svg),
      chambered: Object.keys(window.CHAMBER).length > 0,
      tone: window.OCA_DEBUG && window.OCA_DEBUG.toneModel
              ? window.OCA_DEBUG.toneModel() : "MISSING",
    })""")
    for key in ("fingered", "templated", "chambered"):
        if not state[key]:
            failures.append(f"{tag}: {key} not installed for {inst_id}")
    if state["notes"] < 5:
        failures.append(f"{tag}: {inst_id} has only {state['notes']} notes")
    if state["tone"] not in (None, "MISSING"):
        failures.append(f"{tag}: {inst_id} shipped no tone.json but installed "
                        f"{state['tone']}")
    if state["tone"] == "MISSING":
        failures.append(f"{tag}: OCA_DEBUG.toneModel() missing (audio.js change?)")
    if errs:
        failures.append(f"{tag}: {inst_id} page errors {errs}")
    return page


TONE_PROBE = """
() => {
  const ch1Ids = window.NOTES.filter(id => window.CHAMBER[id] === 1)
    .sort((a, b) => freqOf(a) - freqOf(b));
  if (ch1Ids.length < 6) return {setup: "chamber 1 needs 6+ notes for an in-between probe"};
  const lo = ch1Ids[0], mid = ch1Ids[1], top = ch1Ids[ch1Ids.length - 1];
  const probe = ch1Ids[Math.floor(ch1Ids.length / 2)];
  const fLo = freqOf(lo), fMid = freqOf(mid), fTop = freqOf(top);
  const fProbe = freqOf(probe);
  if (!(fLo < fMid && fMid < fProbe && fProbe < fTop))
    return {setup: "probe note does not sit strictly between the anchors"};
  const rows = [
    {"note": lo, "f": fLo,  "h": [1, 0.010, 0.020, 0.004, 0.002],
     "levelDb": 0.0,  "wanderC": 6.0, "wobPct": 5.0, "wobHz": 2.0,
     "noiseLoDb": -26.0, "noiseBumpQ": 8.0, "attackF": 1.0,
     "chiff": {"peak": 0.010, "startHz": 1800}},                  // no len here
    {"note": mid, "f": fMid, "h": [1, 0.020, 0.040, 0.008, 0.004],
     "levelDb": 6.0,  "wanderC": 3.0, "wobPct": 4.0, "wobHz": 3.0,
     "noiseLoDb": -28.0, "noiseBumpQ": 6.0, "attackF": 1.5, "osDb": 2.0,
     "chiff": {"peak": 0.015, "startHz": 2600, "len": 0.09}},     // osDb only here
    {"note": top, "f": fTop, "h": [1, 0.030, 0.060, 0.012, 0.006],
     "levelDb": 12.0, "wanderC": 1.0, "wobPct": 3.0, "wobHz": 4.0,
     "noiseLoDb": -30.0, "noiseBumpQ": 4.0, "attackF": 2.0,
     "chiff": {"peak": 0.020, "startHz": 3400, "len": 0.10}}
  ];
  const MODEL = {instrument: "probe", chambers: {"1": rows},
                 global: {"lpMult": 5.5, "lpQ": 0.55}};
  // generic snapshot for the parity check (wobRate is re-jittered per note)
  const clone = o => JSON.parse(JSON.stringify(o, (k, v) => k === "wobRate" ? 0 : v));
  const generic = clone(OCA_DEBUG.profile(lo));

  installToneModel(MODEL, "probe");
  const pMid = OCA_DEBUG.profile(probe);
  const pTop = OCA_DEBUG.profile(top);
  // expected interpolations, built from the same math as the fitted path
  const interp = (defs, fz) => {
    const pts = defs.filter(d => d && d.v != null).map(d => [d.f, d.v]);
    if (!pts.length) return null;
    return pts.length === 1 ? pts[0][1] : vInterp(pts, fz);
  };
  const col = (key) => rows.map(r => ({"f": r.f, "v": r[key]}));
  const hcol = (i) => rows.map(r => ({"f": r.f, "v": r.h ? r.h[i] : null}));
  const chiff = rows.map(r => ({"f": r.f, "v": r.chiff && r.chiff.peak}));
  const chLen = rows.map(r => ({"f": r.f, "v": r.chiff && r.chiff.len}));

  // per-field fallback: drop wobPct from EVERY row → the field reads the
  // generic table (fitted branch, so the hard-blow hh offset stays out)
  const bareFields = rows.map(r => {
    const c = JSON.parse(JSON.stringify(r)); delete c.wobPct; return c;
  });
  installToneModel({instrument: "probe2", chambers: {"1": bareFields}}, "probe2");
  const pNoWob = OCA_DEBUG.profile(probe);
  installToneModel(MODEL, "probe"); // restore

  // shapes: bare row (all fields fall back), junk, reset
  installToneModel({instrument: "bare", chambers: {"1": [{"note": lo, "f": fLo}]}}, "bare");
  const bareOk = !!OCA_DEBUG.toneModel()
                 && OCA_DEBUG.toneModel().chambers.length === 1
                 && OCA_DEBUG.toneModel().chambers[0].rows.length === 1;
  const pBare = OCA_DEBUG.profile(lo);
  installToneModel({instrument: "junk", chambers: {"1": "not an array"}}, "junk");
  const junkNull = OCA_DEBUG.toneModel() === null;
  installToneModel({instrument: "junk2", chambers: {}}, "junk2");
  const junk2Null = OCA_DEBUG.toneModel() === null;
  installToneModel(null, "reset");
  const resetNull = OCA_DEBUG.toneModel() === null;
  const backToGeneric = OCA_DEBUG.profile(lo);

  return {
    setup: null,
    hMid: [pMid.h[1], interp(hcol(1), fProbe)],
    h4Mid: [pMid.h[3], interp(hcol(3), fProbe)],
    levelMid: [pMid.levelLin, db2lin(vInterp(rows.map(r => [r.f, r.levelDb]), fProbe))],
    windQMid: [pMid.windQ, interp(col("noiseBumpQ"), fProbe)],
    wanderMidStraightNoHh: [pMid.wanderC, interp(col("wanderC"), fProbe)],
    wobMid: [pMid.wobDepth, interp(col("wobPct"), fProbe) / 100],
    wobFieldFallback: [pNoWob.wobDepth, vInterp(V_ANCHORS.wobPct, fProbe) / 100],
    attackMid: [pMid.attackF, interp(col("attackF"), fProbe)],
    osMidConstant: [pMid.osDb, interp(col("osDb"), fProbe)],
    osTopConstant: [pTop.osDb, interp(col("osDb"), fTop)], // single point: constant even at the top anchor,
    enLpMult: [pMid.en.lpMult, 5.5],
    enLpQ: [pMid.en.lpQ, 0.55],
    chiffPeakMid: [pMid.en.chiff.peak, interp(chiff, fProbe)],
    chiffLenMid: [pMid.en.chiff.len, interp(chLen, fProbe)],
    chiffAttackAbsent: pMid.en.chiff.attack === undefined,
    edgeNoKeys: Object.keys(pMid.en.edge).length === 0,
    bareInstalled: bareOk,
    bareWindQGeneric: [pBare.windQ, vInterp(V_ANCHORS.noiseBumpQ, fLo)],
    junkNull, junk2Null, resetNull,
    genericParity:
      generic.h.join() === backToGeneric.h.join() &&
      generic.windQ === backToGeneric.windQ &&
      generic.osDb === backToGeneric.osDb &&
      generic.attackF === backToGeneric.attackF &&
      generic.levelLin === backToGeneric.levelLin &&
      generic.en === null && backToGeneric.en === null,
  };
}
"""


TPL_PROBE = """
() => ({
  tpl: currentTemplatePath(), id: currentSongId(), title: currentSongTitle(),
})
"""

TYPED = """
async (title) => {
  // Typed input renders on a short settle (the per-keystroke debounce):
  // poll for the typed song's own title before any probe reads state.
  const ta = document.getElementById('src');
  ta.value = '# ' + title + '\\n\\nC4 D4 E4';
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  const t0 = Date.now();
  while (document.getElementById('title').textContent !== title &&
         Date.now() - t0 < 3000) {
    await new Promise(r => setTimeout(r, 15));
  }
  return document.getElementById('title').textContent;
}
"""


def close(got, want, tol=1e-9):
    return isinstance(got, (int, float)) and isinstance(want, (int, float)) \
        and abs(got - want) <= tol


def assert_close(failures, tag, key, pair, tol=1e-9):
    if not isinstance(pair, list) or len(pair) != 2:
        failures.append(f"{tag}: {key} probe malformed: {pair!r}")
        return
    got, want = pair
    if not close(got, want, tol):
        failures.append(f"{tag}: {key} = {got!r}, expected {want!r}")


def main():
    manifest = json.loads((ROOT / "instruments.json").read_text())
    inst_ids = [i["id"] for i in manifest["instruments"]]
    tone_ids = [i["id"] for i in manifest["instruments"] if i.get("tone")]
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS,
                                        args=["--autoplay-policy=no-user-gesture-required"])

            # 1 — every instrument boots from its folder
            print("== per-folder boot battery", flush=True)
            for inst_id in inst_ids:
                print(f"   {inst_id}", flush=True)
                page = boot_instrument(browser, base, inst_id, failures, "boot")
                page.close()
            print(f"   ({len(inst_ids)} instruments, "
                  f"{len(tone_ids)} declare tone.json)", flush=True)

            # 2 — tone model plumbing on the default instrument (a synthetic
            # 3-anchor chamber installed through installToneModel)
            print("== tone model install / interpolate / fallback", flush=True)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base + "?inst=" + inst_ids[0])
            page.wait_for_function(BOOT_WAIT)
            r = page.evaluate(TONE_PROBE)
            if errs:
                failures.append(f"tone model: page errors {errs}")
            if not r or not isinstance(r, dict) or r.get("setup"):
                failures.append(f"tone model: probe setup failed {r}")
            else:
                assert_close(failures, "interp", "h2 mid", r["hMid"])
                assert_close(failures, "interp", "h4 mid", r["h4Mid"])
                assert_close(failures, "interp", "level mid", r["levelMid"])
                assert_close(failures, "interp", "windQ mid", r["windQMid"])
                assert_close(failures, "fitted-no-hh", "wanderC mid",
                             r["wanderMidStraightNoHh"])
                assert_close(failures, "interp", "wob mid", r["wobMid"])
                assert_close(failures, "field-fallback", "wob fallback",
                             r["wobFieldFallback"])
                assert_close(failures, "interp", "attack mid", r["attackMid"])
                assert_close(failures, "single-point", "os mid", r["osMidConstant"])
                assert_close(failures, "single-point", "os top", r["osTopConstant"])
                assert_close(failures, "global", "en.lpMult", r["enLpMult"])
                assert_close(failures, "global", "en.lpQ", r["enLpQ"])
                assert_close(failures, "envelope", "chiff.peak mid", r["chiffPeakMid"])
                assert_close(failures, "envelope", "chiff.len mid (2 rows)",
                             r["chiffLenMid"])
                if not r["chiffAttackAbsent"]:
                    failures.append("envelope: chiff.attack must be absent from the "
                                    "spec (per-field fallback), got a value")
                if not r["edgeNoKeys"]:
                    failures.append("envelope: edge block unexpectedly carried keys")
                if not r["bareInstalled"]:
                    failures.append("shapes: bare single-row chamber not installed")
                assert_close(failures, "fallback", "bare windQ generic",
                             r["bareWindQGeneric"])
                if not (r["junkNull"] and r["junk2Null"] and r["resetNull"]):
                    failures.append(f"shapes: corrupt models must uninstall "
                                    f"(junk {r['junkNull']} junk2 {r['junk2Null']} "
                                    f"reset {r['resetNull']})")
                if not r["genericParity"]:
                    failures.append("parity: uninstalling must restore the generic "
                                    "profile bit-for-bit (incl. en === null)")
            page.close()
            # 3 — per-song ocarina template selection (svgWhen): on the
            # 12-hole Alto C the plain sarias-song body is out of range (so
            # the dropdown stays empty — a stem-id match there can only be a
            # linker/zen link case), making the in-range alto variant the
            # id-path probe (its id carries the stem as prefix). The rule
            # must ALSO fire by matching song title (hand-typed Saria's Song)
            # and stay on the generic template for other titles.
            print("== per-song ocarina template (svgWhen)", flush=True)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base + "?inst=oot-alto-c-12&song=sarias-song-alto&oot")
            page.wait_for_function(BOOT_WAIT)
            # FINGERINGS install precedes the library tail (the tone-model
            # round-trip comes after in loadInstrument): probing #scale/#src
            # can otherwise race the ?song load in.
            page.wait_for_function(
                "() => document.getElementById('scale').value ==="
                " 'sarias-song-alto'")
            byId = page.evaluate(TPL_PROBE)
            page.goto(base + "?inst=oot-alto-c-12&oot")
            page.wait_for_function(BOOT_WAIT)
            # BOOT_WAIT (practice + NOTES) can fire before boot() reaches its
            # tail — the home song's library load then still overwrites #src
            # and clobbers typed text. Pin the library tail first (#scale), as
            # the id-path leg above does, before any typed probe.
            page.wait_for_function(
                "() => document.getElementById('scale').value ==="
                " 'song-of-storms-alto'")
            page.evaluate(TYPED, "Saria's Song")
            byTitle = page.evaluate(TPL_PROBE)
            page.evaluate(TYPED, "Zelda's Lullaby")
            byOtherTitle = page.evaluate(TPL_PROBE)
            if errs:
                failures.append(f"svgWhen: page errors {errs}")
            if not str(byId.get("tpl") or "").endswith(
                    "ocarina-template-saria.svg"):
                failures.append(
                    "svgWhen: song id sarias-song-alto (stem sarias-song) "
                    f"must select the saria template, got {byId!r}")
            if not str(byTitle.get("tpl") or "").endswith(
                    "ocarina-template-saria.svg"):
                failures.append(
                    "svgWhen: a typed Saria's Song body must also select the "
                    f"saria template, got {byTitle!r}")
            if not str(byOtherTitle.get("tpl") or "").endswith(
                    "ocarina-template.svg"):
                failures.append(
                    "svgWhen: an unrelated title must keep the generic "
                    f"template, got {byOtherTitle!r}")
            page.close()

            # 4 — boot diagnostics: an unknown ?inst id and a duplicated
            # manifest id both report loudly in #err (append, never clobber)
            # while the boot itself still lands fail-soft. A FRESH context per
            # leg: the service worker installs during the earlier suites in a
            # shared context and would serve its precached instruments.json,
            # hiding the routed doctored manifest from the app entirely.
            ctx4 = browser.new_context()
            page = ctx4.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base + "?inst=bogus99")
            page.wait_for_function(BOOT_WAIT)
            page.wait_for_function(
                "() => document.getElementById('scale').value ||"
                " document.querySelectorAll('#scale option').length > 1")
            bogus = page.evaluate(
                "() => ({ err: document.getElementById('err').textContent,"
                        " inst: window.CURRENT_INSTRUMENT &&"
                        " window.CURRENT_INSTRUMENT.id })")
            if "bogus99" not in bogus["err"]:
                failures.append(
                    "an unknown ?inst id must be reported in #err naming the "
                    f"id, got {bogus['err']!r}")
            if bogus["inst"] != "oot-alto-c-12":
                failures.append(
                    "the boot must still land on the manifest default after "
                    f"an unknown id, got {bogus['inst']!r}")
            if errs:
                failures.append(f"boot diagnostics: page errors {errs}")
            page.close()
            ctx4.close()

            # Duplicated manifest id: intercept instruments.json with a
            # doctored copy; the app must report the repeat and still boot.
            # FRESH context: this leg's first load still installs a SW whose
            # precache holds the REAL instruments.json — reused here (shared
            # with the bogus99 leg above), the SW would claim the second
            # navigation and serve its cache, hiding the routed manifest.
            ctx5 = browser.new_context()
            page = ctx5.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.route("**/instruments.json", lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body="""{"default": "oot-alto-c-12", "instruments": [
                  {"id": "ico-oak-leaf-bass-c-triple",
                   "fingerings": "instruments/ico-oak-leaf-bass-c-triple/fingerings.json",
                   "svg": "instruments/ico-oak-leaf-bass-c-triple/ocarina-template.svg"},
                  {"id": "ico-oak-leaf-bass-c-triple",
                   "fingerings": "instruments/ico-oak-leaf-bass-c-triple/fingerings.json",
                   "svg": "instruments/ico-oak-leaf-bass-c-triple/ocarina-template.svg"},
                  {"id": "oot-alto-c-12",
                   "fingerings": "instruments/oot-alto-c-12/fingerings.json",
                   "svg": "instruments/oot-alto-c-12/ocarina-template.svg"}
                ]}"""))
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            dup = page.evaluate(
                "() => ({ err: document.getElementById('err').textContent,"
                        " notes: (window.NOTES || []).length })")
            if "ico-oak-leaf-bass-c-triple" not in dup["err"] or \
                    "repeat" not in dup["err"]:
                failures.append(
                    "a duplicated manifest id must be reported in #err "
                    f"(got {dup['err']!r})")
            if not dup["notes"]:
                failures.append(
                    "the boot must still land with a working instrument "
                    "after reporting the duplicate id")
            page.close()
            ctx5.close()
            if errs:
                failures.append(f"boot diagnostics: page errors {errs}")

            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: every ocarina boots from its folder; tone plumbing installs, "
          "interpolates and falls back per field.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
