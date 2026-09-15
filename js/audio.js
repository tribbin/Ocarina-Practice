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

function unlockAudio() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
  } catch (e) {}
}

["pointerdown","keydown","touchstart"].forEach(ev =>
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

function cutLive() {
  liveVoices.forEach(n => { try { (n.fade || n.stop)(); } catch (e) {} });
  liveVoices = [];
}

function playNote(id, durSec) {
  cutLive();
  playNoteAt(id, null, durSec == null ? tokenSeconds(4) : durSec, liveVoices);
}

function playNoteAt(id, when, durSec, bag) {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
    const ctx = audioCtx;
    const t0 = when == null ? ctx.currentTime : when;
    const freq = freqOf(id);
    const dur = Math.max(0.12, durSec);
    const master = ctx.createGain();
    master.gain.setValueAtTime(0.0001, t0);
    master.gain.linearRampToValueAtTime(0.26, t0 + 0.02);
    master.gain.setValueAtTime(0.26, t0 + Math.max(0.03, dur - 0.04));
    master.gain.linearRampToValueAtTime(0.0001, t0 + dur);
    master.connect(ctx.destination);

    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.setValueAtTime(Math.min(2800, freq * 4.2), t0);
    lp.Q.value = 0.7;
    lp.connect(master);

    const wave = ctx.createPeriodicWave(
      new Float32Array([0, 1, 0.07, 0.03, 0.012, 0.006]),
      new Float32Array([0, 0, 0, 0, 0, 0])
    );
    const osc = ctx.createOscillator();
    osc.setPeriodicWave(wave);
    osc.frequency.setValueAtTime(freq * 0.992, t0);
    osc.frequency.exponentialRampToValueAtTime(freq, t0 + 0.04);
    osc.connect(lp);
    osc.start(t0);
    osc.stop(t0 + dur);

    const nLen = Math.max(1, Math.floor(ctx.sampleRate * dur));
    const nBuf = ctx.createBuffer(1, nLen, ctx.sampleRate);
    const data = nBuf.getChannelData(0);
    for (let i = 0; i < nLen; i++) data[i] = Math.random() * 2 - 1;
    const noise = ctx.createBufferSource();
    noise.buffer = nBuf;
    const hp = ctx.createBiquadFilter();
    hp.type = "highpass";
    hp.frequency.value = 1200;
    const ng = ctx.createGain();
    ng.gain.setValueAtTime(0.0001, t0);
    ng.gain.exponentialRampToValueAtTime(0.045, t0 + 0.02);
    ng.gain.exponentialRampToValueAtTime(0.012, t0 + Math.min(0.12, dur * 0.2));
    ng.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    noise.connect(hp); hp.connect(ng); ng.connect(lp);
    noise.start(t0);
    noise.stop(t0 + dur);
    if (bag) {
      bag.push({
        stop() { try { osc.stop(); } catch (e) {} try { noise.stop(); } catch (e) {} },
        fade() {
          const now = ctx.currentTime;
          try {
            master.gain.cancelScheduledValues(now);
            master.gain.setValueAtTime(Math.max(0.0001, master.gain.value || 0.26), now);
            master.gain.linearRampToValueAtTime(0.0001, now + 0.03);
            osc.stop(now + 0.05);
            noise.stop(now + 0.05);
          } catch (e) {}
        }
      });
    }
  } catch (e) {}
}

function isMelodyPlaying() { return melodyPlaying; }
function isMelodyPaused() { return melodyPaused; }

function stopMelody() {
  melodyPlaying = false;
  melodyPaused = false;
  melodyBag.forEach(n => { try { (n.fade || n.stop)(); } catch (e) {} });
  melodyBag = [];
  if (melodyTimer) { clearTimeout(melodyTimer); melodyTimer = 0; }
  const btn = document.getElementById("playMel");
  if (btn) btn.textContent = "Play";
  clearHighlight();
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
  while (melodyIdx < melodyTokens.length && melodyTokens[melodyIdx].type === "bar") melodyIdx++;
  if (melodyIdx >= melodyTokens.length) {
    if (document.getElementById("loopMel") && document.getElementById("loopMel").checked) {
      melodyIdx = 0;
      while (melodyIdx < melodyTokens.length && melodyTokens[melodyIdx].type === "bar") melodyIdx++;
      if (melodyIdx >= melodyTokens.length) { stopMelody(); return; }
      melodyPos = 0;
      melodyHoldUntil = -1;
    } else { stopMelody(); return; }
  }
  const tok = melodyTokens[melodyIdx];
  highlightToken(melodyIdx, tok.id);
  const step = swungBeats(tok, melodyPos) * quarterSec();
  melodyPos += tokenGridBeats(tok);
  const pitched = (tok.type === "note" || tok.type === "tie") && NOTES.includes(tok.id);
  if (pitched && melodyIdx > melodyHoldUntil) {
    const hold = soundingGridBeats(melodyTokens, melodyIdx) * quarterSec();
    playNoteAt(tok.id, when, Math.max(0.12, hold * 0.92), melodyBag);
    melodyHoldUntil = lastHoldIndex(melodyTokens, melodyIdx);
  }
  melodyIdx++;
  const nextWhen = when + step;
  melodyTimer = setTimeout(() => {
    scheduleMelody(Math.max(audioCtx.currentTime, nextWhen));
  }, Math.max(0, (nextWhen - audioCtx.currentTime) * 1000));
}
