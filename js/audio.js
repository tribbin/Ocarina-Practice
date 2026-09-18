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
  // == Pitch-keyed voice profile (measured-curve synthesis) ==
  // Harmonic amplitudes are no longer one fixed wave: every note rebuilds
  // its PeriodicWave from V_ANCHORS (below noteArticulation), interpolated
  // in log-pitch through the tuner-verified alto C5/G6 recordings and
  // conservatively extrapolated below C4. These multipliers scale the
  // anchor curves globally (by-ear brightening all notes at once).
  h2Mul: 1, h3Mul: 1, h4Mul: 1, h5Mul: 1,
  // Chamber "hard blow" drift: more open holes lose more air on big
  // chambers, so the player blows harder — wind noise rebalances toward
  // the upper bands, slow wobble deepens and the attack overshoot grows,
  // rising toward the top of every chamber and resetting at each boundary
  // (the smallest chamber hardly shows it). 0 disables the drift.
  hardAmt: 1,
  // Measured non-monotonic loudness curve between chambers, dialed to a
  // mild fraction of the recorded chamber jumps (0 = even playback).
  levelCurveAmt: 1,
  // Slow intrinsic wander layers measured in the recordings (the
  // recordings contain NO periodic vibrato): slow pitch wander (cents)
  // and slow breath (amplitude) wobble, one LFO driving both.
  wanderAmt: 1, wobbleAmt: 1,
  // Broadband wind/breath noise keyed to the measured noise bands.
  windAmt: 1,
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
  // The recordings show nothing measurable at that slot, so the level is 0.
  airLevel: 0.0, airFade: 0.75, airRatio: 2.01,
  // Expressive vibrato/tremolo LFO: shared pitch+loudness wobble — belongs
  // to Zen/focus mode like the reverb (gated per voice by vibratoEnabled,
  // on/off only switches what NEW notes get; live ones are left alone).
  // The reference recordings contain no periodic vibrato (slow intrinsic
  // wander only), which is why it is off in normal playback.
  vibRate: 5.5, vibDepth: 0.0035, vibHighFade: 0.4, tremDepth: 0.05,
  vibDelay: 0.35,
  // Zen stereo chorus: sustained Zen notes split the core tone — clean LEFT,
  // pitch-vibrato twin RIGHT (a douber-chorus); chiff/edge/wind stay center.
  // 0 = mono again, 1 = fully hard sides.
  zenPan: 0.9,
  // Edge / windway whistle: recordings show no tonal content near 1.01-1.05×f0
  // (only a faint ~-40 dB island on D6), so the whistle sits just under that.
  edgeBase: 0.0008, edgeReg: 0.0005, edgeFade: 0.7,
  edgeDet: 0.012, edgeDetSpread: 0.008,
  wanderDepth: 0.006, wanderFade: 0.8,
  // Dry-clay onset chiff: the recorded chiff is a ~60-80 ms broadband swipe,
  // nearly inaudible, so the length now matches it directly (chiffBase +
  // chiffSize per chamber size) and the level scale stays small.
  chiffScale: 0.25, chiffBase: 0.075, chiffSize: 0.05,
  // Onset octave overtone ("blown on a bottle" bloom): level, the extra
  // part scaling with attackEffort, noise/sine mix, and the decay length —
  // recorded ~60-115 ms total (was 0.22-0.36 s).
  otBase: 0.00137, otEffort: 0.0011, otNoise: 0.35,
  otDurMax: 0.10, otDurEffort: 0.05,
  // Full-voice master gain plateau (the breathy pre-tone and "tone speaks"
  // stages scale proportionally so the envelope shape holds). Kept at the
  // pre-tune playback loudness: the recording's absolute level is a mic-gain
  // artifact, so comparisons below use ratios, never absolute level.
  masterLevel: 0.40,
  reverbWet: 0.20,
};
const AUDIO_DEBUG = Object.assign({}, AUDIO_DEFAULTS);
// Exposed for the dev panel: params are tweaked in place; invalidateWave()
// drops the cached PeriodicWave so the next note rebuilds it from the
// current harmonic amplitudes.
window.OCA_DEBUG = {
  params: AUDIO_DEBUG,
  defaults: AUDIO_DEFAULTS,
  invalidateWave() { ocWaveCache = null; },
  // Live audit helper: the full derived voice profile for a note id.
  profile(id) { return voiceProfileFor(id, freqOf(id)); },
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

// Expressive vibrato/tremolo belongs to Zen/focus mode like the reverb: the
// UI calls this on the same Zen transitions. Voices read the flag per note,
// so switching only changes what future notes get (short-lived voices make
// any live ramp pointless).
let vibratoEnabled = false;
function setVibratoEnabled(on) {
  vibratoEnabled = !!on;
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

// ---------------------------------------------------------------------------
// PITCH-KEYED VOICE PROFILE — interpolated/extrapolated from the alto
// recordings (analysis/alto-recordings-tone-data.json; tuner-verified C5 and
// G6 takes, C5 = the shipped ideal tone). The low end (A3-B4, below any
// measurement) is extrapolated conservatively: harmonics roughly 2x the C5
// values at A3 and somewhat deeper wobble, to be re-fitted once the physical
// triple bass can be recorded.
//
// Chamber model (from the player + fingerings.json): bigger chambers with
// more open holes lose more air, so the player must blow harder toward the
// top of every chamber — wind noise rebalances toward the upper bands, slow
// wobble deepens and the attack overshoot grows. It resets at each chamber
// boundary. The smallest (top) chamber hardly shows the drift at all, but it
// carries the measured G6 "different character": a high formant with
// H3 > H2 near 4.7 kHz that grows across chamber 3.
//
// Each table is keyed by f0 (Hz) and interpolated linearly in log2-f, with a
// slope-clamped extrapolation (max ±1.5 octaves) outside the measured range.
// ---------------------------------------------------------------------------
const V_ANCHORS = {
  // Harmonic amplitudes re H1. Deliberately smooth pitch curves: the
  // measured D6 dip (H3 0.0027) in the recordings is an artifact of that
  // alto fingering (worst case of the LARGE chamber), not a feature to copy
  // — on the triple, that pitch sits at the pure floor of chamber 3.
  h2: [[220, 0.0095], [523.25, 0.00469], [1174, 0.0040], [1568, 0.0033]],
  h3: [[220, 0.0140], [523.25, 0.0076], [1174, 0.0090], [1568, 0.021]],
  h4: [[220, 0.0015], [523.25, 0.00077], [1174, 0.0008], [1568, 0.0096]],
  h5: [[220, 0.0017], [523.25, 0.0015], [1174, 0.0006], [1568, 0.0017]],
  // Relative plateau loudness (dB vs C5). The measured chamber jumps
  // (+14.9 dB at the hard D6, +10.2 dB at G6) are dialed to a mild fraction
  // for playback; scaled live by levelCurveAmt.
  levelDb: [[220, -2.5], [523.25, 0], [1174, 6.7], [1568, 4.6]],
  // Slow intrinsic pitch wander (detrended std, cents; low notes wander
  // much more than the steadier top of the range).
  wanderC: [[220, 9.0], [523.25, 6.9], [1174, 1.3], [1568, 1.05]],
  // Breath (amplitude) wobble: depth (% of plateau) and dominant rate (Hz).
  wobPct: [[220, 7.0], [523.25, 5.5], [1568, 4.9]],
  wobHz: [[220, 2.0], [523.25, 2.5], [1568, 4.5]],
  // Wind/breath noise band re H1 (dB): the measured bands around the tone.
  // Low end is NOT conservative — the big bass chamber's hiss reads louder
  // to the player than the C5 extrapolation suggested.
  noiseLoDb: [[220, -22.0], [523.25, -25.9], [1174, -28.6], [1568, -29.4]],
  // Chamber-resonance bump sharpness of that noise: the bass chamber
  // concentrates its hiss just above the tone (residual centroid ~1.2xf0),
  // the top chamber's measured bands flatten into a broad wash. Anchored at
  // A3 too: below C5 the bump must NOT keep narrowing (an overtight bump
  // hides the noise from the ear).
  noiseBumpQ: [[220, 6.0], [523.25, 9.0], [1568, 2.5]],
  // Onset attack stretch vs C5 (measured attack time 20 → 35 ms up the range).
  attackF: [[220, 0.9], [523.25, 1.0], [1174, 1.25], [1568, 1.75]],
};

// Wind-noise spectral-shape constants (mirrored in synth_replica.py):
// white noise -> chamber bump (1.26xf0, pitch-keyed Q) -> steep noise
// lowpass. The trims are an absolute calibration of the noise chain
// against the band meters (white noise through the filters reads hotter
// than the band-relative design targets).
const WIND_SHAPE = { bumpRatio: 1.26, noiseLpRatio: 2.7, noiseLpQ: 1.2 };

// Piecewise-linear interpolation in log2-f with slope-clamped extrapolation.
function vInterp(pts, f) {
  for (let i = 0; i < pts.length - 1; i++) {
    const [f0, v0] = pts[i], [f1, v1] = pts[i + 1];
    if (f <= f1) {
      // Clamp the extrapolation span so a stray table can't run away.
      const t = Math.max(-1.5, Math.min(1.5, Math.log2(f / f0) / Math.log2(f1 / f0)));
      return v0 + (v1 - v0) * t;
    }
  }
  // Beyond the last point: continue the last segment's slope.
  const n = pts.length - 1;
  const [f0, v0] = pts[n - 1], [f1, v1] = pts[n];
  const slope = (v1 - v0) / Math.log2(f1 / f0);
  return v1 + slope * Math.max(-1.5, Math.min(1.5, Math.log2(f / f1)));
}
const db2lin = db => Math.pow(10, db / 20);

// Everything a single note's voice needs, derived live from AUDIO_DEBUG +
// V_ANCHORS + the note's chamber data (never cached — the debug panel must
// be able to retune mid-session).
function voiceProfileFor(id, freq) {
  const art = noteArticulation(id);
  // "Hard blow" drive: air lost through open holes. The larger the chamber
  // the more that loss costs breath pressure (openF weight grows with
  // sizeF), and hardAmt scales the whole effect.
  const hh = Math.max(0, Math.min(1,
    art.openF * (0.25 + 0.75 * art.sizeF) * AUDIO_DEBUG.hardAmt));
  return {
    // PeriodicWave harmonic amplitudes (real/cosine parts, h1 fixed at 1).
    h: [1,
        vInterp(V_ANCHORS.h2, freq) * AUDIO_DEBUG.h2Mul,
        vInterp(V_ANCHORS.h3, freq) * AUDIO_DEBUG.h3Mul,
        vInterp(V_ANCHORS.h4, freq) * AUDIO_DEBUG.h4Mul,
        vInterp(V_ANCHORS.h5, freq) * AUDIO_DEBUG.h5Mul],
    // Plateau loudness multiplier for the master envelope.
    levelLin: db2lin(vInterp(V_ANCHORS.levelDb, freq) * AUDIO_DEBUG.levelCurveAmt),
    // Wind noise: one chain keyed to the measured band (gain), the blow
    // shape coming out of the pitch-keyed bump Q. The loud-note part of the
    // hard signature is carried by the level curve (reproduces the real
    // absolute noise growth with breath pressure).
    windBump: db2lin(vInterp(V_ANCHORS.noiseLoDb, freq) - 2.0) * AUDIO_DEBUG.windAmt,
    windQ: vInterp(V_ANCHORS.noiseBumpQ, freq),
    // Slow intrinsic wander (one LFO drives pitch + loudness in phase,
    // like breath pressure does physically; deeper + faster on hard blow).
    wanderC: (vInterp(V_ANCHORS.wanderC, freq) + 2.0 * hh) * AUDIO_DEBUG.wanderAmt,
    wobDepth: (vInterp(V_ANCHORS.wobPct, freq) + 2.5 * hh) / 100 * AUDIO_DEBUG.wobbleAmt,
    wobRate: (vInterp(V_ANCHORS.wobHz, freq) + 1.2 * hh) * (0.9 + 0.2 * Math.random()),
    // Attack timing stretch + the blow-dependent amplitude overshoot.
    attackF: vInterp(V_ANCHORS.attackF, freq),
    osDb: 0.8 + 3.2 * hh,
  };
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

// Seamless-looping wind-noise buffer: the raw loop of white noise clicks
// every wrap (a ~10 ms broadband step at these levels), audible as ticks.
// Overwrite the buffer tail with a short crossfade INTO THE HEAD so the
// wrap is continuous; the head itself stays untouched for chiff/ot (which
// only read the first ~150 ms and never reach the tail).
let windBuf = null;
function getWindBuffer(ctx) {
  if (windBuf && windBuf.sampleRate === ctx.sampleRate) return windBuf;
  const len = Math.floor(ctx.sampleRate * 0.5);
  const buf = ctx.createBuffer(1, len, ctx.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
  const k = Math.floor(ctx.sampleRate * 0.01); // 10 ms crossfade at the seam
  for (let i = 0; i < k; i++) {
    const w = (i + 1) / (k + 1);
    d[len - k + i] = d[len - k + i] * (1 - w) + d[i] * w;
  }
  windBuf = buf;
  return buf;
}

// Cached ocarina periodic waves — one per distinct harmonic set (the
// pitch-keyed profile only changes smoothly), reused across notes instead of
// rebuilding on every note. Keyed by the rounded harmonic values; invalidated
// wholesale by the debug panel's invalidateWave().
let ocWaveCache = null;
function getOcarinaWave(ctx, vp) {
  const k = vp.h.join(",");
  if (ocWaveCache && ocWaveCache._ctx === ctx) {
    const hit = ocWaveCache.get(k);
    if (hit) return hit;
  } else {
    ocWaveCache = new Map();
    ocWaveCache._ctx = ctx;
  }
  const w = ctx.createPeriodicWave(
    new Float32Array([0].concat(vp.h)),
    new Float32Array([0, 0, 0, 0, 0, 0])
  );
  ocWaveCache.set(k, w);
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

    // Per-note voice profile (pitch-keyed harmonics, chamber-relative
    // loudness, wobble/wind levels, attack shape) — derived live so the
    // debug panel can retune anything mid-session.
    const vp = voiceProfileFor(id, freq);

    // LITE VOICE: a minimal 3-node voice (osc → lowpass → gain) for slow
    // devices. Skips the air/edge/wander/chiff/vibrato/overtone layers and
    // the profile's slow-wander/wind layers so the audio thread isn't
    // overloaded (the main crackle cause). Same pitch, level and rough
    // envelope so it still reads as the ocarina, just plainer.
    if (liteMode()) {
      const lvM = AUDIO_DEBUG.masterLevel * vp.levelLin;
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.linearRampToValueAtTime(lvM, t0 + Math.min(0.03, dur * (slideFrom ? 0.4 : 0.2)));
      g.gain.setValueAtTime(lvM, intoSlide ? t0 + dur : t0 + relStart);
      g.gain.linearRampToValueAtTime(0.0001, t0 + dur + fadeOff);
      const lp2 = ctx.createBiquadFilter();
      lp2.type = "lowpass";
      lp2.frequency.value = Math.min(AUDIO_DEBUG.lpMax, freq * AUDIO_DEBUG.lpMult);
      lp2.Q.value = AUDIO_DEBUG.lpQ;
      const osc2 = ctx.createOscillator();
      osc2.setPeriodicWave(getOcarinaWave(ctx, vp));
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

    // Zen CHORUS: sustained Zen notes double the core tone — the clean core
    // goes hard LEFT, a vibrato twin (pitch LFO only) hard RIGHT; chiff /
    // edge / wind / onset layers stay center mono (they are tiny anyway).
    // Uses the same envelope schedule on every send, and the reverb bus
    // preserves per-channel sums for stereo sources.
    const VIB_DELAY = AUDIO_DEBUG.vibDelay;
    const vibOn = vibratoEnabled &&
      (AUDIO_DEBUG.vibDepth > 1e-4 || AUDIO_DEBUG.tremDepth > 1e-4);
    const chorus = vibOn && dur > VIB_DELAY + 0.1;
    const zenPan = Math.max(0, Math.min(1, AUDIO_DEBUG.zenPan));

    const master = ctx.createGain();
    // Master plateau level (dev-tunable) scaled by the note's profile level
    // curve (mild reproduction of the measured non-monotonic chamber
    // loudness). The breathy pre-tone and "tone speaks" stages keep their
    // original proportions of 0.26 so the envelope shape is unchanged at the
    // default and simply scales with the level.
    const M = AUDIO_DEBUG.masterLevel * vp.levelLin;
    const preLevel = M * (0.05 / 0.26);   // breathy pre-tone (exactly 0.05 at default M)
    const toneLevel = M * (0.16 / 0.26);  // tone begins to speak (exactly 0.16 at default M)
    // Tone speaks slightly after onset (breathy pre-tone → full), pairing with
    // the pitch "catch up" bloom below for a soft ocarina attack. Larger
    // chambers + more open holes build pressure slower → a longer, softer
    // attack (see attackEffort), stretched further by the profile's
    // measured attack-time curve. The big bass chamber is especially
    // demanding: the pure tone takes noticeably longer to reach full
    // equilibrium.
    const art = noteArticulation(id);
    const effort = attackEffort(id, freq);
    const speak = Math.min(0.05, Math.max(0.006, dur * 0.08)) * (0.5 + effort) * vp.attackF;
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
    // Measured attack-window overshoot (0.5-4.8 dB, hard blows worse):
    // right after the tone speaks, the level briefly busts above the plateau
    // and settles back — a real "blown harder than it needs" tell.
    const osLin = slideFrom ? 1 : Math.pow(10, vp.osDb / 20);
    // The full note envelope, also reused verbatim by the Zen chorus sends.
    function schedEnv(g) {
      g.gain.setValueAtTime(0.0001, t0);
      if (slideFrom) {
        // ~ Legato: the tone carries straight over from the previous note — no
        // breathy pre-tone or tongued attack; swell to full in ~35ms while the
        // glide leaves the previous pitch.
        g.gain.linearRampToValueAtTime(M, t0 + Math.min(0.035, dur * 0.4));
      } else {
        g.gain.linearRampToValueAtTime(preLevel, t1); // breathy pre-tone
        if (t3 > t2 + 0.001) {
          if (osLin > 1.02) {
            // Overshoot bump between "tone speaks" and equilibrium, then settle.
            const osAt = Math.min(t3 - 0.01, t2 + Math.max(0.03, (t3 - t2) * 0.45));
            g.gain.linearRampToValueAtTime(toneLevel, t2); // tone begins to speak
            g.gain.linearRampToValueAtTime(M * osLin, osAt);
            g.gain.linearRampToValueAtTime(M, t3); // settles at full equilibrium
          } else {
            g.gain.linearRampToValueAtTime(toneLevel, t2); // tone begins to speak
            g.gain.linearRampToValueAtTime(M, t3); // reaches full equilibrium
          }
        } else {
          // Very short note: no room for the two-stage climb; go straight to full
          // by t2 so the automation stays monotonic and click-free.
          g.gain.linearRampToValueAtTime(M, Math.min(t2, relStartT - 0.003));
        }
      }
      g.gain.setValueAtTime(M, intoSlide ? t0 + dur : relStartT);
      g.gain.linearRampToValueAtTime(0.0001, t0 + dur + fadeOff);
      if (!intoSlide) g.gain.setValueAtTime(0.0001, t0 + dur + tail);
    }
    schedEnv(master);
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

    // Core-tone send routing for the Zen chorus (see above): CLEAN core to
    // the left channel; in normal playback the core rides master as always.
    if (chorus) {
      const coreL = ctx.createGain();
      schedEnv(coreL);
      const panL = ctx.createStereoPanner();
      panL.pan.value = -zenPan;
      trem.connect(coreL); coreL.connect(panL);
      panL.connect(getReverbBus(ctx));
    } else {
      trem.connect(master);
    }

    const wave = getOcarinaWave(ctx, vp);
    // The pitch automation (legato bend / catch-up bloom / release sag) —
    // also used verbatim by the chorus twin so both sides land identically.
    function scheduleFreq(o) {
      if (slideFrom) {
        // ~ Legato portamento: pick the pitch up exactly where the prior note
        // left off, bend fast to the target, then settle through the same tiny
        // overshoot a freshly blown note has, so the landed pitch reads + sounds
        // identically.
        const over = 1.002 + 0.004 * effort;
        const settle = Math.min(0.05, Math.max(0.02, dur * 0.2));
        o.frequency.setValueAtTime(slideFrom, t0);
        o.frequency.linearRampToValueAtTime(freq * over, t0 + glide);
        o.frequency.exponentialRampToValueAtTime(freq, t0 + glide + settle);
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
        o.frequency.setValueAtTime(freq * flat, t0);            // starts flat (air slow)
        o.frequency.linearRampToValueAtTime(freq * over, overshootAt); // overshoot sharp
        o.frequency.exponentialRampToValueAtTime(freq, settleAt);      // settle to pitch
        // Release pitch sag: as breath pressure falls at the end of the note the
        // pitch bends flat — a subtle downward "sigh". Scaled by effort/chamber
        // so bigger chambers sag a touch more. Only if the note is long enough to
        // have settled first, and never on a note that flows into a ~ slide
        // (the pitch must stay put until the glide takes over).
        if (!intoSlide && relStart > settleAt + 0.02) {
          const sag = 0.01 + 0.008 * effort; // ~17–31 cents flat over the release
          o.frequency.setValueAtTime(freq, relStart);
          o.frequency.linearRampToValueAtTime(freq * (1 - sag), t0 + dur);
        }
      }
    }
    const osc = ctx.createOscillator();
    osc.setPeriodicWave(wave);
    scheduleFreq(osc);
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

    // Slow INTRINSIC wander (the recordings' non-vibrato wobble): breath
    // pressure meanders quasi-randomly, so ONE sine reads as obvious —
    // two INCOMMENSURATE LFOs (triangle + sine at an inharmonic rate ratio,
    // per-note re-jittered so every note starts elsewhere) share the depth;
    // their sum is a meander, not a warble. Both modulations in phase with
    // each other per component: breath pressure moves pitch AND loudness
    // together. Combined depth ≈ std×0.88 (sine-equivalent) — faithful to
    // the measured detrended std WITHOUT the earlier sine overshoot.
    const wobAmpGains = [];     // shared with the chorus twin's tremolo below
    if (vp.wanderC > 0.01 || vp.wobDepth > 0.0005) {
      const comps = [
        { share: 0.85, rate: vp.wobRate, type: "triangle" },
        { share: 0.6, rate: vp.wobRate * (0.61 + 0.08 * Math.random()), type: "sine" },
      ];
      for (const c of comps) {
        const wob = ctx.createOscillator();
        wob.type = c.type;
        wob.frequency.value = c.rate;
        const wobPitch = ctx.createGain();  // pitch drift depth (Hz)
        const wobAmp = ctx.createGain();    // loudness wobble depth
        wobPitch.gain.value = freq * (Math.pow(2, vp.wanderC * 1.2 * c.share / 1200) - 1);
        wobAmp.gain.value = vp.wobDepth * 0.85 * c.share;
        // Settle in just after the attack so it doesn't smear the onset.
        wobPitch.gain.setValueAtTime(0.0001, t0);
        wobAmp.gain.setValueAtTime(0.0001, t0);
        wobPitch.gain.linearRampToValueAtTime(wobPitch.gain.value, t0 + 0.35);
        wobAmp.gain.linearRampToValueAtTime(wobAmp.gain.value, t0 + 0.35);
        wob.connect(wobPitch); wobPitch.connect(osc.frequency);
        wob.connect(wobAmp); wobAmp.connect(trem.gain);
        wob.start(t0); wob.stop(t0 + dur + stopOff);
        wobAmpGains.push(wobAmp);
      }
    }

    // Expressive vibrato ZEN MODE ONLY (vibratoEnabled, gated like the
    // reverb), and on sustained notes it runs as a stereo CHORUS: clean core
    // LEFT, vibrato twin RIGHT (see the chorus note above). The vibrato LFO
    // therefore lives on the TWIN — the left side stays clean — and short
    // notes (no room for the vibrato entry) simply stay mono-centered.
    const lfoGain = ctx.createGain();     // pitch depth
    const tremGain = ctx.createGain();    // amplitude depth (in phase)
    let twinOsc = null, lfoT = null;
    if (chorus) {
      const vibDepth = freq * AUDIO_DEBUG.vibDepth * (1 - AUDIO_DEBUG.vibHighFade * hiF); // ~6 cents, a touch less up high
      const tremDepth = AUDIO_DEBUG.tremDepth; // ~5% loudness wobble, in phase with pitch
      lfoGain.gain.setValueAtTime(0.0001, t0);
      lfoGain.gain.setValueAtTime(0.0001, t0 + VIB_DELAY);
      lfoGain.gain.linearRampToValueAtTime(vibDepth, t0 + VIB_DELAY + 0.2);
      tremGain.gain.setValueAtTime(0.0001, t0);
      tremGain.gain.setValueAtTime(0.0001, t0 + VIB_DELAY);
      tremGain.gain.linearRampToValueAtTime(tremDepth, t0 + VIB_DELAY + 0.2);
      // RIGHT channel: twin of the core tone, pitch+amp vibrato only.
      twinOsc = ctx.createOscillator();
      twinOsc.setPeriodicWave(wave);
      scheduleFreq(twinOsc);
      const lpT = ctx.createBiquadFilter();
      lpT.type = "lowpass";
      if (slideFrom) {
        lpT.frequency.setValueAtTime(Math.min(AUDIO_DEBUG.lpMax, slideFrom * AUDIO_DEBUG.lpMult), t0);
        lpT.frequency.linearRampToValueAtTime(Math.min(AUDIO_DEBUG.lpMax, freq * AUDIO_DEBUG.lpMult), t0 + glide);
      } else {
        lpT.frequency.setValueAtTime(Math.min(AUDIO_DEBUG.lpMax, freq * AUDIO_DEBUG.lpMult), t0);
      }
      lpT.Q.value = AUDIO_DEBUG.lpQ;
      const tremT = ctx.createGain();
      tremT.gain.value = 1;
      const twinEnv = ctx.createGain();
      schedEnv(twinEnv);
      const panR = ctx.createStereoPanner();
      panR.pan.value = zenPan;
      twinOsc.connect(lpT); lpT.connect(tremT); tremT.connect(twinEnv);
      twinEnv.connect(panR);
      panR.connect(getReverbBus(ctx));
      wobAmpGains.forEach(g => g.connect(tremT.gain));
      lfoT = ctx.createOscillator();
      lfoT.type = "sine";
      lfoT.frequency.value = AUDIO_DEBUG.vibRate;
      lfoT.connect(lfoGain);
      lfoGain.connect(twinOsc.frequency);
      lfoT.connect(tremGain);
      tremGain.connect(tremT.gain);
      twinOsc.start(t0); twinOsc.stop(t0 + dur + stopOff);
      lfoT.start(t0); lfoT.stop(t0 + dur + stopOff);
    } else {
      lfoGain.gain.setValueAtTime(0.0001, t0);
      tremGain.gain.setValueAtTime(0.0001, t0);
    }

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

    // Broadband wind/breath noise (measured: the band 0.85–1.95×f0 sits at
    // −26..−29 dB re H1, concentrated just above the tone by the chamber's
    // resonance). One looping noise source through the chamber bump and a
    // steep post lowpass. Truly broadband — a hard blow must NEVER be tuned
    // as a sustained pitched partial (the band-1 metric is blind to narrow
    // tones, so only the island detector can catch that mistake).
    if (vp.windBump > 1e-5) {
      const windSrc = ctx.createBufferSource();
      windSrc.buffer = getWindBuffer(ctx);
      windSrc.loop = true;
      // Chamber-resonance bump just above the tone.
      const windBp = ctx.createBiquadFilter();
      windBp.type = "bandpass";
      windBp.frequency.value = Math.min(9000, freq * WIND_SHAPE.bumpRatio);
      windBp.Q.value = vp.windQ;
      // Steep noise lowpass: keeps the hiss hugging the tone instead of a
      // bright wash at the octave+ (the recordings show the upper noise
      // bands dropping ~14+ dB by 4×f0).
      const windLp = ctx.createBiquadFilter();
      windLp.type = "lowpass";
      windLp.frequency.value = Math.min(ctx.sampleRate * 0.45, freq * WIND_SHAPE.noiseLpRatio);
      windLp.Q.value = WIND_SHAPE.noiseLpQ;
      const windGain = ctx.createGain();
      windGain.gain.setValueAtTime(0.0001, t0);
      windGain.gain.linearRampToValueAtTime(vp.windBump, t0 + 0.06);
      windGain.gain.setValueAtTime(vp.windBump, t0 + relStart);
      windGain.gain.linearRampToValueAtTime(0.0001, t0 + dur);
      windSrc.connect(windBp); windBp.connect(windLp); windLp.connect(windGain);
      windGain.connect(master);
      windSrc.start(t0);
      windSrc.stop(t0 + dur + tail);
      if (bag) bag.push({
        stop() { try { windSrc.stop(); } catch (e) {} },
        fade() { const n = ctx.currentTime + 0.05; try { windSrc.stop(n); } catch (e) {} }
      });
    }

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
      const chiffLen = Math.min(
        (AUDIO_DEBUG.chiffBase + chSize * AUDIO_DEBUG.chiffSize) * (0.85 + 0.15 * chOpen),
        relStart - 0.005);
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
      const otDur = Math.max(slideFrom ? 0.03 : 0.04,
        Math.min(otRoom, AUDIO_DEBUG.otDurMax + AUDIO_DEBUG.otDurEffort * effort)); // recorded-scale bloom
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
      const stopN = (n, t) => { try { if (n) (t == null ? n.stop() : n.stop(t)); } catch (e) {} };
      bag.push({
        // lfo/lfoT: only the chorus twin's LFO exists, and only in Zen.
        stop() { stopN(osc); stopN(twinOsc); stopN(lfoT); stopN(air); stopN(edge); stopN(wander); stopN(chiffSrc); },
        fade() {
          const now = ctx.currentTime;
          try {
            master.gain.cancelScheduledValues(now);
            master.gain.setValueAtTime(Math.max(0.0001, master.gain.value || M), now);
            master.gain.linearRampToValueAtTime(0.0001, now + 0.03);
            stopN(osc, now + 0.05); stopN(twinOsc, now + 0.05); stopN(lfoT, now + 0.05);
            stopN(air, now + 0.05); stopN(edge, now + 0.05); stopN(wander, now + 0.05);
            stopN(chiffSrc, now + 0.05);
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
