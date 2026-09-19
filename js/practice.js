// Practice mode: the song advances when the player HITS each note with the
// ocarina through the microphone — a real articulation (fresh attack after a
// short silence), not a slide into the pitch. A sliding, chamber-colored bar
// fills while the note stays in tune; wandering out drains it at 2x; emptying
// it resets the note to a new attack. A tuner (needle + in-tune zone) guides
// the player.
//
// Notation drives everything: the bar's length is the note's own sounding
// duration at the SONG's tempo (header + inline `# tempo`); the playback
// tempo dial is ignored here. Staccato notes require half their normal
// duration. Ties are one hit held for the chain's whole summed length, even
// across a bar line, and a `~` slide becomes a CHAIN: one segment per
// pitch; each zone must earn 75% of its equal share — the player must
// actually travel through the pitches (transit between zones is neutral;
// each zone is reached with its own onset tolerance; successful zones lock
// in, and only an all-zones-complete bar advances). The missing quarter is
// the player's travel budget: chains get a rather large grace toward the
// next zone (chainTravelMs) that covers breaths in transit and settling
// after arrival.
//
// Every bar earns its release at 75% of the notated hold (REQUIRED_FRAC) —
// dragging the whole note out before moving on is no longer asked for.
// Credit is gradient-based: 1x inside the clean zone; beyond the green
// edge, within the outer bandwidth (2x the clean zone), the rate falls off
// linearly 1 -> -2 — drifting far out drains (swimming against the
// current); leaving the outer bandwidth or silence beyond the grace wipes
// the bar (gapMs for single notes, chainTravelMs inside a chain), while
// shorter hiccups just pause it.
//
// The mic pipeline is analyser-only (never connected to the destination) so
// there is no monitoring feedback, and no reference tone is ever played.
//
// Tests: appending ?practiceTest=1 replaces the mic frames with the synthetic
// provider at window.__pracFrame = { hz, rms } (the same code paths run).
(function () {
  "use strict";

  const TICK_MS = 66;          // detection/UI tick
  const REQUIRED_FRAC = 0.75;  // a zone needs 75% of its share to be done —
                               // the freed quarter is travel time toward the
                               // next note
  const MIN_HZ = 160;
  // Ceiling must cover the highest in-use note plus attack overshoot:
  // C7 (the alto's top note) reads ~2093 Hz — its autocorrelation lag
  // (~22.9 samples at 48 kHz) sits BELOW the search floor when MAX_HZ was
  // 2000, and the detector then reported a far-lower ghost peak.
  const MAX_HZ = 2600;
  const needleLo = -50;        // display window in cents
  const needleHi = 50;

  const P = {
    active: false, paused: false, completed: false,
    calibrating: false,
    tokens: [], idx: 0, quarter: 0.5,
    bar: null,          // { startIdx, endIdx, zones:[hz], targetSec, filled, chainId, slide:false, stac:false }
    state: "idle",      // await | ready | hit | fill | drain? (drain is fill w/ neg) | rest
    gapAcc: 0,          // ms of continuous silence accumulated (await phase)
    transientLeft: 0,   // ms of onset-grace remaining
    restLeft: 0,        // ms left of a rest
    hz: 0, hzSm: 0, rms: 0, cents: 0,
    mic: null,          // { stream, source, analyser, buf, sr }
    interval: 0, last: 0,
    err: "",
  };

  const TEST = /[?&]practiceTest=1\b/.test(location.search);

  // ---------------------------------------------------------------- helpers
  function dbg() {
    return (window.OCA_DEBUG && OCA_DEBUG.params) ||
      (typeof AUDIO_DEFAULTS !== "undefined" ? AUDIO_DEFAULTS : {});
  }

  function freqOfId(id) {
    if (typeof freqOf === "function") return freqOf(id);
    const m = String(id).match(/^([A-G]s?)(\d)$/);
    if (!m) return 440;
    const semi = { C: 0, Cs: 1, D: 2, Ds: 3, E: 4, F: 5, Fs: 6, G: 7, Gs: 8, A: 9, As: 10, B: 11 };
    return 440 * Math.pow(2, (semi[m[1]] + (+m[2] + 1) * 12 - 69) / 12);
  }
  function gridBeats(t) {
    if (!t || t.type === "bar" || t.type === "tempo") return 0;
    return t.beats || ((4 / (t.dur || 4)) * (t.dotted ? 1.5 : 1) * (t.triplet ? 2 / 3 : 1));
  }
  function spelled(id, tok) {
    if (tok && typeof spelledLabel === "function") return spelledLabel(tok);
    return String(id).replace(/^([A-G])s(\d)$/, "$1#$2");
  }
  function centsOf(hz, target) {
    return hz > 0 && target > 0 ? 1200 * Math.log2(hz / target) : 999;
  }

  function isPitchedTok(t) {
    return (t.type === "note" || t.type === "tie") && window.NOTES && NOTES.includes(t.id);
  }
  function soundableAfter(tokens, i) {
    // first non bar/tempo token at or after i (the junction check for ~)
    for (let k = i; k < tokens.length; k++) {
      const t = tokens[k];
      if (t.type === "bar" || t.type === "tempo") continue;
      return k;
    }
    return -1;
  }

  // Absorb the tie chain that follows a note, passing straight through bar
  // and tempo lines — a long note crossing a bar (`A4/2 | -/4`) is still one
  // hold spanning its whole summed notated length.
  function absorbTies(tokens, from, id) {
    let end = from;
    for (let k = from + 1; k < tokens.length; k++) {
      const t = tokens[k];
      if (t.type === "bar" || t.type === "tempo") continue;
      if (t.type === "tie" && NOTES.includes(t.id) && t.id === id) { end = k; continue; }
      break;
    }
    return end;
  }

  // Absorb consecutive ~ slide hops: each next soundable token that bends
  // in (slideFrom === previous pitch, playable, a NEW pitch) joins the
  // chain, and each hop's own ties are absorbed across bar lines too.
  function absorbHops(tokens, from, firstId) {
    const zones = [freqOfId(firstId)];
    const names = [firstId];
    const zoneIdx = [from];
    let end = absorbTies(tokens, from, firstId);
    let prevId = firstId;
    let slide = false;
    for (;;) {
      const j = soundableAfter(tokens, end + 1);
      if (j < 0) break;
      const nt = tokens[j];
      if (nt.type === "tie" || !nt.slide || !NOTES.includes(nt.id) ||
          nt.id === prevId || nt.slideFrom !== prevId) break;
      slide = true;
      zones.push(freqOfId(nt.id));
      names.push(nt.id);
      zoneIdx.push(j);
      prevId = nt.id;
      end = absorbTies(tokens, j, nt.id);
    }
    return { end, zones, names, zoneIdx, slide };
  }

  // One practice bar = one hit + one fill track made of one segment per
  // pitch (single notes have just zone 0). Ties are absorbed across bar
  // lines; a ~ slide chain adds one zone per hop and the player must credit
  // 75% of every zone's equal share — camping the first note no longer
  // finishes.
  function buildBar(tokens, i) {
    const chainId = tokens[i].id;
    const { end, zones, names, zoneIdx, slide } = absorbHops(tokens, i, chainId);
    let beats = 0;
    for (let k = i; k <= end; k++) {
      if (tokens[k].type === "bar" || tokens[k].type === "tempo") continue;
      beats += gridBeats(tokens[k]);
    }
    // Staccato: practice half the note's normal duration (melody is leading).
    const stac = tokens[i].staccato && end === i;
    const targetSec = Math.max(0.05, beats * P.quarter * (stac ? 0.5 : 1));
    const freqs = zones.slice().sort((a, b) => a - b);
    return {
      startIdx: i, endIdx: end, zones, names, chainId, slide, stac,
      zoneIdx,                               // token index of each zone
      hiZone: 0,                             // zone currently highlighted
      targetSec,
      segTarget: targetSec * 1000 * REQUIRED_FRAC / zones.length, // ms each zone must earn
      segs: zones.map(() => 0),              // ms credited per zone
      grace: zones.map(() => 0),             // arrival tolerance left per zone
      minZ: freqs[0], maxZ: freqs[freqs.length - 1], // corridor bounds
    };
  }

  // ------------------------------------------------------------ state texts
  function barName() { return spelled(P.bar.names ? P.bar.names[0] : P.bar.chainId, P.tokens[P.bar.startIdx]); }
  function barChain() { return (P.bar.names || [P.bar.chainId]).join("\u2192"); }
  function barFilled(b) { let s = 0; for (const x of b.segs) s += x; return s; }
  // Progress toward the release point: segTarget already carries the 75%
  // requirement, so the whole-bar fraction reaches 1 exactly when the bar
  // completes (every zone holding its required credit).
  function barFrac(b) {
    const need = b.segTarget * b.zones.length;
    return need > 0 ? Math.max(0, Math.min(1, barFilled(b) / need)) : 0;
  }
  function barDone(b) { return b.segs.every(x => x >= b.segTarget - 1e-6); }
  function statusText(s) {
    switch (s) {
      case "await": return "Fresh attack needed — pause briefly, then hit " + barName();
      case "ready": return "Ready — play " + barName();
      case "hit": return "Hit. Steady to the pitch…";
      case "fill": return P.bar.slide ? "Bend " + barChain() : "Hold " + barName();
      case "rest": return "Rest";
      default: return "";
    }
  }

  // ------------------------------------------------------------------ UI
  let panel = null, els = {};
  function buildPanel() {
    if (panel || typeof document === "undefined") return panel;
    panel = document.createElement("div");
    panel.className = "prac-panel noprint";
    panel.hidden = true;
    panel.innerHTML =
      '<div class="prac-row1"><span class="prac-note">—</span>' +
      '<span class="prac-cents">0¢</span>' +
      '<span class="prac-status"></span>' +
      '<span class="prac-fillval"></span></div>' +
      '<div class="prac-scale"><div class="prac-zone"></div><div class="prac-mark"></div></div>' +
      '<div class="prac-track"><div class="prac-fill"></div></div>';
    els.note = panel.querySelector(".prac-note");
    els.cents = panel.querySelector(".prac-cents");
    els.status = panel.querySelector(".prac-status");
    els.fillval = panel.querySelector(".prac-fillval");
    els.scale = panel.querySelector(".prac-scale");
    els.zone = panel.querySelector(".prac-zone");
    els.mark = panel.querySelector(".prac-mark");
    els.track = panel.querySelector(".prac-track");
    els.fill = panel.querySelector(".prac-fill");
    // No Pause/Skip/Restart/End here: the transports own mode control, and
    // clicking any token re-anchors the practice. The panel is a pure tuner
    // display (draggable by its face).
    makeDraggable(panel);
    // Inside #tabPanel in both layouts: it must be visible while the
    // zen fullscreen is active (body-level content would be painted over).
    const host = document.getElementById("tabPanel") || document.body;
    host.appendChild(panel);
    return panel;
  }

  function makeDraggable(p) {
    let sx = 0, sy = 0, ox = 0, oy = 0, dragging = false;
    p.addEventListener("pointerdown", e => {
      if (e.button !== 0) return;
      if (e.target.closest("button")) return; // drag the face, not the controls
      const r = p.getBoundingClientRect();
      // Drop the centering transform; anchor by the panel's top-left corner
      // (clamped to stay on screen when re-applying after zen relief).
      p.style.transform = "none";
      p.style.left = r.left + "px";
      p.style.top = r.top + "px";
      dragging = true;
      sx = e.clientX; sy = e.clientY; ox = r.left; oy = r.top;
      p.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    p.addEventListener("pointermove", e => {
      if (!dragging) return;
      const w = p.offsetWidth, h = p.offsetHeight;
      const x = Math.max(4, Math.min(window.innerWidth - w - 4, ox + e.clientX - sx));
      const y = Math.max(4, Math.min(window.innerHeight - h - 4, oy + e.clientY - sy));
      p.style.left = x + "px";
      p.style.top = y + "px";
    });
    const done = () => dragging = false;
    p.addEventListener("pointerup", done);
    p.addEventListener("pointercancel", done);
  }

  function zoneHex() {
    const id = P.bar.chainId;
    const ch = window.CHAMBER ? CHAMBER[id] : 1;
    return "var(--ch" + (ch || 1) + ")";
  }
  function zoneHexFor(id) {
    const ch = window.CHAMBER ? CHAMBER[id] : 1;
    return "var(--ch" + (ch || 1) + ")";
  }
  // Chain bars draw the track as one section per zone: N cells, each with
  // its own credit-filled inner bar (colored by that zone's chamber).
  // Single-note bars keep one slice; returns true when slice mode was used.
  function fillSlices(el, bar) {
    const n = bar.zones.length;
    if (n > 1) {
      if (el._slices !== n) {
        el._slices = n;
        el.innerHTML = "";
        el.style.display = "flex";
        el.style.gap = "2px";
        el.style.width = "100%";
        el.style.background = "transparent";
        for (let k = 0; k < n; k++) {
          const cell = document.createElement("div");
          cell.style.cssText = "flex:1 1 0;position:relative;background:rgba(0,0,0,.25);border-radius:2px;overflow:hidden;height:100%";
          const inner = document.createElement("div");
          inner.style.cssText = "position:absolute;left:0;top:0;bottom:0;width:0%;transition:width .1s linear";
          cell.appendChild(inner);
          el.appendChild(cell);
        }
      }
      [...el.children].forEach((cell, k) => {
        const seg = bar.segs[k] || 0;
        const frac = Math.max(0, Math.min(1, seg / (bar.segTarget || 1)));
        const inner = cell.firstChild;
        inner.style.width = (frac * 100) + "%";
        inner.style.background = zoneHexFor(bar.names[k]);
        inner.style.opacity = seg >= bar.segTarget ? "1" : ".8";
      });
      return true;
    }
    if (el._slices != null) {
      // back to single mode: clear the section DOM so the plain fill applies
      el._slices = null;
      el.innerHTML = "";
      el.style.display = "";
      el.style.gap = "";
      el.style.width = "";
      el.style.background = "";
    }
    return false;
  }
  function renderPanel() {
    if (!panel || !P.bar) return;
    const dg = dbg();
    let studio = P.paused
      ? (P.completed ? "Song end — Play or Practice resumes." : "Paused — Play/Practice or Space resumes.")
      : (statusText(P.state) || P.err);
    // 44.1/48 kHz suspicion: when the mic track reports a rate that differs
    // from the analyser context's, that mismatch would show up as a fixed
    // ±148.7¢ in the cents readout — say so, it is a measurement, displayed.
    if (P.mic && !TEST && P.mic.trackRate && P.mic.trackRate !== P.mic.sr) {
      studio += " · mic " + (P.mic.trackRate / 1000).toFixed(1) + "kHz → ctx " +
        (P.mic.sr / 1000).toFixed(1) + "kHz";
    }
    els.status.textContent = studio;
    if (P.bar) {
      // The tuner names the CURRENT target: the chain's frontier zone —
      // "zone 2/3" means the note shown is the one you must be on now.
      const nm = (P.bar.names && P.zonesNear >= 0 ? P.bar.names[P.zonesNear] : P.bar.names ? P.bar.names[0] : P.bar.chainId);
      els.note.textContent = String(nm).replace(/^([A-G])s(\d)$/, "$1#$2");
      // needle
      const c = Math.max(needleLo, Math.min(needleHi, P.cents));
      els.mark.style.left = (50 + (c / needleHi) * 50) + "%";
      els.cents.textContent = Math.abs(P.cents) > 300 ? "—" : (P.cents > 0 ? "+" : "") + P.cents.toFixed(0) + "\u00A2";
      const zw = Math.min(100, (dg.tuneCents / needleHi) * 50);
      els.zone.style.left = (50 - zw) + "%";
      els.zone.style.width = (zw * 2) + "%";
      // fill
      const pct = barFrac(P.bar) * 100;
      if (!fillSlices(els.fill, P.bar)) {
        els.fill.style.width = pct + "%";
        els.fill.style.background = (P.state === "fill" && barFilled(P.bar) > 0) || P.state === "hit"
          ? zoneHex() : (barFilled(P.bar) > 0 ? "var(--accent)" : "transparent");
      }
      els.fillval.textContent = (P.bar.zones.length > 1
        ? "zone " + ((P.zonesNear < 0 ? 0 : P.zonesNear) + 1) + "/" + P.bar.zones.length + " · " : "") +
        Math.round(pct) + "% · " + (P.bar.targetSec).toFixed(1) + "s";
      els.fillval.classList.toggle("prac-warn", P.state === "fill" && barFilled(P.bar) <= 0 && P.rms > dg.rmsGate);
    }
  }

  // Fill line under the highlighted token/card (both strips + live card).
  let fillBars = new Map(); // element -> span child
  const posRel = new Set();  // elements we granted .prac-pos-rel
  function updateFillOverlays() {
    if (!P.active) { clearOverlays(); return; }
    const targets = ["#tokens", "#focusTokens", "#sheet"].map(s => document.querySelector(s)).filter(Boolean);
    const dg = dbg();
    const pct = P.bar ? barFrac(P.bar) : 0;
    const live = new Set();
    for (const host of targets) {
      // token strips and card sheets: the sliding fill lives on whichever
      // element is highlighted (.tok.now in grid mode, .card.now otherwise)
      const el = host.querySelector(".tok.now") || host.querySelector(".card.now");
      if (!el) continue;
      live.add(el);
      let bar = fillBars.get(el);
      if (!bar) {
        if (getComputedStyle(el).position === "static") {
          el.classList.add("prac-pos-rel");
          posRel.add(el);
        }
        bar = document.createElement("span");
        bar.className = "prac-tok-fill";
        el.appendChild(bar);
        fillBars.set(el, bar);
      }
      bar.style.background = P.state === "fill" || P.state === "hit" ? zoneHex() : "var(--accent)";
      bar.style.opacity = P.state === "fill" || P.state === "hit" || pct > 0 ? "1" : "0.35";
      if (!fillSlices(bar, P.bar)) bar.style.width = (pct * 100) + "%";
      else bar.style.width = "100%";
    }
    for (const [el, bar] of Array.from(fillBars)) {
      if (!live.has(el)) { try { bar.remove(); } catch (e) {} fillBars.delete(el); }
    }
  }

  // Remove every accuracy bar and the positioning helper classes — leaving
  // practice (or completing the song) must return the score to its normal look.
  function clearOverlays() {
    for (const [, bar] of Array.from(fillBars)) { try { bar.remove(); } catch (e) {} }
    fillBars.clear();
    for (const el of Array.from(posRel)) { try { el.classList.remove("prac-pos-rel"); } catch (e) {} }
    posRel.clear();
  }

  // ------------------------------------------------------------------- mic
  async function ensureMic() {
    if (P.mic) return;
    // TEST harness: no real capture — frames come from window.__pracFrame;
    // the fake track exposes plain rates for the diagnostics readout.
    if (TEST) {
      P.mic = { stream: null, source: null, analyser: null, buf: null, sr: 48000, trackRate: 48000 };
      return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("Microphone access needs HTTPS (localhost is fine).");
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }
    });
    if (typeof unlockAudio === "function") unlockAudio();
    const ctx = typeof audioCtx !== "undefined" && audioCtx ? audioCtx : null;
    if (!ctx) throw new Error("Audio context unavailable.");
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser); // NOT to ctx.destination — no monitoring feedback
    // Rate diagnostics: the browser resamples the mic into the context rate,
    // so analysis at ctx.sampleRate is normally exact; a track/context rate
    // disagreement is displayed in the tuner (a 44.1/48 mix would read a
    // fixed ±148.7¢ in the cents delta).
    let trackRate = null;
    try {
      const st = stream.getAudioTracks()[0] && stream.getAudioTracks()[0].getSettings();
      if (st && st.sampleRate) trackRate = st.sampleRate;
    } catch (e) {}
    P.mic = {
      stream, source, analyser,
      buf: new Float32Array(analyser.fftSize),
      sr: ctx.sampleRate,
      trackRate,
    };
  }

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
    const minLag = Math.max(2, Math.floor(sr / MAX_HZ));
    const maxLag = Math.min(half, Math.ceil(sr / MIN_HZ));
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

  function readFrame() {
    if (TEST) {
      const f = window.__pracFrame;
      if (!f) { P.rms = 0; P.hz = 0; return; }
      P.rms = f.rms || 0;
      P.hz = f.hz || 0;
    } else if (P.mic) {
      P.mic.analyser.getFloatTimeDomainData(P.mic.buf);
      const buf = P.mic.buf, sr = P.mic.sr;
      let s = 0;
      for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
      P.rms = Math.sqrt(s / buf.length);
      P.hz = P.rms >= dbg().rmsGate ? autoCorrelate(buf, sr) : 0;
    }
    // The pitch is measured as-is — no correction factors. Whatever the
    // capture chain does shows up in the cents delta, displayed live.
    if (P.hz && (P.hz < MIN_HZ * 0.6 || P.hz > MAX_HZ * 1.3)) P.hz = 0;
    P.hzSm = P.rms > 0 ? (P.hzSm && P.hz ? P.hzSm * (1 - 0.55) + P.hz * 0.55 : P.hz) : 0;
    const zones = P.bar ? P.bar.zones : [];
    let best = 999;
    zones.forEach((z, k) => {
      const c = centsOf(P.hzSm, z);
      if (c === 999) return;
      const a = Math.abs(c);
      if (a < best) best = a;
    });
    // The tuner (and the credit) point at the NEXT REQUIRED section: the
    // first zone that still needs its share. Sections fill strictly in
    // order along the chain — a pitch duplicated later in the chain must
    // never advance its later section while the middle is still open.
    let near = -1, cents = 999;
    if (P.bar) {
      const segT = P.bar.segTarget;
      near = P.bar.zones.findIndex((z, k) => P.bar.segs[k] < segT - 1e-6);
      if (near < 0) near = zones.length - 1; // all locked: park on the last zone
      cents = centsOf(P.hzSm, zones[near]);
    }
    P.zonesBest = best;
    P.zonesNear = near;
    P.zonesNearCents = near >= 0 && cents !== 999 ? Math.abs(cents) : 999;
    P.cents = cents;
  }

  // Zen glow, practice edition: same envelope as the play-mode pulse — the
  // halo rises toward the duration-scaled PEAK (not to full white) over the
  // note body while the player holds it, sinks when the hold breaks, and on
  // completion the current intensity SPARKS (brief overshoot, then fades).
  // ON TOP: the HIT gets a burst — a bright pop that explodes outward from
  // the halo center and decays back onto the sustain rise (strong positive
  // feedback for the articulation itself). Playback's one-shot pulse is
  // bypassed (highlightToken sound=false).
  const BURST_MS = 360;
  let sparkUntil = 0, sparkTimer = 0;
  let burstUntil = 0, burstT0 = 0;

  function glowParams() {
    const id = P.bar ? P.bar.chainId : null;
    const t = (typeof noteMidi === "function" && id)
      ? Math.max(0, Math.min(1, (noteMidi(id) - 57) / 34))
      : 0;
    const dur = P.bar ? P.bar.targetSec * 1000 : 400;
    const startScale = 0.7;
    const fullScale = Math.min(1.25, startScale + dur / 3000);
    const durF = Math.min(1, dur / 1200);
    const peak = (0.28 + t * t * 0.4) * (0.45 + 0.55 * durF);
    return { t, startScale, fullScale, peak };
  }

  function zenGlowApply(panel, alpha, scale, fadeMs) {
    panel.style.setProperty("--glow-alpha", alpha.toFixed(3));
    panel.style.setProperty("--glow-scale", scale.toFixed(3));
    panel.style.setProperty("--glow-fade", fadeMs + "ms");
  }

  function zenGlowFill() {
    const panel = document.getElementById("tabPanel");
    if (!panel || !panel.classList.contains("focus")) return;
    if (performance.now() < sparkUntil) return; // the completion spark owns the glow
    // Anchor the halo on the live card, same as pulseZenGlow.
    const card = panel.querySelector(".card.live") ||
                 panel.querySelector(".sheet.live .card") ||
                 panel.querySelector("svg.ocarina");
    if (card) {
      const p = panel.getBoundingClientRect();
      const c = card.getBoundingClientRect();
      if (p.width && p.height) {
        panel.style.setProperty("--glow-x", ((c.left + c.width / 2 - p.left) / p.width * 100) + "%");
        panel.style.setProperty("--glow-y", ((c.top + c.height / 2 - p.top) / p.height * 100) + "%");
      }
    }
    const { t, startScale, fullScale, peak } = glowParams();
    panel.style.setProperty("--glow-hue", Math.round(30 + t * 160));
    panel.style.setProperty("--glow-sat", Math.round(72 - t * t * 72) + "%");
    panel.style.setProperty("--glow-light", Math.round(50 + t * t * 48) + "%");
    // HIT BURST: bright pop, ring exploding outward, decaying onto the rise.
    if (performance.now() < burstUntil) {
      const p = Math.min(1, (performance.now() - burstT0) / BURST_MS);
      const k = Math.pow(1 - p, 1.4);
      const alpha = Math.min(1, peak * 2.4) * k;
      const scale = fullScale * (0.8 + 0.55 * p); // expands outward past the reach
      zenGlowApply(panel, alpha, scale, 60);
      return;
    }
    const f = P.bar ? barFrac(P.bar) : 0;
    const e = 1 - (1 - f) * (1 - f); // ease-out, like the play pulse's rise
    if (P.state === "hit") {
      // At the onset the glow starts swelling right away, like play.
      const p0 = 1 - (P.transientLeft / Math.max(1, dbg().transientMs));
      zenGlowApply(panel, 0.45 * peak * p0, startScale + 0.15 * (fullScale - startScale), 140);
    } else if (P.state === "fill" && f > 0) {
      zenGlowApply(panel, peak * e, startScale + (fullScale - startScale) * e, 140);
    } else {
      zenGlowApply(panel, 0, startScale, 450);
    }
  }

  // HIT burst: fired exactly when the onset is armed. The circle pops at a
  // high intensity and blows outward past the normal reach, giving the
  // player an immediate "you hit it" flash before the sustain glow takes
  // over.
  function zenGlowBurst() {
    const panel = document.getElementById("tabPanel");
    if (!panel || !panel.classList.contains("focus")) return;
    burstT0 = performance.now();
    burstUntil = burstT0 + BURST_MS;
    zenGlowFill(); // apply the first burst frame immediately
  }

  // Completion spark: the current intensity overshoots briefly, then dies.
  function zenGlowSpark() {
    const panel = document.getElementById("tabPanel");
    if (!panel || !panel.classList.contains("focus")) return;
    const { fullScale, peak } = glowParams();
    clearTimeout(sparkTimer);
    zenGlowApply(panel, Math.min(1, peak * 1.7), fullScale * 1.15, 90);
    sparkUntil = performance.now() + 480;
    sparkTimer = setTimeout(() => {
      sparkTimer = 0;
      if (!panel.classList.contains("focus")) return;
      zenGlowApply(panel, 0, fullScale, 340);
    }, 140);
  }

  function zenGlowOff() {
    sparkUntil = 0;
    burstUntil = 0;
    if (sparkTimer) { clearTimeout(sparkTimer); sparkTimer = 0; }
    if (typeof freezeZenGlow === "function") { try { freezeZenGlow(); } catch (e) {} }
  }

  // ------------------------------------------------------------- transport
  // Button on/off classes and disable states live in ui.js
  // (updateTransportUI — the single symmetric source of truth).

  function enterIdx(i) {
    P.idx = i;
    const t = P.tokens[i];
    if (!t) { P.state = "done"; return; }
    if (t.type === "tempo") { P.quarter = quarterSecFor(t.bpm); enterIdx(i + 1); return; }
    if (t.type === "bar") { enterIdx(i + 1); return; }
    if (t.type === "rest") {
      P.state = "rest";
      P.restLeft = gridBeats(t) * P.quarter * 1000;
      try { if (typeof highlightToken === "function") highlightToken(i, null, undefined, false); } catch (e) {}
      return;
    }
    P.bar = buildBar(P.tokens, i);
    P.state = "await";
    P.gapAcc = 0;
    P.transientLeft = 0;
    P.hzSm = 0;
    try {
      // sound=false: the practice glow is driven by the FILL progress below,
      // not by the one-shot arrival pulse of playback.
      if (typeof highlightToken === "function") highlightToken(i, t.id, P.bar ? P.bar.targetSec : undefined, false);
    } catch (e) {}
  }

  function advance() { enterIdx(P.idx + 1); }
  function nextPitchedIdx(i) {
    for (let k = i; k < P.tokens.length; k++) if (isPitchedTok(P.tokens[k])) return k;
    return -1;
  }

  function tick() {
    if (!P.active || P.paused) return;
    const now = performance.now();
    const dt = Math.min(50, now - (P.last || now));
    P.last = now;
    const dg = dbg();

    const t = P.tokens[P.idx];
    if (!t) { endReached(); return; }
    readFrame();

    // auto-pass tokens
    if (t.type === "tempo") { P.quarter = quarterSecFor(t.bpm); advance(); return; }
    if (t.type === "bar") { advance(); return; }
    if (t.type === "rest") {
      P.state = "rest";
      P.restLeft -= dt;
      if (P.restLeft <= 0) advance();
      return;
    }

    const b = P.bar;
    const sounding = P.rms >= dg.rmsGate;

    switch (P.state) {
      case "await": {
        // A hit needs a real articulation: continuous silence for gapMs first.
        if (!sounding) {
          P.gapAcc += dt;
          if (P.gapAcc >= dg.gapMs) { P.state = "ready"; renderPanel(); }
        } else P.gapAcc = 0;
        break;
      }
      case "ready": {
        // Arm on in-tune onset (transient tolerance against zone 0).
        const armErr = Math.abs(centsOf(P.hzSm, b.zones[0]));
        if (P.hzSm > 0 && armErr <= dg.transientCents) {
          P.state = "hit";
          P.transientLeft = dg.transientMs;
          b.segs = b.segs.map(() => 0);
          b.grace = b.grace.map(() => 0);
          b.grace[0] = dg.transientMs;
          zenGlowBurst(); // "you hit it" — the halo pops and blows outward
        } else if (!sounding) P.gapAcc = Math.min(P.gapAcc + dt, dg.gapMs);
        break;
      }
      case "hit": {
        // Onset grace: the chiff may read flat/short. The onset COUNTS: the
        // moment it lands in tolerance the hold accrues from there on.
        P.transientLeft -= dt;
        b.segs[0] = Math.min(b.segTarget, b.segs[0] + dt);
        if (barDone(b)) { finishBar(); return; }
        if (P.transientLeft <= 0) { P.state = "fill"; }
        break;
      }
      case "fill": {
        // Gradient credit: 1x inside the clean zone. Beyond the green edge
        // — still inside the outer bandwidth (2x the green width) — the
        // rate falls off linearly from 1 to a 2x DRAIN at the outer edge:
        // drift further out and it feels like swimming against a current
        // that grows with how far off you are. Leaving the outer bandwidth
        // of the bar's corridor, or silence beyond the grace, wipes the bar
        // (fresh attack); a shorter hiccup only pauses it (a measurement
        // glitch must not bankrupt a real hold).
        //
        // Chain bars (~/slides, multi-hop) split the notated length into
        // equal shares, one per zone: each zone must earn 75% of its own
        // share ("the ones that were successful count in the chain") — the
        // freed quarter is travel budget. The region between zones is in
        // transit: neutral — no accrual, no drain (so a fast sweep and a
        // slow walk are both legitimate). Chains get a rather large grace
        // toward the next zone (chainTravelMs): it is the wipe threshold
        // for silence and stray pitches mid-travel, and it renews the
        // arrival tolerance — so a breath between fingerings, a slow sweep
        // and settling onto the next pitch after arrival are all
        // legitimate. Completed zones are locked and never drained.
        const TUNE = dg.tuneCents, TRANS = dg.transientCents, OUTER = dg.tuneCents * 2;
        const chain = b.zones.length > 1;
        const wipeMs = chain ? dg.chainTravelMs : dg.gapMs;
        const arrMs = chain ? Math.max(dg.transientMs, dg.chainTravelMs) : dg.transientMs;
        const k = P.zonesNear, ci = P.zonesNearCents;
        const outOfCorridor = !sounding ||
          (P.hz && (centsOf(P.hzSm, b.minZ) < -OUTER || centsOf(P.hzSm, b.maxZ) > OUTER));
        if (outOfCorridor) {
          P.dropAcc = (P.dropAcc || 0) + dt;
          if (P.dropAcc >= wipeMs) {
            b.segs = b.segs.map(() => 0);
            P.dropAcc = 0;
            P.state = "await";
            P.gapAcc = 0;
          }
        } else if (k < 0) {
          // defensive: sounding but unmappable (should not happen)
        } else if (ci <= TUNE) {
          P.dropAcc = 0;
          b.grace[k] = arrMs;
          if (b.segs[k] < b.segTarget) b.segs[k] = Math.min(b.segTarget, b.segs[k] + dt);
        } else if (ci <= TRANS && b.grace[k] > 0) {
          // arrival tolerance: the note counts from the moment it lands
          P.dropAcc = 0;
          b.grace[k] -= dt;
          if (b.segs[k] < b.segTarget) b.segs[k] = Math.min(b.segTarget, b.segs[k] + dt);
        } else if (ci <= OUTER) {
          P.dropAcc = 0;
          if (b.segs[k] < b.segTarget) {
            const rate = 1 - 3 * (ci - TUNE) / (OUTER - TUNE); // 1 .. -2
            b.segs[k] = Math.max(0, b.segs[k] + rate * dt);
          }
        } else {
          // inside the corridor but far from every zone: in transit
          P.dropAcc = 0;
          b.grace[k] = arrMs; // renewed for the arrival
        }
        if (barDone(b)) { finishBar(); return; }
        // A finished section advances the frontier: move the reading line,
        // the token bar and the fingering card to the CURRENT target.
        const nf = b.zones.findIndex((z, k) => b.segs[k] < b.segTarget - 1e-6);
        const fi = nf < 0 ? b.zones.length - 1 : nf;
        if (fi !== b.hiZone && b.zoneIdx) {
          b.hiZone = fi;
          // Keep the tuner on the new target in the same tick: needle, cents
          // and note name must not lag a frame behind the reading line.
          P.zonesNear = fi;
          P.zonesNearCents = Math.abs(centsOf(P.hzSm, b.zones[fi]));
          P.cents = centsOf(P.hzSm, b.zones[fi]);
          const hi = Math.min(fi, b.zoneIdx.length - 1);
          try { if (typeof highlightToken === "function") highlightToken(b.zoneIdx[hi], b.names[fi], b.targetSec, false); } catch (e) {}
        }
        break;
      }
    }
    renderPanel();
    zenGlowFill();
    updateFillOverlays();
  }

  function finishBar() {
    zenGlowSpark(); // the completed note's intensity sparks as the advance lands
    const afterIdx = P.bar.endIdx + 1;
    enterIdx(afterIdx < P.tokens.length ? afterIdx : P.tokens.length);
    if (P.idx >= P.tokens.length) endReached();
  }

  // There is no "end" state per the mode's design: the song just stops
  // waiting — with Loop on it wraps and keeps practicing, without it the
  // practice disengages to paused (the user toggles Loop themselves).
  function endReached() {
    if (typeof loopOn === "function" && loopOn()) {
      enterIdx(nextPitchedIdx(0));
      return;
    }
    standby();
  }

  function standby() {
    P.completed = true;
    P.paused = true; // frozen at the end; Resume wraps to the first note
    clearOverlays(); // the last note's bar ends with the song
    if (panel) panel.hidden = true; // neutral: no tuner
    zenGlowOff();
    if (typeof syncTransport === "function") try { syncTransport(); } catch (e) {}
  }

  // --------------------------------------------------------------- control
  function startPractice(fromIdx) {
    if (typeof stopMelody === "function") try { stopMelody(); } catch (e) {}
    P.tokens = (typeof lastTokens !== "undefined" && lastTokens.length)
      ? lastTokens : (typeof parse === "function" ? parse(document.getElementById("src").value) : []);
    if (!P.tokens.length) { P.err = "No melody to practice — type some notes first."; openPanel(); renderPanel(); return; }
    P.quarter = quarterSec();
    P.completed = false;
    P.paused = false;
    P.err = "";
    P.active = true;
    openPanel();
    const start = nextPitchedIdx((typeof fromIdx === "number") ? fromIdx : 0);
    if (start < 0) { P.err = "No playable notes in this melody."; renderPanel(); return; }
    enterIdx(start);
    if (!TEST) { try { micFlow(); } catch (e) { P.err = String(e && e.message || e); renderPanel(); } }
    if (!P.interval) {
      P.last = performance.now();
      P.interval = setInterval(tick, TICK_MS);
    }
    syncTransportAny();
  }

  async function micFlow() {
    try {
      await ensureMic();
      P.err = "";
    } catch (e) {
      P.err = String(e && e.message || e).replace("Error: ", "");
      renderPanel();
    }
  }

  function stopPractice() {
    P.active = false; P.paused = false; P.completed = false; P.bar = null;
    if (P.interval) { clearInterval(P.interval); P.interval = 0; }
    if (P.mic) {
      try { P.mic.source.disconnect(); } catch (e) {}
      try { P.mic.stream.getTracks().forEach(tr => tr.stop()); } catch (e) {}
      P.mic = null;
    }
    clearOverlays();
    // The last note is still wearing its "now" highlight; reset the score UI
    // so nothing of practice mode is left behind.
    if (typeof clearHighlight === "function") { try { clearHighlight(); } catch (e) {} }
    zenGlowOff();
    if (panel) panel.hidden = true;
    syncTransportAny();
  }

  function practicePauseToggle() {
    if (!P.active) return;
    P.paused = !P.paused;
    P.last = performance.now();
    // Disengaged (paused) = neutral: the tuner never shows while practice is
    // not running.
    if (panel) panel.hidden = P.paused;
    zenGlowOff(); // pause must not leave the halo animating on its own
    // Resuming while parked at the song end: wrap to the first note (a fresh
    // pass), regardless of the Loop setting.
    if (!P.paused && P.idx >= P.tokens.length) enterIdx(nextPitchedIdx(0));
    renderPanel();
    syncTransportAny();
  }
  function practiceFrom(idx) {
    if (!P.active) return;
    P.paused = false; P.completed = false;
    enterIdx(nextPitchedIdx(idx));
    renderPanel();
    syncTransportAny();
  }

  function openPanel() {
    buildPanel();
    panel.hidden = false;
  }

  function syncTransportAny() {
    if (typeof updateTransportUI === "function") { try { updateTransportUI(); } catch (e) {} }
  }

  // Public surface (guarded-globals like the other modules)
  window.OCA_PRACTICE = {
    // state getters (debug/tests)
    active: () => P.active, paused: () => P.paused, idx: () => P.idx,
    state: () => P.state, fillPct: () => P.bar ? Math.max(0, Math.min(1, barFilled(P.bar) / (P.bar.targetSec * 1000))) : 0,
    targetSec: () => P.bar ? P.bar.targetSec : 0,
    seq: () => P.tokens.map(t => t.id || t.type).join(" "),
    barInfo: () => P.bar && { start: P.bar.startIdx, end: P.bar.endIdx, zones: P.bar.zones, names: P.bar.names, sec: P.bar.targetSec, chain: P.bar.zones.length > 1, slide: P.bar.slide, stac: P.bar.stac },
    micOn: () => !!P.mic,
    _p: P, // diagnostics/tests: full live state
    // Detector test hook: renders a tone at f/sr with a harmonic mix (h =
    // [1, 0.15] default = fundamental + 15% H2) plus optional noise, and
    // returns the measured Hz — for verifying autoCorrelate from the console.
    testAC: function (f, sr, h, noise) {
      const n = 2048, buf = new Float32Array(n);
      const H = h || [1, 0.15];
      let seed = 42;
      const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
      for (let i = 0; i < n; i++) {
        let v = 0;
        for (let k = 0; k < H.length; k++) {
          v += H[k] * Math.sin(2 * Math.PI * f * (k + 1) * i / sr);
        }
        if (noise) v += noise * (rnd() * 2 - 1);
        buf[i] = v;
      }
      return autoCorrelate(buf, sr);
    },
    // transport anchors: where practice currently stands (token idx)
    posIdx: () => P.idx,
    from: practiceFrom, pauseToggle: practicePauseToggle,
    start: startPractice, stop: stopPractice,
    status: () => panel && els.status ? panel.querySelector(".prac-status").textContent : "",
  };
})();

// Convenience globals used by ui.js hooks (guarded by typeof at call sites)
function isPracticeActive() { return !!(window.OCA_PRACTICE && OCA_PRACTICE.active()); }
function isPracticePaused() { return !!(window.OCA_PRACTICE && OCA_PRACTICE.paused()); }
function practiceToggle() { if (window.OCA_PRACTICE) OCA_PRACTICE.pauseToggle(); }
