#!/usr/bin/env python3
# Jet-drive A/B contract (?jet=1): the experimental whole-voice AudioWorklet
# runs a 2-pole resonator + delayed sigmoid jet + gated turbulence from
# instruments/<id>/jet_model.json. Pins:
#   - the worklet module loads and renders a finite, audible note;
#   - node parameters and the note timeline come from the supplied jet row;
#   - absent jet fields fall back to the documented defaults;
#   - playNoteAt takes the jet path only when the flag, a fitted model and a
#     ready worklet all agree; otherwise it falls back to v4-breath;
#   - ?jet=0 keeps the breath voice, and the three recorded instruments
#     install their single/multi-chamber jet models;
#   - the debug panel's Jet switch flips the session flag.
#
#   python3 tests/jet_engine.py      # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function'"
        " && document.getElementById('scale').options.length > 0")

from suite_server import start_server


WORKLET_DRIVER = """
async () => {
  const mod = await import('/js/jet-voice.js');
  const off = new OfflineAudioContext(1, 57600, 48000);
  const ok = await mod.prepareJetWorklet(off);
  const row = {
    f0: 523.25, Q: 42, delay_ratio: 0.5, jet_k: 1, jet_h2: 0.3,
    jet_h3: 0.2, jet_drive: 0.5, jet_feedback: 0.1, turb_gain: 0.005,
    turb_gate: 0.5, turb_bypass: 0.2, out_gain: 1,
    noise_slope_db_oct: -8,
  };
  const model = mod.loadJetModelFromObject({
    schema: 'ocarina-jet-v1', notes: [row],
  });
  const nf = {
    rel_s: 0.08, atk_pre_s: 0.008, atk_speak_s: 0.028,
    overshoot_db: 0.4, wobble_hz: 0.45, slope_db_oct: -8,
  };
  const h = mod.scheduleJetNote(off, off.destination, {
    jetModel: model, f0: 523.25, when: 0.2, holdSec: 0.55,
    master: 1, nf: nf,
  });
  const buf = await off.startRendering();
  const d = buf.getChannelData(0);
  let finite = 0, acc = 0, max = 0, pre = 0, preN = 0;
  const a = Math.floor(0.35 * 48000), b = Math.floor(0.7 * 48000);
  for (let i = 0; i < b; i++) {
    const v = d[i];
    if (i >= a) {
      if (isFinite(v)) { finite++; acc += v * v; if (Math.abs(v) > max) max = Math.abs(v); }
    } else if (i < Math.floor(0.15 * 48000)) {
      pre += v * v; preN++;
    }
  }
  const defaults = mod.interpJet(mod.loadJetModelFromObject({
    schema: 'ocarina-jet-v1', notes: [{ f0: 523.25 }],
  }), 523.25);
  return {
    ok, finite, n: b - a, rms: Math.sqrt(acc / (b - a)), max,
    preRms: Math.sqrt(pre / preN),
    params: h._jet.params, tl: h._jet.timeline,
    defaults: {
      Q: defaults.Q, delay_ratio: defaults.delay_ratio,
      jet_k: defaults.jet_k, turb_gain: defaults.turb_gain,
      out_gain: defaults.out_gain,
    },
  };
}
"""

PATH_DRIVER = """
(id) => {
  const path = (playNoteAt(id, null, 0.5), OCA_DEBUG.lastVoicePath());
  return {
    path,
    enabled: OCA_DEBUG.jetEnabled(),
    ready: OCA_DEBUG.jetReady(),
    model: !!OCA_DEBUG.jetModel(),
    chambers: OCA_DEBUG.jetModel() ? Object.keys(OCA_DEBUG.jetModel().chambers || {}) : [],
    errors: OCA_DEBUG.voiceErrors(),
  };
}
"""

PANEL_DRIVER = """
() => {
  const btn = document.getElementById('dbgJet');
  if (!btn) return { present: false };
  const before = OCA_DEBUG.jetEnabled();
  btn.click();
  const after = OCA_DEBUG.jetEnabled();
  btn.click();
  return { present: true, before, after, restored: OCA_DEBUG.jetEnabled(),
           pressed: btn.getAttribute('aria-pressed') };
}
"""


def boot_page(browser, base, query, errs):
    page = browser.new_page()
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(base + query)
    page.wait_for_function(WAIT)
    return page


def wait_jet(page):
    try:
        page.wait_for_function("OCA_DEBUG.jetReady()", timeout=20000)
    except Exception:
        pass


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=HEADLESS,
                args=["--autoplay-policy=no-user-gesture-required"])
            errs = []

            # --- the worklet graph + a real rendered note ---
            page = boot_page(browser, base, "?inst=oot-alto-c-12&jet=1", errs)
            wait_jet(page)
            if not page.evaluate("() => OCA_DEBUG.jetReady()"):
                failures.append("?jet=1 boot must load the AudioWorklet module")
            work = page.evaluate(WORKLET_DRIVER)
            if not work["ok"]:
                failures.append("the worklet must register on an offline context too")
            if work["finite"] != work["n"]:
                failures.append(f"jet output has non-finite samples ({work['finite']}/{work['n']})")
            if work["preRms"] > 0.001:
                failures.append(
                    f"the jet node must stay silent before its note (pre-note "
                    f"rms {work['preRms']:.4f} — the A4 default leak)")
            if work["rms"] < 0.01:
                failures.append(f"jet output is silent/too low (rms {work['rms']:.4f})")
            if work["max"] > 2:
                failures.append(f"jet output is runaway (max {work['max']:.2f})")
            params = work["params"]
            want = {"Q": 42, "delay_ratio": 0.5, "jet_k": 1, "jet_h2": 0.3,
                    "jet_h3": 0.2, "jet_drive": 0.5, "jet_feedback": 0.1,
                    "turb_gain": 0.005, "turb_gate": 0.5, "turb_bypass": 0.2,
                    "out_gain": 1}
            for key, val in want.items():
                if abs(params[key] - val) > 1e-6:
                    failures.append(f"node parameter {key} is {params[key]}, expected {val}")
            tl = work["tl"]
            if abs(tl["when"] - 0.2) > 1e-9:
                failures.append(f"jet timeline when is {tl['when']}, expected 0.2")
            if abs(tl["tOff"] - (tl["tHoldEnd"] + 0.08)) > 1e-9:
                failures.append(
                    f"jet release must land at tOff = tHoldEnd + rel, got "
                    f"{tl['tOff']:.3f} vs {tl['tHoldEnd'] + 0.08:.3f}")
            if abs(tl["stopAt"] - (tl["tOff"] + 0.06)) > 1e-9:
                failures.append(
                    f"jet stopAt must be tOff + 0.06, got {tl['stopAt']:.3f}")
            defaults = work["defaults"]
            if defaults["Q"] != 30 or defaults["jet_k"] != 1 \
                    or defaults["delay_ratio"] != 0.5 \
                    or defaults["turb_gain"] != 0 or defaults["out_gain"] != 1:
                failures.append(f"absent jet fields must use defaults, got {defaults}")

            # --- the real play path: jet when flag+model+worklet agree ---
            path = page.evaluate(PATH_DRIVER, "C5")
            if path["path"] != "jet":
                failures.append(f"?jet=1 with a fitted/ready model must play jet, got {path['path']}")
            if path["errors"]["count"]:
                failures.append(f"jet path recorded voice errors: {path['errors']}")
            page.close()

            # --- all three recorded instruments install their jet models ---
            for iid, chambers in (
                    ("oot-alto-c-12", ["1"]),
                    ("stein-double-alto-c", ["1", "2"]),
                    ("ico-oak-leaf-bass-c-triple", ["1", "2", "3"])):
                page = boot_page(browser, base, f"?inst={iid}&jet=1", errs)
                wait_jet(page)
                state = page.evaluate(PATH_DRIVER, "C5")
                if not state["model"]:
                    failures.append(f"{iid} must install its jet_model.json")
                elif sorted(state["chambers"]) != chambers:
                    failures.append(
                        f"{iid} jet chambers {state['chambers']} != {chambers}")
                if not state["ready"]:
                    failures.append(f"{iid}: the worklet must be ready for ?jet=1")
                if state["path"] != "jet":
                    failures.append(f"{iid}: ?jet=1 must take the jet path, got {state['path']}")
                page.close()

            # --- no jet fit: the six-hole falls back to breath ---
            page = boot_page(browser, base, "?inst=six-hole-c&jet=1", errs)
            wait_jet(page)
            state = page.evaluate(PATH_DRIVER, "C5")
            if state["path"] != "breath":
                failures.append(
                    f"an instrument without jet_model.json must fall back to breath, "
                    f"got {state['path']}")
            if state["errors"]["count"]:
                failures.append(f"jet fallback recorded voice errors: {state['errors']}")
            page.close()

            # --- ?jet=0 keeps the breath voice ---
            page = boot_page(browser, base, "?inst=oot-alto-c-12&jet=0", errs)
            state = page.evaluate(PATH_DRIVER, "C5")
            if state["enabled"]:
                failures.append("?jet=0 must start the jet A/B off")
            if state["path"] != "breath":
                failures.append(f"?jet=0 must play the breath voice, got {state['path']}")
            page.close()

            # --- debug panel Jet switch ---
            page = boot_page(browser, base, "?inst=oot-alto-c-12&jet=1&debug=1", errs)
            wait_jet(page)
            panel = page.evaluate(PANEL_DRIVER)
            if not panel["present"]:
                failures.append("the debug panel must carry the Jet switch")
            elif not (panel["before"] is True and panel["after"] is False
                      and panel["restored"] is True):
                failures.append(
                    f"the Jet switch must toggle the session flag "
                    f"({panel['before']} -> {panel['after']} -> {panel['restored']})")
            page.close()

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
    print("\nPASS: the jet-drive AudioWorklet loads, renders a finite note, "
          "takes parameters/timeline from the fitted model, falls back to "
          "breath without a fit, and ?jet=0/panel switch the A/B.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
