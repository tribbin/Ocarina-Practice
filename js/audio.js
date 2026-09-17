let audioCtx = null;
let hoverQuietUntil = 0;
let liveVoices = [];
let melodyBag = [];
let melodyTimer = 0;
let melodyPlaying = false;
let melodyTokens = [];
let melodyIdx = 0;
let melodyFrom = 0;
let melodyPos = 0;
let melodyHoldUntil = -1;
let melodyPaused = false;
let melodyNextTime = 0; // absolute ctx time of the next note to schedule
let melodyQuarter = null; // seconds per quarter for the CURRENT tempo (inline # tempo changes update this)
let lastHoldSec = 0.5; // sounding duration of the last scheduled note (for zen glow)

// ---- Dev-tunable synthesis parameters -------------------------------------
// The defaults are exactly the values that used to be hardcoded throughout
// this file. The dev panel (js/debug.js — enable with `DEBUG=1` in the
// console) mutates these live and persists them to localStorage, so
// synthesis code must READ these values per note — never bake them into a
// closure or a cached node at build time.
const AUDIO_DEFAULTS = {
  // Base PeriodicWave harmonic amplitudes (real/cosine parts; imag = 0).
  // Normalized by the Web Audio API, so these set the relative mix.
  h1: 1, h2: 0.06, h3: 0.03, h4: 0.012, h5: 0.006,
  // Tone lowpass: cutoff tracks the fundamental (lpMult × freq), capped at
  // lpMax so high notes keep their harmonic tail (higher-bright edits here
  // are usually the fix if the top of the range sounds dull OR stringy).
  lpMult: 4.2, lpMax: 9000, lpQ: 0.7,
  // High-note mapping: the "hiF" factor that fades air/edge layers toward
  // the top of the range. hiFrom = frequency where fading begins, hiTo =
  // where the fade reaches full. Changing this shifts where the tone turns.
  hiFrom: 660, hiTo: 1568,
  // Faint inharmonic "air" partial: level, how much it recedes on high
  // notes (airFade), and its frequency ratio (slightly detuned octave).
  airLevel: 0.02, airFade: 0.75, airRatio: 2.01,
  // Vibrato/tremolo LFO: shared 5.5Hz pitch+loudness wobble.
  vibRate: 5.5, vibDepth: 0.0035, vibHighFade: 0.4, tremDepth: 0.05,
  // Edge / windway whistle: level grows with the chamber register
  // (edgeBase + reg²·edgeReg) and recedes on high notes (edgeFade).
  // edgeDet/edgeDetSpread sit it sharp of pitch; wanderDepth adds slow
  // pitch instability (itself scaled by wanderFade edgeFade at the top).
  edgeBase: 0.035, edgeReg: 0.022, edgeFade: 0.7,
  edgeDet: 0.012, edgeDetSpread: 0.008,
  wanderDepth: 0.006, wanderFade: 0.8,
  // Dry-clay onset chiff level (multiplier on the chamber-shaped peak).
  chiffScale: 1,
  // Onset octave overtone ("blown on a bottle" bloom): level and the extra
  // part that scales with attackEffort, plus its noise/sine mix.
  otBase: 0.12, otEffort: 0.08, otNoise: 0.35,
  // Full-voice master gain plateau (the breathy pre-tone and "tone speaks"
  // stages scale proportionally so the envelope shape holds).
  masterLevel: 0.26,
  reverbWet: 0.32,
};
const AUDIO_DEBUG = Object.assign({}, AUDIO_DEFAULTS);
// Exposed for the dev panel: params are tweaked in place; invalidateWave()
// drops the cached PeriodicWave so the next note rebuilds it from the
// current harmonic amplitudes.
window.OCA_DEBUG = {
  params: AUDIO_DEBUG,
  defaults: AUDIO_DEFAULTS,
  invalidateWave() { ocarinaWave = null; },
};

function syncTransport() {
  if (typeof updateTransportUI === "function") updateTransportUI();
}

// Seconds per quarter note for a given bpm, clamped to the same 40–180 range
// the tempo slider uses. Used for inline "# tempo N" changes during playback.
function quarterSecFor(bpm) {
  return 60 / Math.max(40, Math.min(180, (+bpm) || 100));
}

function tokenGridBeats(tok) {
  if (!tok || tok.type === "bar" || tok.type === "tempo") return 0;
  return tok.beats || ((4 / (tok.dur || 4)) * (tok.dotted ? 1.5 : 1));
}

function soundingGridBeats(tokens, idx) {
  let p = tokenGridBeats(tokens[idx]);
  for (let i = idx + 1; i < tokens.length; i++) {
    if (tokens[i].type === "bar" || tokens[i].type === "tempo") continue;
    if (tokens[i].type === "tie") p += tokenGridBeats(tokens[i]);
    else break;
  }
  return p;
}

function lastHoldIndex(tokens, idx) {
  let last = idx;
  for (let i = idx + 1; i < tokens.length; i++) {
    if (tokens[i].type === "bar" || tokens[i].type === "tempo") continue;
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
    if (tokens[i].type === "note") return true;
    if (tokens[i].type === "tie" && NOTES.includes(tokens[i].id)) return true;
  }
  return false;
}

function swungBeats(tok, pos) {
  const beats = tokenGridBeats(tok);
  const s = (typeof currentSwing === "function" ? currentSwing() : 0) / 100;
  if (s <= 0 || Math.abs(beats - 0.5) > 1e-6) return beats;
  const longF = 0.5 + s / 6;
  const onBeat = Math.round(pos * 2) % 2 === 0;
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
  reverbWetGain = wet;
  reverbBus = input;
  return reverbBus;
}

// Lightweight output bus for Lite mode: a limiter + output gain, but NO
// convolver. The reverb convolver (a 2.6s stereo impulse) convolves every
// sample continuously and is one of the heaviest nodes on mobile — it runs
// even when the wet level is 0. Lite voices route here to skip it entirely.
let liteBus = null;
function getLiteBus(ctx) {
  if (liteBus && liteBus.context === ctx) return liteBus;
  const input = ctx.createGain();
  const limiter = ctx.createDynamicsCompressor();
  limiter.threshold.value = -6;
  limiter.knee.value = 6;
  limiter.ratio.value = 12;
  limiter.attack.value = 0.006;
  limiter.release.value = 0.2;
  const outGain = ctx.createGain();
  outGain.gain.value = 0.6;
  input.connect(limiter); limiter.connect(outGain); outGain.connect(ctx.destination);
  liteBus = input;
  return liteBus;
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

function unlockAudio() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
  } catch (e) {}
}

["pointerdown","pointerover","keydown","touchstart"].forEach(ev =>
  document.addEventListener(ev, unlockAudio, {passive:true})
);

function hushHovers() {
  hoverQuietUntil = Date.now() + 400;
  cutLive();
}
window.addEventListener("focus", hushHovers);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) cutLive();
  else hushHovers();
});

function freqOf(id) {
  const m = String(id).match(/^([A-G]s?)(\d)$/);
  if (!m) return 440;
  const semi = {C:0,Cs:1,D:2,Ds:3,E:4,F:5,Fs:6,G:7,Gs:8,A:9,As:10,B:11};
  const midi = semi[m[1]] + (+m[2] + 1) * 12;
  return 440 * Math.pow(2, (midi - 69) / 12);
}

// Per-chamber frequency ranges, cached from window.CHAMBER / window.NOTES.
let chamberRanges = null;
function getChamberRanges() {
  const notes = window.NOTES, chamberOf = window.CHAMBER;
  if (!notes || !chamberOf) return {};
  // Rebuild if the note set changed (e.g. instrument swapped).
  if (chamberRanges && chamberRanges._key === notes.length + ":" + notes[0]) {
    return chamberRanges;
  }
  const r = { _key: notes.length + ":" + notes[0] };
  notes.forEach(id => {
    const ch = chamberOf[id];
    if (ch == null) return;
    const f = freqOf(id);
    const cur = r[ch] || (r[ch] = { min: f, max: f });
    if (f < cur.min) cur.min = f;
    if (f > cur.max) cur.max = f;
  });
  chamberRanges = r;
  return r;
}

// Breathiness position (0..1) of a note WITHIN its own chamber: rises toward
// the top of each chamber and resets when a new chamber begins. Falls back to
// absolute pitch if chamber data is unavailable.
function chamberReg(id, freq) {
  const chamberOf = window.CHAMBER;
  const ch = chamberOf && chamberOf[id];
  const ranges = getChamberRanges();
  const range = ch != null ? ranges[ch] : null;
  if (range && range.max > range.min) {
    return Math.max(0, Math.min(1,
      Math.log2(freq / range.min) / Math.log2(range.max / range.min)));
  }
  return Math.max(0, Math.min(1, Math.log2(freq / 262) / 2));
}

// Per-chamber maximum covered-hole count (the chamber's fully-closed note),
// cached, used to derive how many holes are open for a given note.
let chamberMaxCover = null;
function getChamberMaxCover() {
  const notes = window.NOTES, chamberOf = window.CHAMBER, cover = window.COVER;
  if (!notes || !chamberOf || !cover) return {};
  const key = notes.length + ":" + notes[0];
  if (chamberMaxCover && chamberMaxCover._key === key) return chamberMaxCover;
  const m = { _key: key };
  notes.forEach(id => {
    const ch = chamberOf[id];
    const n = (cover[id] || []).length;
    if (ch == null) return;
    if (m[ch] == null || n > m[ch]) m[ch] = n;
  });
  chamberMaxCover = m;
  return m;
}

// Chamber size (0..1, larger/lower-numbered = 1) and open-hole fraction
// (0 = fully closed, 1 = all open) for a note. Drives both the attack
// softness and the chiff character.
function noteArticulation(id) {
  const chamberOf = window.CHAMBER;
  const ch = chamberOf && chamberOf[id];
  if (ch == null) return { sizeF: 0.5, openF: 0.5 };
  const chambers = Object.keys((window.FING && FING.chambers) || { 1: 1 }).map(Number);
  const maxCh = Math.max(...chambers, ch);
  const sizeF = maxCh > 1 ? (maxCh - ch) / (maxCh - 1) : 1;
  const maxCover = getChamberMaxCover()[ch] || 0;
  const openF = maxCover > 0
    ? Math.max(0, Math.min(1, 1 - (window.COVER[id] || []).length / maxCover))
    : 0;
  return { sizeF, openF };
}

// "Attack effort" (0..1) shaping the onset softness / pitch overshoot.
// Larger (lower-numbered) chambers build air pressure more slowly → bigger
// overshoot and longer attack; within a chamber, MORE OPEN HOLES increase it
// further. Returns ~0 for the smallest chamber fully closed, ~1 for the
// largest chamber wide open.
function attackEffort(id, freq) {
  const { sizeF, openF } = noteArticulation(id);
  // Weighted blend: chamber size dominates, open holes modulate within it.
  return Math.max(0, Math.min(1, 0.6 * sizeF + 0.4 * openF));
}

// Short white-noise buffer reused for chiff bursts.
let chiffBuf = null;
function getChiffBuffer(ctx) {
  if (chiffBuf && chiffBuf.sampleRate === ctx.sampleRate) return chiffBuf;
  const len = Math.floor(ctx.sampleRate * 0.5);
  const buf = ctx.createBuffer(1, len, ctx.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
  chiffBuf = buf;
  return buf;
}

// Cached ocarina periodic wave — reused across notes instead of rebuilding it
// on every note (per-note allocation adds needless main-thread work).
let ocarinaWave = null;
function getOcarinaWave(ctx) {
  if (ocarinaWave && ocarinaWave._ctx === ctx) return ocarinaWave;
  const w = ctx.createPeriodicWave(
    new Float32Array([0, AUDIO_DEBUG.h1, AUDIO_DEBUG.h2, AUDIO_DEBUG.h3,
                      AUDIO_DEBUG.h4, AUDIO_DEBUG.h5]),
    new Float32Array([0, 0, 0, 0, 0, 0])
  );
  w._ctx = ctx;
  ocarinaWave = w;
  return w;
}

function cutLive() {
  liveVoices.forEach(n => { try { (n.fade || n.stop)(); } catch (e) {} });
  liveVoices = [];
}

function playNote(id, durSec) {
  cutLive();
  playNoteAt(id, null, durSec == null ? tokenSeconds(4) : durSec, liveVoices);
}

function playNoteAt(id, when, durSec, bag, slideFromId, intoSlide) {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
    const ctx = audioCtx;
    const t0 = when == null ? ctx.currentTime : when;
    const freq = freqOf(id);
    const dur = Math.max(0.12, durSec);
    const tail = 0.03;
    const slideFrom = slideFromId && slideFromId !== id ? freqOf(slideFromId) : 0;
    const glide = slideFrom ? Math.min(Math.max(0.0125, dur * 0.0875), 0.0375) : 0; // fast bend (4x the old portamento)
    // A note flowing directly into a following ~ slide holds full level right
    // up to the junction, then crossfades briefly PAST it (the slide note
    // begins at the same pitch, so the seam is inaudible — no gap, no re-blow).
    const fadeOff = intoSlide ? 0.04 : 0;
    const stopOff = intoSlide ? tail * 2 : tail;
    const rel = intoSlide ? 0.04 : Math.min(0.18, Math.max(0.05, dur * 0.35)); // ~40ms fade before a slide, else 50–180ms taper
    const relStart = Math.max(0.02, dur - rel);

    // LITE VOICE: a minimal 3-node voice (osc → lowpass → gain) for slow
    // devices. Skips the air/edge/wander/chiff/vibrato/overtone layers so the
    // audio thread isn't overloaded (the main crackle cause). Same pitch and
    // rough envelope so it still reads as the ocarina, just plainer.
    if (liteMode()) {
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.linearRampToValueAtTime(AUDIO_DEBUG.masterLevel, t0 + Math.min(0.03, dur * (slideFrom ? 0.4 : 0.2)));
      g.gain.setValueAtTime(AUDIO_DEBUG.masterLevel, intoSlide ? t0 + dur : t0 + relStart);
      g.gain.linearRampToValueAtTime(0.0001, t0 + dur + fadeOff);
      const lp2 = ctx.createBiquadFilter();
      lp2.type = "lowpass";
      lp2.frequency.value = Math.min(AUDIO_DEBUG.lpMax, freq * AUDIO_DEBUG.lpMult);
      lp2.Q.value = AUDIO_DEBUG.lpQ;
      const osc2 = ctx.createOscillator();
      osc2.setPeriodicWave(getOcarinaWave(ctx));
      if (slideFrom) {
        osc2.frequency.setValueAtTime(slideFrom, t0);
        osc2.frequency.linearRampToValueAtTime(freq, t0 + glide);
      } else {
        osc2.frequency.setValueAtTime(freq, t0);
      }
      osc2.connect(lp2); lp2.connect(g); g.connect(getLiteBus(ctx));
      osc2.start(t0); osc2.stop(t0 + dur + stopOff);
      if (bag) bag.push({
        stop() { try { osc2.stop(); } catch (e) {} },
        fade() {
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

    const master = ctx.createGain();
    // Master plateau level (dev-tunable). The breathy pre-tone and "tone
    // speaks" stages keep their original proportions of 0.26 so the envelope
    // shape is unchanged at the default and simply scales with the level.
    const M = AUDIO_DEBUG.masterLevel;
    const preLevel = M * (0.05 / 0.26);   // breathy pre-tone (exactly 0.05 at default M)
    const toneLevel = M * (0.16 / 0.26);  // tone begins to speak (exactly 0.16 at default M)
    // Tone speaks slightly after onset (breathy pre-tone → full), pairing with
    // the pitch "catch up" bloom below for a soft ocarina attack. Larger
    // chambers + more open holes build pressure slower → a longer, softer
    // attack (see attackEffort). The big bass chamber is especially demanding:
    // the pure tone takes noticeably longer to reach full equilibrium.
    const art = noteArticulation(id);
    const effort = attackEffort(id, freq);
    const speak = Math.min(0.05, Math.max(0.006, dur * 0.08)) * (0.5 + effort);
    const equilib = Math.min(dur * 0.4, art.sizeF * art.sizeF * 0.16); // big chamber = slow to settle
    const t1 = t0 + speak * 0.5;
    const t2 = t0 + speak + 0.015;
    // Ensure the final "equilibrium" ramp has a real duration but also finishes
    // BEFORE the release begins. When equilib≈0 (high chamber) t3 would equal t2
    // (instant jump → click); when the note is short & high-effort (e.g. D5/16)
    // an unclamped t3 would land after relStart, creating out-of-order gain
    // automation (another click). Clamp into (t2, relStart).
    const relStartT = t0 + relStart;
    const t3 = Math.min(relStartT - 0.005, Math.max(t2 + 0.015, t2 + equilib));
    master.gain.setValueAtTime(0.0001, t0);
    if (slideFrom) {
      // ~ Legato: the tone carries straight over from the previous note — no
      // breathy pre-tone or tongued attack; swell to full in ~35ms while the
      // glide leaves the previous pitch.
      master.gain.linearRampToValueAtTime(M, t0 + Math.min(0.035, dur * 0.4));
    } else {
      master.gain.linearRampToValueAtTime(preLevel, t1); // breathy pre-tone
      if (t3 > t2 + 0.001) {
        master.gain.linearRampToValueAtTime(toneLevel, t2); // tone begins to speak
        master.gain.linearRampToValueAtTime(M, t3); // reaches full equilibrium
      } else {
        // Very short note: no room for the two-stage climb; go straight to full
        // by t2 so the automation stays monotonic and click-free.
        master.gain.linearRampToValueAtTime(M, Math.min(t2, relStartT - 0.003));
      }
    }
    master.gain.setValueAtTime(M, intoSlide ? t0 + dur : relStartT);
    master.gain.linearRampToValueAtTime(0.0001, t0 + dur + fadeOff);
    if (!intoSlide) master.gain.setValueAtTime(0.0001, t0 + dur + tail);
    master.connect(getReverbBus(ctx));

    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    // Keep the cutoff a roughly FIXED MULTIPLE of the fundamental across the
    // whole range so the timbre stays consistently pure/hollow like a real
    // ocarina. A hard absolute cap (e.g. 2800) collapses cutoff/f on high
    // notes, thinning the tone and — with the edge/air partials below — making
    // it read as a bowed string. A high ceiling only guards against aliasing.
    if (slideFrom) {
      // Timbre morphs WITH the glide so the landed note speaks with the same
      // brightness a fresh onset of that pitch would have (down-slides no
      // longer stay stubbornly bright, up-slides no longer start over-bright).
      lp.frequency.setValueAtTime(Math.min(AUDIO_DEBUG.lpMax, slideFrom * AUDIO_DEBUG.lpMult), t0);
      lp.frequency.linearRampToValueAtTime(Math.min(AUDIO_DEBUG.lpMax, freq * AUDIO_DEBUG.lpMult), t0 + glide);
    } else {
      lp.frequency.setValueAtTime(Math.min(AUDIO_DEBUG.lpMax, freq * AUDIO_DEBUG.lpMult), t0);
    }
    lp.Q.value = AUDIO_DEBUG.lpQ;
    // Tremolo node: vibrato modulates breath pressure, which on a Helmholtz
    // resonator changes pitch AND loudness together (in phase). The tone runs
    // through `trem` so the same LFO can add a small amplitude wobble; its
    // depth is driven below, in phase with the pitch vibrato.
    const trem = ctx.createGain();
    trem.gain.value = 1;
    lp.connect(trem);
    trem.connect(master);

    const wave = getOcarinaWave(ctx);
    const osc = ctx.createOscillator();
    osc.setPeriodicWave(wave);
    if (slideFrom) {
      // ~ Legato portamento: pick the pitch up exactly where the prior note
      // left off, bend fast to the target, then settle through the same tiny
      // overshoot a freshly blown note has, so the landed pitch reads + sounds
      // identically.
      const over = 1.002 + 0.004 * effort;
      const settle = Math.min(0.05, Math.max(0.02, dur * 0.2));
      osc.frequency.setValueAtTime(slideFrom, t0);
      osc.frequency.linearRampToValueAtTime(freq * over, t0 + glide);
      osc.frequency.exponentialRampToValueAtTime(freq, t0 + glide + settle);
    } else {
      // Airflow "catch up" onset: the pitch begins slightly flat and blooms
      // to target with a tiny overshoot — a brief breath chiff, NOT a long
      // pitch slide (that reads as brass). The pitch locks in fast (~15–30ms)
      // even on high-effort notes; effort mainly shapes the softer AMPLITUDE
      // attack (see `speak` above), not a long glide.
      const rise = Math.min(0.03, Math.max(0.01, dur * 0.12)) * (0.7 + 0.3 * effort);
      const flat = 0.993 - 0.007 * effort;  // start pitch: 0.7%–1.4% flat
      const over = 1.002 + 0.004 * effort;  // overshoot: 0.2%–0.6% sharp
      const overshootAt = t0 + rise;
      const settleAt = overshootAt + rise * 0.9;
      osc.frequency.setValueAtTime(freq * flat, t0);            // starts flat (air slow)
      osc.frequency.linearRampToValueAtTime(freq * over, overshootAt); // overshoot sharp
      osc.frequency.exponentialRampToValueAtTime(freq, settleAt);      // settle to pitch
      // Release pitch sag: as breath pressure falls at the end of the note the
      // pitch bends flat — a subtle downward "sigh". Scaled by effort/chamber
      // so bigger chambers sag a touch more. Only if the note is long enough to
      // have settled first, and never on a note that flows into a ~ slide
      // (the pitch must stay put until the glide takes over).
      if (!intoSlide && relStart > settleAt + 0.02) {
        const sag = 0.01 + 0.008 * effort; // ~17–31 cents flat over the release
        osc.frequency.setValueAtTime(freq, relStart);
        osc.frequency.linearRampToValueAtTime(freq * (1 - sag), t0 + dur);
      }
    }
    osc.connect(lp);
    osc.start(t0);
    osc.stop(t0 + dur + stopOff);

    // Faint inharmonic "air" partial: a quiet, slightly detuned sine just
    // above the 2nd harmonic adds breathy shimmer without muddying pitch. Its
    // level tapers off toward the top of the range: on high notes this beating
    // partial is a strong bowed-string cue, and a real ocarina is nearly a
    // pure sine up high, so it should recede there.
    const hiF = Math.max(0, Math.min(1, (freq - AUDIO_DEBUG.hiFrom) /
      Math.max(60, AUDIO_DEBUG.hiTo - AUDIO_DEBUG.hiFrom))); // 0 below E5 → 1 by G6 (dev-tunable)
    const air = ctx.createOscillator();
    air.type = "sine";
    if (slideFrom) {
      // Keep the same harmonic ratio while the pitch morphs (no beating).
      air.frequency.setValueAtTime(slideFrom * AUDIO_DEBUG.airRatio, t0);
      air.frequency.linearRampToValueAtTime(freq * AUDIO_DEBUG.airRatio, t0 + glide);
    } else {
      air.frequency.setValueAtTime(freq * AUDIO_DEBUG.airRatio, t0);
    }
    const airGain = ctx.createGain();
    const airLevel = AUDIO_DEBUG.airLevel * (1 - AUDIO_DEBUG.airFade * hiF);
    airGain.gain.setValueAtTime(0.0001, t0);
    airGain.gain.linearRampToValueAtTime(airLevel, t0 + 0.03);
    airGain.gain.setValueAtTime(airLevel, t0 + relStart);
    airGain.gain.linearRampToValueAtTime(0.0001, t0 + dur);
    air.connect(airGain); airGain.connect(lp);
    air.start(t0);
    air.stop(t0 + dur + tail);

    // Gentle vibrato (~5.5 Hz), only on SUSTAINED notes: it begins after a
    // fixed settle delay, so short/fast notes end before it starts. Breath
    // vibrato couples PITCH and LOUDNESS in phase (harder blow = sharper AND
    // louder), so the same LFO drives both osc.frequency and the tremolo gain.
    const VIB_DELAY = 0.35;
    const lfo = ctx.createOscillator();
    lfo.type = "sine";
    lfo.frequency.value = AUDIO_DEBUG.vibRate;
    const lfoGain = ctx.createGain();     // pitch depth
    const tremGain = ctx.createGain();    // amplitude depth (in phase)
    // Only wire up vibrato if the note is long enough to reach the sustain.
    if (dur > VIB_DELAY + 0.1) {
      const vibDepth = freq * AUDIO_DEBUG.vibDepth * (1 - AUDIO_DEBUG.vibHighFade * hiF); // ~6 cents, a touch less up high
      const tremDepth = AUDIO_DEBUG.tremDepth; // ~5% loudness wobble, in phase with pitch
      lfoGain.gain.setValueAtTime(0.0001, t0);
      lfoGain.gain.setValueAtTime(0.0001, t0 + VIB_DELAY);
      lfoGain.gain.linearRampToValueAtTime(vibDepth, t0 + VIB_DELAY + 0.2);
      tremGain.gain.setValueAtTime(0.0001, t0);
      tremGain.gain.setValueAtTime(0.0001, t0 + VIB_DELAY);
      tremGain.gain.linearRampToValueAtTime(tremDepth, t0 + VIB_DELAY + 0.2);
    } else {
      lfoGain.gain.setValueAtTime(0.0001, t0);
      tremGain.gain.setValueAtTime(0.0001, t0);
    }
    lfo.connect(lfoGain);
    lfoGain.connect(osc.frequency);
    lfo.connect(tremGain);
    tremGain.connect(trem.gain);
    lfo.start(t0);
    lfo.stop(t0 + dur + stopOff);

    // Chamber-relative "blowing effort": rises toward the top of each chamber
    // and resets at the next, so a higher note within a chamber is breathier.
    // Drives the edge-whistle level below.
    const reg = chamberReg(id, freq);

    // Edge / windway whistle: the jet crossing the labium sings a faint,
    // breathy tone slightly SHARP of the fundamental, with a little pitch
    // instability. This is the characteristic hollow "whispered pitch" of a
    // fipple/vessel flute. It grows with blowing effort (reg). On high notes
    // this detuned, FM-wandering partial beats close to the fundamental and is
    // the main reason the top of the range reads as a bowed string, so its
    // level, detune spread and wander all recede toward the top (hiF → 1).
    const edge = ctx.createOscillator();
    edge.type = "sine";
    const detune = 1 + AUDIO_DEBUG.edgeDet +
      Math.random() * AUDIO_DEBUG.edgeDetSpread * (1 - hiF); // tighter to pitch up high
    if (slideFrom) {
      edge.frequency.setValueAtTime(slideFrom * detune, t0);
      edge.frequency.linearRampToValueAtTime(freq * detune, t0 + glide);
    } else {
      edge.frequency.setValueAtTime(freq * detune, t0);
    }
    // Slow, subtle wander so it doesn't sound like a locked pure tone.
    const wander = ctx.createOscillator();
    wander.type = "sine";
    wander.frequency.value = 7 + Math.random() * 4;
    const wanderGain = ctx.createGain();
    wanderGain.gain.value = freq * AUDIO_DEBUG.wanderDepth * (1 - AUDIO_DEBUG.wanderFade * hiF);
    wander.connect(wanderGain); wanderGain.connect(edge.frequency);
    const edgeGain = ctx.createGain();
    const edgeLevel = (AUDIO_DEBUG.edgeBase + reg * reg * AUDIO_DEBUG.edgeReg) *
      (1 - AUDIO_DEBUG.edgeFade * hiF); // recede up high
    edgeGain.gain.setValueAtTime(0.0001, t0);
    edgeGain.gain.linearRampToValueAtTime(edgeLevel, t0 + 0.03);
    edgeGain.gain.setValueAtTime(edgeLevel, t0 + relStart);
    edgeGain.gain.linearRampToValueAtTime(0.0001, t0 + dur);
    // A little breathiness on the whistle itself via a gentle bandpass.
    const edgeBp = ctx.createBiquadFilter();
    edgeBp.type = "bandpass";
    if (slideFrom) {
      edgeBp.frequency.setValueAtTime(slideFrom * detune, t0);
      edgeBp.frequency.linearRampToValueAtTime(freq * detune, t0 + glide);
    } else {
      edgeBp.frequency.value = freq * detune;
    }
    edgeBp.Q.value = 4;
    edge.connect(edgeBp); edgeBp.connect(edgeGain); edgeGain.connect(master);
    edge.start(t0); edge.stop(t0 + dur + tail);
    wander.start(t0); wander.stop(t0 + dur + tail);

    // Dry-clay CHIFF: the tongued onset is a noise burst that "focuses" as the
    // Helmholtz cavity catches the jet. Its color is set by chamber size: big
    // (bass) chambers give a dark, muffled, longer "phh"; small chambers a
    // bright, airy "tss". More open holes = leakier, brighter, breathier.
    // A ~ slide note CONTINUES the previous note's breath, so it gets no chiff
    // at all — no tongued burst at onset, no extra burst when the glide lands.
    if (!slideFrom) {
      const { sizeF: chSize, openF: chOpen } = art;
      // Cap to the note's release start so the chiff always fades to zero before
      // `master` cuts the note. On short notes (fast 16ths) an uncapped chiff is
      // still at high level when master fades at t0+dur → truncation click.
      const chiffLen = Math.min((0.11 + chSize * 0.24) * (0.85 + 0.15 * chOpen), relStart - 0.005);
      // Chamber character comes from WHERE the noise energy sits. A big (bass)
      // chamber is a dark, muffled "phh"; a small chamber a bright, airy "tss".
      // Use a resonant lowpass with a strongly chamber-dependent cutoff and a
      // wide spread so the timbres are clearly distinct, sweeping down as the
      // cavity focuses. `bright` spans ~4 octaves between largest & smallest.
      const bright = Math.min(9, Math.pow(2, (1 - chSize) * 3.5 + chOpen * 1.2)); // ~1x (big) → capped ~9x
      const startHz = Math.min(11000, 900 * bright);   // broad/high at onset
      const endHz = Math.min(9000, 500 * bright);      // settles, still chamber-colored
      const chiffSrc = ctx.createBufferSource();
      chiffSrc.buffer = getChiffBuffer(ctx);
      const chiffHp = ctx.createBiquadFilter();
      chiffHp.type = "highpass";
      chiffHp.frequency.value = Math.max(300, 300 * bright * 0.4); // trim low rumble; floor keeps it airy not rumbly
      const chiffLp = ctx.createBiquadFilter();
      chiffLp.type = "lowpass";
      chiffLp.Q.value = 0.4; // non-resonant: avoids a chirp/ring on bright high-chamber sweeps
      chiffLp.frequency.setValueAtTime(startHz, t0);
      chiffLp.frequency.exponentialRampToValueAtTime(endHz, t0 + chiffLen * 0.6);
      const chiffGain = ctx.createGain();
      const chiffPeak = (0.018 - 0.0812 * chSize + 0.1412 * chSize * chSize) * AUDIO_DEBUG.chiffScale; // low strong, mid softest, high modest
      // Gentle attack, then a sustain-and-decay so the breathy onset lingers as
      // the tone establishes. The tail uses a linear ramp that actually reaches
      // zero (exponential ramps never do) with a small guard before the source
      // stops, avoiding a truncation click that reads as "clipping" on short
      // (high-chamber) bursts.
      const chAtk = Math.max(0.012, Math.min(0.025, chiffLen * 0.3)); // softer attack, min 12ms
      chiffGain.gain.setValueAtTime(0.0001, t0);
      chiffGain.gain.linearRampToValueAtTime(chiffPeak, t0 + chAtk);
      chiffGain.gain.linearRampToValueAtTime(chiffPeak * 0.85, t0 + chiffLen * 0.5);
      chiffGain.gain.linearRampToValueAtTime(0.0, t0 + chiffLen); // reach true zero
      chiffSrc.connect(chiffHp); chiffHp.connect(chiffLp); chiffLp.connect(chiffGain); chiffGain.connect(master);
      chiffSrc.start(t0); chiffSrc.stop(t0 + chiffLen + 0.02);
    }

    // Overblown-mode ONSET overtone ("blowing on a bottle"): when the jet first
    // hits the labium it is momentarily too fast and briefly excites the first
    // overblown mode — around the octave above — before the airflow settles and
    // the fundamental takes over. Rendered as a BREATHY, pitched whistle: noise
    // through a bandpass centered on the octave (airy character) plus a faint
    // sine for pitch definition. It speaks at the onset and decays as the
    // fundamental blooms in; bigger/breathier attacks (more effort) let it
    // speak a touch longer and louder. A ~ slide note fires its bloom (softer)
    // when the glide lands, so the arrived tone matches a fresh onset's color.
    const otF = freq * 2;
    const otOff = slideFrom ? glide : 0;
    const otRoom = relStart - otOff - 0.005;
    if (otF < ctx.sampleRate * 0.45 && (!slideFrom || otRoom > 0.03)) { // guard against aliasing on the very top notes
      const otDur = Math.max(slideFrom ? 0.03 : 0.04, Math.min(otRoom, 0.22 + 0.14 * effort)); // longer, breathy bloom
      const otPeak = (AUDIO_DEBUG.otBase + AUDIO_DEBUG.otEffort * effort) * (slideFrom ? 0.85 : 1); // toned down from the audibility test
      // Shared onset envelope: fast in, exponential collapse (the mode "loses").
      const otGain = ctx.createGain();
      otGain.gain.setValueAtTime(0.0001, t0 + otOff);
      otGain.gain.linearRampToValueAtTime(otPeak, t0 + otOff + Math.min(0.02, otDur * 0.25));
      otGain.gain.exponentialRampToValueAtTime(0.0001, t0 + otOff + otDur);
      // Connect PAST master's attack envelope (which is near-zero during the
      // onset and would swallow this transient) straight to the output bus.
      otGain.connect(getReverbBus(ctx));

      // Noisy, airy component: bandpass-filtered noise around the octave, with a
      // little downward sweep as the tone "focuses" onto the fundamental. High Q
      // keeps it pitched/whistly (a breath of air on the overtone) rather than
      // broadband white noise; it's the supporting texture, not the main voice.
      const otBp = ctx.createBiquadFilter();
      otBp.type = "bandpass";
      otBp.Q.value = 18; // strongly pitched: airy overtone, not white noise
      otBp.frequency.setValueAtTime(otF * 1.02, t0 + otOff);
      otBp.frequency.exponentialRampToValueAtTime(otF, t0 + otOff + otDur * 0.7);
      const otNoise = ctx.createBufferSource();
      otNoise.buffer = getChiffBuffer(ctx);
      const otNoiseGain = ctx.createGain();
      otNoiseGain.gain.value = AUDIO_DEBUG.otNoise; // quiet: just a breathy edge on the overtone
      otNoise.connect(otBp); otBp.connect(otNoiseGain); otNoiseGain.connect(otGain);
      otNoise.start(t0 + otOff); otNoise.stop(t0 + otOff + otDur + 0.02);

      // Sine overtone at the octave — the MAIN pitched voice of the transient,
      // a hair sharp sagging onto the true octave.
      const ot = ctx.createOscillator();
      ot.type = "sine";
      ot.frequency.setValueAtTime(otF * 1.004, t0 + otOff);
      ot.frequency.linearRampToValueAtTime(otF, t0 + otOff + otDur);
      const otSine = ctx.createGain();
      otSine.gain.value = 1.0; // dominant layer
      ot.connect(otSine); otSine.connect(otGain);
      ot.start(t0 + otOff); ot.stop(t0 + otOff + otDur + 0.02);

      if (bag) bag.push({
        stop() { try { ot.stop(); } catch (e) {} try { otNoise.stop(); } catch (e) {} },
        fade() { const n = ctx.currentTime + 0.05; try { ot.stop(n); } catch (e) {} try { otNoise.stop(n); } catch (e) {} }
      });
    }

    if (bag) {
      bag.push({
        stop() { try { osc.stop(); } catch (e) {} try { lfo.stop(); } catch (e) {} try { air.stop(); } catch (e) {} try { edge.stop(); } catch (e) {} try { wander.stop(); } catch (e) {} try { chiffSrc.stop(); } catch (e) {} },
        fade() {
          const now = ctx.currentTime;
          try {
            master.gain.cancelScheduledValues(now);
            master.gain.setValueAtTime(Math.max(0.0001, master.gain.value || M), now);
            master.gain.linearRampToValueAtTime(0.0001, now + 0.03);
            osc.stop(now + 0.05);
            lfo.stop(now + 0.05);
            air.stop(now + 0.05);
            edge.stop(now + 0.05);
            wander.stop(now + 0.05);
            try { chiffSrc.stop(now + 0.05); } catch (e) {}
          } catch (e) {}
        }
      });
    }
  } catch (e) {}
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
    if (audioCtx.state === "suspended") audioCtx.resume();
    const ctx = audioCtx;
    const t0 = when == null ? ctx.currentTime : when;
    const dur = 0.04;
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
    if (bag) bag.push({ stop() { try { osc.stop(); } catch (e) {} } });
  } catch (e) {}
}

function isMelodyPlaying() { return melodyPlaying; }function isMelodyPaused() { return melodyPaused; }

function stopMelody() {
  melodyPlaying = false;
  melodyPaused = false;
  melodyBag.forEach(n => { try { (n.fade || n.stop)(); } catch (e) {} });
  melodyBag = [];
  if (melodyTimer) { clearTimeout(melodyTimer); melodyTimer = 0; }
  if (typeof freezeZenGlow === "function") freezeZenGlow();
  const btn = document.getElementById("playMel");
  if (btn) btn.textContent = "Play";
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
  melodyPos = gridBeatsBefore(melodyTokens, melodyIdx);
  // Seed the current tempo: header tempo, then any inline "# tempo" tokens that
  // occur before the start index (so playing from mid-song uses the right one).
  melodyQuarter = quarterSec();
  for (let i = 0; i < melodyIdx && i < melodyTokens.length; i++) {
    if (melodyTokens[i].type === "tempo") melodyQuarter = quarterSecFor(melodyTokens[i].bpm);
  }
  if (!melodyTokens.length) return;
  audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === "suspended") audioCtx.resume();
  melodyPlaying = true;
  const btn = document.getElementById("playMel");
  if (btn) btn.textContent = "Stop";
  syncTransport();
  scheduleMelody(audioCtx.currentTime + 0.05);
}

function pauseMelody() {
  if (!melodyPlaying) return;
  melodyPlaying = false;
  melodyPaused = true;
  melodyBag.forEach(n => { try { (n.fade || n.stop)(); } catch (e) {} });
  melodyBag = [];
  if (melodyTimer) { clearTimeout(melodyTimer); melodyTimer = 0; }
  if (typeof freezeZenGlow === "function") freezeZenGlow();
  const btn = document.getElementById("playMel");
  if (btn) btn.textContent = "Play";
  syncTransport();
}

function resumeMelody() {
  if (melodyPlaying || !melodyPaused || !melodyTokens.length) { melodyPaused = false; return; }
  melodyPaused = false;
  audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === "suspended") audioCtx.resume();
  melodyPlaying = true;
  const btn = document.getElementById("playMel");
  if (btn) btn.textContent = "Stop";
  syncTransport();
  scheduleMelody(audioCtx.currentTime + 0.05);
}

function togglePlayPause() {
  if (melodyPlaying) pauseMelody();
  else if (melodyPaused) resumeMelody();
  else playMelody();
}

function rewindMelody() {
  const wasActive = melodyPlaying || melodyPaused;
  stopMelody();
  if (wasActive) { playMelody(0); return; }
  const toks = parse(document.getElementById("src").value);
  if (!toks.length) return;
  if (typeof firstSoundIdx === "function" && typeof highlightToken === "function") {
    highlightToken(firstSoundIdx(toks), null);
  }
}

// Windowed lookahead scheduler. Instead of arming one timer per note ~80ms
// ahead (where a single late/janky timer would schedule a note with no lead
// time → audio-thread underrun → crackle), this pushes every note due within
// SCHED_AHEAD out to the audio clock, then re-checks on a fixed short interval.
// Audio timing is therefore decoupled from main-thread jitter.
const SCHED_AHEAD = 0.3;  // schedule this far ahead of the audio clock (s)
const SCHED_TICK = 0.05;  // how often the scheduler wakes up (s)

function scheduleMelody(when) {
  if (!melodyPlaying) return;
  // First call after (re)start seeds the clock from the passed absolute time.
  if (when != null) melodyNextTime = when;

  while (melodyNextTime < audioCtx.currentTime + SCHED_AHEAD) {
    let atBar = (melodyIdx === melodyFrom);
    // Consume bar lines (zero time) and inline tempo changes. A "tempo" token
    // switches the sec-per-quarter used from this point forward.
    while (melodyIdx < melodyTokens.length &&
           (melodyTokens[melodyIdx].type === "bar" || melodyTokens[melodyIdx].type === "tempo")) {
      if (melodyTokens[melodyIdx].type === "tempo") melodyQuarter = quarterSecFor(melodyTokens[melodyIdx].bpm);
      else atBar = true;
      melodyIdx++;
    }
    if (melodyIdx >= melodyTokens.length) {
      if (document.getElementById("loopMel") && document.getElementById("loopMel").checked) {
        melodyIdx = 0;
        melodyQuarter = quarterSec(); // reset to the header tempo at loop start
        while (melodyIdx < melodyTokens.length &&
               (melodyTokens[melodyIdx].type === "bar" || melodyTokens[melodyIdx].type === "tempo")) {
          if (melodyTokens[melodyIdx].type === "tempo") melodyQuarter = quarterSecFor(melodyTokens[melodyIdx].bpm);
          melodyIdx++;
        }
        if (melodyIdx >= melodyTokens.length) { stopMelody(); return; }
        melodyPos = 0;
        melodyHoldUntil = -1;
        atBar = true;
      } else {
        // No loop: stop once the last scheduled note's time has passed;
        // otherwise keep the scheduler ticking so it can finish it.
        if (melodyNextTime <= audioCtx.currentTime) { stopMelody(); return; }
        melodyTimer = setTimeout(() => scheduleMelody(null), SCHED_TICK * 1000);
        return;
      }
    }
    const noteWhen = melodyNextTime;
    if (atBar && tickEnabled() && barHasNote(melodyTokens, melodyIdx)) playTickAt(noteWhen, melodyBag);
    const tok = melodyTokens[melodyIdx];
    const step = Math.max(0.001, swungBeats(tok, melodyPos) * melodyQuarter); // floor guards against a 0-beat token spinning the loop
    melodyPos += tokenGridBeats(tok);
    const pitched = (tok.type === "note" || tok.type === "tie") && NOTES.includes(tok.id);
    let didSound = false;
    if (pitched && melodyIdx > melodyHoldUntil) {
      const hold = soundingGridBeats(melodyTokens, melodyIdx) * melodyQuarter;
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
    setTimeout(() => { if (melodyPlaying) highlightToken(hlIdx, hlId, hlDur, hlSound); }, hlDelay);
    melodyIdx++;
    melodyNextTime += step;
  }

  melodyTimer = setTimeout(() => scheduleMelody(null), SCHED_TICK * 1000);
}
