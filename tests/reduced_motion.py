#!/usr/bin/env python3
# OS-level motion gate: @media (prefers-reduced-motion: reduce) must switch
# off the decorative motion everywhere, not only the zen halo —
#   * .range-warn box-shadow pulse (dies; banner still marks the warning)
#   * .zen-wave screen sweep (keeps an opacity-only fade, no scale swell)
#   * .perf-btn.alerted infinite red pulse (dies; colour still marks it)
#   * zen focus-token scale swell (dies; the ring highlight stays)
# Asserts computed styles BOTH under the emulated reduce setting and in the
# default no-preference mode (so a future selector break can't pass while the
# animations silently vanish).
#
#   python3 tests/reduced_motion.py      # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
BOOT_WAIT = ("window.NOTES && window.NOTES.length"
             " && typeof parse === 'function'")

PROBE = """
() => {
  // Reproduce each animated selector's matched context with inert stand-ins;
  // the real elements are transient (warning banner, wave) or hold stateful
  // audio, which this probe does not need — computed styles of a clone with
  // the same class chain are identical.
  const host = document.getElementById('inputBlock').parentElement;
  const anchor = document.getElementById('inputBlock');
  const mk = (cls) => {
    const d = document.createElement('div');
    d.className = cls;
    anchor.insertAdjacentElement('afterend', d);
    return d;
  };
  const rangeWarn = mk('range-warn');
  const zenWave = mk('zen-wave');
  const perf = document.querySelector('.perf-btn');
  if (perf) perf.classList.add('alerted');
  // Match #tabPanel.focus .focus-tokens .tok.now
  const panel = document.getElementById('tabPanel');
  panel.classList.add('focus');
  const tokens = document.createElement('div');
  tokens.className = 'focus-tokens';
  const tok = document.createElement('div');
  tok.className = 'tok now';
  tokens.appendChild(tok);
  panel.appendChild(tokens);
  const cs = (el) => getComputedStyle(el);
  const out = {
    rangeWarnAnim: cs(rangeWarn).animationName,
    zenWaveAnim: cs(zenWave).animationName,
    perfAnim: perf ? cs(perf).animationName : null,
    tokTransform: cs(tok).transform,
    tokTransition: cs(tok).transitionDuration,
  };
  rangeWarn.remove(); zenWave.remove(); tokens.remove();
  panel.classList.remove('focus');
  if (perf) perf.classList.remove('alerted');
  return out;
}
"""


from suite_server import start_server


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            page = browser.new_page()
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            default = page.evaluate(PROBE)

            page.emulate_media(reduced_motion="reduce")
            reduced = page.evaluate(PROBE)

            # Controls: in the default mode the animations must still exist —
            # this pins the probes themselves against selector rot.
            if default["rangeWarnAnim"] != "rangeWarnPulse":
                failures.append(
                    f"default: .range-warn lost its pulse animation, got "
                    f"{default['rangeWarnAnim']!r}")
            if default["zenWaveAnim"] != "zen-wave":
                failures.append(
                    f"default: .zen-wave lost its sweep animation, got "
                    f"{default['zenWaveAnim']!r}")
            if default["perfAnim"] != "perfPulse":
                failures.append(
                    f"default: .perf-btn.alerted lost its pulse, got "
                    f"{default['perfAnim']!r}")
            if default["tokTransform"] == "none":
                failures.append(
                    "default: focus token swell (transform) missing — probe "
                    "selector broke")
            if default["tokTransition"] == "0s":
                failures.append(
                    "default: focus token transition missing — probe selector "
                    "broke")

            # The gate itself.
            if reduced["rangeWarnAnim"] != "none":
                failures.append(
                    f"reduce: .range-warn must stop pulsing, got "
                    f"{reduced['rangeWarnAnim']!r}")
            if reduced["zenWaveAnim"] != "zen-wave-reduce":
                failures.append(
                    f"reduce: .zen-wave must swap to the opacity-only "
                    f"keyframes, got {reduced['zenWaveAnim']!r}")
            if reduced["perfAnim"] != "none":
                failures.append(
                    f"reduce: .perf-btn.alerted must stop the infinite pulse, "
                    f"got {reduced['perfAnim']!r}")
            if reduced["tokTransform"] != "none":
                failures.append(
                    f"reduce: focus token must not swell (transform none), "
                    f"got {reduced['tokTransform']!r}")
            if reduced["tokTransition"] != "0s":
                failures.append(
                    f"reduce: focus token must not transition, got "
                    f"transition-duration {reduced['tokTransition']!r}")

            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: prefers-reduced-motion gates every decorative motion "
          "(range-warn pulse, zen wave, perf-alert pulse, token swell) "
          "while identical probes confirm the animations exist without it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
