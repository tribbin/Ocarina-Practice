/**
 * Helmholtz ocarina voice. v3i replaces the tone graph.
 *
 * Dry sine. H2/H3/H4 are separate oscillators, slightly detuned so they
 * drift and do not lock into a steam-horn wave. Noise is a falling floor,
 * a narrow halo on f0, and an air band. Chiff only on the attack.
 *
 * Attack, speak, release, overshoot and the cut-bus are the existing
 * envelope. Chorus and reverb stay in audio.js.
 */
export const VOICE_REV = "v3i-floor";

export function loadTwinModelFromObject(obj) {
  if (!obj || !Array.isArray(obj.notes) || !obj.notes.length) {
    throw new Error("twin_model.json: missing notes[]");
  }
  const notes = obj.notes.slice().sort((a, b) => a.f0 - b.f0);
  return {
    schema: obj.schema || "ocarina-twin-v2",
    instrument: obj.instrument || "",
    chamber: String(obj.chamber || "1"),
    globals: Object.assign({ halo_q: 7.5, chiff_q: 2.2, sync_amt: 0.35 }, obj.globals || {}),
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
    const h = [];
    for (let k = 0; k < hlen; k++) h.push(lerp(a.h[k] || 0, b.h[k] || 0, t));
    const keys = [
      "level", "Q", "noise_Q", "halo_db", "floor_db", "slope_db_oct",
      "air_db", "air_lo_hz", "air_hi_hz", "noise_res_db", "noise_hiss_db",
      "atk_pre_s", "atk_speak_s", "overshoot_db", "chiff_peak", "chiff_len_s",
      "rel_s", "wander_cents_std", "wobble_pct", "wobble_hz",
    ];
    const out = { note: null, f0, h, open_holes: t < 0.5 ? a.open_holes : b.open_holes };
    keys.forEach((k) => { out[k] = lerp(a[k] == null ? 0 : a[k], b[k] == null ? 0 : b[k], t); });
    return out;
  }
  return Object.assign({}, notes[notes.length - 1], { f0 });
}

let _noiseBuf = null;
function noiseBuffer(ctx) {
  if (_noiseBuf && _noiseBuf.sampleRate === ctx.sampleRate) return _noiseBuf;
  const n = Math.floor(ctx.sampleRate * 4);
  const buf = ctx.createBuffer(1, n, ctx.sampleRate);
  const d = buf.getChannelData(0);
  let acc = 0;
  for (let i = 0; i < n; i++) {
    acc = 0.98 * acc + (Math.random() * 2 - 1);
    d[i] = acc * 0.12;
  }
  const k = Math.floor(ctx.sampleRate * 0.01);
  for (let i = 0; i < k; i++) {
    const w = (i + 1) / (k + 1);
    d[n - k + i] = d[n - k + i] * (1 - w) + d[i] * w;
  }
  _noiseBuf = buf;
  return buf;
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

  const bodyGain = ctx.createGain();
  bodyGain.gain.value = 0;
  osc.connect(bodyGain);
  bodyGain.connect(out);

  const noise = ctx.createBufferSource();
  noise.buffer = noiseBuffer(ctx);
  noise.loop = true;

  const haloBp = ctx.createBiquadFilter();
  haloBp.type = "bandpass";
  haloBp.frequency.value = f0;
  haloBp.Q.value = g.halo_q || 7.5;
  const haloGain = ctx.createGain();
  haloGain.gain.value = 0;
  noise.connect(haloBp);
  haloBp.connect(haloGain);
  haloGain.connect(out);

  // Falling floor, the body of the Python air. Highpassed so it does not
  // sit under the note. The buffer is already pink, about -6 dB/octave.
  const floorHp = ctx.createBiquadFilter();
  floorHp.type = "highpass";
  floorHp.frequency.value = Math.max(900, 2.2 * f0);
  floorHp.Q.value = 0.7;
  const floorLp = ctx.createBiquadFilter();
  floorLp.type = "lowpass";
  floorLp.frequency.value = 6000;
  floorLp.Q.value = 0.7;
  const floorGain = ctx.createGain();
  floorGain.gain.value = 0;
  noise.connect(floorHp);
  floorHp.connect(floorLp);
  floorLp.connect(floorGain);
  floorGain.connect(out);

  const airLo = nf.air_lo_hz || 1800;
  const airHi = nf.air_hi_hz || 5000;
  const airHp = ctx.createBiquadFilter();
  airHp.type = "highpass";
  airHp.frequency.value = airLo;
  airHp.Q.value = 0.7;
  const airLp = ctx.createBiquadFilter();
  airLp.type = "lowpass";
  airLp.frequency.value = airHi;
  airLp.Q.value = 0.7;
  const airGain = ctx.createGain();
  airGain.gain.value = 0;
  noise.connect(airHp);
  airHp.connect(airLp);
  airLp.connect(airGain);
  airGain.connect(out);

  const chiffBp = ctx.createBiquadFilter();
  chiffBp.type = "bandpass";
  chiffBp.frequency.value = Math.min(1800, f0 * 3);
  chiffBp.Q.value = g.chiff_q || 2.2;
  const chiffGain = ctx.createGain();
  chiffGain.gain.value = 0;
  noise.connect(chiffBp);
  chiffBp.connect(chiffGain);
  chiffGain.connect(out);

  // Separate oscillators, a fraction of a hertz off, so they do not lock.
  const partials = [];
  const h = nf.h || [];
  for (let k = 2; k <= 4; k++) {
    const hk = h[k - 1] || 0;
    if (hk < 1e-4) continue;
    const p = ctx.createOscillator();
    p.type = "sine";
    p.frequency.value = f0 * k;
    const pg = ctx.createGain();
    pg.gain.value = hk;
    p.connect(pg);
    pg.connect(bodyGain);
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
    if (opts.intoSlide) p.setValueAtTime(peak, tHoldEnd);
    else {
      p.setValueAtTime(peak, Math.max(tSpeak + 0.02, tHoldEnd - rel));
      p.linearRampToValueAtTime(0, tOff);
    }
  }
  envGain(bodyGain, 1);
  envGain(haloGain, dbToLin(nf.halo_db == null ? -34 : nf.halo_db));
  envGain(floorGain, dbToLin(nf.floor_db == null ? -54 : nf.floor_db));
  envGain(airGain, dbToLin(nf.air_db == null ? (nf.noise_hiss_db == null ? -50 : nf.noise_hiss_db) : nf.air_db));

  const chiffPeak = Math.max(0, (nf.chiff_peak || 1) - 1) * dbToLin((nf.air_db == null ? -50 : nf.air_db) + 6);
  const tCh1 = tOn + Math.max(0.02, nf.chiff_len_s || 0.045);
  chiffGain.gain.setValueAtTime(0, when);
  chiffGain.gain.setValueAtTime(0, tOn);
  chiffGain.gain.linearRampToValueAtTime(chiffPeak, tOn + (tCh1 - tOn) * 0.35);
  chiffGain.gain.linearRampToValueAtTime(0, tCh1);

  osc.start(when); wander.start(when); noise.start(when);
  partials.forEach((p) => p.start(when));
  if (vib) vib.start(when);

  const stopAt = tOff + 0.02;
  function stopNodes(t) {
    const tt = t != null ? t : ctx.currentTime;
    try { osc.stop(tt); } catch (e) {}
    try { wander.stop(tt); } catch (e) {}
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
      stopNodes(tt + 0.04);
    },
    stop(t) { this.fade(t); },
    frequency: osc.frequency,
    out,
  };
}
