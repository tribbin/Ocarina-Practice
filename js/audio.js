let audioCtx = null;
let hoverQuietUntil = 0;
let liveVoices = [];
let melodyBag = [];
let melodyTimer = 0;
let melodyPlaying = false;
let melodyTokens = [];
let melodyIdx = 0;
let melodyFrom = 0;
let melodyPos = 0;
let melodyHoldUntil = -1;
let melodyPaused = false;
let lastHoldSec = 0.5; // sounding duration of the last scheduled note (for zen glow)

function syncTransport() {
  if (typeof updateTransportUI === "function") updateTransportUI();
}

function tokenGridBeats(tok) {
  if (!tok || tok.type === "bar") return 0;
  return tok.beats || ((4 / (tok.dur || 4)) * (tok.dotted ? 1.5 : 1));
}

function soundingGridBeats(tokens, idx) {
  let p = tokenGridBeats(tokens[idx]);
  for (let i = idx + 1; i < tokens.length; i++) {
    if (tokens[i].type === "bar") continue;
    if (tokens[i].type === "tie") p += tokenGridBeats(tokens[i]);
    else break;
  }
  return p;
}

function lastHoldIndex(tokens, idx) {
  let last = idx;
  for (let i = idx + 1; i < tokens.length; i++) {
    if (tokens[i].type === "bar") continue;
    if (tokens[i].type === "tie") last = i;
    else break;
  }
  return last;
}

function swungBeats(tok, pos) {
  const beats = tokenGridBeats(tok);
  const s = (typeof currentSwing === "function" ? currentSwing() : 0) / 100;
  if (s <= 0 || Math.abs(beats - 0.5) > 1e-6) return beats;
  const longF = 0.5 + s / 6;
  const onBeat = Math.round(pos * 2) % 2 === 0;
  return onBeat ? longF : 1 - longF;
}

function gridBeatsBefore(tokens, idx) {
  let p = 0;
  for (let i = 0; i < idx; i++) p += tokenGridBeats(tokens[i]);
  return p;
}

let reverbBus = null;   // input node that notes connect to (dry + wet split)
let reverbWetGain = null;
let reverbEnabled = false;

function makeReverbImpulse(ctx, seconds, decay) {
  const rate = ctx.sampleRate;
  const len = Math.floor(rate * seconds);
  const buf = ctx.createBuffer(2, len, rate);
  for (let ch = 0; ch < 2; ch++) {
    const d = buf.getChannelData(ch);
    for (let i = 0; i < len; i++) {
      d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
    }
  }
  return buf;
}

// Lazily build (and return) the reverb bus. All melodic voices connect here
// instead of straight to ctx.destination, so the wet level can be toggled.
// A limiter on the bus output protects headroom: individual voices sum to
// well over 1.0 under polyphony (overlapping/tied notes) and with reverb,
// which would clip hard at ctx.destination without it.
function getReverbBus(ctx) {
  if (reverbBus && reverbBus.context === ctx) return reverbBus;
  const input = ctx.createGain();
  const dry = ctx.createGain();
  dry.gain.value = 1;
  const convolver = ctx.createConvolver();
  convolver.buffer = makeReverbImpulse(ctx, 2.6, 3.2);
  const wet = ctx.createGain();
  wet.gain.value = reverbEnabled ? 0.5 : 0;
  // Brickwall-ish limiter: fast, high ratio, threshold just below 0 dBFS.
  const limiter = ctx.createDynamicsCompressor();
  limiter.threshold.value = -3;
  limiter.knee.value = 0;
  limiter.ratio.value = 20;
  limiter.attack.value = 0.003;
  limiter.release.value = 0.15;
  dry.connect(limiter);
  input.connect(dry);
  input.connect(convolver); convolver.connect(wet); wet.connect(limiter);
  limiter.connect(ctx.destination);
  reverbWetGain = wet;
  reverbBus = input;
  return reverbBus;
}

// Called by the UI when Zen mode is entered/exited.
function setReverbEnabled(on) {
  reverbEnabled = !!on;
  if (reverbWetGain && audioCtx) {
    const now = audioCtx.currentTime;
    reverbWetGain.gain.cancelScheduledValues(now);
    reverbWetGain.gain.setValueAtTime(reverbWetGain.gain.value, now);
    reverbWetGain.gain.linearRampToValueAtTime(reverbEnabled ? 0.32 : 0, now + 0.25);
  }
}

function unlockAudio() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
  } catch (e) {}
}

["pointerdown","pointerover","keydown","touchstart"].forEach(ev =>
  document.addEventListener(ev, unlockAudio, {passive:true})
);

function hushHovers() {
  hoverQuietUntil = Date.now() + 400;
  cutLive();
}
window.addEventListener("focus", hushHovers);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) cutLive();
  else hushHovers();
});

function freqOf(id) {
  const m = String(id).match(/^([A-G]s?)(\d)$/);
  if (!m) return 440;
  const semi = {C:0,Cs:1,D:2,Ds:3,E:4,F:5,Fs:6,G:7,Gs:8,A:9,As:10,B:11};
  const midi = semi[m[1]] + (+m[2] + 1) * 12;
  return 440 * Math.pow(2, (midi - 69) / 12);
}

// Per-chamber frequency ranges, cached from window.CHAMBER / window.NOTES.
let chamberRanges = null;
function getChamberRanges() {
  const notes = window.NOTES, chamberOf = window.CHAMBER;
  if (!notes || !chamberOf) return {};
  // Rebuild if the note set changed (e.g. instrument swapped).
  if (chamberRanges && chamberRanges._key === notes.length + ":" + notes[0]) {
    return chamberRanges;
  }
  const r = { _key: notes.length + ":" + notes[0] };
  notes.forEach(id => {
    const ch = chamberOf[id];
    if (ch == null) return;
    const f = freqOf(id);
    const cur = r[ch] || (r[ch] = { min: f, max: f });
    if (f < cur.min) cur.min = f;
    if (f > cur.max) cur.max = f;
  });
  chamberRanges = r;
  return r;
}

// Breathiness position (0..1) of a note WITHIN its own chamber: rises toward
// the top of each chamber and resets when a new chamber begins. Falls back to
// absolute pitch if chamber data is unavailable.
function chamberReg(id, freq) {
  const chamberOf = window.CHAMBER;
  const ch = chamberOf && chamberOf[id];
  const ranges = getChamberRanges();
  const range = ch != null ? ranges[ch] : null;
  if (range && range.max > range.min) {
    return Math.max(0, Math.min(1,
      Math.log2(freq / range.min) / Math.log2(range.max / range.min)));
  }
  return Math.max(0, Math.min(1, Math.log2(freq / 262) / 2));
}

// Per-chamber maximum covered-hole count (the chamber's fully-closed note),
// cached, used to derive how many holes are open for a given note.
let chamberMaxCover = null;
function getChamberMaxCover() {
  const notes = window.NOTES, chamberOf = window.CHAMBER, cover = window.COVER;
  if (!notes || !chamberOf || !cover) return {};
  const key = notes.length + ":" + notes[0];
  if (chamberMaxCover && chamberMaxCover._key === key) return chamberMaxCover;
  const m = { _key: key };
  notes.forEach(id => {
    const ch = chamberOf[id];
    const n = (cover[id] || []).length;
    if (ch == null) return;
    if (m[ch] == null || n > m[ch]) m[ch] = n;
  });
  chamberMaxCover = m;
  return m;
}

// Chamber size (0..1, larger/lower-numbered = 1) and open-hole fraction
// (0 = fully closed, 1 = all open) for a note. Drives both the attack
// softness and the chiff character.
function noteArticulation(id) {
  const chamberOf = window.CHAMBER;
  const ch = chamberOf && chamberOf[id];
  if (ch == null) return { sizeF: 0.5, openF: 0.5 };
  const chambers = Object.keys((window.FING && FING.chambers) || { 1: 1 }).map(Number);
  const maxCh = Math.max(...chambers, ch);
  const sizeF = maxCh > 1 ? (maxCh - ch) / (maxCh - 1) : 1;
  const maxCover = getChamberMaxCover()[ch] || 0;
  const openF = maxCover > 0
    ? Math.max(0, Math.min(1, 1 - (window.COVER[id] || []).length / maxCover))
    : 0;
  return { sizeF, openF };
}

// "Attack effort" (0..1) shaping the onset softness / pitch overshoot.
// Larger (lower-numbered) chambers build air pressure more slowly → bigger
// overshoot and longer attack; within a chamber, MORE OPEN HOLES increase it
// further. Returns ~0 for the smallest chamber fully closed, ~1 for the
// largest chamber wide open.
function attackEffort(id, freq) {
  const { sizeF, openF } = noteArticulation(id);
  // Weighted blend: chamber size dominates, open holes modulate within it.
  return Math.max(0, Math.min(1, 0.6 * sizeF + 0.4 * openF));
}

// Short white-noise buffer reused for chiff bursts.
let chiffBuf = null;
function getChiffBuffer(ctx) {
  if (chiffBuf && chiffBuf.sampleRate === ctx.sampleRate) return chiffBuf;
  const len = Math.floor(ctx.sampleRate * 0.5);
  const buf = ctx.createBuffer(1, len, ctx.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
  chiffBuf = buf;
  return buf;
}

function cutLive() {
  liveVoices.forEach(n => { try { (n.fade || n.stop)(); } catch (e) {} });
  liveVoices = [];
}

function playNote(id, durSec) {
  cutLive();
  playNoteAt(id, null, durSec == null ? tokenSeconds(4) : durSec, liveVoices);
}

function playNoteAt(id, when, durSec, bag, slideFromId) {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
    const ctx = audioCtx;
    const t0 = when == null ? ctx.currentTime : when;
    const freq = freqOf(id);
    const dur = Math.max(0.12, durSec);
    const slideFrom = slideFromId && slideFromId !== id ? freqOf(slideFromId) : 0;
    const rel = Math.min(0.18, Math.max(0.05, dur * 0.35)); // ~50–180ms taper
    const relStart = Math.max(0.02, dur - rel);
    const tail = 0.03;
    const master = ctx.createGain();
    // Tone speaks slightly after onset (breathy pre-tone → full), pairing with
    // the pitch "catch up" bloom below for a soft ocarina attack. Larger
    // chambers + more open holes build pressure slower → a longer, softer
    // attack (see attackEffort). The big bass chamber is especially demanding:
    // the pure tone takes noticeably longer to reach full equilibrium.
    const art = noteArticulation(id);
    const effort = attackEffort(id, freq);
    const speak = Math.min(0.05, Math.max(0.006, dur * 0.08)) * (0.5 + effort);
    const equilib = Math.min(dur * 0.4, art.sizeF * art.sizeF * 0.16); // big chamber = slow to settle
    const t1 = t0 + speak * 0.5;
    const t2 = t0 + speak + 0.015;
    // Ensure the final "equilibrium" ramp has a real duration but also finishes
    // BEFORE the release begins. When equilib≈0 (high chamber) t3 would equal t2
    // (instant jump → click); when the note is short & high-effort (e.g. D5/16)
    // an unclamped t3 would land after relStart, creating out-of-order gain
    // automation (another click). Clamp into (t2, relStart).
    const relStartT = t0 + relStart;
    const t3 = Math.min(relStartT - 0.005, Math.max(t2 + 0.015, t2 + equilib));
    master.gain.setValueAtTime(0.0001, t0);
    master.gain.linearRampToValueAtTime(0.05, t1); // breathy pre-tone
    if (t3 > t2 + 0.001) {
      master.gain.linearRampToValueAtTime(0.16, t2); // tone begins to speak
      master.gain.linearRampToValueAtTime(0.26, t3); // reaches full equilibrium
    } else {
      // Very short note: no room for the two-stage climb; go straight to full
      // by t2 so the automation stays monotonic and click-free.
      master.gain.linearRampToValueAtTime(0.26, Math.min(t2, relStartT - 0.003));
    }
    master.gain.setValueAtTime(0.26, relStartT);
    master.gain.linearRampToValueAtTime(0.0001, t0 + dur);
    master.gain.setValueAtTime(0.0001, t0 + dur + tail);
    master.connect(getReverbBus(ctx));

    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.setValueAtTime(Math.min(2800, Math.max(freq, slideFrom || freq) * 4.2), t0);
    lp.Q.value = 0.7;
    // Tremolo node: vibrato modulates breath pressure, which on a Helmholtz
    // resonator changes pitch AND loudness together (in phase). The tone runs
    // through `trem` so the same LFO can add a small amplitude wobble; its
    // depth is driven below, in phase with the pitch vibrato.
    const trem = ctx.createGain();
    trem.gain.value = 1;
    lp.connect(trem);
    trem.connect(master);

    const wave = ctx.createPeriodicWave(
      new Float32Array([0, 1, 0.06, 0.03, 0.012, 0.006]),
      new Float32Array([0, 0, 0, 0, 0, 0])
    );
    const osc = ctx.createOscillator();
    osc.setPeriodicWave(wave);
    if (slideFrom) {
      const glide = Math.min(Math.max(0.03, dur * 0.22), 0.1);
      osc.frequency.setValueAtTime(slideFrom, t0);
      osc.frequency.linearRampToValueAtTime(freq, t0 + glide);
    } else {
      // Airflow "catch up" onset: the pitch begins slightly flat and blooms
      // to target with a tiny overshoot — a brief breath chiff, NOT a long
      // pitch slide (that reads as brass). The pitch locks in fast (~15–30ms)
      // even on high-effort notes; effort mainly shapes the softer AMPLITUDE
      // attack (see `speak` above), not a long glide.
      const rise = Math.min(0.03, Math.max(0.01, dur * 0.12)) * (0.7 + 0.3 * effort);
      const flat = 0.993 - 0.007 * effort;  // start pitch: 0.7%–1.4% flat
      const over = 1.002 + 0.004 * effort;  // overshoot: 0.2%–0.6% sharp
      const overshootAt = t0 + rise;
      const settleAt = overshootAt + rise * 0.9;
      osc.frequency.setValueAtTime(freq * flat, t0);            // starts flat (air slow)
      osc.frequency.linearRampToValueAtTime(freq * over, overshootAt); // overshoot sharp
      osc.frequency.exponentialRampToValueAtTime(freq, settleAt);      // settle to pitch
      // Release pitch sag: as breath pressure falls at the end of the note the
      // pitch bends flat — a subtle downward "sigh". Scaled by effort/chamber
      // so bigger chambers sag a touch more. Only if the note is long enough to
      // have settled first.
      if (relStart > settleAt + 0.02) {
        const sag = 0.01 + 0.008 * effort; // ~17–31 cents flat over the release
        osc.frequency.setValueAtTime(freq, relStart);
        osc.frequency.linearRampToValueAtTime(freq * (1 - sag), t0 + dur);
      }
    }
    osc.connect(lp);
    osc.start(t0);
    osc.stop(t0 + dur + tail);

    // Faint inharmonic "air" partial: a quiet, slightly detuned sine just
    // above the 2nd harmonic adds breathy shimmer without muddying pitch.
    const air = ctx.createOscillator();
    air.type = "sine";
    air.frequency.setValueAtTime(freq * 2.01, t0);
    const airGain = ctx.createGain();
    airGain.gain.setValueAtTime(0.0001, t0);
    airGain.gain.linearRampToValueAtTime(0.02, t0 + 0.03);
    airGain.gain.setValueAtTime(0.02, t0 + relStart);
    airGain.gain.linearRampToValueAtTime(0.0001, t0 + dur);
    air.connect(airGain); airGain.connect(lp);
    air.start(t0);
    air.stop(t0 + dur + tail);

    // Gentle vibrato (~5.5 Hz), only on SUSTAINED notes: it begins after a
    // fixed settle delay, so short/fast notes end before it starts. Breath
    // vibrato couples PITCH and LOUDNESS in phase (harder blow = sharper AND
    // louder), so the same LFO drives both osc.frequency and the tremolo gain.
    const VIB_DELAY = 0.35;
    const lfo = ctx.createOscillator();
    lfo.type = "sine";
    lfo.frequency.value = 5.5;
    const lfoGain = ctx.createGain();     // pitch depth
    const tremGain = ctx.createGain();    // amplitude depth (in phase)
    // Only wire up vibrato if the note is long enough to reach the sustain.
    if (dur > VIB_DELAY + 0.1) {
      const vibDepth = freq * 0.0035; // ~6 cents peak (subtler)
      const tremDepth = 0.05;         // ~5% loudness wobble, in phase with pitch
      lfoGain.gain.setValueAtTime(0.0001, t0);
      lfoGain.gain.setValueAtTime(0.0001, t0 + VIB_DELAY);
      lfoGain.gain.linearRampToValueAtTime(vibDepth, t0 + VIB_DELAY + 0.2);
      tremGain.gain.setValueAtTime(0.0001, t0);
      tremGain.gain.setValueAtTime(0.0001, t0 + VIB_DELAY);
      tremGain.gain.linearRampToValueAtTime(tremDepth, t0 + VIB_DELAY + 0.2);
    } else {
      lfoGain.gain.setValueAtTime(0.0001, t0);
      tremGain.gain.setValueAtTime(0.0001, t0);
    }
    lfo.connect(lfoGain);
    lfoGain.connect(osc.frequency);
    lfo.connect(tremGain);
    tremGain.connect(trem.gain);
    lfo.start(t0);
    lfo.stop(t0 + dur + tail);

    // Chamber-relative "blowing effort": rises toward the top of each chamber
    // and resets at the next, so a higher note within a chamber is breathier.
    // Drives the edge-whistle level below.
    const reg = chamberReg(id, freq);

    // Edge / windway whistle: the jet crossing the labium sings a faint,
    // breathy tone slightly SHARP of the fundamental, with a little pitch
    // instability. This is the characteristic hollow "whispered pitch" of a
    // fipple/vessel flute. It grows with blowing effort (reg).
    const edge = ctx.createOscillator();
    edge.type = "sine";
    const detune = 1.012 + Math.random() * 0.008; // ~20–34 cents sharp: breathy, not sour
    edge.frequency.setValueAtTime(freq * detune, t0);
    // Slow, subtle wander so it doesn't sound like a locked pure tone.
    const wander = ctx.createOscillator();
    wander.type = "sine";
    wander.frequency.value = 7 + Math.random() * 4;
    const wanderGain = ctx.createGain();
    wanderGain.gain.value = freq * 0.006;
    wander.connect(wanderGain); wanderGain.connect(edge.frequency);
    const edgeGain = ctx.createGain();
    const edgeLevel = 0.035 + reg * reg * 0.022; // ~0.035 low → ~0.057 high (gentler climb)
    edgeGain.gain.setValueAtTime(0.0001, t0);
    edgeGain.gain.linearRampToValueAtTime(edgeLevel, t0 + 0.03);
    edgeGain.gain.setValueAtTime(edgeLevel, t0 + relStart);
    edgeGain.gain.linearRampToValueAtTime(0.0001, t0 + dur);
    // A little breathiness on the whistle itself via a gentle bandpass.
    const edgeBp = ctx.createBiquadFilter();
    edgeBp.type = "bandpass";
    edgeBp.frequency.value = freq * detune;
    edgeBp.Q.value = 4;
    edge.connect(edgeBp); edgeBp.connect(edgeGain); edgeGain.connect(master);
    edge.start(t0); edge.stop(t0 + dur + tail);
    wander.start(t0); wander.stop(t0 + dur + tail);

    // Dry-clay CHIFF: the tongued onset is a noise burst that "focuses" as the
    // Helmholtz cavity catches the jet. Its color is set by chamber size: big
    // (bass) chambers give a dark, muffled, longer "phh"; small chambers a
    // bright, airy "tss". More open holes = leakier, brighter, breathier.
    const { sizeF: chSize, openF: chOpen } = art;
    // Cap to the note's release start so the chiff always fades to zero before
    // `master` cuts the note. On short notes (fast 16ths) an uncapped chiff is
    // still at high level when master fades at t0+dur → truncation click.
    const chiffLen = Math.min((0.11 + chSize * 0.24) * (0.85 + 0.15 * chOpen), relStart - 0.005);
    // Chamber character comes from WHERE the noise energy sits. A big (bass)
    // chamber is a dark, muffled "phh"; a small chamber a bright, airy "tss".
    // Use a resonant lowpass with a strongly chamber-dependent cutoff and a
    // wide spread so the timbres are clearly distinct, sweeping down as the
    // cavity focuses. `bright` spans ~4 octaves between largest & smallest.
    const bright = Math.min(9, Math.pow(2, (1 - chSize) * 3.5 + chOpen * 1.2)); // ~1x (big) → capped ~9x
    const startHz = Math.min(11000, 900 * bright);   // broad/high at onset
    const endHz = Math.min(9000, 500 * bright);      // settles, still chamber-colored
    const chiffSrc = ctx.createBufferSource();
    chiffSrc.buffer = getChiffBuffer(ctx);
    const chiffHp = ctx.createBiquadFilter();
    chiffHp.type = "highpass";
    chiffHp.frequency.value = Math.max(300, 300 * bright * 0.4); // trim low rumble; floor keeps it airy not rumbly
    const chiffLp = ctx.createBiquadFilter();
    chiffLp.type = "lowpass";
    chiffLp.Q.value = 0.4; // non-resonant: avoids a chirp/ring on bright high-chamber sweeps
    chiffLp.frequency.setValueAtTime(startHz, t0);
    chiffLp.frequency.exponentialRampToValueAtTime(endHz, t0 + chiffLen * 0.6);
    const chiffGain = ctx.createGain();
    const chiffPeak = 0.018 - 0.0812 * chSize + 0.1412 * chSize * chSize; // low strong, mid softest, high modest
    // Gentle attack, then a sustain-and-decay so the breathy onset lingers as
    // the tone establishes. The tail uses a linear ramp that actually reaches
    // zero (exponential ramps never do) with a small guard before the source
    // stops, avoiding a truncation click that reads as "clipping" on short
    // (high-chamber) bursts.
    const chAtk = Math.max(0.012, Math.min(0.025, chiffLen * 0.3)); // softer attack, min 12ms
    chiffGain.gain.setValueAtTime(0.0001, t0);
    chiffGain.gain.linearRampToValueAtTime(chiffPeak, t0 + chAtk);
    chiffGain.gain.linearRampToValueAtTime(chiffPeak * 0.85, t0 + chiffLen * 0.5);
    chiffGain.gain.linearRampToValueAtTime(0.0, t0 + chiffLen); // reach true zero
    chiffSrc.connect(chiffHp); chiffHp.connect(chiffLp); chiffLp.connect(chiffGain); chiffGain.connect(master);
    chiffSrc.start(t0); chiffSrc.stop(t0 + chiffLen + 0.02);
    if (bag) {
      bag.push({
        stop() { try { osc.stop(); } catch (e) {} try { lfo.stop(); } catch (e) {} try { air.stop(); } catch (e) {} try { edge.stop(); } catch (e) {} try { wander.stop(); } catch (e) {} try { chiffSrc.stop(); } catch (e) {} },
        fade() {
          const now = ctx.currentTime;
          try {
            master.gain.cancelScheduledValues(now);
            master.gain.setValueAtTime(Math.max(0.0001, master.gain.value || 0.26), now);
            master.gain.linearRampToValueAtTime(0.0001, now + 0.03);
            osc.stop(now + 0.05);
            lfo.stop(now + 0.05);
            air.stop(now + 0.05);
            edge.stop(now + 0.05);
            wander.stop(now + 0.05);
            try { chiffSrc.stop(now + 0.05); } catch (e) {}
          } catch (e) {}
        }
      });
    }
  } catch (e) {}
}

function tickEnabled() {
  const cb = document.getElementById("tickMel");
  return !!(cb && cb.checked);
}

function playTickAt(when, bag) {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
    const ctx = audioCtx;
    const t0 = when == null ? ctx.currentTime : when;
    const dur = 0.04;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.linearRampToValueAtTime(0.09, t0 + 0.002);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    g.connect(ctx.destination);
    const osc = ctx.createOscillator();
    osc.type = "square";
    osc.frequency.setValueAtTime(1600, t0);
    osc.connect(g);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
    if (bag) bag.push({ stop() { try { osc.stop(); } catch (e) {} } });
  } catch (e) {}
}

function isMelodyPlaying() { return melodyPlaying; }function isMelodyPaused() { return melodyPaused; }

function stopMelody() {
  melodyPlaying = false;
  melodyPaused = false;
  melodyBag.forEach(n => { try { (n.fade || n.stop)(); } catch (e) {} });
  melodyBag = [];
  if (melodyTimer) { clearTimeout(melodyTimer); melodyTimer = 0; }
  if (typeof freezeZenGlow === "function") freezeZenGlow();
  const btn = document.getElementById("playMel");
  if (btn) btn.textContent = "Play";
  clearHighlight();
  if (typeof cueFirstNote === "function") cueFirstNote();
  syncTransport();
}

function playMelody(fromIdx) {
  const from = (typeof fromIdx === "number") ? fromIdx : 0;
  if (typeof fromIdx !== "number" && melodyPlaying) { stopMelody(); return; }
  stopMelody();
  cutLive();
  melodyTokens = parse(document.getElementById("src").value);
  melodyIdx = from;
  melodyFrom = from;
  melodyHoldUntil = -1;
  melodyPaused = false;
  melodyPos = gridBeatsBefore(melodyTokens, melodyIdx);
  if (!melodyTokens.length) return;
  audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === "suspended") audioCtx.resume();
  melodyPlaying = true;
  const btn = document.getElementById("playMel");
  if (btn) btn.textContent = "Stop";
  syncTransport();
  scheduleMelody(audioCtx.currentTime + 0.05);
}

function pauseMelody() {
  if (!melodyPlaying) return;
  melodyPlaying = false;
  melodyPaused = true;
  melodyBag.forEach(n => { try { (n.fade || n.stop)(); } catch (e) {} });
  melodyBag = [];
  if (melodyTimer) { clearTimeout(melodyTimer); melodyTimer = 0; }
  if (typeof freezeZenGlow === "function") freezeZenGlow();
  const btn = document.getElementById("playMel");
  if (btn) btn.textContent = "Play";
  syncTransport();
}

function resumeMelody() {
  if (melodyPlaying || !melodyPaused || !melodyTokens.length) { melodyPaused = false; return; }
  melodyPaused = false;
  audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === "suspended") audioCtx.resume();
  melodyPlaying = true;
  const btn = document.getElementById("playMel");
  if (btn) btn.textContent = "Stop";
  syncTransport();
  scheduleMelody(audioCtx.currentTime + 0.05);
}

function togglePlayPause() {
  if (melodyPlaying) pauseMelody();
  else if (melodyPaused) resumeMelody();
  else playMelody();
}

function rewindMelody() {
  const wasActive = melodyPlaying || melodyPaused;
  stopMelody();
  if (wasActive) { playMelody(0); return; }
  const toks = parse(document.getElementById("src").value);
  if (!toks.length) return;
  if (typeof firstSoundIdx === "function" && typeof highlightToken === "function") {
    highlightToken(firstSoundIdx(toks), null);
  }
}

function scheduleMelody(when) {
  if (!melodyPlaying) return;
  let atBar = (melodyIdx === melodyFrom);
  while (melodyIdx < melodyTokens.length && melodyTokens[melodyIdx].type === "bar") { melodyIdx++; atBar = true; }
  if (melodyIdx >= melodyTokens.length) {
    if (document.getElementById("loopMel") && document.getElementById("loopMel").checked) {
      melodyIdx = 0;
      while (melodyIdx < melodyTokens.length && melodyTokens[melodyIdx].type === "bar") melodyIdx++;
      if (melodyIdx >= melodyTokens.length) { stopMelody(); return; }
      melodyPos = 0;
      melodyHoldUntil = -1;
      atBar = true;
    } else { stopMelody(); return; }
  }
  if (atBar && tickEnabled()) playTickAt(when, melodyBag);
  const tok = melodyTokens[melodyIdx];
  const step = swungBeats(tok, melodyPos) * quarterSec();
  melodyPos += tokenGridBeats(tok);
  const pitched = (tok.type === "note" || tok.type === "tie") && NOTES.includes(tok.id);
  let didSound = false;
  if (pitched && melodyIdx > melodyHoldUntil) {
    const hold = soundingGridBeats(melodyTokens, melodyIdx) * quarterSec();
    const slideFrom = (tok.slide && NOTES.includes(tok.slideFrom)) ? tok.slideFrom : null;
    // Staccato: sound only a short portion of the slot, leaving an audible gap
    // (an implied pause) before the next note. Never applies to slurred/tied notes.
    const soundHold = tok.staccato
      ? Math.min(hold * 0.4, 0.16)
      : hold * 0.92;
    playNoteAt(tok.id, when, Math.max(0.09, soundHold), melodyBag, slideFrom);
    melodyHoldUntil = lastHoldIndex(melodyTokens, melodyIdx);
    lastHoldSec = Math.max(0.09, soundHold);
    didSound = true;
  }
  const hlIdx = melodyIdx, hlId = tok.id, hlDur = lastHoldSec, hlSound = didSound;
  const hlDelay = Math.max(0, (when - audioCtx.currentTime) * 1000);
  setTimeout(() => { if (melodyPlaying) highlightToken(hlIdx, hlId, hlDur, hlSound); }, hlDelay);
  melodyIdx++;
  const nextWhen = when + step;
  const LOOKAHEAD = 0.08;
  melodyTimer = setTimeout(() => {
    scheduleMelody(Math.max(audioCtx.currentTime, nextWhen));
  }, Math.max(0, (nextWhen - audioCtx.currentTime - LOOKAHEAD) * 1000));
}
