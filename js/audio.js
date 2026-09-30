import { parse } from "./parse.js";
import { currentSwing, tempoPct } from "./library.js";
import { freqOf, quarterSecFor, tokenGridBeats } from "./music-math.js";
import { bumpHoverQuiet, clearHighlight, cueFirstNote, freezeZenGlow,
         highlightToken, isFocusMode, quarterSec, tokenSeconds, updateTransportUI } from "./ui.js";
import { isPracticeActive } from "./practice.js";
import { wakeHold, wakeDrop } from "./wakelock.js";
import { loadTwinModelFromObject, interpNote, scheduleHelmholtzNote, VOICE_REV } from "./helmholtz-voice.js?v=3";
let audioCtx = null;
let liveVoices = [];
let melodyBag = [];
// Ledger of site-MADE sound (synth voices, ticks, previews, leftovers of a
// cut): the latest absolute ctx time any of it can still ring, so practice
// can deafen itself instead of registering the speakers as an ocarina.
let sysSoundUntil = 0;
function markSystemSound(t) { if (t > sysSoundUntil) sysSoundUntil = t; }
function sysSoundUntilSec() { return sysSoundUntil; }
let melodyTimer = 0;
let melodyPlaying = false;
let melodyTokens = [];
let melodyIdx = 0;
let melodyFrom = 0;
// Melody position on the NOTATION grid, in integer 96ths of a beat (96 divides
// every duration the parser emits: dyadic values, dots and triplets). Compare
// via beat integer, never via accumulated float: triplet-flavored ulps would
// drift the swing-parity sample off the beat over long songs.
let melodyPos96 = 0;
let melodyHoldUntil = -1;
let melodyPaused = false;
let melodyNextTime = 0; // absolute ctx time of the next note to schedule
// The song's tempo line: [pos96, quarter] pairs in beat order. The melody
// owns the clock — every stream looks up the quarter at its OWN position
// instead of mutating one shared value. A shared mutable quarter let each
// walker's "# tempo" token own the switch for its tick (the track walker
// runs first, so its marker could re-time the melody and vice versa), and a
// pause/restart re-anchored nobody's clock, so the streams drifted apart.
let tempoLine = null;
let lastHoldSec = 0.5; // sounding duration of the last scheduled note (for zen glow)

// ---- Dev-tunable synthesis parameters -------------------------------------
// The defaults are exactly the values that used to be hardcoded throughout
// this file. The dev panel (js/debug.js — enable with `DEBUG=1` in the
// console) mutates these live and persists them to localStorage, so
// synthesis code must READ these values per note — never bake them into a
// closure or a cached node at build time.
const AUDIO_DEFAULTS = {
  // Twin-voice retunes (js/helmholtz-voice.js). Wander/wobble scale the
  // model's own rows (1 = the fit). Vibrato is Zen-only.
  wanderAmt: 1, wobbleAmt: 1,
  hiFrom: 660, hiTo: 1568,
  vibRate: 5.5, vibDepth: 0.0035, vibHighFade: 0.4, tremDepth: 0.05,
  vibDelay: 0.35,
  zenPan: 0.9,
  slideTapMs: 0.03,
  masterLevel: 0.40,
  supportLevel: 1,
  instOotDb: 0,
  instSteinDb: 0,
  instOakDb: 0,
  instContraDb: 0,
  instDummyDb: 0,
  reverbWet: 0.20,
  tuneCents: 20, transientCents: 60, transientMs: 150,
  gapMs: 120, rmsGate: 0.01, chainTravelMs: 800,
  dipMs: 60, dipFrac: 0.5,
};
const AUDIO_DEBUG = Object.assign({}, AUDIO_DEFAULTS);
// Voice builders (playNoteAt/playTickAt) swallow any WebAudio failure so a
// bad synth call can never break the page — but an ocarina that silently
// plays nothing is the worst failure mode for a practice tool. Record
// count + site + cause; the debug panel surfaces it via OCA_DEBUG.voiceErrors().
let voiceErrorCount = 0, lastVoiceError = "", voiceWarnAt = 0;
function recordVoiceError(site, e) {
  voiceErrorCount++;
  lastVoiceError = site + ": " + (e && e.message ? e.message : String(e));
  const now = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
  if (now - voiceWarnAt > 1000) {   // at most one console line per second
    voiceWarnAt = now;
    try { console.warn("[audio] voice build failed: " + lastVoiceError); } catch (err) {}
  }
}
// resume() rejects under autoplay policy (no user gesture yet); never let
// that surface as an unhandled-rejection error — the next real gesture
// retries via unlockAudio.
function safeResume(ctx) {
  try {
    if (!ctx || ctx.state !== "suspended") return;
    const p = ctx.resume();
    if (p && p.catch) p.catch(() => {});
  } catch (e) {}
}

// Autoplay policy/OS routing can suspend a RUNNING context mid-session
// (tab backgrounded on phones, audio-endpoint takeover): the audio clock
// freezes while the scheduler keeps timing against it and the UI would
// keep claiming playback over silence. Mark the ctx once and watch it:
// a suspension pauses the transport cleanly (grid position preserved, a
// later Play resumes from the frozen beat); the context returning to
// running NEVER restarts the melody by itself — the user resumes.
function attachCtxStateWatch(ctx) {
  if (!ctx || ctx.__stateWatched) return ctx;
  ctx.__stateWatched = true;
  try {
    ctx.addEventListener("statechange", () => {
      if (ctx.state === "suspended" && melodyPlaying && !melodyPaused) {
        pauseMelody();
      }
    });
  } catch (e) {}
  return ctx;
}
// Exposed for the dev panel: params are tweaked in place; invalidateWave()
// drops the cached PeriodicWave so the next note rebuilds it from the
// current harmonic amplitudes.
window.OCA_DEBUG = {
  params: AUDIO_DEBUG,
  defaults: AUDIO_DEFAULTS,
  invalidateWave() {},
  // The instrument-loudness dial's read side (suites + dev panel): the
  // linear factor the currently loaded instrument contributes.
  instLevelGain() { return instLevelGain(); },
  voiceErrors() { return { count: voiceErrorCount, last: lastVoiceError }; },
  clearVoiceErrors() { voiceErrorCount = 0; lastVoiceError = ""; },
  // Alive hover/piano voices right now (debug panel + tests expose how much
  // audio machinery a stray script is building).
  liveVoiceCount() { return countAliveVoices(liveVoices); },
  // "none" / "suspended" / "running" — the autoplay-policy state of the ctx.
  audioState() { return audioCtx ? audioCtx.state : "none"; },
  // Melody position on the scheduler's integer 96th-of-a-beat grid — the
  // swing parity reads it; suites pin that the integer grid is held exactly.
  melodyPos96() { return melodyPos96; },
  // Transport diagnostics (suites + dev panel): how many melody-bag voices
  // are alive right now and how many cut bus generations exist / were cut.
  melodyAlive() { return countAliveVoices(melodyBag); },
  busAudit() { return { cutBusCount: cutBuses.size, retiredCount: retiredBuses.length }; },
  // Spike watch (the single-frame "tick" hunt): the pure classifier pinned
  // by the suites, the recent state cards, and a synthetic entry so the
  // perf-panel row can be probed without waiting for a real tick.
  spikeClassify(win) { return spikeClassify(win); },
  spikeWatch() { return perf.spikeLog.slice(); },
  spikeCount() { return perf.spikes; },
  spikeFake() {
    perf.spikes++;
    perf.spikeLog.push({ fake: true, t: audioCtx ? audioCtx.currentTime : -1,
                         jump: 1, lite: liteMode(), onsets: [],
                         ambient: ambientContext(performance.now()) });
    if (perf.spikeLog.length > 24) perf.spikeLog.shift();
  },
  // The installed Helmholtz twin model (instruments/<id>/twin_model.json) —
  // null while no twin model is installed for the CURRENT instrument.
  twinModel() { return TWIN_MODEL; },
  // Running voice identity: the module stamp + whether a twin is installed
  // + whether a service worker is controlling this page. Typed in the
  // console as OCA_DEBUG.voiceCard() when the preview and the site disagree.
  voiceRev() { return VOICE_REV; },
  voiceCard() {
    const tm = TWIN_MODEL;
    let sw = "none";
    try {
      if (navigator.serviceWorker && navigator.serviceWorker.controller) {
        sw = navigator.serviceWorker.controller.scriptURL;
      }
    } catch (e) {}
    const inst = (typeof window !== "undefined") ? window.CURRENT_INSTRUMENT : null;
    const notes = (typeof window !== "undefined" && window.NOTES) ? window.NOTES : [];
    const chMap = (typeof window !== "undefined") ? window.CHAMBER : null;
    return {
      rev: VOICE_REV,
      protocol: typeof location !== "undefined" ? location.protocol : "",
      twin: tm ? tm.instrumentId : null,
      chambers: tm ? Object.keys(tm.chambers || {}) : [],
      chart: inst ? inst.id : null,
      range: notes.length ? [notes[0], notes[notes.length - 1]] : [],
      f6: chMap && chMap.F6 != null ? chMap.F6 : null,
      mismatch: !!(tm && inst && tm.instrumentId !== inst.id),
      sw,
    };
  },
  // DEBUG panel "Induce lag": fakes audio-clock starvation. Seeds what
  // raisePerfAlert needs (a running ctx + one alive voice, the button click
  // itself is the user gesture), then loads the lag budget; the next
  // watchdog tick (<0.5 s) consumes it — the exact path real starvation
  // takes: glitch counter + Lite proposal.
  simulateLag() {
    try {
      unlockAudio();
      const notes = window.NOTES || [];
      if (!countAliveVoices(melodyBag) && !liveVoices.length)
        playNote(notes[Math.floor(notes.length / 2)] || "C5", 0.9);
      perf.lag = 1;
    } catch (e) {}
  },
  // ms until the 15 s alert throttle releases (0 = next raise goes through).
  alertThrottleLeftMs() {
    return Math.max(0, perfLastAlert + 15000 - performance.now());
  },
};

function syncTransport() {
  if (typeof updateTransportUI === "function") updateTransportUI();
}

// Seconds per quarter note at the song's own 100% tempo for a given bpm
// (the song's leading header or any inline "# tempo N" change). The tempo
// slider is a RELATIVE playback speed (10–100%) applied at scheduling time
// (see quarterAt uses in scheduleMelody), so it must not bake in here.
// Relative playback speed from the tempo slider (0.1–1 of the song tempo).
// Guarded: audio.js also runs in tooling without the library/UI scripts.
function tempoSpeed() {
  if (typeof tempoPct !== "function") return 1;
  return Math.max(0.1, Math.min(1, (tempoPct() || 100) / 100));
}

// One [pos96, quarter] entry at every inline "# tempo" position of the
// melody's tokens: pos96 is the 96th-grid position where the new quarter
// takes effect (the step of the first musical token AFTER the marker uses
// it), matching the scheduler's consumption order. A track block's own
// "# tempo" line, if ever written, is transparent to the shared clock —
// the melody's tempo line is the song's one clock.
function buildTempoLine(tokens) {
  const line = [];
  let pos = 0; // 96ths, the same grid the walkers advance
  for (const t of tokens) {
    if (t.type === "tempo") { line.push([pos, quarterSecFor(t.bpm)]); continue; }
    if (t.type === "bar" || t.type === "bass") continue;
    pos += Math.round(tokenGridBeats(t) * 96);
  }
  return line;
}

// Seconds per quarter at 100% speed for a beat position on the melody's
// tempo line — the single clock source for the melody, the named #track
// streams and the support plan. Header quarter until the first marker; at a
// loop wrap the position returns to 0 and the header quarter applies again.
function quarterAt(pos96) {
  let q = quarterSec();
  for (const [p, qq] of tempoLine) {
    if (p <= pos96) q = qq; else break;
  }
  return q;
}

// tokenGridBeats and quarterSecFor ride the music-math import — the
// binding names keep the windowed compat surface and the ESM export list.

function soundingGridBeats(tokens, idx) {
  let p = tokenGridBeats(tokens[idx]);
  for (let i = idx + 1; i < tokens.length; i++) {
    if (tokens[i].type === "bar" || tokens[i].type === "tempo" || tokens[i].type === "bass") continue;
    if (tokens[i].type === "tie") p += tokenGridBeats(tokens[i]);
    else break;
  }
  return p;
}

function lastHoldIndex(tokens, idx) {
  let last = idx;
  for (let i = idx + 1; i < tokens.length; i++) {
    if (tokens[i].type === "bar" || tokens[i].type === "tempo" || tokens[i].type === "bass") continue;
    if (tokens[i].type === "tie") last = i;
    else break;
  }
  return last;
}

// Does the bar starting at `idx` have a sounding token at its start? Used to
// gate the metronome tick. Genuinely empty bars — a trailing pause of whole
// rests — stay quiet, since a lone downbeat click there sounds odd. But a tie
// token means the previous note is being HELD across the downbeat
// ("G4/1 | -/1 | A4/1"): one connected sound spans the bar line, time keeps
// passing, so the click must keep counting those bars too.
function barHasNote(tokens, idx) {
  for (let i = idx; i < tokens.length; i++) {
    if (tokens[i].type === "bar") return false;
    if (tokens[i].type === "bass") continue; // hidden support marker: transparent
    if (tokens[i].type === "note") return true;
    if (tokens[i].type === "tie" && NOTES.includes(tokens[i].id)) return true;
  }
  return false;
}

function swungBeats(tok, pos96) {
  const beats = tokenGridBeats(tok);
  const s = (typeof currentSwing === "function" ? currentSwing() : 0) / 100;
  if (s <= 0 || Math.abs(beats - 0.5) > 1e-6) return beats;
  const longF = 0.5 + s / 6;
  // pos96 IS the beat position (integer 96ths): half-beats are exact multiples
  // of 48, so the parity test needs no rounding tolerance at all.
  const onBeat = Math.round(pos96 / 48) % 2 === 0;
  return onBeat ? longF : 1 - longF;
}

function gridBeatsBefore(tokens, idx) {
  let p = 0;
  for (let i = 0; i < idx; i++) p += tokenGridBeats(tokens[i]);
  return p;
}

let reverbBus = null;   // input node that notes connect to (dry + wet split)
let reverbWetGain = null;
let reverbEnabled = false;
// Canonical "on" wet level lives in AUDIO_DEBUG.reverbWet (dev-tunable).

function makeReverbImpulse(ctx, seconds, decay) {
  const rate = ctx.sampleRate;
  const len = Math.floor(rate * seconds);
  const buf = ctx.createBuffer(2, len, rate);
  for (let ch = 0; ch < 2; ch++) {
    const d = buf.getChannelData(ch);
    for (let i = 0; i < len; i++) {
      d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
    }
  }
  return buf;
}

// ---------------------------------------------------------------------------
// PERFORMANCE / HEADROOM METERS — diagnostics for the phone "clipping" (see
// the perf dropdown in ui.js). The bus wiring below is deliberately STATIC:
// the convolver stays in the graph even at wet = 0, because connect/
// disconnect switching of the reverb mid-playback is believed to cause
// audible cut-outs — Lite voice is the supported path on slow devices
// instead. The meters exist to SEE the cost: output peak → headroom, how
// hard the output limiter is working, audio-clock stalls (underruns).
// ---------------------------------------------------------------------------
const perf = {
  wallBase: null, clockBase: null,
  glitches: 0,   // audio clock lagged the wall clock by >0.25 s in one window
  jumps: 0,      // audio clock suddenly leapt forward (context restart)
  lag: 0,        // cumulative audio-clock lag budget (s) — sees slow/mild
                 // starvation the per-window stall threshold misses (an
                 // underrun blanks buffer chunks while the clock keeps
                 // moving, so "stalls" can read 0 while clicks are audible)
  sessionPeak: 0, // max |sample| at the output since the last reset
  snapBuf: null,
  spikes: 0,     // single-frame waveform steps (spike watch, see below)
  spikeLog: [],  // recent spike state cards (cap 24)
  spikeBuf: null,
};
let perfAnalyser = null;
let perfComps = [];   // the buses' DynamicsCompressors, for .reduction reads
let perfAlertListener = null;
let perfLastAlert = -15000; // ms; first alert is never throttled

// The UI registers a callback (ui.js: perfAlert) that gets called when a
// glitch is suspected — it pulses the perf button and proposes Lite mode.
function setPerfAlertListener(fn) { perfAlertListener = fn; }

function raisePerfAlert() {
  if (!perfAlertListener) return;
  const now = performance.now();
  if (now - perfLastAlert < 15000) return; // throttle: one toast per 15 s max
  if (countAliveVoices(melodyBag) < 1 && liveVoices.length < 1) return;
  perfLastAlert = now;
  try { perfAlertListener(); } catch (e) {}
}

// Voices that still have scheduled content ahead (bag entries prune
// themselves once their `until` is past — see pruneBag).
function countAliveVoices(bag) {
  if (!audioCtx || !bag) return 0;
  const now = audioCtx.currentTime;
  let v = 0;
  for (let i = 0; i < bag.length; i++) {
    const n = bag[i];
    if (n && (n.until == null || n.until > now)) v++;
  }
  return v;
}

function getPerfTap(ctx) {
  if (perfAnalyser && perfAnalyser.context === ctx) return perfAnalyser;
  perfAnalyser = ctx.createAnalyser();
  perfAnalyser.fftSize = 1024;
  return perfAnalyser; // metering only — never connected to the destination
}

// Watchdog: the audio clock normally tracks (even slightly leads) the wall
// clock while streaming; a large deficit means the audio thread starved.
setInterval(() => {
  if (!audioCtx || audioCtx.state !== "running") { perf.wallBase = null; return; }
  const wall = performance.now() / 1000, clock = audioCtx.currentTime;
  if (perf.wallBase != null) {
    const dWall = wall - perf.wallBase, dClock = clock - perf.clockBase;
    if (dWall > 0.3 && dClock < dWall - 0.25) { perf.glitches++; raisePerfAlert(); }
    else if (dClock > dWall + 0.3) perf.jumps++;
    // Cumulative lag budget: lends credibility to mild, continuous
    // starvation (e.g. phones) that never lags one window by 0.25 s. Behind
    // by >50 ms per window accumulates; caught up time pays back.
    if (dClock - dWall < -0.05) perf.lag += (dWall - dClock) - 0.05;
    else if (dClock - dWall > 0.05) perf.lag = Math.max(0, perf.lag - ((dClock - dWall) - 0.05));
    if (perf.lag > 0.12) {
      perf.glitches++;
      perf.lag = 0;
      raisePerfAlert();
    }
  }
  perf.wallBase = wall; perf.clockBase = clock;
}, 500);

// Live snapshot for the UI probe. Reading the analyser here folds anything
// since the last read into the session peak, so the UI can read it as often
// as it likes and lose nothing that matters.
function audioPerfSnapshot() {
  const p = { ok: false };
  if (!audioCtx) return p;
  p.ok = true;
  p.state = audioCtx.state;
  p.sampleRate = audioCtx.sampleRate;
  p.baseLatency = typeof audioCtx.baseLatency === "number" ? audioCtx.baseLatency : null;
  p.outputLatency = typeof audioCtx.outputLatency === "number" ? audioCtx.outputLatency : null;
  p.voices = countAliveVoices(melodyBag);
  p.hoverVoices = countAliveVoices(liveVoices);
  p.glitches = perf.glitches;
  p.jumps = perf.jumps;
  p.spikes = perf.spikes;
  p.reverb = reverbEnabled;
  p.lite = liteMode();
  if (perfAnalyser && perfAnalyser.context === audioCtx) {
    if (!perf.snapBuf || perf.snapBuf.length !== perfAnalyser.fftSize) {
      perf.snapBuf = new Float32Array(perfAnalyser.fftSize);
    }
    perfAnalyser.getFloatTimeDomainData(perf.snapBuf);
    let peak = 0;
    for (let i = 0; i < perf.snapBuf.length; i++) {
      const v = Math.abs(perf.snapBuf[i]);
      if (v > peak) peak = v;
    }
    if (peak > perf.sessionPeak) perf.sessionPeak = peak;
    p.cur = peak; // this analyser window's level — 0-ish after silence
  } else {
    p.cur = 0;
  }
  p.peak = perf.sessionPeak;
  let red = 0;
  for (const comp of perfComps) {
    try {
      const r = (comp && typeof comp.reduction === "number" && isFinite(comp.reduction)) ? comp.reduction : 0;
      if (r < red) red = r; // deepest gain reduction of any working limiter
    } catch (e) {}
  }
  p.limitReduction = red;
  return p;
}

function audioPerfReset() { perf.sessionPeak = 0; }

// ---------------------------------------------------------------------------
// SPIKE WATCH — Robin's 2026-09-24 field report: sporadic single-frame
// "ticks" (a one-sample waveform jump that leaves the CURRENT note silent
// while playback continues), Lite-invariant, invisible to the clock-lag
// watchdog above (a one-sample discontinuity never approaches its 0.3 s
// criterion), engine-timing sensitive (Chrome repros, VS Code's embedded
// Chromium never did). Class: a parameter-automation seam re-anchored
// mid-note, not CPU starvation. The detector rides the post-limiter tap:
// a pure classifier flags one ISOLATED sample-plane step (attack ramps,
// smooth tones and sub-floor micro steps must pass through untouched);
// onset/stop windows already marked by markSystemSound are subtracted.
// Each hit logs a state card into the perf panel so the next field catch
// names its own seam.
// ---------------------------------------------------------------------------

// The classifier is pure so the suites can pin its judgement tables.
// Isolation is the load-bearing rule, and a STEP has two shapes: the value
// jumps to a NEW level and stays (ONE delta above threshold — the
// jump-to-silence that kills the current note), or a single sample swings
// out and back (a MIRRORED PAIR of adjacent deltas, up-then-down). Anything
// editing several adjacent samples is a slope (attack ramp class): several
// above-threshold deltas in a row → not a spike. The absolute floor keeps
// silence-level jitter (inaudible) from counting.
function spikeClassify(win) {
  if (!(win && win.length > 4)) return null;
  const deltas = new Array(win.length - 1);
  for (let i = 0; i < deltas.length; i++) {
    deltas[i] = win[i + 1] - win[i];
  }
  const mags = deltas.map(Math.abs);
  const ordered = mags.slice().sort((a, b) => a - b);
  const med = ordered[Math.floor(ordered.length / 2)];
  const thr = Math.max(0.04, med * 8);
  const hot = [];
  for (let i = 0; i < mags.length; i++) {
    if (mags[i] > thr) hot.push(i);
  }
  if (hot.length === 1) {
    return { i: hot[0], jump: mags[hot[0]], level: med };
  }
  if (hot.length === 2 && hot[1] === hot[0] + 1 &&
      Math.sign(deltas[hot[0]]) !== Math.sign(deltas[hot[1]])) {
    // one-sample excursion: up-then-down (or down-then-up)
    const j = Math.max(mags[hot[0]], mags[hot[1]]);
    return { i: hot[0], jump: j, level: med };
  }
  return null;
}

// Recent playNoteAt onsets (id + scheduled audio time + slide flag) so a
// spike card can point at the voice that was starting when it hit.
const onsetRing = [];
function ringOnset(id, when, intoSlide) {
  onsetRing.push({ id, at: when == null ? -1 : Math.round(when * 1000) / 1000, into: !!intoSlide });
  if (onsetRing.length > 8) onsetRing.shift();
}

// Ambient context ring, paired with the spike cards the same way: the
// field hunt's newest evidence (Robin, phone) couples the ticks to a
// screen-orientation flip — the flip fires them EVERY time, the three perf
// counters stay at 0, and the ticks arrive in runs. Marking the flips (and
// the resize bursts that trail them) lets the next spike card pair itself
// with the flip — naming the seam's plane — while a card that stays silent
// while the phone still hops proves the discontinuity lives below the
// analyser (device level). Resize burst throttled; markers age out at 4 s.
const ambientRing = [];
let lastResizeMark = 0;
function markAmbient(kind) {
  if (kind === "resize") {
    const w = performance.now();
    if (w - lastResizeMark < 800) return;
    lastResizeMark = w;
  }
  ambientRing.push({ kind, wall: performance.now() });
  if (ambientRing.length > 8) ambientRing.shift();
}
function ambientContext(now) {
  const out = [];
  for (const a of ambientRing) {
    if (now - a.wall > 4000) continue;
    out.push({ kind: a.kind, agoMs: Math.max(0, Math.round(now - a.wall)) });
    if (out.length === 3) break;
  }
  return out.reverse();
}
try {
  window.addEventListener("orientationchange", () => markAmbient("flip"));
  if (screen.orientation)
    screen.orientation.addEventListener("change", () => markAmbient("flip"));
  window.addEventListener("resize", () => markAmbient("resize"));
} catch (e) {}

// 20 ms sampling: the analyser window is fftSize (1024) samples ≈ 23 ms at
// 44.1 kHz, so consecutive reads overlap and no sample escapes coverage.
// Cost is one 1024-float read + a linear scan per tick.
setInterval(() => {
  if (!audioCtx || audioCtx.state !== "running" || !perfAnalyser) return;
  const now = audioCtx.currentTime;
  const winDur = perfAnalyser.fftSize / audioCtx.sampleRate;
  if (now - winDur < sysSoundUntil) return;   // onset/stop seam windows
  if (perf.spikeLog.length && now - perf.spikeLog[perf.spikeLog.length - 1].t < 0.2) {
    return;                                    // one card per tick event
  }
  if (perf.spikeBuf == null || perf.spikeBuf.length !== perfAnalyser.fftSize) {
    perf.spikeBuf = new Float32Array(perfAnalyser.fftSize);
  }
  perfAnalyser.getFloatTimeDomainData(perf.spikeBuf);
  const hit = spikeClassify(perf.spikeBuf);
  if (!hit) return;
  const sr = audioCtx.sampleRate;
  const t = now - (perf.spikeBuf.length - 2 - hit.i) / sr;
  if (perf.spikeLog.length && t - perf.spikeLog[perf.spikeLog.length - 1].t < 0.2) {
    return;
  }
  perf.spikes++;
  perf.spikeLog.push({
    t: Math.round(t * 1000) / 1000,
    jump: Math.round(hit.jump * 1000) / 1000,
    mel96: melodyPos96,
    lite: liteMode(),
    onsets: onsetRing.slice(-3).map(o =>
      o.id + "@" + o.at + (o.into ? "~" : "")),
    ambient: ambientContext(performance.now()),
  });
  if (perf.spikeLog.length > 24) perf.spikeLog.shift();
  // A spike is never a normal sound: name it in the console, throttled so a
  // burst of neighbors cannot spam the pasted #err digests.
  const last = perf.spikeLog[perf.spikeLog.length - 1];
  const took = new Date(performance.now()).toISOString().slice(11, 19);
  console.warn("spike watch: single-frame step at audio-clock t=" + t.toFixed(3) +
               " s (jump " + last.jump + ") — card: " +
               JSON.stringify({ mel96: last.mel96, lite: last.lite,
                                onsets: last.onsets, wall: took,
                                ambient: last.ambient }));
}, 20);

// Lazily build (and return) the reverb bus. All melodic voices connect here
// instead of straight to ctx.destination, so the wet level can be toggled.
// A limiter on the bus output protects headroom: individual voices sum to
// well over 1.0 under polyphony (overlapping/tied notes) and with reverb,
// which would clip hard at ctx.destination without it.
function getReverbBus(ctx) {
  if (reverbBus && reverbBus.context === ctx) return reverbBus;
  const input = ctx.createGain();
  const dry = ctx.createGain();
  dry.gain.value = 1;
  const convolver = ctx.createConvolver();
  convolver.buffer = makeReverbImpulse(ctx, 2.6, 3.2);
  const wet = ctx.createGain();
  wet.gain.value = reverbEnabled ? AUDIO_DEBUG.reverbWet : 0;
  // Safety limiter to catch peaks. Lower threshold + a soft knee and slower
  // attack keep it from clamping the vibrato/tremolo peaks of a sustained note
  // hard enough to add buzzy harmonic distortion; the outGain below provides
  // the actual headroom so the limiter should rarely engage.
  const limiter = ctx.createDynamicsCompressor();
  limiter.threshold.value = -6;
  limiter.knee.value = 6;
  limiter.ratio.value = 12;
  limiter.attack.value = 0.006;
  limiter.release.value = 0.2;
  dry.connect(limiter);
  input.connect(dry);
  input.connect(convolver); convolver.connect(wet); wet.connect(limiter);
  // Output headroom: the per-voice partial stack (osc + air + edge + reverb)
  // can push the limiter into its knee on sustained low notes, and any
  // remaining peaks would clip when the OS mixes our output with other audio
  // (e.g. a call). Attenuate after the limiter so the signal sits well below
  // 0 dBFS with margin for inter-sample overshoot.
  const outGain = ctx.createGain();
  outGain.gain.value = 0.6;
  limiter.connect(outGain);
  outGain.connect(ctx.destination);
  outGain.connect(getPerfTap(ctx)); // headroom probe (post-limiter output)
  perfComps.push(limiter);
  // Pin the bus input at 2 channels with a forever-silent stereo feed: when
  // the first Zen chorus panner connects (or the connection's channel count
  // changes later), a mono↔stereo topology switch can click. With the anchor
  // the bus is always stereo and mono voices just upmix silently.
  const anchor = ctx.createOscillator();
  anchor.type = "sine";
  const anchorGain = ctx.createGain();
  anchorGain.gain.value = 0;
  const anchorPan = ctx.createStereoPanner();
  anchor.connect(anchorGain); anchorGain.connect(anchorPan);
  anchorPan.connect(input);
  anchor.start();
  reverbWetGain = wet;
  reverbBus = input;
  return reverbBus;
}

// Cut-safe melody bus: every melody-bag voice feeds this thin layer before the
// output buses. Cutting the melody (stop / pause / practice swap) decays THIS
// gain only — it carries its own single-event timeline (statically 1, set once
// at creation), so the decay's start value is unambiguous — the exact static
// value, never a cancel-and-re-anchor guess: no cancelScheduledValues /
// cancelAndHoldAtTime / .value reads anywhere on this path. Per-voice fades
// still run underneath for hover/live cuts. Live-preview voices bypass this
// bus intentionally: they cut via their own fades.
const cutBuses = new Map(); // wire -> bus gain
function getMelodyCutBus(ctx, wire) {
  let b = cutBuses.get(wire);
  if (!b || b.context !== ctx) {
    b = ctx.createGain();
    b.gain.value = 1;
    b.connect(wire);
    cutBuses.set(wire, b);
  }
  return b;
}
function isMelodyBag(bag) { return bag === melodyBag || !!(bag && bag.melodyRoute); }
// Fixed support loudness (twin voice). A support/track voice rides the
// melody instrument's fitted level rows today (every below-chart support
// note clamps to a far anchor row), which put the twin-engine support
// 12.7-13.1 dB under the additive engine's support on the same notes
// (measured 2026-09-28: eponas support D3/E3/G3, twin plateau ≈ −29.5 dBFS
// vs additive-generic ≈ −16.6 dBFS — Robin: "the 12-hole has softer support
// than the oak leaf triple"). Support is a mixing decision (the audible
// percent), never a melody-dynamics decision, so non-melody melodyRoute bags
// (track walker both zones + the legacy support forwarder; NOT the melody
// bag, NOT the flag-less live-preview voices) divide the interpolated level
// back out and play at this anchored constant. Timbre stays fitted (Q, h,
// noise rows untouched); only the loudness flattens. The value anchors the
// additive support plateau through the shared masterLevel.
const TWIN_SUPPORT_LEVEL = 0.75;
// Render-cut the melody buses as ONE continuous event per bus: an exponential
// setTargetAtTime decay, scheduled a little AHEAD of the render cursor. Three
// rules come straight from this bug's history:
// 1. Never schedule at exactly .currentTime — events that land on/behind the
//    cursor execute as an instant step (the "speaker connect" pop; the same
//    collapse playNoteAt already fights for note attacks with its +15 ms
//    lead). A 30 ms lead buys the event safe headroom in front of the cursor.
// 2. No .value writes at cut time — each raw write renders blockwise and was
//    audible as individual clicks (the 10 ms staircase turned the pop into
//    crackle). One continuous event replaces the whole staircase.
// 3. Never cancel/re-anchor — the bus is statically 1 with no other
//    automation, so the decay starts from the exact true value with no seam,
//    and two cuts in a row chain smoothly (each event continues from the
//    value the previous decay had reached).
const CUT_LEAD = 0.03; // s ahead of the cursor when scheduling the decay
const CUT_TAU = 0.035; // s time constant (~-60 dB after 6 tau ≈ 0.21 s)
// Earliest safe source-stop horizon: strictly past the bus decay's end, so a
// stopped oscillator can never sweep a still-sounding level.
const melodyStopAt = ctx => ctx.currentTime + CUT_LEAD + 0.27;
// Buses of already-cut generations. disconnect()ing a bus drops the whole
// dead voice branch — but only once it is provably silent (voices are
// stopped at melodyStopAt), or the disconnect itself is a wave-abort click.
const retiredBuses = []; // { bus, at } — at = audio time of the cut
function reapRetiredBuses(ctx) {
  if (!ctx) return;
  const now = ctx.currentTime;
  for (let i = retiredBuses.length; i-- > 0;) {
    const r = retiredBuses[i];
    if (r.at + 0.4 < now) {
      try { r.bus.disconnect(); } catch (e) {}
      retiredBuses.splice(i, 1);
    }
  }
}
function fadeMelodyBuses(ctx) {
  if (!ctx) return;
  const at = ctx.currentTime + CUT_LEAD;
  for (const b of cutBuses.values()) {
    if (b.context !== ctx) continue;
    try { b.gain.setTargetAtTime(0.0001, at, CUT_TAU); } catch (e) {}
    retiredBuses.push({ bus: b, at: ctx.currentTime });
  }
  cutBuses.clear();
  reapRetiredBuses(ctx);
}
// Prepares a fresh bus generation (the next melody voices build brand-new
// buses). No value writes: nothing here can disturb a still-decaying older
// generation, and a replay pressed immediately after a cut can no longer
// un-mute it (the old generation keeps decaying on its retired bus).
function resetMelodyBuses(ctx) {
  if (!ctx) return;
  cutBuses.clear();
  reapRetiredBuses(ctx);
}

// Called by the UI when Zen mode is entered/exited. Idempotent: safe to call
// with the same state repeatedly. `reverbEnabled` is the single source of
// truth — a lazily-created reverb bus reads it at build time, and any existing
// wet gain is ramped here, so the flag and the live node can never disagree.
function setReverbEnabled(on) {
  reverbEnabled = !!on;
  if (reverbWetGain && audioCtx) {
    const now = audioCtx.currentTime;
    const target = reverbEnabled ? AUDIO_DEBUG.reverbWet : 0;
    reverbWetGain.gain.cancelScheduledValues(now);
    reverbWetGain.gain.setValueAtTime(reverbWetGain.gain.value, now);
    reverbWetGain.gain.linearRampToValueAtTime(target, now + 0.25);
  }
}

// Expressive vibrato/tremolo belongs to Zen/focus mode like the reverb: the
// UI calls this on the same Zen transitions. Voices read the flag per note,
// so switching only changes what future notes get (short-lived voices make
// any live ramp pointless).
let vibratoEnabled = false;
function setVibratoEnabled(on) {
  vibratoEnabled = !!on;
}

// Melody duck: while ON, the MAIN melody voice is scheduled at the duck
// level so the player's live ocarina leads over the (full-level) supports
// and #track layers. Session-only; the transport button toggles it.
let melodyDuck = false;
const MELODY_DUCK_LEVEL = 0.2;
function setMelodyDuck(on) { melodyDuck = !!on; }
function melodyDuckOn() { return melodyDuck; }

function unlockAudio() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  attachCtxStateWatch(audioCtx);
    safeResume(audioCtx);
  } catch (e) {}
}

// Real user activations only. pointerover used to be in the list "to warm up"
// but is not a gesture on Safari/Firefox — its resume() only ever rejected.
["pointerdown","keydown","touchstart"].forEach(ev =>
  document.addEventListener(ev, unlockAudio, {passive:true})
);

function hushHovers() {
  bumpHoverQuiet();
  cutLive();
}
window.addEventListener("focus", hushHovers);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) cutLive();
  else hushHovers();
});

// Test seam + shared-context accessor (module boundary): suites capture the
// playNoteAt calls without monkeypatching a module-internal binding, and the
// debug WAV export needs a legal handle on the one shared AudioContext.
let noteSink = null;
let auditionSink = null;
function setNoteSink(fn) { noteSink = fn || null; }
function setAuditionSink(fn) { auditionSink = fn || null; }
function sharedAudioCtx() {
  audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  attachCtxStateWatch(audioCtx);
  return audioCtx;
}

function cutLive() {
  if (audioCtx) markSystemSound(audioCtx.currentTime + 0.1); // fades + stops land soon after
  liveVoices.forEach(n => { try { (n.fade || n.stop)(); } catch (e) {} });
  liveVoices = [];
}

// ---------------------------------------------------------------------------
// Hidden support notes (|[C2], |["Name",C2], [C2/4.] anywhere between bars):
// each bracket plays ONE long, low supporting note with the modelled
// instrument's own voice — playNoteAt, so it sounds exactly like playing the
// note, chorus / reverb / wind layers included. Zen PLAYBACK only (never
// practice, it would deafen the tuner); leaving Zen mid-note cuts the voices
// via setBassEnabled(false) — see playSupportAt before scheduleMelody.
// ---------------------------------------------------------------------------

// Live handles for the "leave Zen mid-playback" cut: every scheduled support
// voice lands here (and in the melody bag, so pause/stop/loop cover it too).
let bassBag = [];
function setBassEnabled(on) {
  if (on || !bassBag.length) return;
  if (audioCtx) markSystemSound(audioCtx.currentTime + 0.35);
  bassBag.forEach(n => { try { (n.fade || n.stop)(); } catch (e) {} });
  bassBag = [];
}


// Retire voices whose scheduled end time has passed: disconnect their head
// sends so the browser can drop the whole finished branch from the graph, and
// drop the JS references. Without this the bag closures keep every node of
// every note alive for the whole song — 300+ finished voices still churning
// their filters at the audio thread on slow phones (the meter read exactly
// that as "Active voices").
function pruneBag(bag) {
  if (!audioCtx || !bag || !bag.length) return;
  const now = audioCtx.currentTime;
  for (let i = bag.length; i-- > 0;) {
    const n = bag[i];
    if (n && n.until != null && n.until < now) {
      try { if (n.kill) n.kill(); } catch (e) {}
      bag.splice(i, 1);
    }
  }
}

// Per-instrument loudness dial: AUDIO_DEBUG's instDb keys map by instrument
// id; the loaded instrument (window.CURRENT_INSTRUMENT, set by app.js) reads
// its own offset — 0 dB = untouched (10^(dB/20), ±0.1 dB resolution).
const INST_DB_KEYS = {
  "oot-alto-c-12": "instOotDb",
  "stein-double-alto-c": "instSteinDb",
  "ico-oak-leaf-bass-c-triple": "instOakDb",
  "ico-contrabass-11-c": "instContraDb",
  "dummy-bass-c-double": "instDummyDb",
};
function instLevelGain() {
  const inst = window.CURRENT_INSTRUMENT;
  const key = inst && INST_DB_KEYS[inst.id];
  const db = key ? AUDIO_DEBUG[key] : 0;
  return db ? Math.pow(10, db / 20) : 1;
}
let TWIN_MODEL = null; // { instrumentId, chambers: { ch: { model, gain } } } | null
function logVoiceCard(path) {
  try {
    const c = (typeof window !== "undefined" && window.OCA_DEBUG
               && window.OCA_DEBUG.voiceCard)
      ? window.OCA_DEBUG.voiceCard()
      : { rev: VOICE_REV, twin: null, chambers: [], sw: "none" };
    console.info("[voice] " + c.rev + " path=" + path
      + " twin=" + (c.twin || "off")
      + " ch=" + ((c.chambers || []).join("|") || "-")
      + " sw=" + (c.sw || "none"));
  } catch (e) {}
}
function installTwinModel(data, instId) {
  if (!data || typeof data !== "object") {
    TWIN_MODEL = null;
    logVoiceCard("none");
    return;
  }
  try {
    let chambers;
    if (data.chambers && typeof data.chambers === "object" &&
        !Array.isArray(data.chambers)) {
      // multi-chamber wrapper ("ocarina-twin-multi-v1"): one model + one
      // chain-relative gain per chamber; each entry may also BE a bare
      // model (gain-less). Never lerps across a chamber boundary.
      chambers = {};
      for (const [ch, entry] of Object.entries(data.chambers)) {
        const base = entry && typeof entry.model === "object" ? entry.model : entry;
        chambers[String(ch)] = {
          model: loadTwinModelFromObject(base),
          gain: entry && isFinite(entry.gain) ? +entry.gain : 1,
        };
      }
      if (!Object.keys(chambers).length) throw new Error("twin: empty chambers");
    } else {
      // the single-chamber schema (the 12-hole's shape): one model, all notes
      chambers = { "1": { model: loadTwinModelFromObject(data), gain: 1 } };
    }
    TWIN_MODEL = { instrumentId: instId || null, chambers };
    logVoiceCard("twin");
  } catch (e) {
    TWIN_MODEL = null;
    try {
      console.warn("[voice] twin install failed:",
                   e && e.message ? e.message : e);
    } catch (e2) {}
    logVoiceCard("none");
  }
}

function playNote(id, durSec) {
  cutLive();
  if (auditionSink) try { auditionSink(id, durSec); } catch (e) {}
  playNoteAt(id, null, durSec == null ? tokenSeconds(4) : durSec, liveVoices);
}

function playNoteAt(id, when, durSec, bag, slideFromId, intoSlide) {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  attachCtxStateWatch(audioCtx);
    if (audioCtx.state === "suspended") safeResume(audioCtx);
    const ctx = audioCtx;
    ringOnset(id, when, intoSlide);
    // Per-track mix: the melody voice and every legacy bag carry no
    // trackGain (full volume); a named track's bag scales both its plateau
    // (M below) and — reported to the sink here — the mix ratio observable.
    // Melody duck (the transport toggle): only the MAIN melody drops to the
    // duck level; tracks and supports keep full volume, so the player's
    // live ocarina leads.
    const duckGain = bag === melodyBag && melodyDuck ? MELODY_DUCK_LEVEL : 1;
    const voiceGain = (isMelodyBag(bag) && bag.trackGain != null
                       ? bag.trackGain : 1) * duckGain;
    if (noteSink) try { noteSink(id, when, durSec, slideFromId, intoSlide, voiceGain); } catch (e) {}
    // Late scheduling (a main-thread stall past the 0.3 s lookahead — GC/JIT
    // bursts, worse on phones) hands a `when` already in the past. All gain/
    // pitch automation scheduled for the past collapses into one instant
    // step: the whole attack executes as a jump to plateau level — audible
    // as a click. Never start earlier than a small live lead; a late note
    // joins the grid late, it must not click.
    let t0 = when == null ? ctx.currentTime : when;
    if (t0 < ctx.currentTime + 0.015) t0 = ctx.currentTime + 0.015;
    const freq = freqOf(id);
    const dur = Math.max(0.12, durSec);
    const tail = 0.03;
    const slideFrom = slideFromId && slideFromId !== id ? freqOf(slideFromId) : 0;
    // The glide jump is a FINGER-TAP: the recorded transients (storms/kokiri
    // plateau-to-plateau jumps in skills/tone-analysis) run 10-60 ms with the
    // tone carrying through (0.2-0.5 dB dip on adjacent steps), so the bend
    // length is a fixed short window anymore — never scaled by note duration.
    const glide = slideFrom ? AUDIO_DEBUG.slideTapMs : 0;
    // A note flowing directly into a following ~ slide holds full level right
    // up to the junction, then crossfades briefly PAST it (the slide note
    // begins at the same pitch, so the seam is inaudible — no gap, no re-blow).
    const fadeOff = intoSlide ? 0.04 : 0;
    const stopOff = intoSlide ? tail * 2 : tail;
    // this voice (its layers and their tails through the output bus) counts
    // as site-made sound for practice-mode deafness
    markSystemSound(t0 + dur + stopOff);

    // Helmholtz twin voice — the only synth. See skills/ocarina-twin/SKILL.md.
    if (!TWIN_MODEL) {
      recordVoiceError("playNoteAt " + id, new Error("no twin model"));
      return;
    }
    // Chamber routing: missing chamber keys (a shared 12-hole twin on a
    // multi-chamber chart) fall back to chamber 1 — Helmholtz only.
    const chKey = typeof CHAMBER !== "undefined" && CHAMBER && CHAMBER[id] != null
      ? String(CHAMBER[id]) : "1";
    const twEntry = TWIN_MODEL.chambers[chKey]
      || TWIN_MODEL.chambers["1"]
      || Object.values(TWIN_MODEL.chambers)[0]
      || null;
    if (!twEntry) {
      recordVoiceError("playNoteAt " + id, new Error("no twin chamber"));
      return;
    }
    {
        const tmDest = isMelodyBag(bag) ? getMelodyCutBus(ctx, getReverbBus(ctx)) : getReverbBus(ctx);
        const nf = interpNote(twEntry.model, freq);
        // Support compensation: a non-melody melodyRoute bag trades the
        // fitted level row for the fixed TWIN_SUPPORT_LEVEL anchor (see the
        // constant's note) — timbre keeps the fit, loudness is the mix.
        const supportComp = bag && bag.melodyRoute && bag !== melodyBag && nf.level
          ? TWIN_SUPPORT_LEVEL * (AUDIO_DEBUG.supportLevel || 1) / nf.level
          : 1;
        // Dev-panel retunes scale the model's own wander/wobble rows (the
        // defaults are 1, so an untouched panel plays the fit verbatim).
        nf.wander_cents_std = (nf.wander_cents_std || 0) * AUDIO_DEBUG.wanderAmt;
        nf.wobble_pct = (nf.wobble_pct || 0) * AUDIO_DEBUG.wobbleAmt;
        const twRel = Math.max(0.04, nf.rel_s || 0.07);
        // LITE TWIN: the handoff's reduced voice — a sine through the cavity
        // resonator (bandpass at f0, the model's own Q) — replaces the
        // additive lite's osc→lowpass chain. Same envelope/level shape as the
        // legacy lite voice.
        if (liteMode()) {
          const lvM = AUDIO_DEBUG.masterLevel * voiceGain * (nf.level || 1) * supportComp * instLevelGain();
          const g = ctx.createGain();
          g.gain.setValueAtTime(0.0001, t0);
          g.gain.linearRampToValueAtTime(lvM, t0 + Math.min(0.03, dur * (slideFrom ? 0.4 : 0.2)));
          g.gain.setValueAtTime(lvM, intoSlide ? t0 + dur : t0 + Math.max(0.02, dur - twRel));
          g.gain.linearRampToValueAtTime(0.0001, t0 + dur + fadeOff);
          const bw = ctx.createBiquadFilter();
          bw.type = "bandpass";
          bw.Q.value = Math.max(8, Math.min(80, nf.Q || 45));
          const osc2 = ctx.createOscillator();
          osc2.type = "sine";
          if (slideFrom) {
            bw.frequency.setValueAtTime(Math.max(40, slideFrom), t0);
            bw.frequency.linearRampToValueAtTime(Math.max(40, freq), t0 + glide);
            osc2.frequency.setValueAtTime(slideFrom, t0);
            osc2.frequency.linearRampToValueAtTime(freq, t0 + glide);
          } else {
            bw.frequency.value = freq;
            osc2.frequency.setValueAtTime(freq, t0);
          }
          osc2.connect(bw); bw.connect(g); g.connect(tmDest);
          osc2.start(t0); osc2.stop(t0 + dur + stopOff);
          if (bag) bag.push({
            until: t0 + dur + stopOff + 0.08,
            stop() { try { osc2.stop(); } catch (e) {} },
            kill() { g.disconnect(); },
            fade() {
              if (isMelodyBag(bag)) {
                try { osc2.stop(melodyStopAt(ctx)); } catch (e) {}
                return;
              }
              const now = ctx.currentTime;
              try {
                g.gain.cancelScheduledValues(now);
                g.gain.setValueAtTime(Math.max(0.0001, g.gain.value || AUDIO_DEBUG.masterLevel), now);
                g.gain.linearRampToValueAtTime(0.0001, now + 0.03);
                osc2.stop(now + 0.05);
              } catch (e) {}
            }
          });
          return;
        }
        // The module's release is a plateau→0 taper spanning hold−rel →
        // hold+rel, so `hold` places it: a plain note ends AT t0+dur
        // (release inside the slot, as the additive envelope did); a note
        // flowing into a ~ slide holds full level through the junction and
        // crossfades past it (the slide target starts at the same pitch).
        const twHold = intoSlide
          ? Math.max(0.05, dur + twRel)
          : Math.max(0.05, dur - twRel);
        const VIB_DELAY = AUDIO_DEBUG.vibDelay;
        const vibOn = vibratoEnabled &&
          (AUDIO_DEBUG.vibDepth > 1e-4 || AUDIO_DEBUG.tremDepth > 1e-4);
        const twChorus = vibOn && dur > VIB_DELAY + 0.1;
        const hiF = Math.max(0, Math.min(1, (freq - AUDIO_DEBUG.hiFrom) /
          Math.max(60, AUDIO_DEBUG.hiTo - AUDIO_DEBUG.hiFrom)));
        const zenPan2 = Math.max(0, Math.min(1, AUDIO_DEBUG.zenPan));
        const baseOpts = {
          model: twEntry.model,
          f0: freq,
          when: t0,
          holdSec: twHold,
          dest: tmDest,
          master: AUDIO_DEBUG.masterLevel * voiceGain * twEntry.gain * supportComp * instLevelGain(),
        };
        if (slideFrom) {
          baseOpts.slideFromHz = slideFrom;
          baseOpts.slideSec = glide;
        }
        const twVoices = [];
        if (twChorus) {
          // Zen stereo chorus on the twin voice: the clean cavity core goes
          // hard LEFT, the vibrato twin (pitch LFO on the model's f0, depth
          // receding up the range as before) hard RIGHT. Both carry the same
          // fitted envelope; every layer of the voice pans with the core.
          const mkTwin = (vib, pan) => {
            const o = Object.assign({}, baseOpts);
            o.vibrato = vib ? {
              rate: AUDIO_DEBUG.vibRate,
              depth: AUDIO_DEBUG.vibDepth * (1 - AUDIO_DEBUG.vibHighFade * hiF),
              delay: VIB_DELAY,
            } : null;
            const h = scheduleHelmholtzNote(ctx, tmDest, o);
            if (pan) {
              const p = ctx.createStereoPanner();
              p.pan.value = pan;
              h.out.disconnect();
              h.out.connect(p);
              p.connect(tmDest);
              h._pan = p;
            }
            return h;
          };
          twVoices.push(mkTwin(false, -zenPan2), mkTwin(true, zenPan2));
        } else {
          const o = Object.assign({}, baseOpts);
          o.vibrato = null; // plain notes stay clean (gated like the reverb)
          twVoices.push(scheduleHelmholtzNote(ctx, tmDest, o));
        }
        // the twin's own tail can outlast the additive slot math — re-mark
        markSystemSound(twVoices[0].until);
        if (bag) {
          const twKill = () => {
            for (const h of twVoices) {
              try { if (h._pan) h._pan.disconnect(); } catch (e) {}
              try { h.out.disconnect(); } catch (e) {}
            }
          };
          bag.push({
            until: twVoices[0].until + 0.06,
            stop() { twVoices.forEach(h => { try { h.stop(); } catch (e) {} }); },
            kill() { twKill(); },
            fade() {
              // Melody cuts: the cut-bus decay owns the audible fade — the
              // voices' own ramps land strictly past it (level ~0 there), and
              // the sources stop right behind. Live/hover cuts take the
              // module's own 30 ms fade.
              if (isMelodyBag(bag)) {
                const stopAt = melodyStopAt(ctx);
                twVoices.forEach(h => { try { h.fade(stopAt - 0.03); } catch (e) {} });
                return;
              }
              twVoices.forEach(h => { try { h.fade(); } catch (e) {} });
            }
          });
        }
        return;
    }
  } catch (e) { recordVoiceError("playNoteAt " + id, e); }
}

function tickEnabled() {
  const cb = document.getElementById("tickMel");
  return !!(cb && cb.checked);
}

// Lite mode: a lightweight voice + reduced per-note visuals, to avoid audio
// crackling caused by CPU overload on slower devices (phones).
function liteMode() {
  const cb = document.getElementById("liteMel");
  return !!(cb && cb.checked);
}

function playTickAt(when, bag) {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  attachCtxStateWatch(audioCtx);
    if (audioCtx.state === "suspended") safeResume(audioCtx);
    const ctx = audioCtx;
    let t0 = when == null ? ctx.currentTime : when;
    if (t0 < ctx.currentTime + 0.015) t0 = ctx.currentTime + 0.015; // past-scheduled tick = click (see playNoteAt)
    const dur = 0.04;
    markSystemSound(t0 + dur + 0.02); // the tick is site sound too
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.linearRampToValueAtTime(0.09, t0 + 0.002);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    g.connect(ctx.destination);
    const osc = ctx.createOscillator();
    osc.type = "square";
    osc.frequency.setValueAtTime(1600, t0);
    osc.connect(g);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
    if (bag) bag.push({
      until: t0 + dur + 0.02 + 0.08,
      stop() { try { osc.stop(); } catch (e) {} },
      kill() { g.disconnect(); },
      fade() {
        // A mid-tick cut needs NO gain writes: the tick's own envelope
        // (attack to 0.09 in 2 ms, exponential down to 0.0001 by t0+40 ms)
        // always finishes before any reachable stop time — a cut scheduled
        // at now lands at earliest t0+50 ms, past the envelope's silent end,
        // so stopping there can never sweep a sounding level. A tick cut
        // before its start time simply never sounds.
        try { osc.stop(ctx.currentTime + 0.05); } catch (e) {}
      }
    });
  } catch (e) { recordVoiceError("playTickAt", e); }
}

function isMelodyPlaying() { return melodyPlaying; }
function isMelodyPaused() { return melodyPaused; }

function stopMelody() {
  melodyPlaying = false;
  trackStreams = []; // the named tracks die with the melody by construction
  wakeDrop("melody"); // the transport died: the phone may sleep again
  dropHighlightPlan();
  melodyPaused = false;
  if (audioCtx) markSystemSound(melodyStopAt(audioCtx)); // sources stop past the bus decay
  melodyBag.forEach(n => { try { (n.fade || n.stop)(); } catch (e) {} });
  melodyBag = [];
  fadeMelodyBuses(audioCtx); // one setTargetAtTime decay per bus — the melody's audible cut
  if (melodyTimer) { clearTimeout(melodyTimer); melodyTimer = 0; }
  if (typeof freezeZenGlow === "function") freezeZenGlow();
  clearHighlight();
  if (typeof cueFirstNote === "function") cueFirstNote();
  syncTransport();
}

function playMelody(fromIdx) {
  const from = (typeof fromIdx === "number") ? fromIdx : 0;
  if (typeof fromIdx !== "number" && melodyPlaying) { stopMelody(); return; }
  stopMelody();
  cutLive();
  melodyTokens = parse(document.getElementById("src").value);
  melodyIdx = from;
  melodyFrom = from;
  melodyHoldUntil = -1;
  melodyPaused = false;
  melodyPos96 = Math.round(gridBeatsBefore(melodyTokens, melodyIdx) * 96);
  // Statically anchor the second, parallel support melody to these tokens:
  // its events fire at melody pivots while the walk runs.
  supportPlan = buildSupportPlan(melodyTokens);
  // The named "#track" streams become real second walks on the same clock.
  setupTrackStreams(document.getElementById("src").value, from, melodyPos96);
  // The song's tempo line (header quarter + its inline "# tempo" switches) is
  // the shared clock: every stream looks up the quarter at its own position,
  // so a mid-song start inherits the tempo that holds at the start beat.
  tempoLine = buildTempoLine(melodyTokens);
  if (!melodyTokens.length) return;
  audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  attachCtxStateWatch(audioCtx);
  if (audioCtx.state === "suspended") audioCtx.resume();
  melodyPlaying = true;
  wakeHold("melody"); // screen stays up while the song plays (Robin 2026-09-25)
  syncTransport();
  resetMelodyBuses(audioCtx); // fresh bus generation for the upcoming voices
  const startWhen = audioCtx.currentTime + 0.05;
  rebaseTrackTimes(startWhen); // the named tracks start exactly at the melody
  scheduleMelody(startWhen);
}

function pauseMelody() {
  if (!melodyPlaying) return;
  melodyPlaying = false;
  melodyPaused = true;
  wakeDrop("melody"); // paused = the phone may sleep again
  dropHighlightPlan(); // highlights of a paused transport never fire
  if (audioCtx) markSystemSound(melodyStopAt(audioCtx)); // sources stop past the bus decay
  melodyBag.forEach(n => { try { (n.fade || n.stop)(); } catch (e) {} });
  melodyBag = [];
  fadeMelodyBuses(audioCtx); // one setTargetAtTime decay per bus — the melody's audible cut
  if (melodyTimer) { clearTimeout(melodyTimer); melodyTimer = 0; }
  if (typeof freezeZenGlow === "function") freezeZenGlow();
  syncTransport();
}

function resumeMelody() {
  if (melodyPlaying || !melodyPaused || !melodyTokens.length) { melodyPaused = false; return; }
  melodyPaused = false;
  audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  attachCtxStateWatch(audioCtx);
  if (audioCtx.state === "suspended") audioCtx.resume();
  melodyPlaying = true;
  wakeHold("melody"); // resume = screen stays up again
  syncTransport();
  resetMelodyBuses(audioCtx); // fresh bus generation for the upcoming voices
  const resumeWhen = audioCtx.currentTime + 0.05;
  rebaseTrackTimes(resumeWhen);
  scheduleMelody(resumeWhen);
}

function togglePlayPause() {
  if (melodyPlaying) pauseMelody();
  else if (melodyPaused) resumeMelody();
  else playMelody();
}

// Windowed lookahead scheduler. Instead of arming one timer per note ~80ms
// ahead (where a single late/janky timer would schedule a note with no lead
// time → audio-thread underrun → crackle), this pushes every note due within
// SCHED_AHEAD out to the audio clock, then re-checks on a fixed short interval.
// Audio timing is therefore decoupled from main-thread jitter.
const SCHED_AHEAD = 0.3;  // schedule this far ahead of the audio clock (s)
const SCHED_TICK = 0.05;  // how often the scheduler wakes up (s)

// ---------------------------------------------------------------------------
// The support layer is a SECOND, PARALLEL MELODY (the contrabass track).
// Brackets are its notes written inline: [C3/2] a note, [-/2] a tie that
// extends the running chain, [~G3/2] a glide into a pitch. This pre-pass
// turns markers into statically anchored plan events so the melody walk can
// fire them with the melody's own note semantics at the melody clock — no
// hand-off state, no seams: an event's onset IS the melody time of the pivot
// after its marker (first rest/note; bar/tempo/bass, ties transparent), and
// a ring plus its extensions are ONE voice exactly like a melody tie chain.
// ---------------------------------------------------------------------------

// Static plan built once in playMelody: { byAnchor: Map<idx, events[]>,
// trailing, loopEvents, open }. Events (all in marker order per anchor):
//   { anchorIdx, id, beats(null = durationless), ext, slide, slideFrom,
//     intoSlide } — beats/ext are grid beats, composed at fire time with the
// live quarter the same way melody notes are.
let supportPlan = null;

function buildSupportPlan(tokens) {
  const byAnchor = new Map(), trailing = [];
  let last = null;   // running chain: the last planned note event
  let queue = [];    // markers parked awaiting their pivot, in marker order
  const flush = idx => {
    if (!queue.length) return;
    if (idx >= tokens.length) { // past the last note: the one end-of-song ring
      for (const e of queue) trailing.push(e);
      queue = [];
      return;
    }
    let list = byAnchor.get(idx);
    if (!list) byAnchor.set(idx, list = []);
    for (const e of queue) { e.anchorIdx = idx; list.push(e); }
    queue = [];
  };
  // A glide whose anchor is the running chain's pitch makes that note flow
  // into the slide: full hold, crossfaded past the junction (the melody's
  // own note-into-~ rule, unbroken by melody rests between the slots).
  const markIntoSlide = (e, prev) => {
    if (!prev || !e.slide || !prev.id || e.id === prev.id) return;
    if (e.slideFrom === prev.id) prev.intoSlide = true;
  };
  const park = (id, beats, slide, desc) => {
    const e = { id, beats: beats == null ? null : beats, ext: 0,
                slide: !!slide,
                slideFrom: slide && last && last.id ? last.id : null,
                intoSlide: false };
    if (desc) e.desc = desc; // hidden, kept for round-trips
    markIntoSlide(e, last);
    last = e;
    queue.push(e);
  };
  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    if (t.type === "bar") {
      if (t.bass) park(t.bass, t.beats, t.slide, t.desc);
      continue;
    }
    if (t.type === "tempo") continue; // transparent: markers ride past it
    if (t.type === "bass") {
      if (t.ext != null) {
        // [-/N]: tie — extends the running chain's ring. Ties never sound on
        // their own and never fire; the chain may span melody rests (the
        // glue is the support track's own chain, not the melody's).
        if (last) last.ext += t.ext;
        continue;
      }
      park(t.id, t.beats, t.slide, t.desc);
      continue;
    }
    if (t.type === "note" || t.type === "rest") flush(i); // pivot (ties skip)
  }
  flush(tokens.length); // markers past the last note still get their ring
  return { byAnchor, trailing, loopEvents: null, open: null };
}

// Seconds a durationless support spans: grid time from its anchor to the
// NEXT bar line (an inline tempo change rebalances the tail via its own
// quarter; an end-of-song measure drones to the last token) — the synthesized
// fill the parallel track gets for a bracket with no notated length.
function openSupportSpanSec(startIdx) {
  let time = 0;
  let pos = Math.round(gridBeatsBefore(melodyTokens, startIdx) * 96);
  for (let i = startIdx; i < melodyTokens.length; i++) {
    const t = melodyTokens[i];
    if (t.type === "bar") break;
    if (t.type === "tempo" || t.type === "bass") continue;
    const g = tokenGridBeats(t);
    time += g * quarterAt(pos);
    pos += Math.round(g * 96);
  }
  return Math.max(0.5, time / tempoSpeed());
}

// The support voice IS the modelled instrument voice (playNoteAt), so it
// inherits chorus, reverb, wind/edge layers and the same tuning as playing
// the note on the selected ocarinaZen playback only — the scheduler gates it.
// The bag IS the routing discriminator inside playNoteAt: a melody-bag voice
// feeds the cut layer and stops on the melody's horizon, while anything else
// fell off to the raw reverb bus and the legacy .value fade (the click-prone
// path). This forwarder declares melodyRoute so support voices ride the SAME
// cut bus generation and stop horizon as melody voices, while its push still
// lands the handle in the melody bag (pause/stop/loop decay) AND the bass bag
// (setBassEnabled cuts it when focus mode turns off mid-playback).
function playSupportAt(id, when, durSec, slideFrom, intoSlide) {
  const base = melodyBag.length;
  playNoteAt(id, when, durSec, {
    melodyRoute: true,
    push(v) { melodyBag.push(v); bassBag.push(v); }
  }, slideFrom || null, !!intoSlide);
  return melodyBag.slice(base); // the voice handle(s) this support created
}

// Fires every plan event anchored at the melody token `anchorIdx` (in marker
// order): Zen playback only, checked at fire time so a practice switch later
// in the song never schedules further support notes.
function fireDueSupport(anchorIdx, when) {
  const plan = supportPlan;
  if (!plan) return;
  const list = plan.byAnchor.get(anchorIdx);
  const armed = plan.loopEvents;
  if (!list && !armed) return;
  plan.loopEvents = null; // the loop-pass trailing flush is one-shot
  if (!(typeof isFocusMode === "function") || !isFocusMode()) return;
  if (typeof isPracticeActive === "function" && isPracticeActive()) return;
  if (list) for (const e of list) fireSupportEvent(e, when);
  if (armed) for (const e of armed) fireSupportEvent(e, when);
}

function fireSupportEvent(e, when) {
  let dur, slideFrom = null, intoSlide = false;
  // The pivot's own position on the melody's tempo line (a loop pass replays
  // the same line, so the list position is the right coordinate).
  const anchor96 = Math.round(gridBeatsBefore(melodyTokens, e.anchorIdx) * 96);
  if (e.beats == null) {
    // Durationless: ring until the next bar (or the last token) — the
    // synthesized fill, timed live like the pre-track drones were.
    dur = openSupportSpanSec(e.anchorIdx);
    if (e.ext) dur += e.ext * quarterAt(anchor96) / tempoSpeed();
  } else {
    const hold = (e.beats + e.ext) * quarterAt(anchor96); // holds ride the tempo line at the pivot
    dur = Math.max(0.09, e.intoSlide ? hold : hold * 0.92);
    slideFrom = e.slide ? e.slideFrom : null;
    intoSlide = !!e.intoSlide;
  }
  // A new open-ended ring — and a glide taking over a sustained drone —
  // retires the previous still-open ring (their spans would overlap through
  // the ring/glide otherwise). Plain bounded supports never cut anyone.
  if ((e.beats == null || e.slide) && supportPlan.open &&
      supportPlan.open.anchorIdx !== e.anchorIdx) {
    supportPlan.open.voices.forEach(v => { try { (v.fade || v.stop)(); } catch (err) {} });
    supportPlan.open = null;
  }
  const voices = playSupportAt(e.id, when, dur, slideFrom, intoSlide);
    if (e.beats == null) {
      // Same-anchor open events are a chord: keep one cut-set per pivot.
      if (supportPlan.open && supportPlan.open.anchorIdx === e.anchorIdx)
        supportPlan.open.voices.push(...voices);
      else supportPlan.open = { anchorIdx: e.anchorIdx, voices };
    }
  }

  // ---------------------------------------------------------------------------
  // Multi-track: the named "#track" streams (parse.js parseTracks) play as
  // REAL second melodies on the shared clock — their own token walk, so a
  // bass groove can enter where the melody holds (the one thing the support
  // layer cannot do), with the melody's note semantics and its very
  // playNoteAt voice (equivalence is the test bar, not a new timbre).
  // Zone "audible" (the default) plays wherever the melody plays, including
  // plain practice; zone "zen" mirrors the support gating and lands in the
  // bass bag as well (cut when Zen is left mid-playback).
  // Support markers are melody-stream syntax: inside a track stream the
  // parser chips them, so nothing here ever reads a hidden bass token.
  // ---------------------------------------------------------------------------

  let trackStreams = []; // [{ name, zone, tokens, idx, pos96, nextTime }]

  function trackBagFor(zone, vol) {
    const zen = zone === "zen";
    return { melodyRoute: true, trackGain: vol == null ? 1 : vol,
             push(v) { melodyBag.push(v); if (zen) bassBag.push(v); } };
  }

  // Start-state per stream at play time: from a token offset the bars carry
  // the alignment contract — every track rewinds to the melody's resume beat
  // (a track token straddling that beat is passed over, its tail dropped).
  function setupTrackStreams(src, from, resumeBeats) {
    trackStreams = parseTracks(src).map(tr => ({
      name: tr.name, zone: tr.zone, tokens: tr.tokens,
      vol: tr.vol, idx: 0, pos96: 0, nextTime: 0 }));
    if (from > 0 && resumeBeats > 0) alignTracksToBeats(resumeBeats / 96);
  }

  function alignTracksToBeats(beats) {
    const eps = 1e-6;
    for (const w of trackStreams) {
      let seen = 0, idx = 0;
      for (;;) {
        while (idx < w.tokens.length) {
          const t = w.tokens[idx];
          if (t.type !== "note" && t.type !== "rest" && t.type !== "tie") { idx++; continue; }
          break;
        }
        if (idx >= w.tokens.length || seen >= beats - eps) break;
        seen += tokenGridBeats(w.tokens[idx]);
        idx++;
      }
      w.idx = idx;
      w.pos96 = Math.round(beats * 96);
    }
  }

  // One shared scheduler step: every stream pushes what is due into the same
  // lookahead window the melody walk uses (it runs at the top of each tick).
  function walkTrackStreams() {
    if (!audioCtx || !trackStreams.length) return;
    const horizon = audioCtx.currentTime + SCHED_AHEAD;
    for (const w of trackStreams) walkTrackStream(w, horizon);
  }

  function walkTrackStream(w, horizon) {
    const loopEl = document.getElementById("loopMel");
    const loop = !!(loopEl && loopEl.checked);
    while (w.nextTime < horizon) {
      // Zero-time tokens ride through (bars/tempo/support-markers, transparent).
      // A "tempo" inside the stream NEVER retimes the shared clock — the
      // melody's tempo line is authoritative; a marker here just rides past.
      while (w.idx < w.tokens.length) {
        const zt = w.tokens[w.idx];
        if (zt.type === "bar" || zt.type === "tempo" || zt.type === "bass") {
          w.idx++;
          continue;
        }
        break;
      }
      if (w.idx >= w.tokens.length) {
        if (!loop) return;
        // New pass: the stream loops on the shared clock (its own total
        // equals the melody's; the next onset lands where the melody's does).
        w.idx = 0;
        w.pos96 = 0;
        continue;
      }
      const tok = w.tokens[w.idx];
      const start96 = w.pos96;
      const noteWhen = Math.max(w.nextTime, audioCtx.currentTime + 0.02);
      const step = Math.max(0.001, swungBeats(tok, start96) * quarterAt(start96) /
                    tempoSpeed());
      w.pos96 += Math.round(tokenGridBeats(tok) * 96);
      const zen = w.zone === "zen";
      const gated = zen && (!(typeof isFocusMode === "function") || !isFocusMode() ||
                    (typeof isPracticeActive === "function" && isPracticeActive()));
      if (!gated) soundTrackToken(w, tok, noteWhen, start96);
      w.idx++;
      w.nextTime += step;
      if (!melodyPlaying) return;
    }
  }

  // The melody note body mirrored exactly: same hold math, same slides and
  // staccato. NO chart range check — a track may sit below the melody
  // ocarina's carve, exactly as bracket supports always could.
  function soundTrackToken(w, tok, noteWhen, start96) {
    if (tok.type !== "note" && tok.type !== "tie") return; // rests are silent
    const hold = soundingGridBeats(w.tokens, w.idx) * quarterAt(start96);
    const slideFrom = (tok.slide && NOTES.includes(tok.slideFrom)) ? tok.slideFrom : null;
    let intoSlide = false;
    for (let i = lastHoldIndex(w.tokens, w.idx) + 1; i < w.tokens.length; i++) {
      const nt = w.tokens[i];
      if (nt.type === "bar" || nt.type === "tempo" || nt.type === "bass") continue;
      intoSlide = !!(nt.slide && NOTES.includes(nt.id) &&
                     NOTES.includes(nt.slideFrom) && nt.slideFrom === tok.id && nt.id !== tok.id);
      break;
    }
    const soundHold = tok.staccato
      ? Math.min(hold * 0.4, 0.16)
      : intoSlide ? hold : hold * 0.92;
    playNoteAt(tok.id, noteWhen, Math.max(0.09, soundHold),
               trackBagFor(w.zone, w.vol),
               slideFrom, intoSlide);
  }

  // Pause keeps walker positions (like the melody's); resume rebases every
  // stream onto the same anchor time the melody uses, PRESERVING each stream's
  // beat offset from the melody's next note: a track whose next onset is a
  // beat ahead must stay a beat ahead. Collapsing both streams' next onsets
  // onto one anchor (the old behavior) shifts the whole track by that beat
  // gap for the rest of the song.
  function rebaseTrackTimes(when) {
    for (const w of trackStreams) {
      const offBeats = (w.pos96 - melodyPos96) / 96;
      w.nextTime = when + offBeats * quarterAt(w.pos96) / tempoSpeed();
    }
  }


// ---- shared highlight plan ------------------------------------------------
// Every scheduled token used to carry its OWN setTimeout for highlightToken —
// page-lifetime timers alive across the whole song length. The plan keeps
// them queued by audio-clock position and fires them through ONE timer/rAF
// pair: wakes only as work comes due, rAF for the near-term batches so
// highlight throws land inside a frame instead of a timer clamp.
const highlightPlan = [];   // { at, run } — at = performance.now()-based ms
let highlightTimer = 0;
let highlightRaf = 0;

function armHighlightPlan() {
  if (!highlightPlan.length) { highlightTimer = 0; return; }
  clearTimeout(highlightTimer);
  cancelAnimationFrame(highlightRaf);
  const delay = Math.max(0, highlightPlan[0].at - performance.now());
  if (delay <= 34) {
    highlightRaf = requestAnimationFrame(flushHighlightPlan);
  } else {
    // wake 16 ms BEFORE the next item, so the near-term branch sees it in
    // the same frame it comes due instead of one timer clamp late
    highlightTimer = setTimeout(armHighlightPlan, delay - 16);
  }
}

function flushHighlightPlan() {
  highlightTimer = 0; highlightRaf = 0;
  const now = performance.now();
  while (highlightPlan.length && highlightPlan[0].at <= now) {
    const item = highlightPlan.shift();
    try { item.run(); } catch (e) {}
  }
  armHighlightPlan();
}

function queueHighlight(delayMs, run) {
  // The scheduler walks monotonic positions, but lookahead bursts can land a
  // piece out of order — sort and re-arm so the next wake always targets the
  // earliest due item.
  highlightPlan.push({ at: performance.now() + Math.max(0, delayMs), run: run });
  if (highlightPlan.length > 1) {
    highlightPlan.sort((a, b) => a.at - b.at);
  }
  armHighlightPlan();
}

function dropHighlightPlan() {
  highlightPlan.length = 0;
  clearTimeout(highlightTimer);
  cancelAnimationFrame(highlightRaf);
  highlightTimer = 0; highlightRaf = 0;
}

function scheduleMelody(when) {
  if (!melodyPlaying) return;
  walkTrackStreams(); // every tick: the named tracks push their due notes too
  // First call after (re)start seeds the clock from the passed absolute time.
  if (when != null) melodyNextTime = when;
  pruneBag(melodyBag);
  while (melodyNextTime < audioCtx.currentTime + SCHED_AHEAD) {
    let atBar = (melodyIdx === melodyFrom);
    // Consume bar lines and inline tempo markers (both zero time). Tempo
    // switches ride the precomputed tempo line — the position-based lookup
    // in quarterAt picks the right quarter for each step, so there is no
    // live quarter to update here. Support markers are zero-time too but
    // need no walk: the support plan (buildSupportPlan) is statically
    // anchored to these token indices and fires at the pivot below.
    while (melodyIdx < melodyTokens.length &&
           (melodyTokens[melodyIdx].type === "bar" || melodyTokens[melodyIdx].type === "tempo" ||
            melodyTokens[melodyIdx].type === "bass")) {
      if (melodyTokens[melodyIdx].type === "bar") atBar = true;
      melodyIdx++;
    }
    if (melodyIdx >= melodyTokens.length) {
      if (document.getElementById("loopMel") && document.getElementById("loopMel").checked) {
        melodyIdx = 0;
        // Loop restart: the tempo line re-derives the header quarter at
        // position 0 — the song's own tempo line resumes from its top.
        if (supportPlan) {
          // A new loop: the previous drone must not leak in, and markers
          // parked past the last note (anchored at the token-list end) ring
          // at each new pass's first pivot — armed here, flushed once there.
          supportPlan.open = null;
          supportPlan.loopEvents = supportPlan.trailing.length ? supportPlan.trailing : null;
        }
        while (melodyIdx < melodyTokens.length &&
               (melodyTokens[melodyIdx].type === "bar" || melodyTokens[melodyIdx].type === "tempo" ||
                melodyTokens[melodyIdx].type === "bass")) {
          if (melodyTokens[melodyIdx].type === "bar") atBar = true;
          melodyIdx++;
        }
        if (melodyIdx >= melodyTokens.length) { stopMelody(); return; }
        melodyPos96 = 0;
        melodyHoldUntil = -1;
        atBar = true;
      } else {
        // Support markers trailing past the last note: give them their one
        // ring at the song's end (the plan anchors them at the token-list
        // end). One-shot per playback — the armed flush consumes itself.
        if (supportPlan && supportPlan.trailing.length && !supportPlan.endFired) {
          supportPlan.endFired = true;
          supportPlan.loopEvents = supportPlan.trailing;
          fireDueSupport(melodyTokens.length,
                         Math.max(melodyNextTime, audioCtx.currentTime + 0.02));
        }
        // No loop: stop once the last scheduled note's time has passed;
        // otherwise keep the scheduler ticking so it can finish it.
        if (melodyNextTime <= audioCtx.currentTime) { stopMelody(); return; }
        melodyTimer = setTimeout(() => scheduleMelody(null), SCHED_TICK * 1000);
        return;
      }
    }
    // Keep the grid time but never schedule in the past: a late timer hands
    // melodyNextTime already behind currentTime, and past automation
    // collapses into instant steps (attack skipped → click; see playNoteAt).
    const noteWhen = Math.max(melodyNextTime, audioCtx.currentTime + 0.02);
    if (atBar && tickEnabled() && barHasNote(melodyTokens, melodyIdx)) playTickAt(noteWhen, melodyBag);
    const tok = melodyTokens[melodyIdx];
    // Pivot: a rest or a fresh note onset (ties stay part of the previous
    // chain) is the moment the support plan's events anchored here fire —
    // at this token's exact melody-clock onset.
    if (supportPlan && (tok.type === "note" || tok.type === "rest"))
      fireDueSupport(melodyIdx, noteWhen);
    const step = Math.max(0.001, swungBeats(tok, melodyPos96) * quarterAt(melodyPos96) /
                  tempoSpeed()); // tempo dial: % of the song's own speed (live — mid-song slider moves apply to upcoming notes)
    melodyPos96 += Math.round(tokenGridBeats(tok) * 96);
    const pitched = (tok.type === "note" || tok.type === "tie") && NOTES.includes(tok.id);
    let didSound = false;
    if (pitched && melodyIdx > melodyHoldUntil) {
      const hold = soundingGridBeats(melodyTokens, melodyIdx) * quarterAt(melodyPos96 - Math.round(tokenGridBeats(tok) * 96));
      const slideFrom = (tok.slide && NOTES.includes(tok.slideFrom)) ? tok.slideFrom : null;
      // Does this note flow directly into a following ~ slide? Then sound the
      // FULL slot (no slurred gap) so the tone reaches the slide's onset
      // unbroken; playNoteAt crossfades it past the junction into the glide.
      let intoSlide = false;
      for (let i = lastHoldIndex(melodyTokens, melodyIdx) + 1; i < melodyTokens.length; i++) {
        const nt = melodyTokens[i];
        if (nt.type === "bar" || nt.type === "tempo") continue;
        intoSlide = !!(nt.slide && NOTES.includes(nt.id) &&
                       NOTES.includes(nt.slideFrom) && nt.slideFrom === tok.id && nt.id !== tok.id);
        break;
      }
      // Staccato: sound only a short portion of the slot, leaving an audible gap
      // (an implied pause) before the next note. Never applies to slurred/tied notes.
      const soundHold = tok.staccato
        ? Math.min(hold * 0.4, 0.16)
        : intoSlide ? hold : hold * 0.92;
      playNoteAt(tok.id, noteWhen, Math.max(0.09, soundHold), melodyBag, slideFrom, intoSlide);
      melodyHoldUntil = lastHoldIndex(melodyTokens, melodyIdx);
      lastHoldSec = Math.max(0.09, soundHold);
      didSound = true;
    }
    const hlIdx = melodyIdx, hlId = tok.id, hlDur = lastHoldSec, hlSound = didSound;
    const hlDelay = Math.max(0, (noteWhen - audioCtx.currentTime) * 1000);
    queueHighlight(hlDelay,
      () => { if (melodyPlaying) highlightToken(hlIdx, hlId, hlDur, hlSound); });
    melodyIdx++;
    melodyNextTime += step;
  }

  melodyTimer = setTimeout(() => scheduleMelody(null), SCHED_TICK * 1000);
}

export { AUDIO_DEFAULTS, audioCtx, audioPerfReset, audioPerfSnapshot, cutLive, freqOf,
         getReverbBus, installTwinModel, isMelodyPaused, isMelodyPlaying, liteMode,
         melodyDuckOn, pauseMelody, perf, playMelody, playNote, playNoteAt, quarterSecFor,
         resumeMelody, reverbEnabled, setBassEnabled, setMelodyDuck,
         setPerfAlertListener, setReverbEnabled,
         setVibratoEnabled, soundingGridBeats, stopMelody, syncTransport,
         sysSoundUntilSec, tokenGridBeats, swungBeats, lastHoldIndex, togglePlayPause,
         unlockAudio, setNoteSink, setAuditionSink, sharedAudioCtx };

// Classic-script compat surface (tests + dev console).
// audioCtx is a let swapped on lazy creation, so the mirror is a live getter —
// a plain assignment here would freeze the not-yet-created undefined.
Object.defineProperty(window, "audioCtx", { get () { return audioCtx; } });
window.sharedAudioCtx = sharedAudioCtx;
window.playNote = playNote; window.playMelody = playMelody; window.stopMelody = stopMelody;
window.pauseMelody = pauseMelody; window.resumeMelody = resumeMelody;
window.playNoteAt = playNoteAt; window.isMelodyPlaying = isMelodyPlaying;
window.setNoteSink = setNoteSink; window.setAuditionSink = setAuditionSink;
window.isMelodyPaused = isMelodyPaused; window.playTickAt = playTickAt;
window.tokenGridBeats = tokenGridBeats; window.swungBeats = swungBeats;
window.soundingGridBeats = soundingGridBeats; window.lastHoldIndex = lastHoldIndex;
window.quarterSecFor = quarterSecFor; window.freqOf = freqOf; window.cutLive = cutLive;
window.installTwinModel = installTwinModel;
window.stopMelody = stopMelody;
