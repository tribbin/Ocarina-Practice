// Headless smoke test for js/audio.js param plumbing (stubbed Web Audio).
// Each scenario gets a fresh vm context so module state resets cleanly.
const fs = require("fs");
const vm = require("vm");
const path = require("path");
const APP = "C:/Users/tribb/Documents/git/Triple-Bass-in-C-Ocarina-Tab-Maker";

let failures = 0;
function ok(cond, msg) {
  console.log((cond ? "PASS " : "FAIL ") + msg);
  if (!cond) failures++;
}
const eq = (a, b, eps) => Math.abs(a - b) < (eps == null ? 1e-9 : eps);

function autoParam(init) {
  const o = { value: init, calls: [] };
  ["setValueAtTime", "linearRampToValueAtTime", "exponentialRampToValueAtTime"].forEach(m => {
    o[m] = (v, t) => { o.calls.push([m, v, t]); o.value = v; };
  });
  o.cancelScheduledValues = () => {};
  return o;
}
function makeCtx() {
  const ctx = {};
  ctx.destination = { fake: "destination" };
  ctx.currentTime = 1.234;
  ctx.sampleRate = 48000;
  ctx.state = "running";
  ctx.resume = () => {};
  ctx._nodes = [];
  ctx._waves = [];
  ctx.createGain = () => {
    const node = { context: ctx, connect() {}, gain: autoParam(1) };
    ctx._nodes.push(node);
    return node;
  };
  ctx.createOscillator = () => {
    const node = {
      context: ctx,
      type: "", detune: autoParam(0), frequency: autoParam(440),
      connect() {},
      setPeriodicWave(w) { node._wave = w; },
      start() { node._started = true; },
      stop() { node._stopped = true; },
    };
    ctx._nodes.push(node);
    return node;
  };
  ctx.createBiquadFilter = () => {
    const node = { context: ctx, type: "", Q: autoParam(1), connect() {}, frequency: autoParam(350) };
    ctx._nodes.push(node);
    return node;
  };
  ctx.createBufferSource = () => {
    const node = { context: ctx, buffer: null, connect() {}, start() {}, stop() {} };
    ctx._nodes.push(node);
    return node;
  };
  ctx.createBuffer = (ch, len) => ({ getChannelData: () => new Float32Array(len) });
  ctx.createPeriodicWave = (real, imag) => {
    const w = { real: Array.from(real), imag: Array.from(imag) };
    ctx._waves.push(w);
    return w;
  };
  ctx.createConvolver = () => ({ context: ctx, buffer: null, connect() {} });
  ctx.createDynamicsCompressor = () => ({
    context: ctx,
    threshold: autoParam(0), knee: autoParam(0), ratio: autoParam(0),
    attack: autoParam(0), release: autoParam(0), connect() {},
  });
  return ctx;
}

const fing = JSON.parse(fs.readFileSync(path.join(APP, "fingerings.json"), "utf8"));
const ids = Object.keys(fing.notes);
const CHAMBER = {}, COVER = {}, DISPLAY = {};
ids.forEach(id => {
  CHAMBER[id] = fing.notes[id].chamber;
  COVER[id] = fing.notes[id].covered || [];
});

const docStub = {
  _lite: false,
  getElementById(id) { return { checked: id === "liteMel" && docStub._lite }; },
  addEventListener() {},
};

const SRC = fs.readFileSync(path.join(APP, "js/audio.js"), "utf8");
const DEBUG_SWALLOW = process.env.SWALLOW === "1";

function guest() {
  const sandbox = {
    console: { log() {}, error() {} },
    Math, JSON, Object, Array, String, Number, Boolean, Date, Symbol,
    Float32Array, Float64Array, isFinite, parseInt, parseFloat, isNaN,
    setTimeout: () => 0, clearTimeout: () => {}, setInterval: () => 0, clearInterval: () => {},
    document: docStub,
    NOTES: ids, DISPLAY, CHAMBER, COVER, FING: fing,
  };
  sandbox.console.log = (...a) => console.log(...a); // surface swallowed errors when SWALLOW=1
  sandbox.window = sandbox;
  sandbox.addEventListener = () => {};
  // For debugging: report exceptions swallowed by audio.js's try/catch blocks.
  const src = DEBUG_SWALLOW ? SRC.replace(/} catch \(e\) \{\}/g, '} catch (e) { console.log("[swallowed]", String(e && e.stack || e)); }') : SRC;
  vm.runInNewContext(src, sandbox, { filename: "audio.js" });
  return sandbox;
}

function findFreq(nodes, min, max) {
  return nodes.find(n => n.frequency != null &&
    n.frequency.calls.some(c => c[1] > min && c[1] < max));
}
function hasRamp(node, v, eps) {
  if (!node || !node.gain) return false;
  return node.gain.calls.some(c => c[0] === "linearRampToValueAtTime" && eq(c[1], v, eps == null ? 1e-9 : eps));
}
function near(a, arr, eps) {
  return arr.every((v, i) => eq(a[i], v, eps == null ? 1e-6 : eps));
}

// ================= 1. defaults =================
{
  const ctx = makeCtx();
  const S = guest();
  S.AudioContext = function () { return ctx; };
  S.playNoteAt("A3", null, 0.6, []); // A3 = 220 Hz
  ok(ctx._waves.length === 1, "one PeriodicWave built");
  const D = S.OCA_DEBUG.defaults;
  ok(near(ctx._waves[0].real, [0, D.h1, D.h2, D.h3, D.h4, D.h5]),
     "wave harmonics = shipped defaults (read from OCA_DEBUG.defaults)");
  ok(near(ctx._waves[0].imag, [0, 0, 0, 0, 0, 0]), "imag part zero");
  const biquads = ctx._nodes.filter(n => n.Q);
  ok(biquads.length >= 4, "full voice biquad stack present (" + biquads.length + ")");
  const lp = biquads[0]; // tone lowpass is the first filter created
  ok(lp.type === "lowpass", "first filter is the tone lowpass");
  ok(eq(lp.frequency.value, 220 * 4.2, 1e-6), "lp cutoff = 220*4.2 = 924 (" + lp.frequency.value + ")");
  ok(eq(lp.Q.value, 0.7), "lp Q = 0.7");
  const master = ctx._nodes.find(n => hasRamp(n, D.masterLevel));
  ok(!!master, "master envelope reaches shipped masterLevel");
  ok(master && hasRamp(master, D.masterLevel * (0.05 / 0.26), 1e-6), "pre-tone = masterLevel*(0.05/0.26)");
  ok(master && hasRamp(master, D.masterLevel * (0.16 / 0.26), 1e-6), "tone stage = masterLevel*(0.16/0.26)");
  ok(ctx._nodes.filter(n => hasRamp(n, 0.02)).length === 0,
     "air layer silent at shipped default level 0 (node exists, gain 0)");
  const edge = findFreq(ctx._nodes, 220 * 1.011, 220 * 1.021);
  ok(!!edge, "edge whistle sits sharp of fundamental");
  const ot = findFreq(ctx._nodes, 220 * 2 * 1.004 - 0.01, 220 * 2 * 1.004 + 0.01);
  ok(!!ot, "octave overtone sine present");
  ok(ctx._nodes.some(n => n.gain && eq(n.gain.value, 0)), "reverb bus wet gain built at 0 (reverb off)");
}

// ================= 2. tweaked params =================
{
  const ctx = makeCtx();
  const S = guest();
  S.AudioContext = function () { return ctx; };
  const P = S.OCA_DEBUG.params;
  P.masterLevel = 0.5;
  P.lpMult = 6;
  P.h2 = 0.2;
  S.OCA_DEBUG.invalidateWave();
  S.playNoteAt("C5", null, 0.6, []); // 523.2511 Hz
  ok(ctx._waves.length === 1 && eq(ctx._waves[0].real[2], 0.2, 1e-6),
     "wave rebuilt with h2=0.2 after invalidateWave");
  const lps = ctx._nodes.filter(n => n.Q);
  ok(eq(lps[0].frequency.value, Math.min(9000, 523.2511 * 6), 0.1),
     "lp cutoff follows lpMult=6 (" + Math.min(9000, 523.2511 * 6).toFixed(1) + " Hz)");
  const master = ctx._nodes.find(n => hasRamp(n, 0.5));
  ok(!!master, "master plateau = masterLevel 0.5");
  ok(master && hasRamp(master, 0.5 * (0.05 / 0.26), 1e-6), "pre-tone scaled (" + (0.5 * (0.05 / 0.26)).toFixed(4) + ")");
  ok(master && hasRamp(master, 0.5 * (0.16 / 0.26), 1e-6), "tone stage scaled (" + (0.5 * (0.16 / 0.26)).toFixed(4) + ")");
  ok(ctx._nodes.filter(n => hasRamp(n, 0.02)).length === 0, "air level stays off at shipped default (C5 hiF=0)");
}

// ================= 3. high-note fade map =================
{
  const ctx = makeCtx();
  const S = guest();
  S.AudioContext = function () { return ctx; };
  const P = S.OCA_DEBUG.params;
  P.hiFrom = 400;
  P.hiTo = 1000;
  P.airLevel = 0.02; // re-enable for the fade-map probe (shipped default is 0)
  S.playNoteAt("A5", null, 0.6, []); // 880 Hz -> hiF=(880-400)/600 = 0.8
  const expectedAir = 0.02 * (1 - 0.75 * 0.8); // 0.008
  ok(ctx._nodes.some(n => hasRamp(n, expectedAir, 1e-6)),
     "air level follows remapped fade: " + expectedAir);
  const oldAir = 0.02 * (1 - 0.75 * (880 - 660) / (1568 - 660)); // 0.01637
  ok(!ctx._nodes.some(n => hasRamp(n, oldAir, 1e-6)),
     "old mapping at 660..1568 no longer applies");
  const edge = findFreq(ctx._nodes, 880 * 1.011, 880 * 1.022);
  ok(!!edge, "edge whistle present on A5");
}

// ================= 4. Lite mode =================
{
  docStub._lite = true;
  const ctx = makeCtx();
  const S = guest();
  S.AudioContext = function () { return ctx; };
  const P = S.OCA_DEBUG.params;
  P.masterLevel = 0.5;
  P.lpMult = 6;
  S.playNoteAt("A3", null, 0.6, []);
  ok(ctx._waves.length === 1, "lite builds wave");
  const g = ctx._nodes.find(n => hasRamp(n, 0.5));
  ok(!!g, "lite gain ramps to masterLevel");
  const lp = ctx._nodes.find(n => n.type === "lowpass");
  ok(!!lp && eq(lp.frequency.value, 220 * 6, 1e-6), "lite lowpass = 220*6");
  const oscCount = ctx._nodes.filter(n => n.setPeriodicWave).length;
  ok(oscCount === 1, "lite voice = 1 oscillator (no layered partials)");
  docStub._lite = false;
}

// ================= 5. reverb wet live reread =================
{
  const ctx = makeCtx();
  const S = guest();
  S.AudioContext = function () { return ctx; };
  const P = S.OCA_DEBUG.params;
  S.playNoteAt("A3", null, 0.6, []); // builds reverb bus (reverb off -> wet =
                                     // gain.value 0 by design; target is read at toggle time)
  const wet = ctx._nodes.find(n => n.gain && eq(n.gain.value, 0));
  ok(!!wet, "bus built with reverb off (wet gain value 0)");
  let noErr = true;
  try { S.setReverbEnabled(true); } catch (e) { noErr = false; }
  ok(noErr, "setReverbEnabled runs");
  ok(wet && wet.gain.calls.some(c => c[0] === "linearRampToValueAtTime" && eq(c[1], 0.32)),
     "enable ramp targets default reverbWet = 0.32");
  P.reverbWet = 0.55;
  try { S.setReverbEnabled(true); } catch (e) { noErr = false; }
  ok(wet && wet.gain.calls.some(c => c[0] === "linearRampToValueAtTime" && eq(c[1], 0.55)),
     "live wet re-ramp targets updated reverbWet = 0.55");
}

// ================= 6. defaults table sanity =================
{
  const S = guest();
  const d = S.OCA_DEBUG.defaults;
  ok(Object.keys(d).length >= 28, "default table complete (" + Object.keys(d).length + " params)");
  ok(typeof S.OCA_DEBUG.invalidateWave === "function", "invalidateWave exposed");
}

console.log(failures === 0 ? "\nALL PASS" : "\n" + failures + " FAILURES");
process.exit(failures === 0 ? 0 : 1);
