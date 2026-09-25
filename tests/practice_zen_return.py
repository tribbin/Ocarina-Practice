#!/usr/bin/env python3
# Practice session keeps its seat across view-mode changes: while a practice
# session is running, the live tab's card must name the tone the tuner is
# CURRENTLY expecting — not the song's first note. A zen exit (mode falls
# back) and zen return (back to single) rebuilds the card between practice's
# own highlight calls; without practice-aware seeding the rebuild fell back
# to firstSoundIdx and displayed "start over" while P.idx stayed advanced.
#
# Two causes are pinned:
#   1. The rebuild seed: a zen exit/return (mode round-trip) rebuilds the
#      card between practice's highlight calls — the seed must come from the
#      active session, not firstSoundIdx.
#   2. Zen ENTRY's own stopMelody() (the ui-only zen sync calls it on entering
#      fullscreen with a live tab and no melody): its tail clears the
#      highlight and cues the FIRST note as playback's pickup position —
#      which must not stomp the vine of a RUNNING practice session. The
#      first-note cue is playback's semantics; practice owns the position.
#      (Only the real fullscreen path runs this call — headless zen falls
#      back to the CSS mode, so the leg drives stopMelody directly.)
#
#   python3 tests/practice_zen_return.py          # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
SONG = "# seat test\n# tempo 150\nC5/2 D5/2 E5/2 F5/2 G5/2"


from suite_server import start_server


SCROLL_DRIVER = """
(SRC) => new Promise((resolve, reject) => {
  const ta = document.getElementById('src');
  ta.value = SRC;
  render();
  const feed = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (P.state === "await" || P.state === "dip" || P.state === "rest" || !P.bar) {
      window.__pracFrame = { hz: 0, rms: 0 };
    } else {
      const k = P.zonesNear >= 0 ? P.zonesNear : 0;
      window.__pracFrame = { hz: P.bar.zones[k], rms: 0.4 };
    }
  }, 30);
  OCA_PRACTICE.start();
  let started = false;
  const poll = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (OCA_PRACTICE.active() && !P.paused) started = true;
    if (!started) return;
    if (P.idx >= 2) {
      // mid-song (third note's bar): exit the single view and come back
      setDisplayMode('scroll');          // the zen-exit fallback mode
      setDisplayMode('single');          // the zen return
      const card = document.querySelector('#sheet .card.live');
      const active = { card: card ? card.dataset.i : null,
                       spot: OCA_PRACTICE.spot(),
                       idx: P.idx };
      // with the session stopped, the first note owns the card again
      OCA_PRACTICE.stop();
      window.__pracFrame = { hz: 0, rms: 0 };
      setDisplayMode('scroll');
      setDisplayMode('single');
      const idleCard = document.querySelector('#sheet .card.live');
      clearInterval(feed); clearInterval(poll);
      resolve({ active: active,
                idleCard: idleCard ? idleCard.dataset.i : null });
      return;
    }
  }, 60);
  setTimeout(() => { clearInterval(feed); clearInterval(poll);
    OCA_PRACTICE.stop();
    reject(new Error('practice never reached the third note')); }, 20000);
})
"""

# Zen entry runs stopMelody() (its sync assumes a stray melody keeps ringing
# while the tab hides); the tail must not hand the card to playback's
# pickup-cue while practice is driving the position.
STOPMELODY_DRIVER = """
(SRC) => new Promise((resolve, reject) => {
  const ta = document.getElementById('src');
  ta.value = SRC;
  render();
  setDisplayMode('single');           // the zen view: the live tab owns the sheet
  const feed = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (P.state === "await" || P.state === "dip" || P.state === "rest" || !P.bar) {
      window.__pracFrame = { hz: 0, rms: 0 };
    } else {
      const k = P.zonesNear >= 0 ? P.zonesNear : 0;
      window.__pracFrame = { hz: P.bar.zones[k], rms: 0.4 };
    }
  }, 30);
  OCA_PRACTICE.start();
  let started = false;
  const poll = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (OCA_PRACTICE.active() && !P.paused) started = true;
    if (!started) return;
    if (P.idx >= 2) {
      stopMelody();                       // what zen entry does, verbatim
      const card = document.querySelector('#sheet .card.live');
      clearInterval(feed); clearInterval(poll);
      resolve({ card: card ? card.dataset.i : null,
                spot: OCA_PRACTICE.spot(), idx: P.idx });
      return;
    }
  }, 60);
  setTimeout(() => { clearInterval(feed); clearInterval(poll);
    OCA_PRACTICE.stop();
    reject(new Error('stopMelody leg: practice never reached the third note')); }, 20000);
})
"""


# Zen-only integration: the in-card tuner strip is ZEN's mechanic — the
# plain single view (outside fullscreen/fallback zen) keeps the floating
# overlay face instead of being absorbed into the card's meta band.
OVERLAY_LEG = """
(SRC) => new Promise((resolve, reject) => {
  document.getElementById('src').value = SRC;
  render();
  setDisplayMode('grid');
  OCA_PRACTICE.start();
  const t0 = Date.now();
  const feed = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (P.state === "await" || P.state === "dip" || P.state === "rest" || !P.bar) {
      window.__pracFrame = { hz: 0, rms: 0 };
    } else {
      const k = P.zonesNear >= 0 ? P.zonesNear : 0;
      window.__pracFrame = { hz: P.bar.zones[k], rms: 0.4 };
    }
  }, 30);
  const poll = setInterval(() => {
    const P = OCA_PRACTICE._p;
    if (!P.active) {
      if (Date.now() - t0 < 8000) return;
      clearInterval(poll); clearInterval(feed);
      reject(new Error('overlay: practice never engaged'));
      return;
    }
    setDisplayMode('single');        // the plain (non-zen) single view
    window.practiceRelocatePanel();
    const panel = document.querySelector('.prac-panel');
    const hostOf = () => panel.parentElement === document.body ? 'body'
      : panel.parentElement ? panel.parentElement.className : null;
    const plain = { inCard: panel.classList.contains('in-card'),
                    host: hostOf(),
                    hidden: panel.hidden };
    document.body.classList.add('zen-fallback');   // CSS fallback zen
    window.practiceRelocatePanel();
    const zenfb = { inCard: panel.classList.contains('in-card'),
                    host: hostOf(),
                    hidden: panel.hidden };
    document.body.classList.remove('zen-fallback'); // back out of zen
    window.practiceRelocatePanel();
    const back = { inCard: panel.classList.contains('in-card'),
                   host: hostOf(),
                   hidden: panel.hidden };
    clearInterval(feed); clearInterval(poll); OCA_PRACTICE.stop();
    resolve({ plain, zenfb, back });
  }, 80);
  setTimeout(() => { clearInterval(feed); clearInterval(poll);
    OCA_PRACTICE.stop();
    reject(new Error('overlay: timeout')); }, 20000);
})
"""


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)

            # ---- leg 1: the rebuild seed (zen exit/return round-trip) ----
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base + "?practiceTest=1")
            page.wait_for_function(
                "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                " && window.NOTES && window.NOTES.length"
                " && (function () { const s ="
                " document.getElementById('scale');"
                " return s && s.options.length > 0; })()")
            r = page.evaluate(SCROLL_DRIVER, SONG)
            page.close()
            print(f"== mode round-trip: {r['active']!r}  idle card: {r['idleCard']!r}", flush=True)
            card = r["active"]["card"]
            spot = r["active"]["spot"]
            if card is None:
                failures.append("round-trip: no live card after the mode flip")
            elif r["active"]["idx"] < 2:
                failures.append(f"round-trip: practice never advanced (idx {r['active']['idx']})")
            elif card != str(spot):
                failures.append(
                    f"round-trip: the rebuilt card shows token {card!r} while the tuner "
                    f"expects token {spot!r} — a mid-song session must keep its seat "
                    "across a zen exit/return")
            elif r["idleCard"] not in (None, "0", str(spot)):
                failures.append(
                    f"round-trip: with practice stopped the card should name the song's "
                    f"first note, got {r['idleCard']!r}")
            if errs:
                failures.append(f"round-trip: page errors {errs}")

            # ---- leg 2: zen entry's stopMelody must not re-cue the pickup ----
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base + "?practiceTest=1")
            page.wait_for_function(
                "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                " && window.NOTES && window.NOTES.length"
                " && (function () { const s ="
                " document.getElementById('scale');"
                " return s && s.options.length > 0; })()")
            r = page.evaluate(STOPMELODY_DRIVER, SONG)
            page.close()
            print(f"== stopMelody during practice: {r!r}", flush=True)
            if errs:
                failures.append(f"stopMelody leg: page errors {errs}")
            if r["idx"] < 2:
                failures.append(f"stopMelody leg: practice never advanced (idx {r['idx']})")
            elif r["card"] != str(r["spot"]):
                failures.append(
                    f"stopMelody leg: the card shows token {r['card']!r} while the "
                    f"tuner expects {r['spot']!r} — zen entry's stopMelody tail "
                    "re-cued playback's pickup note over the running practice seat")

            # ---- leg 3: the card-band tuner is zen-only in plain single ----
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base + "?practiceTest=1")
            page.wait_for_function(
                "typeof OCA_PRACTICE !== 'undefined' && !!OCA_PRACTICE"
                " && window.NOTES && window.NOTES.length"
                " && (function () { const s ="
                " document.getElementById('scale');"
                " return s && s.options.length > 0; })()")
            r = page.evaluate(OVERLAY_LEG, SONG)
            page.close()
            print(f"== overlay seats: {r!r}", flush=True)
            if errs:
                failures.append(f"overlay leg: page errors {errs}")
            if not r["plain"]:
                failures.append("overlay leg: no panel found")
            else:
                if r["plain"]["inCard"]:
                    failures.append(
                        f"overlay leg: in the plain single view the tuner absorbed "
                        f"into the card band (in-card, host {r['plain']['host']!r}) "
                        "— outside Zen it must keep the floating overlay face")
                if r["plain"]["host"] != "body":
                    failures.append(
                        f"overlay leg: the plain single view hosts the overlay on "
                        f"{r['plain']['host']!r}, not the body-level float")
                if r["plain"]["hidden"]:
                    failures.append("overlay leg: the plain single view hid the tuner")
            if not r["zenfb"] or not r["zenfb"]["inCard"]:
                failures.append("overlay leg: the CSS fallback zen lost the in-card integration")
            if not r["back"] or r["back"]["inCard"] or r["back"]["hidden"]:
                failures.append(f"overlay leg: leaving zen did not restore the floating overlay ({r.get('back')!r})")
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: an active practice session owns the live card across view "
          "rebuilds AND across zen entry's stopMelody pickup-cue; a stopped "
          "session falls back to the first note as always.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
