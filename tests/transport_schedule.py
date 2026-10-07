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
#   7. The lock also survives a LIVE tempo-dial move mid-song, fired exactly
#      when the melody's next onset sits on an odd half-beat (the worst case:
#      the streams' next onsets are a half-beat apart and the time gap between
#      them absorbs the speed change forever unless the dials re-sync the
#      tracks against the melody ledger).
#   8. ...and a LIVE swing move, fired at the same odd-half-beat phase (the
#      swung pair the two streams are mid-way through no longer sums to the
#      old beat unless the tracks re-derive from the melody's timeline).
#   9. ...and a pause/resume whose rebase gap STRADDLES an inline "# tempo"
#      marker: the track's next onset must be re-anchored by integrating the
#      tempo line across the gap, not by one quarter applied to the whole gap.
#      Each new leg pairs every track onset with the nearest melody onset and
#      asserts the delta stays under tolerance before AND after the
#      perturbation (the pre-bucket is the harness's own control).
#   10. A live tempo-dial move UP from the 10% floor is heard within the
#       scaled remainder of the MELODY's own pending onset, not one whole
#       stale slow step of mostly silence: the dial handlers must re-scale
#       melodyNextTime by the speed ratio (the resyncTrackTimes family,
#       aimed at the melody's own ledger this time).
#  11. Swung-pair conservation (Robin 2026-10-06): swing redistributes wall
#       time across the whole 96th grid, so bar-filled with 1/16 tails,
#       dotted values and mid-half 8ths must integrate the swung map piece
#       by piece — every bar's start stays k*4q of wall exactly.
#  12/13. Zen toggles under swing keep lock (Robin 2026-10-07): Zen entry
#       re-applies the dials through syncFocusMode -> applyTempoPct, whose
#       re-derivation of every #track ledger must reproduce the exact wall
#       value the walkers accumulate. The judgement is REAL TIME ONLY: each
#       captured support onset is paired to its nearest captured melody
#       onset and the pre/post delta pattern must not move. Leg 12 fires
#       gate-controlled toggles at the worst phase on a synthetic swung
#       pair; leg 13 reruns it on the shipped Storms melody+bass arrangement.
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


# Live-dial and rebase legs share this driver: type the song, arm on the
# typed song's own title, play, and fire the dial move only when the melody's
# NEXT unscheduled onset sits on an odd half-beat (melodyPos96 % 96 === 48,
# with the quarter-note track's next onset then a half-beat away — the
# nonzero-gap phase that makes a wall-clock parameter change land on the two
# ledgers at different moments). The dial is written through the real input
# element, so the app's own handler chain (applyTempoPct/applySwing +
# persistPlayHeaders) runs. Dials are reset for the following legs.
DIAL_DRIVER = """
(p) => new Promise((resolve, reject) => {
  const notes = [];
  let changeAt = 0;
  setNoteSink((id, when, dur, s, i, g) => notes.push({ id: id, when: when, g: g }));
  const title = String(p.song).split("\\n")[0].replace(/^#\\s*/, "");
  document.getElementById('src').value = p.song;
  render();
  const t0 = Date.now();
  const arm = () => {
    if (document.getElementById('title').textContent !== title) {
      if (Date.now() - t0 > 4000) { reject(new Error("dial: title never matched")); return; }
      setTimeout(arm, 30);
      return;
    }
    playMelody(0);
    const c0 = audioCtx.currentTime;
    const fire = () => {
      const cur = audioCtx.currentTime;
      if (!changeAt && cur > c0 + 1.2 && OCA_DEBUG.melodyPos96() % 96 === 48) {
        changeAt = cur;
        const d = document.getElementById(p.dial);
        d.value = p.value;
        d.dispatchEvent(new Event('input'));
      }
      if (!changeAt && cur > c0 + 60) { reject(new Error('dial: gate window missed')); return; }
      if (changeAt && cur >= changeAt + 4.2) {
        stopMelody();
        document.getElementById('tempo').value = '100';
        document.getElementById('tempo').dispatchEvent(new Event('input'));
        document.getElementById('swing').value = '0';
        document.getElementById('swing').dispatchEvent(new Event('input'));
        setNoteSink(null);
        setTimeout(() => {
          const mel = notes.filter(n => n.g === 1).sort((a, b) => a.when - b.when);
          const out = [];
          for (const n of notes.filter(n => n.g === 0.5)) {
            if (!mel.length) continue;
            let best = Infinity, sign = 0;
            for (const m of mel) best = Math.min(best, Math.abs(m.when - n.when));
            for (const m of mel) if (Math.abs(m.when - n.when) === best)
              sign = n.when - m.when;
            out.push({ d: sign, w: n.when });
          }
          resolve({
            pre: out.filter(x => x.w < changeAt - 0.4).map(x => x.d),
            post: out.filter(x => x.w >= changeAt + 0.8).map(x => x.d)
          });
        }, 150);
        return;
      }
      setTimeout(fire, 5);
    };
    fire();
  };
  arm();
})
"""

# Pause/resume leg: the marker song carries an inline '# tempo 120' at beat 8;
# the probe pauses exactly while the melody's NEXT unscheduled onset sits at
# beat 7.5 (melodyPos96 === 720), so the track's next onset (a quarter on the
# integer beat 8.0) makes the rebase gap [7.5, 8.0) cross the marker — the
# rebase must integrate the tempo line across the gap, not apply the
# marker-side quarter to the whole gap.
REBASE_DRIVER = """
(SRC) => new Promise((resolve, reject) => {
  const notes = [];
  setNoteSink((id, when, dur, s, i, g) => notes.push({ id: id, when: when, g: g }));
  const title = String(SRC).split("\\n")[0].replace(/^#\\s*/, "");
  document.getElementById('src').value = SRC;
  render();
  const t0 = Date.now();
  const arm = () => {
    if (document.getElementById('title').textContent !== title) {
      if (Date.now() - t0 > 4000) { reject(new Error("rebase: title never matched")); return; }
      setTimeout(arm, 30);
      return;
    }
    playMelody(0);
    const c0 = audioCtx.currentTime;
    const fire = () => {
      const cur = audioCtx.currentTime;
      if (cur > c0 + 3.9 && OCA_DEBUG.melodyPos96() === 720) {
        pauseMelody();
        setTimeout(() => {
          const split = audioCtx.currentTime;
          resumeMelody();
          setTimeout(() => {
            stopMelody();
            setNoteSink(null);
            setTimeout(() => {
              const mel = notes.filter(n => n.g === 1).sort((a, b) => a.when - b.when);
              const out = [];
              for (const n of notes.filter(n => n.g === 0.5)) {
                if (!mel.length) continue;
                let best = Infinity, sign = 0;
                for (const m of mel) best = Math.min(best, Math.abs(m.when - n.when));
                for (const m of mel) if (Math.abs(m.when - n.when) === best)
                  sign = n.when - m.when;
                out.push({ d: sign, w: n.when });
              }
              resolve({
                pre: out.filter(x => x.w < split - 0.4).map(x => x.d),
                post: out.filter(x => x.w >= split + 0.8).map(x => x.d)
              });
            }, 150);
          }, 3200);
        }, 500);
        return;
      }
      if (cur > c0 + 30) { reject(new Error('rebase: pause window missed')); return; }
      setTimeout(fire, 5);
    };
    fire();
  };
  arm();
})
"""

DIAL_SONG = ("# T3 dial\n"
             "# tempo 96\n"
             "# swing 0\n"
             "| C5/8 C5/8 D5/8 D5/8 E5/8 E5/8 F5/8 F5/8 |\n"
             "| G5/8 G5/8 A5/8 A5/8 B5/8 B5/8 C6/8 C6/8 |\n"
             "| D6/8 D6/8 C6/8 C6/8 B5/8 B5/8 A5/8 A5/8 |\n"
             "| G5/8 G5/8 F5/8 F5/8 E5/8 E5/8 D5/8 D5/8 |\n"
             "#track bass audible 50\n"
             "| E4/4 E4/4 G4/4 G4/4 |\n"
             "| A4/4 A4/4 G4/4 G4/4 |\n"
             "| E4/4 E4/4 G4/4 G4/4 |\n"
             "| A4/4 A4/4 G4/4 G4/4 |\n")

MARKER_SONG = ("# T3 rebase\n"
               "# tempo 96\n"
               "# swing 0\n"
               "| C5/8 C5/8 D5/8 D5/8 E5/8 E5/8 F5/8 F5/8 |\n"
               "| G5/8 G5/8 A5/8 A5/8 B5/8 B5/8 C6/8 C6/8 |\n"
               "# tempo 120\n"
               "| C6/8 C6/8 D6/8 D6/8 E6/8 E6/8 F6/8 G6/8 |\n"
               "| A5/8 A5/8 B5/8 B5/8 C5/8 C5/8 D5/8 E5/8 |\n"
               "#track bass audible 50\n"
               "| E4/4 G4/4 A4/4 G4/4 |\n"
               "| E4/4 G4/4 A4/4 G4/4 |\n"
               "| E4/4 G4/4 A4/4 G4/4 |\n"
               "| C4/4 E4/4 G4/4 E4/4 |\n")


def check_lock(failures, label, res, pre_tol=0.03, post_tol=0.02, min_post=2):
    """Assert the track stays on the melody clock across a perturbation:
    the pre-bucket is the harness's own control (locked before the move),
    the post-bucket must stay locked after it."""
    pre, post = res["pre"], res["post"]
    if len(post) < min_post:
        failures.append(f"{label}: post-bucket captured only {len(post)} "
                        f"track onsets, need >= {min_post}")
        return
    pre_max = max(abs(d) for d in pre) if pre else 0.0
    post_max = max(abs(d) for d in post)
    if pre_max > pre_tol:
        failures.append(
            f"{label}: pre-perturbation lock already broken "
            f"(max|Δ| {pre_max:.3f}s) — harness problem, not the change")
    if post_max > post_tol:
        failures.append(
            f"{label}: track drifts {post_max * 1000:.0f} ms off the melody "
            f"clock after the change (max|Δ| {post_max:.4f}s vs the "
            f"{post_tol * 1000:.0f} ms tolerance; pre-change max|Δ| was "
            f"{pre_max * 1000:.0f} ms)")


# Zen-toggle leg: toggles Zen in/out THROUGH the app's own fallback path
# (?nofs=1 body class + the same onZenChange sync) while a swung transport
# runs; the first toggle is fired at the worst phase (the melody's next onset
# on a beat start AND the track's next onset a half-beat inside it), then a
# fire of repeated toggles follows. The pairing judged is REAL TIME ONLY:
# every captured support onset is paired to the nearest captured melody
# onset, and the post-toggles delta pattern must equal the pre-toggle
# pattern (the streams' relative alignment is compared against itself across
# the whole session — no walker arithmetic is re-encoded anywhere).
ZEN_DRIVER = """
(p) => new Promise((resolve, reject) => {
  const notes = [];
  let fireAt = 0, toggles = 0, inside = false;
  setNoteSink((id, when, dur, s, i, g) => notes.push({ id: id, when: when, g: g }));
  const title = String(p.song).split("\\n")[0].replace(/^#\\s*/, "");
  document.getElementById('src').value = p.song;
  document.getElementById('loopMel').checked = true;
  const sw = document.getElementById('swing');
  sw.value = p.swing;
  sw.dispatchEvent(new Event('input'));
  render();
  const t0 = Date.now();
  const arm = () => {
    if (document.getElementById('title').textContent !== title) {
      if (Date.now() - t0 > 4000) { reject(new Error("zen: title never matched")); return; }
      setTimeout(arm, 30);
      return;
    }
    playMelody(0);
    const c0 = audioCtx.currentTime;
    // Perturbation phase gates (p.gate): the lead-side is "mod0" (the
    // melody's next onset on a beat start) or a fixed grid position; the
    // support-side likewise on ITS walker position; notCo keeps zero-width
    // intervals out (co-located pending onsets re-derive to no change) and
    // behind requires the support walker to sit BELOW the melody's position
    // (the interval then rides the melody's consumed tokens, where the
    // partial-span cases actually live).
    const gate = (g) => {
      const m = OCA_DEBUG.melodyPos96(), w = OCA_DEBUG.trackPos96(0);
      if (g.mel === "mod0" ? m % 96 !== 0 : m !== g.mel) return false;
      if (g.trk === "mod48" ? w % 96 !== 48
          : g.trk === "mod0" ? w % 96 !== 0 : w !== g.trk) return false;
      if (g.notCo && w === m) return false;
      if (g.behind && w >= m) return false;
      return true;
    };
    const gateHit = () => p.gate.some(gate);
    const fire = () => {
      const cur = audioCtx.currentTime;
      if (!fireAt && cur > c0 + p.lead && gateHit()) {
        fireAt = cur;
        inside = true;
        document.getElementById('zen').click();
      } else if (fireAt && toggles < p.toggles && cur > fireAt + toggles * p.every &&
                 (inside || gateHit())) {
        toggles++;
        inside = !inside;
        if (inside) document.getElementById('zen').click();
        else { document.body.classList.remove('zen-fallback');
               if (window.onZenChange) window.onZenChange(); }
      }
      if (!fireAt && cur > c0 + p.lead + 8) {
        reject(new Error('zen: gate phase never matched')); return;
      }
      if (fireAt && cur >= fireAt + 4.8) {
        const done = () => {
          stopMelody();
          document.getElementById('loopMel').checked = false;
          const keep = document.getElementById('swing');
          keep.value = '0';
          keep.dispatchEvent(new Event('input'));
          setNoteSink(null);
          setTimeout(() => {
            const mel = notes.filter(n => n.g === 1).sort((a, b) => a.when - b.when);
            const pair = (gs) => {
              const out = [];
              for (const n of notes.filter(n => gs.includes(n.g))) {
                if (!mel.length) continue;
                let best = Infinity, sign = 0;
                for (const m of mel) best = Math.min(best, Math.abs(m.when - n.when));
                for (const m of mel) if (Math.abs(m.when - n.when) === best)
                  sign = n.when - m.when;
                out.push({ d: sign, w: n.when });
              }
              return out;
            };
            resolve({
              fireAt: fireAt,
              streams: (p.support).map(g => pair([g])),
            });
          }, 150);
        };
        if (inside) {
          inside = false;
          document.body.classList.remove('zen-fallback');
          if (window.onZenChange) window.onZenChange();
          setTimeout(done, 120);
        } else done();
        return;
      }
      setTimeout(fire, 5);
    };
    fire();
  };
  arm();
})
"""

ZEN_SWING_SONG = ("# T3 zen swing\n"
                  "# tempo 96\n"
                  "| C5/4 C5/4 C5/4 C5/4 |\n"
                  "| D5/4 D5/4 D5/4 D5/4 |\n"
                  "#track bass audible 50\n"
                  "| E4/8 E4/8 G4/8 G4/8 A4/8 A4/8 G4/8 G4/8 |\n"
                  "| F4/8 F4/8 A4/8 A4/8 G4/8 G4/8 E4/8 E4/8 |\n")


def bucket_pairs(stream, fireAt):
    """Split a paired stream around the first toggle's wall time: the
    pre-bucket ends 0.4 s before it, the post-bucket starts 0.8 s after and
    ends 3.4 s after — inside the capture window, because the walkers
    schedule ~300 ms of lookahead: a track onset whose paired melody onset
    was never captured would pair to the PREVIOUS melody onset and fake a
    moved delta at the capture's cut-off."""
    return {"pre": [x["d"] for x in stream if x["w"] < fireAt - 0.4],
            "post": [x["d"] for x in stream
                     if fireAt + 0.8 <= x["w"] < fireAt + 3.4]}


def clusters_of(sorted_values, gap=0.05):
    out = []
    start = 0
    for i in range(1, len(sorted_values)):
        if sorted_values[i] - sorted_values[i - 1] > gap:
            out.append(sorted_values[start:i])
            start = i
    out.append(sorted_values[start:])
    return out


def check_pattern(failures, label, deltas, tol=0.02, min_pre=2, min_post=4):
    """Real-time alignment check across a perturbation: the support stream's
    nearest-melody-onset deltas before the perturbation are the control; after
    it, the delta PATTERN must be the same (the loop replays the same musical
    content, so a moved ledger shows up as a moved cluster). Both sides are
    clustered and compared by mutual coverage — pattern shape, not count."""
    pre = sorted(deltas["pre"])
    post = sorted(deltas["post"])
    if len(post) < min_post:
        failures.append(f"{label}: post-bucket captured only {len(post)} "
                        f"support onsets, need >= {min_post}")
        return
    # The control is the PRE pattern's own shape (under swing the support
    # onsets sit off the melody's neighbor onsets by fixed swung fractions;
    # those clusters are the real-time baseline): the pre deltas must form
    # stable clusters (the moving-ledger defect shifts every pre cluster).
    pre_clusters = clusters_of(pre)
    if len(pre_clusters) > 2 or any(max(c) - min(c) > 0.03 for c in pre_clusters):
        failures.append(
            f"{label}: pre-perturbation alignment is not a stable pattern "
            f"(clusters {[['%.3f' % d for d in c] for c in pre_clusters]}) — "
            "harness problem, not the change")
        return
    post_clusters = clusters_of(post)
    if len(pre) < min_pre:
        failures.append(f"{label}: pre-bucket captured only {len(pre)} "
                        f"support onsets, need >= {min_pre}")
        return
    # Mutual coverage: every pre cluster must survive into the post window
    # and every post cluster must trace back to a pre one.
    pre_centers = [sum(c) / len(c) for c in pre_clusters]
    post_centers = [sum(c) / len(c) for c in post_clusters]
    missed = []
    for c in pre_centers:
        if not post or min(abs(d - c) for d in post) > tol:
            missed.append(c)
    for c in post_centers:
        if not pre or min(abs(d - c) for d in pre) > tol:
            missed.append(c)
    if missed or len(pre_clusters) != len(post_clusters):
        failures.append(
            f"{label}: the support stream's alignment to the melody moved "
            f"across the toggles (pre clusters "
            f"{['%.3f' % c for c in pre_centers]}, post clusters "
            f"{['%.3f' % c for c in post_centers]}; unmatched "
            f"{['%.3f' % m for m in missed]} vs the {tol * 1000:.0f} ms "
            "tolerance)")


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

            # ---------- 7: live tempo-dial move mid-song ----------
            print('== track phase lock across a live tempo-dial move', flush=True)
            res = page.evaluate(DIAL_DRIVER, {"song": DIAL_SONG,
                                              "dial": "tempo", "value": "50"})
            check_lock(failures, "tempo-dial lock", res)

            # ---------- 8: live swing move mid-song ----------
            print('== track phase lock across a live swing move', flush=True)
            res = page.evaluate(DIAL_DRIVER, {"song": DIAL_SONG,
                                              "dial": "swing", "value": "100"})
            check_lock(failures, "swing lock", res)

            # ---------- 9: pause/resume rebase across an inline tempo marker ----------
            print('== track phase lock across a marker-straddling resume', flush=True)
            res = page.evaluate(REBASE_DRIVER, MARKER_SONG)
            check_lock(failures, "marker-rebase lock", res)

            # ---------- 10: melody pickup across a dial move up from the floor ----------
            print('== melody pickup across a dial move up from 10%', flush=True)
            # The dial starts at the 10% floor BEFORE playback, so one melody
            # step at these quarters is 6.25 s (0.625 s quarter / 0.1 speed):
            # when the dial jumps back to 100% at ~1.6 s the pending next
            # onset is frozen up to ~4.7 s out under the old schedule — the
            # stale silence of Robin's field report. The rebase must scale
            # that remainder by the speed ratio (10%→100% = one tenth), not
            # leave it to play out; the 100% regime must hold afterwards.
            RESP_SONG = ("# T3 dial pickup\n"
                         "# tempo 96\n"
                         "| C5/4 D5/4 E5/4 F5/4\n"
                         "| G5/4 A5/4 B5/4 C6/4")
            res = page.evaluate("""
              (SRC) => new Promise((resolve, reject) => {
                const notes = [];
                let changeAt = 0;
                setNoteSink((id, when, dur, s, i, g) =>
                  notes.push({ id: id, when: when, g: g }));
                const title = String(SRC).split("\\n")[0].replace(/^#\\s*/, "");
                document.getElementById('src').value = SRC;
                render();
                const t0 = Date.now();
                const arm = () => {
                  if (document.getElementById('title').textContent !== title) {
                    if (Date.now() - t0 > 4000) { reject(new Error("pickup: title never matched")); return; }
                    setTimeout(arm, 30);
                    return;
                  }
                  const d = document.getElementById('tempo');
                  d.value = '10';
                  d.dispatchEvent(new Event('input'));
                  playMelody(0);
                  const c0 = audioCtx.currentTime;
                  const fire = () => {
                    const cur = audioCtx.currentTime;
                    if (!changeAt && cur > c0 + 1.6) {
                      changeAt = cur;
                      d.value = '100';
                      d.dispatchEvent(new Event('input'));
                    }
                    if (!changeAt && cur > c0 + 12) { reject(new Error('pickup: move window missed')); return; }
                    if (!changeAt && cur > c0 + 40) { reject(new Error('pickup: never moved')); return; }
                    if (changeAt) {
                      // Collect on the song's own auto-stop: the whole
                      // schedule must complete in either regime, so the
                      // 8-onset count stays a pollution detector.
                      if (!isMelodyPlaying() && !isMelodyPaused()) {
                        d.value = '100';
                        d.dispatchEvent(new Event('input'));
                        setNoteSink(null);
                        setTimeout(() => resolve({
                          changeAt: changeAt,
                          notes: notes.filter(n => n.g === 1).sort((a, b) => a.when - b.when)
                        }), 150);
                        return;
                      }
                      if (cur > c0 + 40) { reject(new Error('pickup: never stopped')); return; }
                    }
                    setTimeout(fire, 5);
                  };
                  fire();
                };
                arm();
              })
            """, RESP_SONG)
            nn = res["notes"]
            if len(nn) != 8:
                failures.append(
                    f"dial-pickup leg: expected 8 melody onsets, got {len(nn)}")
            elif nn[1]["when"] < res["changeAt"]:
                failures.append(
                    f"dial-pickup leg: the second melody onset landed "
                    f"{res['changeAt'] - nn[1]['when']:.3f}s BEFORE the "
                    "move-window fired — the 10% floor did not pace the "
                    "pending step (or the move missed its window): harness "
                    "problem, not the change")
            else:
                lead = nn[1]["when"] - res["changeAt"]
                if lead > 0.9:
                    failures.append(
                        f"dial-pickup leg: the first onset after the move "
                        f"back to 100% landed {lead:.3f}s later (want ≤0.9s "
                        "— the stale low-dial step's remainder must be "
                        "re-scaled by the speed ratio, not left to play out)")
                elif lead < 0.02:
                    failures.append(
                        f"dial-pickup leg: the moved onset came {lead:.3f}s "
                        f"at/before the move itself — the rebase must keep "
                        "the scaled remainder, not jump the phase")
                bad = [b["when"] - a["when"] for a, b in zip(nn[1:], nn[2:])
                       if not (0.5 < b["when"] - a["when"] < 0.75)]
                if bad:
                    failures.append(
                        f"dial-pickup leg: post-move onset gaps {bad} — the "
                        "new 100% regime must hold at 0.625s steps after the "
                        "rebase")

            # ---------- 11: swung-pair conservation across non-8th bar fills ----------
            print('== swung-pair conservation (16th tails, dotted values, mid-half 8ths)', flush=True)
            # Swing only re-times EXACT half-beat tokens today, so whatever
            # else fills a swung pair (1/16 tails, dotted values, an 8th
            # starting mid-half at a 24-96th position) fails to absorb the
            # long/short redistribution: the pair's wall length lands off one
            # beat by s/6, every bar, ADDITIVE — Robin's field drift (the
            # Outset bar-3 1/16 tail runs long ~83 ms/bar, the Storms
            # dotted-quarter bar and the Saria mid-half beat run short).
            # Each leg song = one bar shape repeated 3x; every bar's start
            # must sit at start + k*4q under swing 100 (q = 0.5 at tempo 120).
            CONSERVE_LEG = """
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
                    if (Date.now() - t0 > 4000) { reject(new Error("conserve: title never matched")); return; }
                    setTimeout(arm, 30);
                    return;
                  }
                  const d = document.getElementById('swing');
                  d.value = '100';
                  d.dispatchEvent(new Event('input'));
                  playMelody(0);
                  const poll = setInterval(() => {
                    if (!isMelodyPlaying() && !isMelodyPaused()) {
                      clearInterval(poll);
                      setNoteSink(null);
                      const keep = document.getElementById('swing');
                      keep.value = '0';
                      keep.dispatchEvent(new Event('input'));
                      setTimeout(() => resolve(
                        notes.filter(n => n.g === 1).sort((a, b) => a.when - b.when)), 150);
                    }
                  }, 50);
                };
                arm();
              })
            """
            for tag, bar, stride, bar_beats in (
                ("16th-tail (Outset bar 3, shifted in-carve)",
                 "| B4/8 E5/8 B4/8 C5/8 Cs5/4 r/8 r/16 E5/16", 6, 4.0),
                ("dotted-quarter (Storms theme A bar 3)",
                 "| E6/4. F6/8 E6/8 F6/8", 4, 3.0),
                ("mid-half 8th (Saria theme line 4)",
                 "| B5/8 A5/8 C6/8 B5/8 D6/8 C6/8 E6/16 F6/8 D6/16", 9, 4.0)):
                song = (f"# T3 conserve\n# tempo 120\n"
                        + " ".join(bar for _ in range(3)) + " |")
                ons = page.evaluate(CONSERVE_LEG, song)
                need = stride * 3
                if len(ons) < need:
                    failures.append(
                        f"conserve {tag}: captured {len(ons)} melody onsets, "
                        f"need {need}")
                    continue
                bar0 = ons[0]["when"]
                for k in range(1, 3):
                    got = ons[stride * k]["when"] - bar0
                    want = k * bar_beats * 0.5
                    if abs(got - want) > 0.03:
                        failures.append(
                            f"conserve {tag}: bar {k + 1}'s start sits "
                            f"{got - want:+.4f}s off the conserved grid "
                            f"(onset {got:.4f}s vs wanted {want:.4f}s) — "
                            "the pair's non-half-beat contents must absorb "
                            "the swing redistribution so every bar stays "
                            f"exactly {want:.1f}s of wall regardless of the "
                            "widths filling it")

            # ---------- 12: zen-toggle rebase lock under swing ----------
            print('== track phase lock across zen toggles (swing 100)', flush=True)
            # Zen entry re-applies the PLAYBACK dials through syncFocusMode ->
            # applyTempoPct, which re-derives every #track ledger from the
            # melody's anchor even though nothing moved. Under swing > 0 the
            # wall-span estimate behind that re-derivation must be the TRUE
            # piecewise integral the walkers themselves accumulate — a uniform
            # rate assumed inside a melody token mis-times every rebase whose
            # interval ends mid-token, and the streams drift by up to q/6
            # (Robin's field report: toggle zen in/out repeatedly with swing
            # on and the lead/support pair leaves step for a moment, then
            # lines up again — the phase re-rolls per toggle).
            res = page.evaluate(ZEN_DRIVER, {
                "song": ZEN_SWING_SONG, "swing": "100",
                "lead": 1.0, "toggles": 5, "every": 0.55,
                "tracks": [0], "support": [0.5],
                "gate": [{"mel": "mod0", "trk": "mod48"}],
            })
            check_pattern(failures, "zen-toggle swing lock",
                          bucket_pairs(res["streams"][0], res["fireAt"]))

            # ---------- 13: same lock on the shipped Storms arrangement ----------
            print('== zen toggles on the shipped Storms melody + bass track', flush=True)
            # The field leg: Robin heard this on the Outset arrangement over
            # the triple bass; the shipped Storms bars carry the same real
            # mixed shape (dotted quarters over 8th vamps, 24-grid rest
            # offsets) on the stock alto at its own 160 tempo. Same driver,
            # same real-time lead-vs-support pairing, the shipped data only.
            STORMS_LEG = ("# T3 zen storms\n"
                          "# tempo 160\n"
                          "| D5/8 ~ F5/8 D6/2 |\n"
                          "| D5/8 ~ F5/8 D6/2 |\n"
                          "| E6/4. ~ F6/8 ~ E6/8 ~ F6/8 |\n"
                          "| ~ E6/8 C6/8 A5/2 |\n"
                          "#track bass audible 70\n"
                          "| r/4 A4 A4 |\n"
                          "| r/8 E4/8 B4/2 |\n"
                          "| r/4 C5 C5 |\n"
                          "| r/8 E4/8 B4/2 |\n")
            res = page.evaluate(ZEN_DRIVER, {
                "song": STORMS_LEG, "swing": "100",
                "lead": 1.0, "toggles": 5, "every": 0.55,
                "tracks": [0], "support": [0.7],
                # bar 3 opens on the dotted E6/4. — its [576,720) span makes
                # the melody walker sit at 720 only co-located with the bass
                # (both walkers' next onsets share walls on these bars); the
                # ONE divergent phase is the tick after their joint 576
                # consumption: melody pending F6/8 (720), the bass still
                # pending its first C5 (672) — the span integrator then
                # rides the consumed dotted's last third as a real partial.
                "gate": [{"mel": 720, "trk": "mod0", "notCo": True,
                          "behind": True}],
            })
            check_pattern(failures, "zen-toggle Storms lock",
                          bucket_pairs(res["streams"][0], res["fireAt"]))

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
              "no zombies, the Lite voice leaves layers out of the build, the "
              "named #track stream stays phase-locked to the melody clock across "
              "a pause/resume, a mid-song tempo-marker change, a live tempo-dial "
              "move, a live swing move and a marker-straddling resume, and the "
              "melody's own pending onset re-scales with a dial move up from "
              "the 10% floor so the pickup is heard within the remainder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
