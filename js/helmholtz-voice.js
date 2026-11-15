/**
 * Helmholtz voice, v4-breath graph. The fitted tone path is unchanged:
 * phase-locked partials, slope-colored floor, same body envelope timing.
 * The air noise is a pitch-locked breath engine: band-passed colored noise,
 * f0 comb, f0 AM, a measured/default voicing-formant bump, open-hole vent
 * scaling, an attack excess that decays as the jet locks, sustain wander
 * drift and a release swell. ?breath=0 keeps the plain band-pass path.
 */
export const VOICE_REV = "v4-breath";

// Breath-engine defaults. Every one is safe when a twin model predates the
// fields (the loader keeps today's rows working unchanged).
export const BREATH_DEFAULTS = {
  combFeedback: 0.35,
  combWet: 0.6,
  amDepth: 0.5,
  bandMult: 1.25,
  bandQ: 1.0,
  formantMult: 2.2,
  formantQ: 1.0,
  formantGainDb: 6,
  ventK: 0.25,
  ventGainExp: 0.5,
  ventFloor: 0.15,
  atkOverAirDb: 6,
  driftDb: 1.5,
  releaseSwellDb: 3,
  releaseSwellS: 0.015,
  tongueOverAirDb: 6,
  tongueLenS: 0.01,
  tongueLeadS: 0.015,
};

export function loadTwinModelFromObject(obj) {
  if (!obj || !Array.isArray(obj.notes) || !obj.notes.length) {
    throw new Error("twin_model.json: missing notes[]");
  }
  const notes = obj.notes.slice().sort((a, b) => a.f0 - b.f0);
  return {
    schema: obj.schema || "ocarina-twin-v2",
    instrument: obj.instrument || "",
    chamber: String(obj.chamber || "1"),
    globals: Object.assign({ chiff_q: 2.2 }, obj.globals || {}),
    notes,
  };
}

export async function loadTwinModel(url) {
  const obj = await fetch(url).then((r) => r.json());
  return loadTwinModelFromObject(obj);
}

function lerp(a, b, t) { return a + (b - a) * t; }
function dbToLin(db) { return Math.pow(10, db / 20); }

export function interpNote(model, f0) {
  const notes = model.notes;
  if (!notes.length) throw new Error("empty twin model");
  if (f0 <= notes[0].f0) return Object.assign({}, notes[0], { f0 });
  if (f0 >= notes[notes.length - 1].f0) return Object.assign({}, notes[notes.length - 1], { f0 });
  for (let i = 0; i < notes.length - 1; i++) {
    const a = notes[i], b = notes[i + 1];
    if (f0 > b.f0) continue;
    const t = Math.log(f0 / a.f0) / Math.log(b.f0 / a.f0);
    const hlen = Math.max((a.h || []).length, (b.h || []).length);
    const h = [], hPhase = [];
    for (let k = 0; k < hlen; k++) {
      h.push(lerp(a.h[k] || 0, b.h[k] || 0, t));
      hPhase.push(lerp((a.h_phase && a.h_phase[k]) || 0, (b.h_phase && b.h_phase[k]) || 0, t));
    }
    const keys = [
      "level", "Q", "floor_db", "slope_db_oct", "air_db", "air_lo_hz", "air_hi_hz",
      "atk_pre_s", "atk_speak_s", "overshoot_db", "chiff_peak", "chiff_len_s",
      "rel_s", "wander_cents_std", "wobble_hz",
    ];
    const out = { note: null, f0, h, h_phase: hPhase };
    keys.forEach((k) => { out[k] = lerp(a[k] == null ? 0 : a[k], b[k] == null ? 0 : b[k], t); });
    // Optional breath fields interpolate only when a fit actually supplied
    // them; one-sided rows keep the supplied side (per-field fallback).
    for (const k of ["air_formant_hz", "air_formant_q", "atk_noise_db"]) {
      if (a[k] != null && b[k] != null) out[k] = lerp(+a[k], +b[k], t);
      else if (a[k] != null) out[k] = +a[k];
      else if (b[k] != null) out[k] = +b[k];
    }
    return out;
  }
  return Object.assign({}, notes[notes.length - 1], { f0 });
}

function fftRadix(re, im, inv) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      let t = re[i]; re[i] = re[j]; re[j] = t;
      t = im[i]; im[i] = im[j]; im[j] = t;
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (inv ? 2 : -2) * Math.PI / len;
    const wlenRe = Math.cos(ang), wlenIm = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let wRe = 1, wIm = 0;
      for (let j = 0; j < len / 2; j++) {
        const uRe = re[i + j], uIm = im[i + j];
        const vRe = re[i + j + len / 2] * wRe - im[i + j + len / 2] * wIm;
        const vIm = re[i + j + len / 2] * wIm + im[i + j + len / 2] * wRe;
        re[i + j] = uRe + vRe; im[i + j] = uIm + vIm;
        re[i + j + len / 2] = uRe - vRe; im[i + j + len / 2] = uIm - vIm;
        const nRe = wRe * wlenRe - wIm * wlenIm;
        wIm = wRe * wlenIm + wIm * wlenRe;
        wRe = nRe;
      }
    }
  }
  if (inv) for (let i = 0; i < n; i++) { re[i] /= n; im[i] /= n; }
}

const _colored = new Map();
function coloredBuffer(ctx, slope) {
  const key = slope.toFixed(2) + ":" + ctx.sampleRate;
  if (_colored.has(key)) return _colored.get(key);
  const n = 131072;
  const re = new Float64Array(n);
  const im = new Float64Array(n);
  for (let i = 0; i < n; i++) re[i] = Math.random() * 2 - 1;
  fftRadix(re, im, false);
  const df = ctx.sampleRate / n;
  for (let k = 0; k < n / 2; k++) {
    const f = k * df;
    const s = f > 40 ? Math.pow(f / 700, slope / 6) : 0;
    re[k] *= s; im[k] *= s;
    if (k > 0) { re[n - k] *= s; im[n - k] *= s; }
  }
  fftRadix(re, im, true);
  let acc = 0;
  for (let i = 0; i < n; i++) acc += re[i] * re[i];
  const rms = Math.sqrt(acc / n) || 1;
  const buf = ctx.createBuffer(1, n, ctx.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = re[i] / rms;
  _colored.set(key, buf);
  return buf;
}

function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }

// Vent scaling (Step 2): a note's open-hole area relative to the chart's
// total hole area. Holes may declare `area`; otherwise each hole counts as
// one unit (the documented fallback). Half-vented holes count half. The
// floor keeps the windway/labium hiss alive on a fully closed note instead
// of multiplying the air band to silence.
export function ventScale(fingering, holes) {
  const flat = { ratio: 1, cutoff: 1, gain: 1, sourced: false };
  if (!fingering || !Array.isArray(fingering.covered)) return flat;
  if (!holes || typeof holes !== "object" || Array.isArray(holes)) return flat;
  const ids = Object.keys(holes);
  if (!ids.length) return flat;
  const covered = new Set(fingering.covered);
  const half = new Set(Array.isArray(fingering.half) ? fingering.half : []);
  let total = 0, open = 0;
  for (const id of ids) {
    const h = holes[id] && typeof holes[id] === "object" ? holes[id] : {};
    const area = isFinite(h.area) && h.area > 0 ? +h.area : 1;
    total += area;
    if (!covered.has(id)) open += half.has(id) ? area * 0.5 : area;
  }
  if (total <= 0) return flat;
  const ratio = clamp(open / total, BREATH_DEFAULTS.ventFloor, 1);
  return {
    ratio,
    cutoff: Math.pow(ratio, BREATH_DEFAULTS.ventK),
    gain: Math.pow(ratio, BREATH_DEFAULTS.ventGainExp),
    sourced: true,
  };
}

function formantOf(nf, f0, lo, hi) {
  const hz = nf.air_formant_hz != null
    ? clamp(+nf.air_formant_hz, 60, 16000)
    : clamp(BREATH_DEFAULTS.formantMult * f0, lo, hi);
  const q = nf.air_formant_q != null
    ? Math.max(0.1, +nf.air_formant_q)
    : BREATH_DEFAULTS.formantQ;
  return { hz, q };
}

function leanedWave(ctx, h, phase) {
  const n = Math.max(5, (h || []).length + 1);
  const real = new Float32Array(n);
  const imag = new Float32Array(n);
  for (let k = 1; k < n; k++) {
    const amp = h[k - 1] || 0;
    const ph = (phase && phase[k - 1]) || 0;
    real[k] = amp * Math.sin(ph);
    imag[k] = amp * Math.cos(ph);
  }
  return ctx.createPeriodicWave(real, imag, { disableNormalization: true });
}

export function scheduleHelmholtzNote(ctx, dest, opts) {
  const model = opts.model;
  const f0 = +opts.f0;
  const when = Math.max(ctx.currentTime + 0.012, opts.when == null ? ctx.currentTime + 0.02 : opts.when);
  const hold = Math.max(0.05, +opts.holdSec || 0.4);
  const nf = interpNote(model, f0);
  const g = model.globals;
  const rel = opts.intoSlide ? 0.04 : Math.max(0.04, nf.rel_s || 0.08);
  const pre = Math.max(0, nf.atk_pre_s || 0.01);
  const speak = Math.max(0.006, nf.atk_speak_s || 0.03);
  const master = (opts.master != null ? opts.master : 1) * (nf.level || 1);
  const breath = opts.breath !== false;
  const solo = !!opts.soloAir;
  const vent = breath ? ventScale(opts.fingering, opts.holes)
                       : { ratio: 1, cutoff: 1, gain: 1, sourced: false };

  const out = ctx.createGain();
  out.gain.value = master;
  out.connect(dest);

  const osc = ctx.createOscillator();
  osc.setPeriodicWave(leanedWave(ctx, nf.h, nf.h_phase));
  const startF = opts.slideFromHz && opts.slideFromHz > 0 ? opts.slideFromHz : f0;
  osc.frequency.setValueAtTime(startF, when);
  if (opts.slideFromHz && opts.slideFromHz > 0) {
    osc.frequency.exponentialRampToValueAtTime(Math.max(20, f0), when + (opts.slideSec || 0.03));
  }
  const wander = ctx.createOscillator();
  wander.frequency.value = nf.wobble_hz || 0.45;
  const wanderGain = ctx.createGain();
  wanderGain.gain.value = f0 * 0.0015;
  wander.connect(wanderGain);
  wanderGain.connect(osc.frequency);

  const bodyGain = ctx.createGain();
  bodyGain.gain.value = 0;
  osc.connect(bodyGain);
  bodyGain.connect(out);

  const noise = ctx.createBufferSource();
  noise.buffer = coloredBuffer(ctx, nf.slope_db_oct == null ? -6 : nf.slope_db_oct);
  noise.loop = true;

  const floorGain = ctx.createGain();
  floorGain.gain.value = 0;
  noise.connect(floorGain);
  floorGain.connect(out);

  // Air noise (Step 1/2): native band-pass on the shared colored buffer.
  // The vent factor scales the upper cutoff and the path level; a fitted
  // voicing formant is a peaking node; the comb/AM layers lock the noise
  // to the sounding note. ?breath=0 stops at the plain band-pass.
  const airLo = nf.air_lo_hz || 1800;
  const airHi = Math.max(airLo, (nf.air_hi_hz || 4500) * vent.cutoff);
  const airLin = dbToLin(nf.air_db == null ? -50 : nf.air_db) * vent.gain;
  const air = ctx.createBufferSource();
  air.buffer = noise.buffer;
  air.loop = true;
  const airBp = ctx.createBiquadFilter();
  airBp.type = "bandpass";
  airBp.frequency.value = clamp(BREATH_DEFAULTS.bandMult * f0, airLo, airHi);
  airBp.Q.value = BREATH_DEFAULTS.bandQ;
  const airGain = ctx.createGain();
  airGain.gain.value = 0;
  air.connect(airBp);
  airGain.connect(out);

  let formant = null, combDelay = null, combFeedback = null, combDry = null,
      combWet = null, amOsc = null, amGain = null, amDepth = null,
      driftGain = null, excessGain = null;
  if (breath) {
    const form = formantOf(nf, f0, airLo, airHi);
    formant = ctx.createBiquadFilter();
    formant.type = "peaking";
    formant.frequency.value = form.hz;
    formant.Q.value = form.q;
    formant.gain.value = BREATH_DEFAULTS.formantGainDb;
    airBp.connect(formant);

    // f0 comb: dry + delayed/feedback path mixed back together.
    combDelay = ctx.createDelay(0.06);
    combDelay.delayTime.value = 1 / f0;
    combFeedback = ctx.createGain();
    combFeedback.gain.value = BREATH_DEFAULTS.combFeedback;
    combDry = ctx.createGain();
    combDry.gain.value = 1 - BREATH_DEFAULTS.combWet;
    combWet = ctx.createGain();
    combWet.gain.value = BREATH_DEFAULTS.combWet;
    const mix = ctx.createGain();
    mix.gain.value = 1;
    formant.connect(combDry); combDry.connect(mix);
    formant.connect(combDelay); combDelay.connect(combWet); combWet.connect(mix);
    combDelay.connect(combFeedback); combFeedback.connect(combDelay);

    // AM at f0: a gain node whose gain swings ±amDepth around 1.
    amGain = ctx.createGain();
    amGain.gain.value = 1;
    amOsc = ctx.createOscillator();
    amOsc.type = "sine";
    amOsc.frequency.value = f0;
    amDepth = ctx.createGain();
    amDepth.gain.value = BREATH_DEFAULTS.amDepth;
    amOsc.connect(amDepth); amDepth.connect(amGain.gain);
    mix.connect(amGain);
    amGain.connect(airGain);

    // Attack excess (Step 3): starts at the chiff-peak class level and
    // decays to nothing as the jet locks, leaving the sustain air_db bed.
    excessGain = ctx.createGain();
    excessGain.gain.value = 0;
    amGain.connect(excessGain);
    excessGain.connect(out);

    // Breath instability: the existing wander oscillator adds a small
    // ±1.5 dB drift around the sustain air level.
    driftGain = ctx.createGain();
    driftGain.gain.value = airLin * (dbToLin(BREATH_DEFAULTS.driftDb) - 1);
    wander.connect(driftGain);
    driftGain.connect(airGain.gain);
  } else {
    airBp.connect(airGain);
  }

  let chiffBp = null, chiffGain = null;
  if (!breath) {
    chiffBp = ctx.createBiquadFilter();
    chiffBp.type = "bandpass";
    chiffBp.frequency.value = Math.min(1800, Math.max(400, f0 * 3));
    chiffBp.Q.value = g.chiff_q || 2.2;
    chiffGain = ctx.createGain();
    chiffGain.gain.value = 0;
    noise.connect(chiffBp);
    chiffBp.connect(chiffGain);
    chiffGain.connect(out);
  }

  let vib = null;
  if (opts.vibrato && opts.vibrato.depth) {
    vib = ctx.createOscillator();
    vib.frequency.value = opts.vibrato.rate || 5.5;
    const vg = ctx.createGain();
    vg.gain.setValueAtTime(0, when);
    vg.gain.setValueAtTime(0, when + (opts.vibrato.delay || 0.35));
    vg.gain.linearRampToValueAtTime(f0 * (opts.vibrato.depth || 0.0035), when + (opts.vibrato.delay || 0.35) + 0.15);
    vib.connect(vg);
    vg.connect(osc.frequency);
  }

  const tOn = when + pre;
  const tSpeak = tOn + speak;
  const tHoldEnd = when + hold;
  const tOff = tHoldEnd + rel;
  const os = Math.pow(10, (nf.overshoot_db || 0) / 20);
  const speakAt = hold < 0.16 ? tOn + Math.min(speak, Math.max(0.008, hold * 0.35)) : tSpeak;
  function envGain(node, peak) {
    const p = node.gain;
    p.cancelScheduledValues(when);
    p.setValueAtTime(0, when);
    p.setValueAtTime(0, tOn);
    p.linearRampToValueAtTime(peak * os, speakAt);
    p.linearRampToValueAtTime(peak, speakAt + 0.02);
    if (opts.intoSlide) p.setValueAtTime(peak, tHoldEnd);
    else {
      // Release stays inside the hold the page already shortened. Do not subtract rel again.
      p.setValueAtTime(peak, Math.max(speakAt + 0.015, tHoldEnd - 0.012));
      p.linearRampToValueAtTime(0.0001, tOff);
    }
  }
  // Air envelope (Step 3): the same attack/settle timeline, plus the small
  // release puff just before the hold ends. The ramp still lands at tOff,
  // so the release never outlasts the already-shortened hold.
  const swellEnd = opts.intoSlide ? null
    : Math.max(speakAt + 0.015, tHoldEnd - 0.012);
  const swellStart = swellEnd == null ? null
    : Math.max(speakAt + 0.002, swellEnd - BREATH_DEFAULTS.releaseSwellS);
  function envBreathGain(node, peak) {
    const p = node.gain;
    p.cancelScheduledValues(when);
    p.setValueAtTime(0, when);
    p.setValueAtTime(0, tOn);
    p.linearRampToValueAtTime(peak * os, speakAt);
    if (opts.intoSlide) {
      p.linearRampToValueAtTime(peak, speakAt + 0.02);
      p.setValueAtTime(peak, tHoldEnd);
    } else {
      p.linearRampToValueAtTime(peak, swellStart);
      p.linearRampToValueAtTime(peak * dbToLin(BREATH_DEFAULTS.releaseSwellDb), swellEnd);
      p.linearRampToValueAtTime(0.0001, tOff);
    }
  }
  envGain(bodyGain, solo ? 0.0001 : 1);
  envGain(floorGain, solo ? 0.0001 : dbToLin(nf.floor_db == null ? -54 : nf.floor_db));
  if (breath) envBreathGain(airGain, airLin);
  else envGain(airGain, airLin);

  const atkDb = nf.atk_noise_db != null ? +nf.atk_noise_db
    : (nf.air_db == null ? -50 : nf.air_db) + BREATH_DEFAULTS.atkOverAirDb;
  const atkLin = dbToLin(atkDb) * vent.gain;
  const atkPeakAt = tOn + Math.min(0.01, speak * 0.35);
  if (excessGain) {
    const p = excessGain.gain;
    p.setValueAtTime(0.0001, when);
    p.setValueAtTime(0.0001, tOn);
    p.exponentialRampToValueAtTime(Math.max(0.0001, atkLin), atkPeakAt);
    p.exponentialRampToValueAtTime(0.0001, tSpeak);
  }

  // Plain path keeps the legacy chiff burst; the engine's attack excess
  // replaces it (the chiff only survives under ?breath=0 for A/B).
  if (!breath && hold >= 0.16) {
    const chiffPeak = solo ? 0.0001
      : dbToLin((nf.air_db == null ? -50 : nf.air_db) + 4);
    const tCh1 = tOn + Math.max(0.02, nf.chiff_len_s || 0.028);
    chiffGain.gain.setValueAtTime(0.0001, when);
    chiffGain.gain.exponentialRampToValueAtTime(Math.max(0.0001, chiffPeak), tOn + (tCh1 - tOn) * 0.35);
    chiffGain.gain.exponentialRampToValueAtTime(0.0001, tCh1);
  }

  osc.start(when); wander.start(when);
  const span = Math.max(0, noise.buffer.duration - 0.05);
  const noiseOff = Math.random() * span;
  let airOff = Math.random() * span;
  if (breath && span > 0) {
    // Decorrelate the two beds: never let the air source replay the floor's
    // exact loop position.
    if (Math.abs(airOff - noiseOff) < span * 0.1) airOff = (airOff + span * 0.5) % span;
  } else {
    airOff = noiseOff; // the legacy correlated bed
  }
  noise.start(when, noiseOff); air.start(when, airOff);
  if (amOsc) amOsc.start(when);
  if (vib) vib.start(when);
  const stopAt = tOff + 0.06;
  function stopNodes(t) {
    const tt = t != null ? t : ctx.currentTime;
    try { osc.stop(tt); } catch (e) {}
    try { wander.stop(tt); } catch (e) {}
    try { noise.stop(tt); } catch (e) {}
    try { air.stop(tt); } catch (e) {}
    if (amOsc) try { amOsc.stop(tt); } catch (e) {}
    if (vib) try { vib.stop(tt); } catch (e) {}
  }
  if (!opts.intoSlide) stopNodes(stopAt);
  return {
    until: stopAt,
    fade(t) {
      const tt = t != null ? t : ctx.currentTime;
      for (const node of [bodyGain, floorGain, airGain, excessGain, driftGain, chiffGain]) {
        if (!node) continue;
        try {
          node.gain.cancelScheduledValues(tt);
          node.gain.setValueAtTime(node.gain.value, tt);
          node.gain.linearRampToValueAtTime(0.0001, tt + 0.05);
        } catch (e) {}
      }
      stopNodes(tt + 0.09);
    },
    stop(t) { this.fade(t); },
    frequency: osc.frequency,
    out,
    // Debug/test seam: the breath graph's nodes, offsets and computed
    // timeline (not part of the audible signal path).
    _breath: {
      mode: breath ? "engine" : "plain",
      solo,
      vent,
      airBp, formant, combDelay, combFeedback, combDry, combWet,
      amOsc, amGain, amDepth, airGain, excessGain, driftGain, chiffBp, chiffGain,
      airLo, airHi, airLin, atkLin,
      noiseOffset: noiseOff,
      airOffset: airOff,
      timeline: {
        when, tOn, tSpeak, speakAt, tHoldEnd, tOff, stopAt,
        atkPeakAt, atkEnd: tSpeak, atkDb,
        swellStart, swellEnd,
        airDb: nf.air_db == null ? -50 : nf.air_db,
        hold, rel,
      },
    },
  };
}

// Human articulation (Step 4): a tiny tongued onset burst through the same
// voicing-formant filter, scheduled just ahead of the body onset. The
// scheduler decides when a token is a staccato or a re-attack after a rest;
// this builder only makes the sound. It starts ~15 ms before the body onset,
// so its start is intentionally just ahead of the note's own `when`.
export function scheduleTongueBurst(ctx, dest, opts) {
  const model = opts.model;
  const f0 = +opts.f0;
  const when = Math.max(ctx.currentTime + 0.008,
                         opts.when == null ? ctx.currentTime + 0.02 : opts.when);
  const nf = interpNote(model, f0);
  const vent = ventScale(opts.fingering, opts.holes);
  const lo = nf.air_lo_hz || 1800;
  const hi = Math.max(lo, (nf.air_hi_hz || 4500) * vent.cutoff);
  const form = formantOf(nf, f0, lo, hi);
  const noise = ctx.createBufferSource();
  noise.buffer = coloredBuffer(ctx, nf.slope_db_oct == null ? -6 : nf.slope_db_oct);
  noise.loop = true;
  const bandpass = ctx.createBiquadFilter();
  bandpass.type = "bandpass";
  bandpass.frequency.value = form.hz;
  bandpass.Q.value = form.q;
  const formant = ctx.createBiquadFilter();
  formant.type = "peaking";
  formant.frequency.value = form.hz;
  formant.Q.value = form.q;
  formant.gain.value = BREATH_DEFAULTS.formantGainDb;
  const gain = ctx.createGain();
  gain.gain.value = 0;
  noise.connect(bandpass);
  bandpass.connect(formant);
  formant.connect(gain);
  gain.connect(dest);
  const level = dbToLin((nf.air_db == null ? -50 : nf.air_db)
                         + BREATH_DEFAULTS.tongueOverAirDb) * vent.gain;
  const t1 = when + BREATH_DEFAULTS.tongueLenS;
  gain.gain.setValueAtTime(0.0001, when);
  gain.gain.linearRampToValueAtTime(Math.max(0.0001, level), when + 0.002);
  gain.gain.exponentialRampToValueAtTime(0.0001, t1);
  const offset = Math.random() * Math.max(0, noise.buffer.duration - 0.05);
  noise.start(when, offset);
  const stopAt = t1 + 0.02;
  try { noise.stop(stopAt); } catch (e) {}
  return {
    until: stopAt,
    fade(t) {
      const tt = t != null ? t : ctx.currentTime;
      try {
        gain.gain.cancelScheduledValues(tt);
        gain.gain.setValueAtTime(gain.gain.value, tt);
        gain.gain.linearRampToValueAtTime(0.0001, tt + 0.02);
        noise.stop(tt + 0.04);
      } catch (e) {}
    },
    stop(t) { this.fade(t); },
    kill() { gain.disconnect(); },
    _breath: {
      kind: "tongue",
      bandpass, formant, gain, offset,
      timeline: { when, end: t1, stopAt },
    },
  };
}
