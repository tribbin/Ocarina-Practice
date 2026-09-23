// Practice pitch worker: owns the autocorrelation detector so the melody
// tuner never spends its ~2M multiply-adds (per ~66 ms frame) on the main
// thread. Frames arrive transferred, results come back at a sample count of
// the compute cost; js/pitch-dsp.js is the single source of the detector so
// this worker and the main-thread fallback are bit-identical.
importScripts("pitch-dsp.js");

self.onmessage = (e) => {
  const d = e.data;
  if (!d || !d.buf) { return; }
  const seq = d.seq;
  let hz = 0;
  try { hz = autoCorrelate(d.buf, d.sr) || 0; } catch (err) { hz = 0; }
  self.postMessage({ seq: seq, hz: hz });
};
