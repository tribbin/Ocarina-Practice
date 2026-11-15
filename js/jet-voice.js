/**
 * Jet-drive voice wrapper (experimental ?jet=1 A/B). The AudioWorklet
 * processor carries the whole voice: a 2-pole Helmholtz resonator driven by
 * a delayed sigmoid jet plus gated turbulence. Per-note parameters come from
 * instruments/<id>/jet_model.json; the colored-noise input is the chamber's
 * fitted slope buffer. When the worklet is unavailable the caller falls back
 * to the v4-breath voice.
 */
import { coloredBuffer } from "./helmholtz-voice.js?v=14";

export const JET_REV = "jet-drive-v1";
export const JET_DEFAULTS = {
  Q: 30, delay_ratio: 0.5, jet_k: 1, jet_h2: 0, jet_h3: 0,
  jet_drive: 0.5, jet_feedback: 0.1, turb_gain: 0, turb_gate: 0.5,
  turb_bypass: 0.2, out_gain: 1, noise_slope_db_oct: -8,
};
const WORKLET_URL = "js/jet-voice-processor.js";
const JET_KEYS = [
  "Q", "delay_ratio", "jet_k", "jet_h2", "jet_h3", "jet_drive",
  "jet_feedback", "turb_gain", "turb_gate", "turb_bypass", "out_gain",
  "noise_slope_db_oct",
];

export function loadJetModelFromObject(obj) {
  if (!obj || !Array.isArray(obj.notes) || !obj.notes.length) {
    throw new Error("jet_model.json: missing notes[]");
  }
  const notes = obj.notes.slice().sort((a, b) => a.f0 - b.f0);
  return {
    schema: obj.schema || "ocarina-jet-v1",
    instrument: obj.instrument || "",
    chamber: String(obj.chamber || "1"),
    globals: Object.assign({ voice: JET_REV }, obj.globals || {}),
    notes,
  };
}

function lerp(a, b, t) { return a + (b - a) * t; }

export function interpJet(model, f0) {
  const notes = model.notes;
  if (!notes.length) throw new Error("empty jet model");
  if (f0 <= notes[0].f0) {
    const row = Object.assign({}, notes[0], { f0 });
    for (const key of JET_KEYS) if (row[key] == null) row[key] = JET_DEFAULTS[key];
    return row;
  }
  if (f0 >= notes[notes.length - 1].f0) {
    const row = Object.assign({}, notes[notes.length - 1], { f0 });
    for (const key of JET_KEYS) if (row[key] == null) row[key] = JET_DEFAULTS[key];
    return row;
  }
  for (let i = 0; i < notes.length - 1; i++) {
    const a = notes[i], b = notes[i + 1];
    if (f0 > b.f0) continue;
    const t = Math.log(f0 / a.f0) / Math.log(b.f0 / a.f0);
    const out = { note: null, f0 };
    for (const key of JET_KEYS) {
      if (a[key] != null && b[key] != null) out[key] = lerp(+a[key], +b[key], t);
      else if (a[key] != null) out[key] = +a[key];
      else if (b[key] != null) out[key] = +b[key];
      else out[key] = JET_DEFAULTS[key];
    }
    return out;
  }
  const row = Object.assign({}, notes[notes.length - 1], { f0 });
  for (const key of JET_KEYS) if (row[key] == null) row[key] = JET_DEFAULTS[key];
  return row;
}

const readyCtx = new WeakSet();
const pendingCtx = new WeakMap();
export function jetReady(ctx) { return !!ctx && readyCtx.has(ctx); }

export function prepareJetWorklet(ctx) {
  if (!ctx || !ctx.audioWorklet || typeof AudioWorkletNode === "undefined") {
    return Promise.resolve(false);
  }
  if (readyCtx.has(ctx)) return Promise.resolve(true);
  if (pendingCtx.has(ctx)) return pendingCtx.get(ctx);
  const p = ctx.audioWorklet.addModule(WORKLET_URL)
    .then(() => { readyCtx.add(ctx); return true; })
    .catch(() => false)
    .finally(() => { pendingCtx.delete(ctx); });
  pendingCtx.set(ctx, p);
  return p;
}

export function scheduleJetNote(ctx, dest, opts) {
  if (!jetReady(ctx)) throw new Error("jet worklet not ready");
  const model = opts.jetModel;
  const f0 = +opts.f0;
  const when = Math.max(ctx.currentTime + 0.012,
                         opts.when == null ? ctx.currentTime + 0.02 : opts.when);
  const hold = Math.max(0.05, +opts.holdSec || 0.4);
  const nf = opts.nf || null;
  const jf = interpJet(model, f0);
  const rel = opts.intoSlide ? 0.04 : Math.max(0.04, (nf && nf.rel_s) || 0.08);
  const pre = Math.max(0, (nf && nf.atk_pre_s) || 0.01);
  const speak = Math.max(0.006, (nf && nf.atk_speak_s) || 0.03);
  const tOn = when + pre;
  const tSpeak = tOn + speak;
  const tHoldEnd = when + hold;
  const tOff = tHoldEnd + rel;
  const speakAt = hold < 0.16
    ? tOn + Math.min(speak, Math.max(0.008, hold * 0.35)) : tSpeak;
  const os = Math.pow(10, ((nf && nf.overshoot_db) || 0) / 20);
  const master = opts.master != null ? opts.master : 1;

  const node = new AudioWorkletNode(ctx, "jet-drive", {
    numberOfInputs: 1,
    numberOfOutputs: 1,
    outputChannelCount: [1],
    channelCount: 1,
    channelCountMode: "explicit",
    channelInterpretation: "speakers",
    parameterData: {
      q: jf.Q,
      delayRatio: jf.delay_ratio,
      jetK: jf.jet_k,
      jetH2: jf.jet_h2,
      jetH3: jf.jet_h3,
      jetDrive: jf.jet_drive,
      jetFeedback: jf.jet_feedback,
      turbGain: jf.turb_gain,
      turbGate: jf.turb_gate,
      turbBypass: jf.turb_bypass,
      outGain: jf.out_gain,
    },
  });
  const out = ctx.createGain();
  out.gain.value = master;
  node.connect(out);
  out.connect(dest);

  const f0p = node.parameters.get("f0");
  const startF = opts.slideFromHz && opts.slideFromHz > 0 ? opts.slideFromHz : f0;
  f0p.setValueAtTime(startF, when);
  if (opts.slideFromHz && opts.slideFromHz > 0) {
    f0p.exponentialRampToValueAtTime(Math.max(20, f0), when + (opts.slideSec || 0.03));
  }
  const breath = node.parameters.get("breath");
  breath.cancelScheduledValues(when);
  breath.setValueAtTime(0, when);
  breath.setValueAtTime(0, tOn);
  breath.linearRampToValueAtTime(os, speakAt);
  breath.linearRampToValueAtTime(1, speakAt + 0.02);
  if (opts.intoSlide) breath.setValueAtTime(1, tHoldEnd);
  else {
    breath.setValueAtTime(1, Math.max(speakAt + 0.015, tHoldEnd - 0.012));
    breath.linearRampToValueAtTime(0.0001, tOff);
  }

  const noise = ctx.createBufferSource();
  noise.buffer = coloredBuffer(ctx, (nf && nf.slope_db_oct) || -6);
  noise.loop = true;
  noise.connect(node);
  const wander = ctx.createOscillator();
  wander.frequency.value = (nf && nf.wobble_hz) || 0.45;
  const wanderGain = ctx.createGain();
  wanderGain.gain.value = f0 * 0.0015;
  wander.connect(wanderGain);
  wanderGain.connect(f0p);
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
    vg.connect(f0p);
  }
  const offset = Math.random() * Math.max(0, noise.buffer.duration - 0.05);
  noise.start(when, offset);
  wander.start(when);
  if (vib) vib.start(when);
  const stopAt = tOff + 0.06;
  try { node.port.postMessage({ stopAt }); } catch (e) {}
  if (!opts.intoSlide) {
    try { noise.stop(stopAt); } catch (e) {}
    try { wander.stop(stopAt); } catch (e) {}
    if (vib) try { vib.stop(stopAt); } catch (e) {}
  }
  return {
    until: stopAt,
    fade(t) {
      const tt = t != null ? t : ctx.currentTime;
      try {
        out.gain.cancelScheduledValues(tt);
        out.gain.setValueAtTime(out.gain.value, tt);
        out.gain.linearRampToValueAtTime(0.0001, tt + 0.05);
      } catch (e) {}
      try { node.port.postMessage({ stopAt: tt + 0.09 }); } catch (e) {}
      try { noise.stop(tt + 0.09); } catch (e) {}
      try { wander.stop(tt + 0.09); } catch (e) {}
      if (vib) try { vib.stop(tt + 0.09); } catch (e) {}
      setTimeout(() => { try { node.disconnect(); out.disconnect(); } catch (e) {} }, 140);
    },
    stop(t) { this.fade(t); },
    frequency: f0p,
    out,
    _jet: {
      node, params: jf,
      timeline: { when, tOn, tSpeak, speakAt, tHoldEnd, tOff, stopAt },
      noiseOffset: offset,
    },
  };
}
