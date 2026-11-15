#!/usr/bin/env python3
# Breath-engine contract (v4-breath): the air path is pitch-locked and
# gesture-following. Pins the graph the voice builds from a twin model:
# f0 comb delay, f0 AM oscillator, the voicing-formant peaking filter from
# supplied fields AND defaults, open-hole vent scaling, decorrelated noise
# beds, the attack-excess decay / release swell on the existing note
# timeline, the legacy v2 model fallback (no new keys, no fingering data),
# and the ?breath=0 A/B plain band-pass path.
#
#   python3 tests/breath_engine.py      # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function'"
        " && document.getElementById('scale').options.length > 0")

from suite_server import start_server


GRAPH_DRIVER = """
async () => {
  const mod = await import('/js/helmholtz-voice.js?v=16');
  const ctx = sharedAudioCtx();
  const f0 = 523.25;
  const base = {
    f0: f0, note: 'C5', h: [1, 0.01, 0.004], h_phase: [0, 0.2, 1.1],
    floor_db: -54, slope_db_oct: -8, air_db: -50,
    air_lo_hz: 800, air_hi_hz: 2400,
    atk_pre_s: 0.008, atk_speak_s: 0.028, rel_s: 0.08,
    wander_cents_std: 2.5, wobble_hz: 0.45,
  };
  const mkModel = (row) => mod.loadTwinModelFromObject({
    schema: 'ocarina-twin-v2', globals: { chiff_q: 2.2 }, notes: [row],
  });
  const supplied = mod.scheduleHelmholtzNote(ctx, ctx.destination, {
    model: mkModel(Object.assign({}, base,
      { air_formant_hz: 1900, air_formant_q: 4.2, atk_noise_db: -40 })),
    f0: f0, when: ctx.currentTime + 0.12, holdSec: 0.5, breath: true,
    fingering: null, holes: null,
  });
  const defaults = mod.scheduleHelmholtzNote(ctx, ctx.destination, {
    model: mkModel(base), f0: f0, when: ctx.currentTime + 0.24,
    holdSec: 0.5, breath: true, fingering: null, holes: null,
  });
  // Four of twelve holes open: vent ratio 1/3, cutoff 0.333^0.25,
  // gain 0.333^0.5, all above the 0.15 floor.
  const holes = {};
  for (let i = 0; i < 12; i++) holes['h' + i] = { finger: 'x' };
  const covered = [];
  for (let i = 0; i < 8; i++) covered.push('h' + i);
  const vented = mod.scheduleHelmholtzNote(ctx, ctx.destination, {
    model: mkModel(base), f0: f0, when: ctx.currentTime + 0.36,
    holdSec: 0.5, breath: true,
    fingering: { covered: covered, half: [] }, holes: holes,
  });
  const plain = mod.scheduleHelmholtzNote(ctx, ctx.destination, {
    model: mkModel(base), f0: f0, when: ctx.currentTime + 0.48,
    holdSec: 0.5, breath: false, fingering: null, holes: null,
  });
  const tongue = mod.scheduleTongueBurst(ctx, ctx.destination, {
    model: mkModel(Object.assign({}, base,
      { air_formant_hz: 1900, air_formant_q: 4.2 })),
    f0: f0, when: ctx.currentTime + 0.60,
    fingering: null, holes: null,
  });
  const snap = (h) => {
    const b = h._breath;
    return {
      mode: b.mode,
      delay: b.combDelay ? b.combDelay.delayTime.value : null,
      amFreq: b.amOsc ? b.amOsc.frequency.value : null,
      amDepth: b.amDepth ? b.amDepth.gain.value : null,
      amGain: b.amGain ? b.amGain.gain.value : null,
      formantHz: b.formant ? b.formant.frequency.value : null,
      formantQ: b.formant ? b.formant.Q.value : null,
      formantGain: b.formant ? b.formant.gain.value : null,
      combFeedback: b.combFeedback ? b.combFeedback.gain.value : null,
      combWet: b.combWet ? b.combWet.gain.value : null,
      combDry: b.combDry ? b.combDry.gain.value : null,
      airCenter: b.airBp.frequency.value,
      airNorm: b.airNorm ? b.airNorm.gain.value : null,
      bandNorm: b.bandNorm,
      airLo: b.airLo, airHi: b.airHi, airLin: b.airLin, atkLin: b.atkLin,
      vent: b.vent,
      chiff: !!b.chiffBp,
      noiseOffset: b.noiseOffset, airOffset: b.airOffset,
      timeline: b.timeline,
    };
  };
  const out = {
    supplied: snap(supplied), defaults: snap(defaults), vented: snap(vented),
    plain: snap(plain),
    tongue: {
      kind: tongue._breath.kind,
      formantHz: tongue._breath.formant.frequency.value,
      formantQ: tongue._breath.formant.Q.value,
      when: tongue._breath.timeline.when,
      end: tongue._breath.timeline.end,
      stopAt: tongue._breath.timeline.stopAt,
    },
  };
  setTimeout(() => {
    for (const h of [supplied, defaults, vented, plain, tongue]) {
      try { h.stop(); } catch (e) {}
    }
  }, 900);
  return out;
}
"""

DELAY_COUNT = """
() => new Promise(resolve => {
  const ac = sharedAudioCtx();
  let n = 0;
  const orig = ac.createDelay;
  ac.createDelay = function () { n++; return orig.apply(this, arguments); };
  playNoteAt('C5', null, 0.5);
  setTimeout(() => {
    ac.createDelay = orig;
    cutLive();
    resolve(n);
  }, 120);
})
"""

NORM_DRIVER = """
async () => {
  const mod = await import('/js/helmholtz-voice.js?v=16');
  const row = {
    f0: 523.25, note: 'C5', h: [1, 0.01, 0.004], h_phase: [0, 0.2, 1.1],
    floor_db: -54, slope_db_oct: -8, air_db: -50,
    air_lo_hz: 800, air_hi_hz: 2400,
    atk_pre_s: 0.008, atk_speak_s: 0.028, rel_s: 0.08,
    wander_cents_std: 2.5, wobble_hz: 0.45,
  };
  const model = mod.loadTwinModelFromObject({
    schema: 'ocarina-twin-v2', globals: { chiff_q: 2.2 }, notes: [row],
  });
  const render = async (breath) => {
    const off = new OfflineAudioContext(1, 48000, 48000);
    mod.scheduleHelmholtzNote(off, off.destination, {
      model, f0: 523.25, when: 0.02, holdSec: 0.55, breath, soloAir: true,
      master: 1, fingering: null, holes: null,
    });
    const buf = await off.startRendering();
    const d = buf.getChannelData(0);
    let acc = 0, n = 0;
    for (let i = Math.floor(0.12 * 48000); i < Math.floor(0.42 * 48000); i++) {
      acc += d[i] * d[i]; n++;
    }
    return 20 * Math.log10(Math.sqrt(acc / n) / Math.pow(10, -50 / 20));
  };
  return { plain: await render(false), engine: await render(true) };
}
"""

PANEL_DRIVER = """
() => {
  const btn = document.getElementById('dbgBreath');
  const before = OCA_DEBUG.breathEnabled();
  btn.click();
  const after = OCA_DEBUG.breathEnabled();
  btn.click();
  const restored = OCA_DEBUG.breathEnabled();
  return { present: !!btn, before, after, restored,
           pressed: btn.getAttribute('aria-pressed') };
}
"""


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
            page = browser.new_page()
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(f"{base}?inst=oot-alto-c-12")
            page.wait_for_function(WAIT)

            graph = page.evaluate(GRAPH_DRIVER)
            sup = graph["supplied"]
            dfl = graph["defaults"]
            vent = graph["vented"]
            plain = graph["plain"]

            # --- supplied voicing formant + pitch-lock nodes ---
            if sup["mode"] != "engine":
                failures.append(f"breath engine mode is {sup['mode']!r}, not 'engine'")
            want_delay = 1 / 523.25
            if sup["delay"] is None or abs(sup["delay"] - want_delay) > 1e-6:
                failures.append(
                    f"comb delayTime must be 1/f0 ({want_delay:.6f} s), got {sup['delay']}")
            if sup["amFreq"] is None or abs(sup["amFreq"] - 523.25) > 1e-6:
                failures.append(f"AM oscillator must run at f0, got {sup['amFreq']}")
            if sup["amDepth"] != 0.5:
                failures.append(f"AM depth must default 0.5, got {sup['amDepth']}")
            if sup["amGain"] != 1:
                failures.append(f"AM gain node must sit at 1, got {sup['amGain']}")
            if abs(sup["combFeedback"] - 0.35) > 1e-6:
                failures.append(f"comb feedback must default 0.35, got {sup['combFeedback']}")
            if abs(sup["combWet"] - 0.6) > 1e-6 or abs(sup["combDry"] - 0.4) > 1e-6:
                failures.append(
                    f"comb wet/dry mix must default 0.6/0.4, got "
                    f"{sup['combWet']}/{sup['combDry']}")
            if abs(sup["formantHz"] - 1900) > 1e-3:
                failures.append(
                    f"supplied air_formant_hz must drive the peaking filter "
                    f"(got {sup['formantHz']})")
            if abs(sup["formantQ"] - 4.2) > 1e-6:
                failures.append(
                    f"supplied air_formant_q must drive the peaking filter "
                    f"(got {sup['formantQ']})")
            if abs(sup["formantGain"] - 6) > 1e-6:
                failures.append(f"voicing bump gain must default +6 dB, got {sup['formantGain']}")
            if sup["chiff"]:
                failures.append("the new engine must replace the old chiff burst")

            # --- defaults when the model predates the new keys ---
            want_hz = min(2400, max(800, 2.2 * 523.25))
            if abs(dfl["formantHz"] - want_hz) > 1e-3:
                failures.append(
                    f"absent air_formant_hz must default to clamp(2.2*f0, lo, hi) "
                    f"= {want_hz:.1f} Hz, got {dfl['formantHz']}")
            if dfl["formantQ"] != 1.0:
                failures.append(f"absent air_formant_q must default 1.0, got {dfl['formantQ']}")
            if abs(dfl["timeline"]["atkDb"] - (-44)) > 1e-9:
                failures.append(
                    f"absent atk_noise_db must default air_db + 6 dB (-44), "
                    f"got {dfl['timeline']['atkDb']}")

            # --- vent scaling from the fingering chart ---
            want_ratio = 1 / 3
            want_cut = want_ratio ** 0.25
            want_gain = 1  # cutoff-only: fitted air_db is already per-note
            if not vent["vent"]["sourced"]:
                failures.append("fingering data must mark the vent factor as sourced")
            if abs(vent["vent"]["ratio"] - want_ratio) > 1e-9:
                failures.append(
                    f"open/total hole ratio must be {want_ratio:.6f}, got "
                    f"{vent['vent']['ratio']}")
            if abs(vent["vent"]["cutoff"] - want_cut) > 1e-9 or \
                    abs(vent["vent"]["gain"] - want_gain) > 1e-9:
                failures.append(
                    f"vent cutoff/gain exponents must be k=0.25 / 0.5, got "
                    f"{vent['vent']['cutoff']}/{vent['vent']['gain']}")
            if abs(vent["airHi"] - 2400 * want_cut) > 1e-3:
                failures.append(
                    f"air_hi_eff must scale by the vent cutoff, got {vent['airHi']}")
            if abs(vent["airLin"] - 10 ** (-50 / 20)) > 1e-6:
                failures.append(
                    f"air path level must stay at the fitted air_db (vent is "
                    f"cutoff-only), got {vent['airLin']}")
            if not (vent["bandNorm"] > 1 and
                    abs(vent["airNorm"] - vent["bandNorm"]) < 1e-6):
                failures.append(
                    f"the native band-pass needs its RMS-normalization gain "
                    f"(bandNorm {vent['bandNorm']}, node {vent['airNorm']})")
            if abs(vent["airCenter"] - min(vent["airHi"], max(800, 1.25 * 523.25))) > 1e-3:
                failures.append(
                    f"band-pass center must be clamp(1.25*f0, lo, hi_eff), got "
                    f"{vent['airCenter']} (lo {vent['airLo']}, hi {vent['airHi']})")

            # --- decorrelated beds ---
            if abs(sup["noiseOffset"] - sup["airOffset"]) < 1e-9:
                failures.append(
                    f"noise and air sources must start at different loop offsets "
                    f"(both {sup['noiseOffset']:.3f})")
            if plain["noiseOffset"] != plain["airOffset"]:
                failures.append(
                    "?breath=0 must keep the legacy correlated noise/air bed "
                    f"({plain['noiseOffset']} vs {plain['airOffset']})")

            # --- attack decay and release swell on the existing timeline ---
            tl = sup["timeline"]
            if not (tl["tOn"] < tl["atkPeakAt"] < tl["tSpeak"]):
                failures.append(
                    f"attack excess peak must land between tOn and tSpeak "
                    f"({tl['tOn']:.3f} / {tl['atkPeakAt']:.3f} / {tl['tSpeak']:.3f})")
            if tl["atkEnd"] != tl["tSpeak"]:
                failures.append(
                    f"attack excess must decay by atk_speak_s (tSpeak "
                    f"{tl['tSpeak']:.3f}), got {tl['atkEnd']:.3f}")
            if tl["swellStart"] is None or tl["swellEnd"] is None:
                failures.append("a plain note must carry the release swell")
            else:
                if not (tl["swellStart"] < tl["swellEnd"]):
                    failures.append(
                        f"release swell must rise before it lands "
                        f"({tl['swellStart']:.3f} -> {tl['swellEnd']:.3f})")
                if abs((tl["swellEnd"] - tl["swellStart"]) - 0.015) > 0.002:
                    failures.append(
                        f"release swell length must be ~15 ms, got "
                        f"{tl['swellEnd'] - tl['swellStart']:.4f}s")
                if tl["swellEnd"] > tl["tHoldEnd"] + 1e-9:
                    failures.append(
                        f"release swell must stay inside the hold "
                        f"(end {tl['swellEnd']:.3f} > hold end {tl['tHoldEnd']:.3f})")
            if abs(tl["tOff"] - (tl["tHoldEnd"] + tl["rel"])) > 1e-9:
                failures.append(
                    f"release ramp must land at tOff = tHoldEnd + rel "
                    f"({tl['tOff']:.3f} vs {tl['tHoldEnd'] + tl['rel']:.3f})")
            if abs(tl["stopAt"] - (tl["tOff"] + 0.06)) > 1e-9:
                failures.append(
                    f"stopAt must be exactly tOff + 0.06 s (invariant 6), got "
                    f"{tl['stopAt']:.3f}")
            if tl["tOff"] > tl["stopAt"]:
                failures.append("the release must never outlast stopAt")

            # --- tongued burst graph (Step 4 builder) ---
            tongue = graph["tongue"]
            if tongue["kind"] != "tongue":
                failures.append(f"tongue burst kind is {tongue['kind']!r}")
            if abs(tongue["formantHz"] - 1900) > 1e-3 or \
                    abs(tongue["formantQ"] - 4.2) > 1e-6:
                failures.append(
                    f"tongue burst must ride the Step-2 formant filter "
                    f"({tongue['formantHz']}/{tongue['formantQ']})")
            if abs((tongue["end"] - tongue["when"]) - 0.01) > 1e-9:
                failures.append(
                    f"tongue burst length must be ~10 ms, got "
                    f"{tongue['end'] - tongue['when']:.4f}s")

            # --- live breath on: one comb delay per note ---
            on_count = page.evaluate(DELAY_COUNT)
            if on_count < 1:
                failures.append(
                    f"a default note must build the comb delay (count {on_count})")

            # --- band-pass RMS normalization (air_db semantics) ---
            norm = page.evaluate(NORM_DRIVER)
            if abs(norm["plain"]) > 1.5:
                failures.append(
                    f"the plain band-pass must restore the fitted air_db level "
                    f"(got {norm['plain']:+.1f} dB)")
            if abs(norm["engine"]) > 6:
                failures.append(
                    f"the breath engine must stay within a sane trim of air_db "
                    f"(got {norm['engine']:+.1f} dB)")

            # --- debug panel switch ---
            page.goto(f"{base}?inst=oot-alto-c-12&debug=1")
            page.wait_for_function(WAIT)
            panel = page.evaluate(PANEL_DRIVER)
            if not panel["present"]:
                failures.append("the debug panel must carry the breath switch")
            elif not (panel["before"] is True and panel["after"] is False
                      and panel["restored"] is True):
                failures.append(
                    f"the breath switch must toggle the session flag "
                    f"({panel['before']} -> {panel['after']} -> {panel['restored']})")

            # --- ?breath=0 A/B: plain band-pass, no comb/AM, old chiff ---
            page_off = browser.new_page()
            page_off.on("pageerror", lambda e: errs.append(str(e)))
            page_off.goto(f"{base}?inst=oot-alto-c-12&breath=0")
            page_off.wait_for_function(WAIT)
            flag = page_off.evaluate("() => OCA_DEBUG.breathEnabled()")
            if flag is not False:
                failures.append(f"?breath=0 must start the engine off, got {flag!r}")
            off_count = page_off.evaluate(DELAY_COUNT)
            if off_count != 0:
                failures.append(
                    f"?breath=0 must not build a comb delay (count {off_count})")
            if plain["mode"] != "plain":
                failures.append(f"explicit breath:false mode is {plain['mode']!r}")
            if plain["formantHz"] is not None:
                failures.append("the plain A/B path must not build the formant peaker")
            if plain["delay"] is not None or plain["amFreq"] is not None:
                failures.append("the plain A/B path must not build comb/AM nodes")
            if not plain["chiff"]:
                failures.append("the plain A/B path must keep the legacy chiff burst")
            if abs(plain["airCenter"] - min(2400, max(800, 1.25 * 523.25))) > 1e-3:
                failures.append(
                    f"the plain A/B band-pass must sit at clamp(1.25*f0, lo, hi), "
                    f"got {plain['airCenter']}")

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
    print("\nPASS: the v4-breath engine builds pitch-locked comb/AM/formant "
          "noise, scales by open-hole venting, decorrelates its beds, keeps "
          "the attack/release on the existing timeline, falls back safely on "
          "a legacy twin model, and ?breath=0 keeps the plain band-pass path.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
