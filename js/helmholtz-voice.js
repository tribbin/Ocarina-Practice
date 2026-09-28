/**
 * Helmholtz ocarina voice — high-note air correction.
 *
 * Drop-in for js/helmholtz-voice.js. Scheduler / bags stay in audio.js.
 *
 * Air path (the 12-hole top):
 *   HP tracks 1.6×f0 (not a fixed 2800 Hz)
 *   fitted slope drives a highshelf
 *   part of the hiss bypasses period-sync so C6–F6 rush instead of buzz
 *   noise_Q falls as holes open
 */
export function loadTwinModelFromObject(obj) {
  if (!obj || !Array.isArray(obj.notes) || !obj.notes.length) {
    throw new Error("twin_model.json: missing notes[]");
  }
  const notes = obj.notes.slice().sort((a, b) => a.f0 - b.f0);
  return {
    schema: obj.schema || "ocarina-twin-v2",
    instrument: obj.instrument || "",
    chamber: String(obj.chamber || "1"),
    globals: Object.assign({
      hiss_hp_hz: 2800,          // fallback only; playback uses 1.6×f0
      hiss_hp_ratio: 1.6,
      chiff_q: 2.2,
      sync_amt: 0.65,
      drive_gain: 0.55,
      Q_prior: 45,
      dry_hiss_lo: 0.15,
      dry_hiss_hi: 0.70,
      dry_hiss_f_lo: 520,
      dry_hiss_f_hi: 1400,
    }, obj.globals || {}),
    notes,
  };
}

export async function loadTwinModel(url) {
  const obj = await fetch(url).then((r) => r.json());
  return loadTwinModelFromObject(obj);
}

function lerp(a, b, t) { return a + (b - a) * t; }
function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }
function dbToLin(db) { return Math.pow(10, db / 20); }

export function interpNote(model, f0) {
  const notes = model.notes;
  if (!notes.length) throw new Error("empty twin model");
  if (f0 <= notes[0].f0) return Object.assign({}, notes[0], { f0 });
  if (f0 >= notes[notes.length - 1].f0) {
    return Object.assign({}, notes[notes.length - 1], { f0 });
  }
  for (let i = 0; i < notes.length - 1; i++) {
    const a = notes[i], b = notes[i + 1];
    if (f0 > b.f0) continue;
    const t = Math.log(f0 / a.f0) / Math.log(b.f0 / a.f0);
    const hlen = Math.max(a.h.length, b.h.length);
    const h = [];
    for (let k = 0; k < hlen; k++) h.push(lerp(a.h[k] || 0, b.h[k] || 0, t));
    const keys = [
      "level", "Q", "noise_Q", "noise_res_db", "noise_hiss_db",
      "noise_slope_db_oct", "atk_pre_s", "atk_speak_s", "overshoot_db",
      "chiff_peak", "chiff_len_s", "rel_s", "wander_cents_std",
      "wobble_pct", "wobble_hz",
    ];
    const out = { note: null, f0, h, open_holes: t < 0.5 ? a.open_holes : b.open_holes };
    keys.forEach((k) => { out[k] = lerp(a[k], b[k], t); });
    return out;
  }
  return Object.assign({}, notes[notes.length - 1], { f0 });
}

/** Playback HP for the hole-rush path. Not globals.hiss_hp_hz. */
export function hissHpHz(f0, model) {
  const ratio = (model && model.globals && model.globals.hiss_hp_ratio) || 1.6;
  return clamp(f0 * ratio, 700, 3500);
}

/**
 * Fraction of hiss that bypasses period-sync.
 * Mid notes stay mostly locked to the jet; the 12-hole top must rush.
 */
export function dryHissFrac(f0, model) {
  const g = (model && model.globals) || {};
  const loF = g.dry_hiss_f_lo || 520;
  const hiF = g.dry_hiss_f_hi || 1400;
  const lo = g.dry_hiss_lo == null ? 0.15 : g.dry_hiss_lo;
  const hi = g.dry_hiss_hi == null ? 0.70 : g.dry_hiss_hi;
  const t = clamp((f0 - loF) / Math.max(1, hiF - loF), 0, 1);
  return lerp(lo, hi, t);
}

/**
 * Pink buffer is already ~−6 dB/oct. Fitted slope −11 is “leave it”,
 * fitted −2 (F6) needs a high shelf so 2–8 kHz comes up.
 */
export function slopeShelfDb(slopeDbOct) {
  const s = slopeDbOct == null ? -8 : slopeDbOct;
  return clamp((-6 - s) * 1.15, -2, 12);
}

/** Widen cavity-breath BP as holes open. JSON may still say noise_Q=12. */
export function effectiveNoiseQ(nf) {
  const q = Math.max(4, nf.noise_Q || 12);
  const holes = nf.open_holes;
  if (holes == null) {
    // no fingering: fade Q a little with pitch above A5
    const t = clamp((nf.f0 - 880) / 520, 0, 1);
    return lerp(q, q * 0.55, t);
  }
  const openFrac = clamp(holes / 12, 0, 1);
  return Math.max(4.5, q * (1 - 0.45 * openFrac));
}

let _noiseBuf = null;
function noiseBuffer(ctx) {
  if (_noiseBuf && _noiseBuf.sampleRate === ctx.sampleRate) return _noiseBuf;
  const n = Math.floor(ctx.sampleRate * 4);
  const buf = ctx.createBuffer(1, n, ctx.sampleRate);
  const d = buf.getChannelData(0);
  let acc = 0;
  for (let i = 0; i < n; i++) {
    acc = 0.97 * acc + (Math.random() * 2 - 1);
    d[i] = acc * 0.15;
  }
  const k = Math.floor(ctx.sampleRate * 0.01);
  for (let i = 0; i < k; i++) {
    const w = (i + 1) / (k + 1);
    d[n - k + i] = d[n - k + i] * (1 - w) + d[i] * w;
  }
  _noiseBuf = buf;
  return buf;
}

function makeAirFilter(ctx, f0, model, nf) {
  const hp = ctx.createBiquadFilter();
  hp.type = "highpass";
  hp.frequency.value = hissHpHz(f0, model);
  hp.Q.value = 0.55;

  const shelf = ctx.createBiquadFilter();
  shelf.type = "highshelf";
  shelf.frequency.value = 2200;
  shelf.gain.value = slopeShelfDb(nf.noise_slope_db_oct);
  hp.connect(shelf);
  return { input: hp, output: shelf };
}

/**
 * Build and start one note. Returns { fade, stop, until, frequency, out }.
 */
export function scheduleHelmholtzNote(ctx, dest, opts) {
  const model = opts.model;
  const f0 = +opts.f0;
  const when = Math.max(ctx.currentTime + 0.012, opts.when == null ? ctx.currentTime + 0.02 : opts.when);
  const hold = Math.max(0.05, +opts.holdSec || 0.4);
  const nf = interpNote(model, f0);
  const g = model.globals;
  const rel = opts.intoSlide ? 0.04 : Math.max(0.04, nf.rel_s || 0.07);
  const pre = Math.max(0, nf.atk_pre_s || 0.006);
  const speak = Math.max(0.006, nf.atk_speak_s || 0.02);
  const master = (opts.master != null ? opts.master : 1) * (nf.level || 1);

  const out = ctx.createGain();
  out.gain.value = master;
  out.connect(dest);

  const osc = ctx.createOscillator();
  osc.type = "sine";
  const startF = opts.slideFromHz && opts.slideFromHz > 0 ? opts.slideFromHz : f0;
  osc.frequency.setValueAtTime(startF, when);
  if (opts.slideFromHz && opts.slideFromHz > 0) {
    osc.frequency.exponentialRampToValueAtTime(Math.max(20, f0), when + (opts.slideSec || 0.03));
  }

  const wander = ctx.createOscillator();
  wander.frequency.value = Math.max(0.2, (nf.wobble_hz || 4) * 0.35);
  const wanderGain = ctx.createGain();
  wanderGain.gain.value = f0 * (Math.pow(2, (nf.wander_cents_std || 3) / 1200) - 1);
  wander.connect(wanderGain);
  wanderGain.connect(osc.frequency);

  const toneBp = ctx.createBiquadFilter();
  toneBp.type = "bandpass";
  toneBp.frequency.value = f0;
  toneBp.Q.value = Math.max(8, nf.Q || 45);

  const bodyGain = ctx.createGain();
  bodyGain.gain.value = 0;
  osc.connect(toneBp);
  toneBp.connect(bodyGain);
  bodyGain.connect(out);

  const noise = ctx.createBufferSource();
  noise.buffer = noiseBuffer(ctx);
  noise.loop = true;

  const syncOsc = ctx.createOscillator();
  syncOsc.type = "sine";
  syncOsc.frequency.value = f0;
  const shaper = ctx.createWaveShaper();
  const curve = new Float32Array(256);
  const syncAmt = g.sync_amt == null ? 0.65 : g.sync_amt;
  for (let i = 0; i < 256; i++) {
    const x = (i / 255) * 2 - 1;
    curve[i] = 0.35 + syncAmt * 0.65 * (0.5 - 0.5 * x);
  }
  shaper.curve = curve;
  const syncGain = ctx.createGain();
  syncGain.gain.value = 0;
  syncOsc.connect(shaper);
  shaper.connect(syncGain.gain);
  noise.connect(syncGain);

  const noiseBp = ctx.createBiquadFilter();
  noiseBp.type = "bandpass";
  noiseBp.frequency.value = f0;
  noiseBp.Q.value = effectiveNoiseQ(nf);
  const resGain = ctx.createGain();
  resGain.gain.value = dbToLin(nf.noise_res_db || -28);
  syncGain.connect(noiseBp);
  noiseBp.connect(resGain);
  resGain.connect(bodyGain);

  // --- hole-rush: HP(1.6 f0) + slope shelf, split dry / synced ---
  const hissLin = dbToLin(nf.noise_hiss_db || -50);
  const dry = dryHissFrac(f0, model);
  const airSync = makeAirFilter(ctx, f0, model, nf);
  const airDry = makeAirFilter(ctx, f0, model, nf);

  const hissSyncG = ctx.createGain();
  const hissDryG = ctx.createGain();
  hissSyncG.gain.value = 0;
  hissDryG.gain.value = 0;

  syncGain.connect(airSync.input);
  airSync.output.connect(hissSyncG);
  hissSyncG.connect(out);

  noise.connect(airDry.input); // dry = no sync
  airDry.output.connect(hissDryG);
  hissDryG.connect(out);

  const chiffBp = ctx.createBiquadFilter();
  chiffBp.type = "bandpass";
  chiffBp.frequency.value = f0;
  chiffBp.Q.value = g.chiff_q || 2.2;
  const chiffGain = ctx.createGain();
  chiffGain.gain.value = 0;
  syncGain.connect(chiffBp);
  chiffBp.connect(chiffGain);
  chiffGain.connect(out);

  const partials = [];
  for (let k = 2; k < (nf.h || []).length; k++) {
    const hk = nf.h[k - 1];
    if (!(hk > 1e-4)) continue;
    const p = ctx.createOscillator();
    p.type = "sine";
    p.frequency.value = f0 * k;
    const pg = ctx.createGain();
    pg.gain.value = hk;
    p.connect(pg);
    pg.connect(out);
    partials.push(p);
  }

  let vib = null;
  if (opts.vibrato && opts.vibrato.depth) {
    vib = ctx.createOscillator();
    vib.frequency.value = opts.vibrato.rate || 5.5;
    const vg = ctx.createGain();
    vg.gain.setValueAtTime(0, when);
    vg.gain.setValueAtTime(0, when + (opts.vibrato.delay || 0.35));
    vg.gain.linearRampToValueAtTime(f0 * (opts.vibrato.depth || 0.0035),
      when + (opts.vibrato.delay || 0.35) + 0.15);
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
    if (opts.intoSlide) {
      p.setValueAtTime(peak, tHoldEnd);
    } else {
      p.setValueAtTime(peak, Math.max(tSpeak + 0.02, tHoldEnd - rel));
      p.linearRampToValueAtTime(0, tOff);
    }
  }
  envGain(bodyGain, 1);
  envGain(hissSyncG, hissLin * (1 - dry));
  envGain(hissDryG, hissLin * dry);

  const chiffPeak = Math.max(0, (nf.chiff_peak || 1) - 1) * dbToLin(nf.noise_res_db || -28);
  const tCh0 = tOn;
  const tCh1 = tOn + Math.max(0.02, nf.chiff_len_s || 0.045);
  chiffGain.gain.setValueAtTime(0, when);
  chiffGain.gain.setValueAtTime(0, tCh0);
  chiffGain.gain.linearRampToValueAtTime(chiffPeak, tCh0 + (tCh1 - tCh0) * 0.35);
  chiffGain.gain.linearRampToValueAtTime(0, tCh1);

  osc.start(when); wander.start(when); syncOsc.start(when); noise.start(when);
  partials.forEach((p) => p.start(when));
  if (vib) vib.start(when);

  const stopAt = tOff + 0.02;
  function stopNodes(t) {
    const tt = t != null ? t : ctx.currentTime;
    try { osc.stop(tt); } catch (e) {}
    try { wander.stop(tt); } catch (e) {}
    try { syncOsc.stop(tt); } catch (e) {}
    try { noise.stop(tt); } catch (e) {}
    partials.forEach((p) => { try { p.stop(tt); } catch (e) {} });
    if (vib) try { vib.stop(tt); } catch (e) {}
  }
  if (!opts.intoSlide) stopNodes(stopAt);

  return {
    until: stopAt,
    fade(t) {
      const tt = t != null ? t : ctx.currentTime;
      try {
        bodyGain.gain.cancelScheduledValues(tt);
        bodyGain.gain.setValueAtTime(bodyGain.gain.value, tt);
        bodyGain.gain.linearRampToValueAtTime(0, tt + 0.03);
      } catch (e) {}
      try {
        hissSyncG.gain.cancelScheduledValues(tt);
        hissDryG.gain.cancelScheduledValues(tt);
        hissSyncG.gain.setValueAtTime(hissSyncG.gain.value, tt);
        hissDryG.gain.setValueAtTime(hissDryG.gain.value, tt);
        hissSyncG.gain.linearRampToValueAtTime(0, tt + 0.03);
        hissDryG.gain.linearRampToValueAtTime(0, tt + 0.03);
      } catch (e) {}
      stopNodes(tt + 0.04);
    },
    stop(t) { this.fade(t); },
    frequency: osc.frequency,
    out,
  };
}
