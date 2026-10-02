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

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv


from suite_server import start_server


BOOT_WAIT = ("typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
             " && window.NOTES && window.NOTES.length")


def boot_instrument(browser, base, inst_id, failures, tag):
    """Boots ?inst=<id> and asserts the folder data came up."""
    page = browser.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(f"{base}?inst={inst_id}")
    page.wait_for_function(BOOT_WAIT)
    # The twin round-trip lands as the last step of loadInstrument, but
    # twinModel() is null both before it lands AND for instruments that ship
    # no twin — so `!== undefined` passes on the initial null and the read
    # below races the async install (the boot-tail red under load). boot()
    # only fills the #scale library select AFTER loadInstrument (and its
    # twin round-trip) has fully resolved, and the major/chromatic scales
    # are always in-range, so a populated #scale is the settled rendezvous.
    page.wait_for_function(
        "() => document.getElementById('scale').options.length > 0",
        timeout=15000)
    state = page.evaluate("""() => ({
      notes: window.NOTES.length,
      fingered: !!(window.FING && window.FING.notes && window.FING.notes.length)
                && window.FING.notes[0].id === window.NOTES[0],
      templated: !!(window.CURRENT_INSTRUMENT && window.CURRENT_INSTRUMENT.svg),
      chambered: Object.keys(window.CHAMBER).length > 0,
      twin: typeof window.installTwinModel === "function"
              ? (window.OCA_DEBUG && window.OCA_DEBUG.twinModel
                  ? window.OCA_DEBUG.twinModel() : "MISSING")
              : "MISSING",
      voice: window.OCA_DEBUG && window.OCA_DEBUG.voiceCard
              ? window.OCA_DEBUG.voiceCard() : "MISSING",
    })""")
    for key in ("fingered", "templated", "chambered"):
        if not state[key]:
            failures.append(f"{tag}: {key} not installed for {inst_id}")
    if state["notes"] < 5:
        failures.append(f"{tag}: {inst_id} has only {state['notes']} notes")
    voice = state.get("voice")
    if not isinstance(voice, dict) or voice.get("rev") != "v3k-chamber":
        failures.append(
            f"{tag}: OCA_DEBUG.voiceCard() must stamp v3k-chamber "
            f"(got {voice!r})")
    # twin_model.json: a shipped fit must install as the chamber model —
    # single-chamber schema ({model: {notes}}) or the multi wrapper
    # ({chambers: {ch: {model, gain}}})
    twin_decl = next((i.get("twin") for i in
                      json.loads((ROOT / "instruments.json").read_text())
                      ["instruments"] if i["id"] == inst_id), None)
    twin_path = (ROOT / twin_decl) if twin_decl else None
    if twin_path and twin_path.exists():
        twin = state["twin"] if isinstance(state["twin"], dict) else None
        if state["twin"] == "MISSING":
            failures.append(f"{tag}: OCA_DEBUG.twinModel() missing (audio.js change?)")
        elif not twin:
            failures.append(f"{tag}: {inst_id} ships twin_model.json but none installed")
        else:
            if isinstance(voice, dict) and voice.get("twin") != inst_id:
                failures.append(
                    f"{tag}: voiceCard.twin must be {inst_id!r} when a twin "
                    f"ships (got {voice.get('twin')!r} — additive fallback "
                    "is the high-noise class)")
            def model_ok(d):
                return isinstance(d, dict) and isinstance(d.get("notes"), list) \
                    and d["notes"] and isinstance(d["notes"][0], dict) \
                    and d["notes"][0].get("f0") > 0
            if isinstance(twin.get("model"), dict):
                ok = model_ok(twin["model"])
            elif isinstance(twin.get("chambers"), dict) and twin["chambers"]:
                ok = all(
                    model_ok((c.get("model") if isinstance(c, dict) else c))
                    for c in twin["chambers"].values())
            else:
                ok = False
            if not ok:
                failures.append(f"{tag}: {inst_id} ships twin_model.json but the installed "
                                f"model is wrong/empty: {str(state['twin'])[:160]}")
    elif state["twin"] not in (None, "MISSING"):
        failures.append(f"{tag}: {inst_id} shipped no twin_model.json but installed "
                        f"{str(state['twin'])[:160]}")
    if errs:
        failures.append(f"{tag}: {inst_id} page errors {errs}")
    return page


TPL_PROBE = """
() => ({
  tpl: currentTemplatePath(), id: currentSongId(), title: currentSongTitle(),
})
"""


TWIN_PROBE = """
() => {
  // A well-formed twin model installs; corrupt input uninstalls (never boot).
  const MODEL = {
    schema: "ocarina-twin-v2", instrument: "probe", chamber: "1",
    globals: {hiss_hp_hz: 2800, chiff_q: 2.2, sync_amt: 0.65},
    notes: [
      {note: "A4", f0: 440.0, level: 0.5, h: [1, 0.01, 0.01, 0, 0, 0],
       Q: 60, noise_Q: 12, noise_res_db: -28, noise_hiss_db: -50,
       noise_slope_db_oct: -8, atk_pre_s: 0.006, atk_speak_s: 0.01,
       overshoot_db: 0.5, chiff_peak: 1.2, chiff_len_s: 0.045, rel_s: 0.06,
       wander_cents_std: 3, wobble_pct: 6, wobble_hz: 4},
      {note: "A5", f0: 880.0, level: 1.0, h: [1, 0.02, 0.01, 0, 0, 0],
       Q: 70, noise_Q: 12, noise_res_db: -30, noise_hiss_db: -48,
       noise_slope_db_oct: -6, atk_pre_s: 0.006, atk_speak_s: 0.02,
       overshoot_db: 0.2, chiff_peak: 1.0, chiff_len_s: 0.045, rel_s: 0.08,
       wander_cents_std: 2, wobble_pct: 4, wobble_hz: 4},
    ]};
  installTwinModel(MODEL, "probe");
  const okShape = !!OCA_DEBUG.twinModel()
    && OCA_DEBUG.twinModel().chambers
    && OCA_DEBUG.twinModel().chambers["1"].model.notes.length === 2
    && OCA_DEBUG.twinModel().chambers["1"].model.notes[0].f0 === 440.0
    && OCA_DEBUG.twinModel().chambers["1"].gain === 1;
  installTwinModel({instrument: "junk"}, "junk");
  const junkNull = OCA_DEBUG.twinModel() === null;
  installTwinModel("nope", "junk2");
  const strNull = OCA_DEBUG.twinModel() === null;
  installTwinModel(null, "reset");
  const resetNull = OCA_DEBUG.twinModel() === null;
  // multi-chamber wrapper: per-chamber models + chain-relative gains
  const wrap = (ch) => Object.assign({}, MODEL, {chamber: String(ch),
    instrument: "probe-multi-" + ch});
  const MULTI = {schema: "ocarina-twin-multi-v1", instrument: "multi",
    chambers: {
      "1": {gain: 1.0, model: wrap(1)},
      "2": {gain: 0.5714, model: wrap(2)},
      "3": wrap(3),
    }};
  installTwinModel(MULTI, "multi");
  const mt = OCA_DEBUG.twinModel();
  const multiOk = !!mt && mt.chambers
    && mt.chambers["1"] && mt.chambers["1"].model.notes.length === 2
    && mt.chambers["1"].gain === 1.0
    && mt.chambers["2"].gain === 0.5714
    && mt.chambers["3"] && mt.chambers["3"].gain === 1;
  installTwinModel(MODEL, "probe"); // restore single shape over the multi
  const afterMulti = !!OCA_DEBUG.twinModel()
    && OCA_DEBUG.twinModel().chambers["1"].model.notes.length === 2;
  installTwinModel(null, "reset");
  const resetNull2 = OCA_DEBUG.twinModel() === null;
  return {okShape, junkNull, strNull, resetNull,
          multiOk, afterMulti, resetNull2};
}
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

            # 2 — twin model plumbing: install/shapes on the default instrument
            print("== twin model install / shapes", flush=True)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base + "?inst=" + inst_ids[0])
            page.wait_for_function(BOOT_WAIT)
            r = page.evaluate(TWIN_PROBE)
            if errs:
                failures.append(f"twin model: page errors {errs}")
            if not r or not isinstance(r, dict):
                failures.append(f"twin model: probe failed {r}")
            else:
                if not r["okShape"]:
                    failures.append("twin model: well-formed model not installed")
                if not (r["junkNull"] and r["strNull"] and r["resetNull"]):
                    failures.append(f"twin shapes: corrupt input must uninstall "
                                    f"(junk {r['junkNull']} str {r['strNull']} "
                                    f"reset {r['resetNull']})")
                if not r["multiOk"]:
                    failures.append("twin shapes: multi-chamber wrapper must install "
                                    "per-chamber models with their gains")
                if not (r["afterMulti"] and r["resetNull2"]):
                    failures.append("twin shapes: single-over-multi restore / final "
                                    "reset failed")
            page.close()
            # 3 — per-song ocarina template selection (svgWhen): the saria
            # rule fires when the loaded song's TITLE matches (both by ?song
            # deep link — exact id since the re-key — and by typing the
            # title), and unrelated titles keep the generic template.
            print("== per-song ocarina template (svgWhen)", flush=True)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base + "?inst=oot-alto-c-12&song=sarias-song&oot")
            page.wait_for_function(BOOT_WAIT)
            # FINGERINGS install precedes the library tail (the tone-model
            # round-trip comes after in loadInstrument): probing #scale/#src
            # can otherwise race the ?song load in.
            page.wait_for_function(
                "() => document.getElementById('scale').value ==="
                " 'sarias-song'")
            byId = page.evaluate(TPL_PROBE)
            page.goto(base + "?inst=oot-alto-c-12&oot")
            page.wait_for_function(BOOT_WAIT)
            # BOOT_WAIT (practice + NOTES) can fire before boot() reaches its
            # tail — the home song's library load then still overwrites #src
            # and clobbers typed text. Pin the library tail first (#scale), as
            # the id-path leg above does, before any typed probe.
            page.wait_for_function(
                "() => document.getElementById('scale').value ==="
                " 'song-of-storms'")
            page.evaluate(TYPED, "Saria's Song")
            byTitle = page.evaluate(TPL_PROBE)
            page.evaluate(TYPED, "Zelda's Lullaby")
            byOtherTitle = page.evaluate(TPL_PROBE)
            if errs:
                failures.append(f"svgWhen: page errors {errs}")
            if not str(byId.get("tpl") or "").endswith(
                    "ocarina-template-saria.svg"):
                failures.append(
                    "svgWhen: song id sarias-song must select the saria "
                    f"template, got {byId!r}")
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

            # 3b — generated scales: the C-major and chromatic entries are
            # NOT shipped data; the library synthesizes them for the LOADED
            # chart (C-major = the chart minus black-key ids) and regenerates
            # them when the instrument changes — zero out-of-range by
            # construction, display tokens use the s→# convention.
            print("== generated scales follow the loaded chart", flush=True)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            page.wait_for_function(
                "() => document.getElementById('scale').value === 'song-of-storms'")
            st = page.evaluate(
                "() => { const B = (typeof BUILTIN !== 'undefined' && BUILTIN) || {}; return"
                        " { notes: window.NOTES,"
                        " chrom: (B.chromatic || {}).body || null,"
                        " major: (B.major || {}).body || null,"
                        " chromGroup: (B.chromatic || {}).group,"
                        " majorGroup: (B.major || {}).group }; }")
            import re as _re
            def to_disp(i):
                return _re.sub(r"^([A-G])s", r"\1#", i)
            if not st["chrom"] or not st["major"]:
                failures.append("scales: BUILTIN.major/chromatic must be "
                                "synthesized for the loaded chart")
            elif st["chromGroup"] != "Scales" or st["majorGroup"] != "Scales":
                failures.append(f"scales: wrong groups {st['chromGroup']!r}/{st['majorGroup']!r}")
            else:
                expect_chrom = " ".join(to_disp(n) for n in st["notes"])
                expect_major = " ".join(to_disp(n) for n in st["notes"]
                                        if not _re.match(r"^[A-G]s", n))
                if st["chrom"] != expect_chrom:
                    failures.append("scales: chromatic body must be the loaded "
                                    "chart's ids in order, display-spelled")
                if st["major"] != expect_major:
                    failures.append("scales: major body must be the chart minus "
                                    "black-key ids")
            page.select_option("#instSel", "stein-double-alto-c")
            old_chrom = st["chrom"]
            page.wait_for_function(
                "() => (BUILTIN.chromatic || {}).body !== " + json.dumps(old_chrom),
                timeout=20000)
            st2 = page.evaluate(
                "() => ({ notes: window.NOTES,"
                        " chrom: BUILTIN.chromatic.body, major: BUILTIN.major.body })")
            expect_chrom2 = " ".join(to_disp(n) for n in st2["notes"])
            expect_major2 = " ".join(to_disp(n) for n in st2["notes"]
                                     if not _re.match(r"^[A-G]s", n))
            if st2["chrom"] != expect_chrom2 or st2["major"] != expect_major2:
                failures.append("scales: bodies must regenerate for the newly "
                                "installed chart")
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

            # 5 — ?song / ?zen boot flows (T4's deep-link boots): a bare
            # ?song loads on the manifest default and stays in the grid
            # view; &zen drops the boot straight into zen via the CSS
            # fallback (?nofs=1 pins the fallback in headless), the single
            # view's live card up and the song still loaded — the paths
            # the landing stubs and shared zen links ride.
            print("== ?song / ?zen boot flows", flush=True)
            songs = json.loads((ROOT / "songs.json").read_text(encoding="utf-8"))
            head = (songs["eponas-song"].get("body") or "").strip().split("\n")[0][:30]
            STATE = """() => ({
              title: document.getElementById('title').textContent,
              src: document.getElementById('src').value,
              focus: document.getElementById('tabPanel').classList.contains('focus'),
              zenfb: document.body.classList.contains('zen-fallback'),
              mode: (document.querySelector('[aria-checked="true"].seg-btn')
                     || { dataset: {} }).dataset.mode || null,
              oor: document.querySelectorAll('.card.oor').length,
            })"""
            for tag, extra in (
                    ("?song", "?song=eponas-song"),
                    ("?song+zen", "?song=eponas-song&zen&nofs=1")):
                page = browser.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                page.goto(base + extra)
                page.wait_for_function(BOOT_WAIT)
                page.wait_for_function(
                    "() => document.getElementById('scale').value === 'eponas-song'")
                page.wait_for_timeout(1200)
                st = page.evaluate(STATE)
                if errs:
                    failures.append(f"{tag} boot: page errors {errs}")
                if st["title"] != "Epona's Song":
                    failures.append(f"{tag} boot: title {st['title']!r} "
                                    "!= Epona's Song")
                if head not in st["src"]:
                    failures.append(f"{tag} boot: #src lacks the body head {head!r}")
                if st["oor"]:
                    failures.append(f"{tag} boot: {st['oor']} out-of-range marks "
                                    "on the 12-hole default")
                if tag == "?song" and (st["focus"] or st["zenfb"]):
                    failures.append(
                        f"{tag} boot must stay out of zen "
                        f"(focus={st['focus']} zen-fallback={st['zenfb']})")
                if tag == "?song+zen" and not (st["focus"] and st["zenfb"]):
                    failures.append(
                        f"{tag} boot must land in fallback zen "
                        f"(focus={st['focus']} zen-fallback={st['zenfb']})")

                want_mode = "single" if tag == "?song+zen" else "grid"
                if st["mode"] != want_mode:
                    failures.append(f"{tag} boot: view mode {st['mode']!r} "
                                    f"!= {want_mode!r}")
                page.close()

            # 6 — wet instrument switch auto-selects the in-range family
            # member (the library's same ladder the landing stubs walk):
            # switching with a song loaded jumps to the family member that
            # fits the NEW chart (base first, then variants alphabetically),
            # stays put when the current member already fits, keeps the
            # current song quietly when NOTHING fits, never touches typed
            # text, and never starts transport from a wet switch.
            print("== wet switch auto-selects the in-range family member", flush=True)
            songs = json.loads((ROOT / "songs.json").read_text(encoding="utf-8"))

            def body_head(key):
                body = songs[key].get("body") or ""
                line = next((ln for ln in body.splitlines()
                             if ln.strip() and not ln.lstrip().startswith("#")), "")
                return line.strip()[:30]

            AUTO_STATE = """() => ({
              inst: window.CURRENT_INSTRUMENT && window.CURRENT_INSTRUMENT.id,
              sel: document.getElementById('scale').value,
              selText: (document.getElementById('scale').selectedOptions[0]
                        || {textContent: ''}).textContent,
              label: (document.getElementById('libDdText') || {}).textContent || '',
              title: document.getElementById('title').textContent,
              src: document.getElementById('src').value,
              playing: !!(window.isMelodyPlaying && window.isMelodyPlaying()),
            })"""

            def wait_wet(page, inst, wait_sel, failures, tag):
                """Rendezvous: the new instrument is installed AND (when the
                auto-select must land) the #scale select carries the song."""
                cond = ("() => window.CURRENT_INSTRUMENT &&"
                        " window.CURRENT_INSTRUMENT.id === '" + inst + "'"
                        " && document.getElementById('scale').value === '" +
                        wait_sel + "'")
                try:
                    page.wait_for_function(cond, timeout=15000)
                except Exception:
                    failures.append(f"{tag}: timed out waiting for "
                                    f"inst={inst!r} sel={wait_sel!r}")
                return page.evaluate(AUTO_STATE)

            def run_leg(tag, goto_extra, goto_name, inst, wait_sel,
                        want_song, want_head):
                page = browser.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                page.goto(base + goto_extra)
                page.wait_for_function(BOOT_WAIT)
                # The ?song load (or boot home tail) must land before the
                # switch — the editor title is the rendezvous that works even
                # when the song is range-hidden from the dropdown.
                page.wait_for_function(
                    "() => document.getElementById('title').textContent === "
                    + json.dumps(goto_name), timeout=15000)
                page.select_option("#instSel", inst)
                st = wait_wet(page, inst, wait_sel, failures, tag)
                if errs:
                    failures.append(f"{tag}: page errors {errs}")
                if st["inst"] != inst:
                    failures.append(f"{tag}: instrument is {st['inst']!r}, "
                                    f"expected {inst!r}")
                if wait_sel and st["sel"] != wait_sel:
                    failures.append(f"{tag}: #scale {st['sel']!r} != "
                                    f"{wait_sel!r} (auto-select did not land)")
                if want_song:
                    name = songs[want_song].get("name") or want_song
                    if st["selText"] != name:
                        failures.append(f"{tag}: dropdown option text "
                                        f"{st['selText']!r} != {name!r} "
                                        "(dropdown must reflect the jump)")
                    if st["title"] != name:
                        failures.append(f"{tag}: title {st['title']!r} != {name!r}")
                if want_head:
                    if want_head not in st["src"]:
                        failures.append(f"{tag}: #src lacks {want_head!r}")
                if st["playing"]:
                    failures.append(f"{tag}: a wet switch must not start "
                                    "transport (isMelodyPlaying() true)")
                # The label must always describe what the editor holds.
                if not st["label"]:
                    failures.append(f"{tag}: #libDdText label went empty")
                page.close()

            # a) current member does NOT fit the new chart → jump to the
            #    fitting family member (botw-theme only fits the double alto;
            #    on the triple both -bass and -down3 fit → base-first rule
            #    then alphabetical lands on -bass).
            run_leg("jump alto->bass", "?song=botw-theme",
                    songs["botw-theme"].get("name") or "botw-theme",
                    "ico-oak-leaf-bass-c-triple", "botw-theme-bass",
                    "botw-theme-bass", body_head("botw-theme-bass"))
            # b) current member already fits the new chart → stay put
            #    (song-of-time fits every chart the 12-hole user can reach).
            run_leg("stay when fitting", "?song=song-of-time",
                    songs["song-of-time"].get("name") or "song-of-time",
                    "ico-oak-leaf-bass-c-triple", "song-of-time",
                    None, None)
            # c) the reverse jump: a bass arrangement meets the 12-hole —
            #    the ONLY fitting family member is the base.
            run_leg("jump bass->alto", "?inst=ico-oak-leaf-bass-c-triple&song=eponas-song-bass",
                    songs["eponas-song-bass"].get("name") or "eponas-song-bass",
                    "oot-alto-c-12", "eponas-song",
                    "eponas-song", body_head("eponas-song"))
            # d) nothing fits the new chart → keep the current song and stay
            #    quiet (botw family has no 12-hole member; #scale drops it
            #    per today's filter rule, #src keeps the arrangement).
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base +
                      "?inst=ico-oak-leaf-bass-c-triple&song=botw-theme-bass")
            page.wait_for_function(BOOT_WAIT)
            page.wait_for_function(
                "() => document.getElementById('scale').value === 'botw-theme-bass'")
            page.select_option("#instSel", "oot-alto-c-12")
            try:
                page.wait_for_function(
                    "() => window.CURRENT_INSTRUMENT &&"
                    " window.CURRENT_INSTRUMENT.id === 'oot-alto-c-12'",
                    timeout=15000)
                page.wait_for_timeout(300)
            except Exception:
                failures.append("no-fit: timed out on the instrument install")
            nst = page.evaluate(AUTO_STATE)
            if errs:
                failures.append(f"no-fit keep: page errors {errs}")
            if nst["inst"] != "oot-alto-c-12":
                failures.append(f"no-fit keep: instrument {nst['inst']!r}")
            if body_head("botw-theme-bass") not in nst["src"]:
                failures.append("no-fit keep: the loaded arrangement must stay "
                                "in the editor when no family member fits")
            if not nst["label"]:
                failures.append("no-fit keep: label must keep naming the "
                                "loaded song")
            if nst["playing"]:
                failures.append("no-fit keep: a wet switch must not start "
                                "transport (isMelodyPlaying() true)")
            page.close()
            # e) typed text is nobody's family: a wet switch must leave the
            #    editor text and the no-selection dropdown alone.
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            page.wait_for_function(
                "() => document.getElementById('scale').value === 'song-of-storms'")
            typed = page.evaluate(TYPED, "Scratch Line")
            page.select_option("#instSel", "ico-oak-leaf-bass-c-triple")
            try:
                page.wait_for_function(
                    "() => window.CURRENT_INSTRUMENT &&"
                    " window.CURRENT_INSTRUMENT.id ==="
                    " 'ico-oak-leaf-bass-c-triple' && window.NOTES.length",
                    timeout=15000)
                page.wait_for_timeout(300)
            except Exception:
                failures.append("typed: timed out on the instrument install")
            tst = page.evaluate(AUTO_STATE)
            if typed != "Scratch Line":
                failures.append(f"typed: typed title probe failed ({typed!r})")
            if errs:
                failures.append(f"typed: page errors {errs}")
            if "C4 D4 E4" not in tst["src"]:
                failures.append("typed: a wet switch must not replace typed "
                                f"text, #src {tst['src'][:40]!r}")
            if tst["sel"]:
                failures.append("typed: #scale must stay unselected (no "
                                "family jump off typed text)")
            if tst["playing"]:
                failures.append("typed: a wet switch must not start transport")
            page.close()
            # f) the open generated scale must follow the instrument: the
            #    C-major/Chromatic bodies are synthesized for the loaded
            #    chart under the SAME id, so the wet-switch "stay" (same id,
            #    no loadLibraryItem) would keep the old chart's sheet open.
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base + "?song=major")
            page.wait_for_function(BOOT_WAIT)
            page.wait_for_function(
                "() => document.getElementById('scale').value === 'major'")
            old_major = page.evaluate("() => BUILTIN.major.body")
            sheet_before = page.evaluate(
                "() => document.getElementById('src').value")
            page.select_option("#instSel", "stein-double-alto-c")
            try:
                page.wait_for_function(
                    "() => document.getElementById('scale').value === 'major' &&"
                    " BUILTIN.major.body !== " + json.dumps(old_major) +
                    " && document.getElementById('src').value"
                    " .indexOf(BUILTIN.major.body) >= 0",
                    timeout=15000)
            except Exception:
                failures.append("scale-follow: the open generated scale did "
                                "not refresh to the new chart's body on the "
                                "instrument switch")
            fst = page.evaluate(AUTO_STATE)
            if errs:
                failures.append(f"scale-follow: page errors {errs}")
            if fst["sel"] != "major":
                failures.append(f"scale-follow: #scale {fst['sel']!r} != "
                                "'major' (the open tool must stay selected)")
            elif fst["src"] == sheet_before:
                failures.append("scale-follow: the editor still carries the "
                                "pre-switch chart's sheet")
            if fst["playing"]:
                failures.append("scale-follow: a wet switch must not start "
                                "transport (isMelodyPlaying() true)")
            page.close()

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
