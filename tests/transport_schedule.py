#!/usr/bin/env python3
# Transport contract suite (§6 T3): pins the melody scheduler's arithmetic and
# the melody cut-bus lifecycle against real WebAudio driving — the same
# in-page playNoteAt monkeypatch harness the support-bracket suite
# established.
#
#   1. scheduleMelody emits one playNoteAt call per sounding token, with the
#      gap between onsets equal to the swung steps the scheduler arithmetic
#      demands (recomputed from lastTokens with the app's own
#      swungBeats/quarterSecFor/soundingGridBeats primitives), staccato and
#      tie-chain durations exact, inline "# tempo" switches honored, the
#      melody position landing exactly on the integer 96th grid, and the
#      end-of-song auto-stop actually stopping.
#   2. A looping song replays the identical pitch/duration classes each wrap.
#   3. Cut buses: melody voices route through a cut bus generation; Stop cuts
#      as one event (generation retired, no zombies within the decay
#      horizon), and an instant replay builds a FRESH generation. Support
#      voices (bracket melody) die inside the same horizon.
#   4. Lite mode builds strictly less oscillator machinery than the full
#      voice for the same note (the skipped air/edge/wind/chiff/oct layers).
#   5. A named #track stream stays phase-locked to the melody clock across a
#      pause/resume: each track onset must still land on the melody's same-beat
#      onset after the resume (a rebase that collapses both streams' next notes
#      onto one anchor shifts the track by the beat gap and keeps it there).
#   6. The same lock survives an inline "# tempo" switch mid-song, including a
#      track block carrying its own (deliberately different) "# tempo" marker —
#      the melody's tempo line is authoritative for every stream.
#
#   python3 tests/transport_schedule.py      # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("window.NOTES && window.NOTES.length"
        " && typeof parse === 'function'")


from suite_server import start_server


# Types the melody, waits for ITS OWN title to be on the sheet (the boot tail
# can still re-render its song into the box right after load), starts real
# playback under a playNoteAt capture, and resolves when the scheduler stops.
CAPTURE_DRIVER = """
(SRC) => new Promise((resolve, reject) => {
  const notes = [];
  setNoteSink((id, when, dur) => notes.push({ id: id, when: when, dur: dur }));
  const title = String(SRC).split("\\n").find(l => /^#/.test(l)).replace(/^#\\s*/, "");
  document.getElementById('src').value = SRC;
  render();
  const t0 = Date.now();
  const arm = () => {
    if (document.getElementById('title').textContent !== title) {
      if (Date.now() - t0 > 4000) { reject(new Error("title never matched")); return; }
      setTimeout(arm, 30);
      return;
    }
    playMelody(0);
    const poll = setInterval(() => {
      if (!isMelodyPlaying() && !isMelodyPaused()) {
        clearInterval(poll);
        setNoteSink(null);
        setTimeout(() => resolve(notes), 150);
      }
    }, 50);
  };
  arm();
})
"""


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS,
                                        args=["--autoplay-policy=no-user-gesture-required"])
            errs = []
            page = browser.new_page()
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(WAIT)
            page.evaluate(
                "() => { const b = document.getElementById('playback');"
                " b.querySelector('.collapse-btn').click(); }")

            # ---------- 1: one-shot timing, durations, grid, auto-stop ----------
            print('== scheduler arithmetic leg', flush=True)
            MEL1 = ("# T3 timing\n"
                    "# tempo 96\n"
                    "# swing 33\n"
                    "| A4/2 -/2 D4/4 E4/4 F4/8t F4/8t G4/8t A4! r B4/2.\n"
                    "# tempo 120\n"
                    "| C5/1 C5/4 A5/4 E5/4")
            notes = page.evaluate(CAPTURE_DRIVER, MEL1)

            # Reference walk over the parsed tokens, mirroring scheduleMelody:
            # one step per melodic token, ties extend without re-sounding,
            # staccato tapers, inline tempo switches the quarter.
            ref = page.evaluate("""
              () => {
                const out = { events: [], pos: 0 };
                let quarter = quarterSec();      // header tempo (or 100)
                let holdUntil = -1;
                let pos = 0;
                for (let i = 0; i < lastTokens.length; i++) {
                  const t = lastTokens[i];
                  if (t.type === "tempo") { quarter = quarterSecFor(t.bpm); continue; }
                  if (t.type === "bar" || t.type === "bass") continue;
                  const pitched = (t.type === "note" || t.type === "tie") && NOTES.includes(t.id);
                  if (pitched && i > holdUntil) {
                    const hold = soundingGridBeats(lastTokens, i) * quarter;
                    const dur = t.staccato
                      ? Math.max(0.09, Math.min(hold * 0.4, 0.16))
                      : Math.max(0.09, hold * 0.92);
                    out.events.push({ tokIdx: i, id: t.id, dur: dur });
                    holdUntil = lastHoldIndex(lastTokens, i);
                  }
                  pos += Math.round(tokenGridBeats(t) * 96);
                }
                out.pos = pos;
                return out;
              }
            """)
            pos = page.evaluate(
                "() => ({ pos: OCA_DEBUG.melodyPos96(), playing: isMelodyPlaying() })")

            if pos["playing"]:
                failures.append("end-of-song auto-stop never happened")
            if pos["pos"] != ref["pos"]:
                failures.append(
                    f"melodyPos96 ended at {pos['pos']}, the reference walk "
                    f"sums {ref['pos']} — the position must consume every "
                    "melodic token exactly")
            if len(notes) != len(ref["events"]):
                failures.append(
                    f"captured {len(notes)} playNoteAt calls for "
                    f"{len(ref['events'])} expected sounding tokens: "
                    f"{[n['id'] for n in notes]}")
            else:
                for i, (got, want) in enumerate(zip(notes, ref["events"])):
                    if got["id"] != want["id"]:
                        failures.append(f"event {i}: {got['id']} != {want['id']}")
                    if abs(got["dur"] - want["dur"]) > 0.002:
                        failures.append(
                            f"event {i} ({got['id']}): dur {got['dur']:.4f} != "
                            f"{want['dur']:.4f} — staccato/tie-chain durations "
                            "are exact scheduler arithmetic")
                gaps = page.evaluate("""
                  (REF) => {
                    // For consecutive sounding tokens: sum the swung steps of
                    // every melodic token between them (earlier inclusive,
                    // later exclusive). Tempo tokens are zero-time but switch
                    // the quarter; every token steps at ITS OWN 96th-grid
                    // position — exactly what scheduleMelody does.
                    const sums = [];
                    for (let i = 1; i < REF.events.length; i++) {
                      let sum = 0;
                      for (let k = REF.events[i - 1].tokIdx; k < REF.events[i].tokIdx; k++) {
                        const t = lastTokens[k];
                        if (t.type === "tempo" || t.type === "bar" || t.type === "bass") continue;
                        let p = 0, q = quarterSec();
                        for (let j = 0; j < k; j++) {
                          const tj = lastTokens[j];
                          if (tj.type === "tempo") { q = quarterSecFor(tj.bpm); continue; }
                          if (tj.type === "bar" || tj.type === "bass") continue;
                          p += Math.round(tokenGridBeats(tj) * 96);
                        }
                        sum += swungBeats(t, p) * q;
                      }
                      sums.push(sum);
                    }
                    return sums;
                  }
                """, ref)
                for i, want in enumerate(gaps):
                    got = notes[i + 1]["when"] - notes[i]["when"]
                    if abs(got - want) > 0.05:
                        failures.append(
                            f"onset gap {i}->{i + 1}: scheduler {got:.3f}s != "
                            f"reference {want:.3f}s — absolute onsets must "
                            "reproduce the token walk exactly")

            # ---------- 2: loop wrap parity ----------
            print('== loop wrap leg', flush=True)
            MEL2 = "# T3 loop\n# tempo 96\n| A4/8 C5/8 D5/8 E5/8"
            lnotes = page.evaluate("""
              (SRC) => new Promise((resolve, reject) => {
                const notes = [];
                setNoteSink((id, when, dur) => notes.push({ id: id, when: when, dur: dur }));
                const title = String(SRC).split("\\n").find(l => /^#/.test(l)).replace(/^#\\s*/, "");
                document.getElementById('src').value = SRC;
                document.getElementById('loopMel').checked = true;
                render();
                const t0 = Date.now();
                const arm = () => {
                  if (document.getElementById('title').textContent !== title) {
                    if (Date.now() - t0 > 4000) { reject(new Error("loop: title never matched")); return; }
                    setTimeout(arm, 30);
                    return;
                  }
                  playMelody(0);
                  setTimeout(() => {
                    stopMelody();
                    document.getElementById('loopMel').checked = false;
                    setNoteSink(null);
                    setTimeout(() => resolve(notes), 120);
                  }, 3600);
                };
                arm();
              })
            """, MEL2)
            if len(lnotes) < 8:
                failures.append(
                    f"loop leg scheduled only {len(lnotes)} events — a 4-note "
                    "bar at 96 BPM within 3.6 s must wrap repeatedly")
            else:
                first = lnotes[:4]
                for k in range(4, len(lnotes) - 3, 4):
                    passn = lnotes[k:k + 4]
                    for n, want in enumerate(zip(first, passn)):
                        if want[0]["id"] != want[1]["id"] or \
                                abs(want[0]["dur"] - want[1]["dur"]) > 0.002:
                            failures.append(
                                "loop wraps must replay the identical "
                                f"pitch/duration class ({want[0]['id']} "
                                f"{want[0]['dur']:.3f}s vs {want[1]['id']} "
                                f"{want[1]['dur']:.3f}s at wrap {k // 4 + 1})")
                            break

            # ---------- 3: cut-bus lifecycle ----------
            print('== cut-bus lifecycle leg', flush=True)
            cut = page.evaluate("""
              () => new Promise((resolve, reject) => {
                const title = 'cutbus';
                document.getElementById('src').value = "# cutbus\\n\\nA4/2 C5/2 [E4]";
                render();
                const arm = () => {
                  if (document.getElementById('title').textContent !== title) {
                    setTimeout(arm, 25);
                    return;
                  }
                  playMelody(0);
                  setTimeout(() => {
                    const during = OCA_DEBUG.busAudit();
                    stopMelody();
                    setTimeout(() => {
                      const after = OCA_DEBUG.busAudit();
                      const aliveAfter = OCA_DEBUG.melodyAlive();
                      playMelody(0);   // instant replay
                      setTimeout(() => {
                        const replayAudit = OCA_DEBUG.busAudit();
                        const aliveReplay = OCA_DEBUG.melodyAlive();
                        stopMelody();
                        setTimeout(() => {
                          resolve({
                            during: during,
                            after: after, aliveAfter: aliveAfter,
                            replay: replayAudit, aliveReplay: aliveReplay,
                            dead: OCA_DEBUG.melodyAlive(),
                          });
                        }, 600);
                      }, 90);
                    }, 360);
                  }, 260);
                };
                arm();
              })
            """)
            if cut["during"]["cutBusCount"] < 1:
                failures.append("playing melody voices must route through a "
                                f"cut bus generation (audit: {cut['during']})")
            if cut["after"]["cutBusCount"] != 0:
                failures.append(
                    "Stop must retire the live generation "
                    f"(cutBusCount {cut['after']['cutBusCount']})")
            if cut["after"]["retiredCount"] < 1:
                failures.append("Stop must mark the old generation retired")
            if cut["aliveAfter"] != 0:
                failures.append(
                    "voices must be freed inside the decay horizon after "
                    f"Stop (alive {cut['aliveAfter']} at +0.36 s)")
            if cut["replay"]["cutBusCount"] < 1:
                failures.append("an instant replay must build a FRESH cut bus "
                                "generation")
            if cut["aliveReplay"] < 1:
                failures.append("the replay must have live voices")
            if cut["dead"] != 0:
                failures.append(f"the second stop must free all voices (alive "
                                f"{cut['dead']})")

            # ---------- 4: lite voice builds less machinery ----------
            print('== lite voice leg', flush=True)
            liteCounts = page.evaluate("""
              () => new Promise(resolve => {
                const countingRun = () => new Promise(done => {
                  let n = 0;
                  const ac = audioCtx || sharedAudioCtx();
                  const orig = ac.createOscillator;
                  ac.createOscillator = function () {
                    n++;
                    return orig.apply(this, arguments);
                  };
                  playNote("E5", 0.5);
                  setTimeout(() => { ac.createOscillator = orig; done(n); }, 300);
                });
                countingRun().then(full => {
                  document.getElementById('liteMel').checked = true;
                  setTimeout(() => {
                    countingRun().then(lite => {
                      document.getElementById('liteMel').checked = false;
                      resolve({ full: full, lite: lite });
                    });
                  }, 350);
                });
              })
            """)
            if liteCounts["full"] < 1:
                failures.append("the full voice must build oscillators")
            if liteCounts["lite"] < 1:
                failures.append("the lite voice must still build oscillators")
            if liteCounts["lite"] >= liteCounts["full"]:
                failures.append(
                    "the lite voice must skip air/edge/wind/chiff/oct three "
                    f"layers — full {liteCounts['full']}, lite "
                    f"{liteCounts['lite']} must be strictly less")

            # ---------- 5: named-track phase lock across pause/resume ----------
            print('== track phase lock across pause/resume', flush=True)
            # Melody rides the default ocarina's carve (A4–F6); the track
            # block may sit below it (tracks skip the range check by design).
            LOCK_SONG = ("# T3 lock\n"
                         "# tempo 96\n"
                         "| A4/4 C5/4 D5/4 E5/4\n"
                         "| F5/4 A5/4 C6/4 E6/4\n"
                         "| F5/4 G5/4 A5/4 B5/4\n"
                         "| C6/4 D6/4 E6/4 F6/4\n"
                         "#track support audible 50\n"
                         "| D4/2 D4/2\n"
                         "| E4/2 E4/2\n"
                         "| F4/2 F4/2\n"
                         "| G4/2 G4/2")
            lock = page.evaluate("""
              (SRC) => new Promise((resolve, reject) => {
                const notes = [];
                setNoteSink((id, when, dur, s, i, g) =>
                  notes.push({ id: id, when: when, g: g }));
                const title = String(SRC).split("\\n")[0].replace(/^#\\s*/, "");
                document.getElementById('src').value = SRC;
                render();
                const t0 = Date.now();
                const arm = () => {
                  if (document.getElementById('title').textContent !== title) {
                    if (Date.now() - t0 > 4000) { reject(new Error("lock: title never matched")); return; }
                    setTimeout(arm, 30); return;
                  }
                  playMelody(0);
                  const anchor = notes.find(n => n.g === 1).when;
                  const ctx = audioCtx;
                  const fire = () => {
                    if (ctx.currentTime >= anchor + 2.8) {
                      pauseMelody();
                      setTimeout(() => resumeMelody(), 400);
                    } else { setTimeout(fire, 15); }
                  };
                  fire();
                  const poll = setInterval(() => {
                    if (!isMelodyPlaying() && !isMelodyPaused()) {
                      clearInterval(poll);
                      setNoteSink(null);
                      setTimeout(() => resolve(notes), 150);
                    }
                  }, 50);
                };
                arm();
              })
            """, LOCK_SONG)
            mel = [n for n in lock if n["g"] == 1]
            trk = [n for n in lock if n["g"] == 0.5]
            if len(mel) != 16 or len(trk) != 8:
                failures.append(
                    f"lock leg: expected 16 melody + 8 track onsets, got "
                    f"{len(mel)} + {len(trk)}")
            else:
                if abs(trk[0]["when"] - mel[0]["when"]) > 0.01:
                    failures.append(
                        f"first track onset leads/lags the melody's first "
                        f"onset by {trk[0]['when'] - mel[0]['when']:+.3f}s — "
                        "both streams must leave the start anchor together")
                for m, t in enumerate(trk):
                    want = mel[2 * m]["when"]
                    if abs(t["when"] - want) > 0.06:
                        failures.append(
                            f"track note {m} (beat {2 * m}): onset "
                            f"{t['when'] - mel[0]['when']:.3f}s vs the "
                            f"melody's same-beat onset "
                            f"{want - mel[0]['when']:.3f}s — the named track "
                            f"must stay locked to the melody clock across the "
                            f"pause/resume (Δ {t['when'] - want:+.3f}s)")

            # ---------- 6: named-track phase lock across a tempo change ----------
            print('== track phase lock across a tempo change', flush=True)
            # Same in-range rule: the melody's # tempo line is the song's
            # clock; the track's own marker is deliberately different (60) —
            # the lock must follow the melody's line, not the track's.
            TEMPO_SONG = ("# T3 tempo lock\n"
                          "# tempo 96\n"
                          "| A4/4 C5/4 D5/4 E5/4\n"
                          "# tempo 120\n"
                          "| F5/4 G5/4 A5/4 B5/4\n"
                          "| C6/4 D6/4 E6/4 F6/4\n"
                          "| A5/4 B5/4 C6/4 D6/4\n"
                          "#track support audible 50\n"
                          "| D4/2 D4/2\n"
                          "# tempo 60\n"
                          "| E4/2 E4/2\n"
                          "| F4/2 F4/2\n"
                          "| G4/2 G4/2")
            tnotes = page.evaluate("""
              (SRC) => new Promise((resolve, reject) => {
                const notes = [];
                setNoteSink((id, when, dur, s, i, g) =>
                  notes.push({ id: id, when: when, g: g }));
                const title = String(SRC).split("\\n")[0].replace(/^#\\s*/, "");
                document.getElementById('src').value = SRC;
                render();
                const t0 = Date.now();
                const arm = () => {
                  if (document.getElementById('title').textContent !== title) {
                    if (Date.now() - t0 > 4000) { reject(new Error("tempo lock: title never matched")); return; }
                    setTimeout(arm, 30); return;
                  }
                  playMelody(0);
                  const poll = setInterval(() => {
                    if (!isMelodyPlaying() && !isMelodyPaused()) {
                      clearInterval(poll);
                      setNoteSink(null);
                      setTimeout(() => resolve(notes), 150);
                    }
                  }, 50);
                };
                arm();
              })
            """, TEMPO_SONG)
            mel2 = [n for n in tnotes if n["g"] == 1]
            trk2 = [n for n in tnotes if n["g"] == 0.5]
            if len(mel2) != 16 or len(trk2) != 8:
                failures.append(
                    f"tempo-lock leg: expected 16 melody + 8 track onsets, got "
                    f"{len(mel2)} + {len(trk2)}")
            else:
                if abs(trk2[0]["when"] - mel2[0]["when"]) > 0.01:
                    failures.append(
                        f"tempo lock: first track onset leads/lags the "
                        f"melody's first onset by "
                        f"{trk2[0]['when'] - mel2[0]['when']:+.3f}s")
                for m, t in enumerate(trk2):
                    want = mel2[2 * m]["when"]
                    if abs(t["when"] - want) > 0.06:
                        failures.append(
                            f"tempo lock: track note {m} (beat {2 * m}) at "
                            f"{t['when'] - mel2[0]['when']:.3f}s vs the "
                            f"melody's same-beat onset "
                            f"{want - mel2[0]['when']:.3f}s — the track must "
                            "follow the melody's tempo line, not its own "
                            f"marker (Δ {t['when'] - want:+.3f}s)")

            print('== closing browser', flush=True)
            if errs:
                failures.append(f"page errors {errs}")
            browser.close()
            print('== browser closed', flush=True)
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: scheduler arithmetic (events, durations, onset gaps, grid, "
          "auto-stop), loop-parity replay, cut-bus generation lifecycle with "
          "no zombies, the Lite voice leaves layers out of the build, and the "
          "named #track stream stays phase-locked to the melody clock across "
          "a pause/resume and a mid-song tempo change.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
