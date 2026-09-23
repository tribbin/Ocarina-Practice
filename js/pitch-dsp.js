// Shared pitch DSP — the autocorrelation detector lives here so both the
// main thread (sync fallback) and the practice worker compute IDENTICAL
// results from the same source file: js/practice.js loads it as a classic
// script, js/pitch-ac-worker.js imports it. One detector, one truth.

const PITCH_MIN_HZ = 160;

// The highest visible chamber comfortably exceeds A6 (1760 Hz): its first
// harmonic sits at ~3520+ Hz — but at 48 kHz sample rate a 2600 Hz period
// (~22.9 samples at 48 kHz) sits BELOW the search floor when MAX_HZ was
// higher, so this ceiling is also a resolution guard.
const PITCH_MAX_HZ = 2600;

// Normalized autocorrelation with parabolic peak interpolation.
// History: an earlier "first lag within 95% of the best clarity" octave
// guard snapped onto the SHOULDER of the true peak (only ~4-5% short of the
// true period on mid/high notes), reading +72..+90¢ high depending on the
// note — a pure detector artifact, never a recording problem. The guard is
// gone; octave protection now only considers true SUB-MULTIPLES of the best
// lag (k× the fundamental period — the honest subharmonic case), each with
// a local-maximum clarity check.
function autoCorrelate(buf, sr) {
  const n = buf.length;
  const half = Math.floor(n / 2);
  const minLag = Math.max(2, Math.floor(sr / PITCH_MAX_HZ));
  const maxLag = Math.min(half, Math.ceil(sr / PITCH_MIN_HZ));
  // correlation curve computed once
  const c = new Float32Array(maxLag + 1);
  for (let lag = minLag; lag <= maxLag; lag++) {
    let corr = 0, ea = 0, eb = 0;
    const m = n - lag;
    for (let i = 0; i < m; i++) {
      corr += buf[i] * buf[i + lag];
      ea += buf[i] * buf[i];
      eb += buf[i + lag] * buf[i + lag];
    }
    c[lag] = (ea && eb) ? corr / Math.sqrt(ea * eb) : 0;
  }
  c[0] = -1; c[1] = -1; // sentinel: no lags below minLag exist
  let globalLag = -1, globalC = 0;
  for (let lag = minLag; lag <= maxLag; lag++) {
    if (c[lag] > globalC) { globalC = c[lag]; globalLag = lag; }
  }
  if (globalLag < 0 || globalC < 0.85) return 0;
  // The pitch = the SHORTEST local maximum whose clarity is ~that of the
  // global best. Integer multiples of a fractional period always re-
  // correlate nearly perfectly (the global max can be 5× the true period),
  // and non-maximum shoulders are never periods — comparing against those
  // caused the old +72..+90¢ shoulder-snap.
  let bestLag = -1, bestC = 0;
  for (let lag = minLag; lag < maxLag; lag++) {
    if (c[lag] >= c[lag - 1] && c[lag] >= c[lag + 1] &&
        c[lag] >= globalC * 0.9) {
      bestLag = lag; bestC = c[lag];
      break;
    }
  }
  if (bestLag < 0) { bestLag = globalLag; bestC = globalC; }
  // Sub-multiple safety net (weak fundamentals locked onto a harmonic):
  // only k× multiples qualify, each with local-max clarity.
  for (let k = 4; k >= 2; k--) {
    const cand = Math.round(bestLag / k);
    if (cand < minLag) continue;
    let m = cand;
    if (c[cand - 1] > c[m]) m = cand - 1;
    if (c[cand + 1] > c[m]) m = cand + 1;
    if (m < minLag || m >= bestLag) continue;
    if (c[m] >= bestC * 0.9) { bestLag = m; bestC = c[m]; }
  }
  // Parabolic interpolation around the final lag (sub-sample precision):
  // removes the integer-lag quantization that used to read anywhere from
  // -26¢ to +26¢ depending on where the true period fell.
  let delta = 0;
  if (bestLag > minLag && bestLag < maxLag) {
    const a = c[bestLag - 1], b = c[bestLag], cc = c[bestLag + 1];
    const den = a - 2 * b + cc;
    if (den > 1e-12) {
      delta = 0.5 * (a - cc) / den;
      if (delta > 1 || delta < -1) delta = 0;
    }
  }
  let fl = bestLag + delta;
  // Fine refine: correlate against a linearly-shifted copy on a 0.25-sample
  // grid around the parabolic estimate (the composite curve is not exactly
  // parabolic when harmonics are present, so the analytic apex drifts).
  const fine = (fq) => {
    const k = Math.floor(fq), fr = fq - k;
    const m = Math.min(n - k - 2, n - Math.ceil(fl) - 2);
    if (m < 64) return -1;
    let corr = 0, ea = 0, eb = 0;
    for (let i = 0; i < m; i++) {
      const y = (1 - fr) * buf[i + k] + fr * buf[i + k + 1];
      const xi = buf[i];
      corr += xi * y;
      ea += xi * xi;
      eb += y * y;
    }
    return corr / Math.sqrt(ea * eb);
  };
  let best = -2, bestFl = fl;
  for (let fq = fl - 1; fq <= fl + 1; fq += 0.25) {
    if (fq < minLag || fq > maxLag) continue;
    const v = fine(fq);
    if (v > best) { best = v; bestFl = fq; }
  }
  if (best > 0) {
    // parabola on the fine grid (0.25 steps)
    const fC = fine(bestFl), fL2 = fine(bestFl - 0.25), fR = fine(bestFl + 0.25);
    const den2 = fL2 - 2 * fC + fR;
    let d2 = 0;
    if (den2 > 1e-12) {
      d2 = 0.5 * (fL2 - fR) / den2;
      if (d2 > 1 || d2 < -1) d2 = 0;
    }
    fl = bestFl + d2 * 0.25;
  }
  return sr / fl;
}
