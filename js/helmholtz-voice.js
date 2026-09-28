/**
 * Helmholtz voice — Grok mid-air revision 2026-09-29b (quiet air).
 *
 * LEAD SPEC. Do not put air on a 2.2 kHz highshelf. E6/F6 air is
 * the [1.25 f0, 4 kHz] pedestal. 4–12 kHz must stay quieter than that.
 *
 * Numbers: python/ocarina_twin/air.py — keep JS in lockstep.
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
      hiss_hp_hz: 4000,
      hiss_hp_ratio: 1.25,
      chiff_q: 2.2,
      sync_amt: 0.65,
      drive_gain: 0.55,
      dry_hiss_lo: 0.20,
      dry_hiss_hi: 0.75,
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
      "level", "Q", "noise_Q", "noise_res_db", "noise_mid_db", "noise_hiss_db",
      "noise_slope_db_oct", "atk_pre_s", "atk_speak_s", "overshoot_db",
      "chiff_peak", "chiff_len_s", "rel_s", "wander_cents_std",
      "wobble_pct", "wobble_hz",
    ];
    const out = { note: null, f0, h, open_holes: t < 0.5 ? a.open_holes : b.open_holes };
    keys.forEach((k) => {
      const av = a[k], bv = b[k];
      if (av == null && bv == null) return;
      out[k] = lerp(av == null ? bv : av, bv == null ? av : bv, t);
    });
    if (out.noise_mid_db == null) {
      out.noise_mid_db = (out.noise_hiss_db || -50) + 8;
    }
    return out;
  }
  return Object.assign({}, notes[notes.length - 1], { f0 });
}

export function midLoHz(f0) { return clamp(f0 * 1.25, 200, 3500); }
export function midHiHz() { return 4000; }

export function dryMidFrac(f0, model) {
  const g = (model && model.globals) || {};
  const loF = g.dry_hiss_f_lo || 520;
  const hiF = g.dry_hiss_f_hi || 1400;
  const lo = g.dry_hiss_lo == null ? 0.20 : g.dry_hiss_lo;
  const hi = g.dry_hiss_hi == null ? 0.75 : g.dry_hiss_hi;
  const t = clamp((f0 - loF) / Math.max(1, hiF - loF), 0, 1);
  return lerp(lo, hi, t);
}

export function effectiveNoiseQ(nf) {
  const q = Math.max(3.5, nf.noise_Q || 12);
  const holes = nf.open_holes;
  if (holes == null) {
    const t = clamp((nf.f0 - 880) / 520, 0, 1);
    return Math.max(3.8, q * (1 - 0.55 * t));
  }
  return Math.max(3.8, q * (1 - 0.60 * clamp(holes / 12, 0, 1)));
}

/** Compensates 2nd-order HP+LP insertion loss. Wide low-note mid bands
 *  used to look “fine” in RMS and still miss 1–3 kHz presence. */
export function pinkBandComp(loHz, hiHz) {
  const width = Math.max(80, hiHz - loHz);
  return clamp(0.28 * Math.sqrt(2500 / width), 0.12, 0.50);
}

/** C5–F5: keep the JSON mid_db but don’t let Q=80 + weak presence muffle. */
export function lowNotePresence(f0) {
  const t = clamp((f0 - 500) / 400, 0, 1);
  return lerp(1.25, 1.0, t);
}

export function playbackQ(nf) {
  const q = Math.max(8, nf.Q || 45);
  const cap = 30 + (nf.f0 || 500) * 0.035; // ~48 at C5, ~79 at F6
  return Math.min(q, cap);
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
  const rms = Math.sqrt(d.reduce((s, v) => s + v * v, 0) / n);
  const g = 1 / Math.max(rms, 1e-6);
  for (let i = 0; i < n; i++) d[i] *= g;
  _noiseBuf = buf;
  return buf;
}

function envGain(node, when, tOn, tSpeak, tHoldEnd, rel, peak, intoSlide, os) {
  const p = node.gain;
  p.cancelScheduledValues(when);
  p.setValueAtTime(0, when);
  p.setValueAtTime(0, tOn);
  p.linearRampToValueAtTime(peak * os, tSpeak);
  p.linearRampToValueAtTime(peak, tSpeak + 0.04);
  if (intoSlide) p.setValueAtTime(peak, tHoldEnd);
  else {
    p.setValueAtTime(peak, Math.max(tSpeak + 0.02, tHoldEnd - rel));
    p.linearRampToValueAtTime(0, tHoldEnd + rel);
  }
}

function airGain(db, extra) {
  // Quiet leaky-pink buffer (acc*0.15). JSON dB is vs H1; do NOT
  // also divide by pinkBandComp or the skirt buries the sine.
  const raw = dbToLin(db) * 0.22 * (extra == null ? 1 : extra);
  return clamp(raw, 0, 0.035);
}

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
  const os = Math.min(1.2, Math.pow(10, (nf.overshoot_db || 0) / 20));
  const tOn = when + pre, tSpeak = tOn + speak, tHoldEnd = when + hold;

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
  toneBp.Q.value = playbackQ(nf);
  const bodyGain = ctx.createGain();
  bodyGain.gain.value = 0;
  osc.connect(toneBp); toneBp.connect(bodyGain); bodyGain.connect(out);

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
  syncOsc.connect(shaper); shaper.connect(syncGain.gain);
  noise.connect(syncGain);

  // cavity halo
  const noiseBp = ctx.createBiquadFilter();
  noiseBp.type = "bandpass";
  noiseBp.frequency.value = f0;
  noiseBp.Q.value = effectiveNoiseQ(nf);
  const resGain = ctx.createGain();
  const resComp = pinkBandComp(f0 * 0.7, f0 * 1.25);
  resGain.gain.value = airGain(nf.noise_res_db || -28);
  syncGain.connect(noiseBp); noiseBp.connect(resGain); resGain.connect(bodyGain);

  // MID AIR — the 12-hole top. Bandpass 1.25 f0 … 4 kHz. NO highshelf.
  const midLo = midLoHz(f0);
  const midHp = ctx.createBiquadFilter();
  midHp.type = "highpass";
  midHp.frequency.value = midLo;
  midHp.Q.value = 0.5;
  const midLp = ctx.createBiquadFilter();
  midLp.type = "lowpass";
  midLp.frequency.value = midHiHz();
  midLp.Q.value = 0.5;
  midHp.connect(midLp);
  const midG = ctx.createGain();
  midG.gain.value = 0;
  const midDb = nf.noise_mid_db != null ? nf.noise_mid_db : (nf.noise_hiss_db || -50) + 8;
  const midPeak = airGain(midDb, lowNotePresence(f0));
  noise.connect(midHp);
  midLp.connect(midG); midG.connect(out);

  // high hiss 4–12 kHz — quieter than mid, no shelf
  const hissHp = ctx.createBiquadFilter();
  hissHp.type = "highpass";
  hissHp.frequency.value = 4000;
  hissHp.Q.value = 0.5;
  const hissG = ctx.createGain();
  hissG.gain.value = 0;
  noise.connect(hissHp); hissHp.connect(hissG); hissG.connect(out);

  const chiffBp = ctx.createBiquadFilter();
  chiffBp.type = "bandpass";
  chiffBp.frequency.value = f0;
  chiffBp.Q.value = g.chiff_q || 2.2;
  const chiffGain = ctx.createGain();
  chiffGain.gain.value = 0;
  syncGain.connect(chiffBp); chiffBp.connect(chiffGain); chiffGain.connect(out);

  const partials = [];
  for (let k = 2; k < (nf.h || []).length; k++) {
    const hk = nf.h[k - 1];
    if (!(hk > 1e-4)) continue;
    const p = ctx.createOscillator();
    p.type = "sine";
    p.frequency.value = f0 * k;
    const pg = ctx.createGain();
    pg.gain.value = hk;
    p.connect(pg); pg.connect(out);
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
    vib.connect(vg); vg.connect(osc.frequency);
  }

  envGain(bodyGain, when, tOn, tSpeak, tHoldEnd, rel, 1, opts.intoSlide, os);
  envGain(midG, when, tOn, tSpeak, tHoldEnd, rel, midPeak, opts.intoSlide, os);
  envGain(hissG, when, tOn, tSpeak, tHoldEnd, rel,
    airGain(nf.noise_hiss_db || -55),
    opts.intoSlide, os);

  const chiffPeak = Math.min(0.04, Math.max(0, (nf.chiff_peak || 1) - 1) * dbToLin(nf.noise_res_db || -28));
  const tCh1 = tOn + Math.max(0.02, nf.chiff_len_s || 0.045);
  chiffGain.gain.setValueAtTime(0, when);
  chiffGain.gain.linearRampToValueAtTime(chiffPeak, tOn + (tCh1 - tOn) * 0.35);
  chiffGain.gain.linearRampToValueAtTime(0, tCh1);

  osc.start(when); wander.start(when); syncOsc.start(when); noise.start(when);
  partials.forEach((p) => p.start(when));
  if (vib) vib.start(when);
  const stopAt = tHoldEnd + rel + 0.02;
  function stopNodes(t) {
    const tt = t != null ? t : ctx.currentTime;
    [osc, wander, syncOsc, noise, vib].concat(partials).forEach((n) => {
      try { if (n) n.stop(tt); } catch (e) {}
    });
  }
  if (!opts.intoSlide) stopNodes(stopAt);
  return {
    until: stopAt,
    fade(t) {
      const tt = t != null ? t : ctx.currentTime;
      [bodyGain, midG, hissG].forEach((node) => {
        try {
          node.gain.cancelScheduledValues(tt);
          node.gain.setValueAtTime(node.gain.value, tt);
          node.gain.linearRampToValueAtTime(0, tt + 0.03);
        } catch (e) {}
      });
      stopNodes(tt + 0.04);
    },
    stop(t) { this.fade(t); },
    frequency: osc.frequency,
    out,
  };
}
