# tests/audio_state.py — the AudioContext lifecycle contract (R5):
# a mid-playback suspension must NOT leave the UI claiming playback while
# the audio clock is frozen: the transport flips to a clean paused state
# (pause semantics, not stop), and a gesture-time resume leaves the
# decision to the user (paused stays paused until Play).

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
BOOT_WAIT = ("typeof playMelody === 'function'"
             " && typeof stopMelody === 'function'"
             " && window.OCA_DEBUG")

SETUP_PLAY = """
() => {
  document.getElementById('src').value = '# probe\\n\\nC5/2 D5/2 E5/2';
  render();
  playMelody();
  return { playing: isMelodyPlaying(), paused: isMelodyPaused() };
}
"""

SUSPEND_MID = """
async () => {
  // External policy event analogue: the browser suspends the running
  // context under our feet (tab backgrounded, OS audio interruption).
  await audioCtx.suspend();
  // the statechange handler runs synchronously per event; give the
  // module a tick to settle its UI side.
  await new Promise(r => setTimeout(r, 300));
  return {
    ctxState: audioCtx.state,
    playing: isMelodyPlaying(),
    paused: isMelodyPaused(),
  };
}
"""

RESUME_LATER = """
async () => {
  await audioCtx.resume();
  await new Promise(r => setTimeout(r, 300));
  return {
    ctxState: audioCtx.state,
    // the user pressed nothing: the melody must NOT auto-restart itself
    // after the suspension is lifted.
    playing: isMelodyPlaying(),
    paused: isMelodyPaused(),
  };
}
"""


from suite_server import start_server


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=HEADLESS,
                args=["--autoplay-policy=no-user-gesture-required"])
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(BOOT_WAIT)
            s = page.evaluate(SETUP_PLAY)
            if not s["playing"]:
                failures.append(f"setup: melody should be playing, got {s!r}")
            m = page.evaluate(SUSPEND_MID)
            if m["ctxState"] != "suspended":
                failures.append(f"suspend: ctx state {m['ctxState']!r}")
            if not m["paused"]:
                failures.append(
                    "a mid-playback suspension must pause the transport "
                    f"(the UI must not claim playback against a frozen "
                    f"clock), got playing={m['playing']} "
                    f"paused={m['paused']}")
            r = page.evaluate(RESUME_LATER)
            if r["ctxState"] != "running":
                failures.append(f"resume: ctx state {r['ctxState']!r}")
            if r["playing"] or not r["paused"]:
                failures.append(
                    "returning the context to running must NOT silently "
                    f"restart playback (the user resumes), got {r!r}")
            # cleanup for a clean teardown: stop the (paused) melody
            page.evaluate("() => stopMelody()")
            page.wait_for_timeout(200)
            if errs:
                failures.append(f"page errors {errs}")
            page.close()
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: a mid-playback context suspension pauses the transport "
          "(the UI stops claiming playback over a frozen clock) and lifting "
          "the suspension does not silently restart the melody.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
