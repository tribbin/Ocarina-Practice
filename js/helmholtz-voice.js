/**
 * Helmholtz voice, v3k graph. Same signal as the Python ladder renderer:
 * phase-locked partials, slope-colored floor, air band, chiff only at the attack.
 * No halo, no cavity band-pass. Envelope timing is unchanged.
 */
export const VOICE_REV = "v3k-chamber";

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
  const n = 16384;
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
  const fade = Math.floor(ctx.sampleRate * 0.02);
  for (let i = 0; i < n; i++) d[i] = re[i] / rms;
  for (let i = 0; i < fade; i++) {
    const w = i / fade;
    const tail = d[n - fade + i];
    d[n - fade + i] = tail * (1 - w) + d[i] * w;
  }
  _colored.set(key, buf);
  return buf;
}


function biquad(type, freq, sr) {
  const w0 = 2 * Math.PI * freq / sr;
  const cos = Math.cos(w0), sin = Math.sin(w0);
  const alpha = sin / (2 * 0.707);
  let b0, b1, b2, a0, a1, a2;
  if (type === "hp") {
    b0 = (1 + cos) / 2; b1 = -(1 + cos); b2 = (1 + cos) / 2;
  } else {
    b0 = (1 - cos) / 2; b1 = 1 - cos; b2 = (1 - cos) / 2;
  }
  a0 = 1 + alpha; a1 = -2 * cos; a2 = 1 - alpha;
  return [b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0];
}
function runBiquad(src, c) {
  const out = new Float32Array(src.length);
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < src.length; i++) {
    const x = src[i];
    const y = c[0] * x + c[1] * x1 + c[2] * x2 - c[3] * y1 - c[4] * y2;
    x2 = x1; x1 = x; y2 = y1; y1 = y;
    out[i] = y;
  }
  return out;
}
function airBuffer(ctx, src, lo, hi) {
  const d = src.getChannelData(0);
  let y = runBiquad(d, biquad("hp", lo, ctx.sampleRate));
  y = runBiquad(y, biquad("lp", hi, ctx.sampleRate));
  let acc = 0;
  for (let i = 0; i < y.length; i++) acc += y[i] * y[i];
  const rms = Math.sqrt(acc / y.length) || 1;
  const buf = ctx.createBuffer(1, y.length, ctx.sampleRate);
  const o = buf.getChannelData(0);
  for (let i = 0; i < y.length; i++) o[i] = y[i] / rms;
  return buf;
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

  const air = ctx.createBufferSource();
  air.buffer = airBuffer(ctx, noise.buffer, nf.air_lo_hz || 1800, nf.air_hi_hz || 4500);
  air.loop = true;
  const airGain = ctx.createGain();
  airGain.gain.value = 0;
  air.connect(airGain);
  airGain.connect(out);

  const chiffBp = ctx.createBiquadFilter();
  chiffBp.type = "bandpass";
  chiffBp.frequency.value = Math.min(1800, Math.max(400, f0 * 3));
  chiffBp.Q.value = g.chiff_q || 2.2;
  const chiffGain = ctx.createGain();
  chiffGain.gain.value = 0;
  noise.connect(chiffBp);
  chiffBp.connect(chiffGain);
  chiffGain.connect(out);

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
  function envGain(node, peak) {
    const p = node.gain;
    p.cancelScheduledValues(when);
    p.setValueAtTime(0, when);
    p.setValueAtTime(0, tOn);
    p.linearRampToValueAtTime(peak * os, tSpeak);
    p.linearRampToValueAtTime(peak, tSpeak + 0.04);
    if (opts.intoSlide) p.setValueAtTime(peak, tHoldEnd);
    else {
      p.setValueAtTime(peak, Math.max(tSpeak + 0.02, tHoldEnd - rel));
      p.linearRampToValueAtTime(0, tOff);
    }
  }
  envGain(bodyGain, 1);
  envGain(floorGain, dbToLin(nf.floor_db == null ? -54 : nf.floor_db));
  envGain(airGain, dbToLin(nf.air_db == null ? -50 : nf.air_db));
  const chiffPeak = dbToLin((nf.air_db == null ? -50 : nf.air_db) + 4);
  const tCh1 = tOn + Math.max(0.02, nf.chiff_len_s || 0.028);
  chiffGain.gain.setValueAtTime(0, when);
  chiffGain.gain.setValueAtTime(0, tOn);
  chiffGain.gain.linearRampToValueAtTime(chiffPeak, tOn + (tCh1 - tOn) * 0.35);
  chiffGain.gain.linearRampToValueAtTime(0, tCh1);

  osc.start(when); wander.start(when); noise.start(when); air.start(when);
  if (vib) vib.start(when);
  const stopAt = tOff + 0.06;
  function stopNodes(t) {
    const tt = t != null ? t : ctx.currentTime;
    try { osc.stop(tt); } catch (e) {}
    try { wander.stop(tt); } catch (e) {}
    try { noise.stop(tt); } catch (e) {}
    try { air.stop(tt); } catch (e) {}
    if (vib) try { vib.stop(tt); } catch (e) {}
  }
  if (!opts.intoSlide) stopNodes(stopAt);
  return {
    until: stopAt,
    fade(t) {
      const tt = t != null ? t : ctx.currentTime;
      for (const node of [bodyGain, floorGain, airGain, chiffGain]) {
        try {
          node.gain.cancelScheduledValues(tt);
          node.gain.setValueAtTime(node.gain.value, tt);
          node.gain.linearRampToValueAtTime(0, tt + 0.05);
        } catch (e) {}
      }
      stopNodes(tt + 0.07);
    },
    stop(t) { this.fade(t); },
    frequency: osc.frequency,
    out,
  };
}
